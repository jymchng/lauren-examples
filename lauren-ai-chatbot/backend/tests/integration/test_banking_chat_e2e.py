"""End-to-end tests for POST /api/banking/chat — the BankingChatController."""

import json
import os
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

os.environ.setdefault("PAYLOAD_SECRET", "banking-e2e-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")
os.environ.setdefault("PORT", "8003")

from app.crypto.crypto_service import CryptoService  # noqa: E402
from lauren_ai._transport import CompletionChunk, ToolCallDelta, TokenUsage  # noqa: E402

_SECRET = os.environ["PAYLOAD_SECRET"]


def _sign(body: bytes, secret: str = _SECRET) -> str:
    svc = CryptoService.__new__(CryptoService)
    svc._secret = secret.encode()
    return svc.sign(body)


def _body(
    content: str = "What is my balance?",
    user_id: str = "alice",
    conversation_id: str | None = None,
) -> bytes:
    payload: dict = {
        "messages": [{"role": "user", "content": content}],
        "model": "openai/gpt-4o-mini",
        "user_id": user_id,
    }
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    return json.dumps(payload).encode()


def _signed(body: bytes) -> dict:
    return {"content-type": "application/json", "x-signature": _sign(body)}


def _parse_sse(raw: bytes) -> list[dict]:
    events: list[dict] = []
    current: dict = {}
    for line in raw.decode().splitlines():
        if line.startswith("event: "):
            current["event"] = line[7:].strip()
        elif line.startswith("data: "):
            current["data"] = line[6:]
        elif line == "" and current:
            events.append(current)
            current = {}
    return events


# ---------------------------------------------------------------------------
# run_stream() mock helpers
# ---------------------------------------------------------------------------


async def _stream_text(text: str):
    """Async generator yielding text as a single chunk + final stop chunk."""
    if text:
        yield CompletionChunk(delta=text)
    yield CompletionChunk(
        delta="",
        stop_reason="end_turn",
        usage=TokenUsage(input_tokens=10, output_tokens=max(1, len(text) // 4)),
    )


def _patch_run_stream_with(content: str):
    """Patch AgentRunnerBase.run_stream to yield ``content`` as one chunk."""

    async def fake_run_stream(self, agent, prompt, **kwargs):
        return _stream_text(content)

    return patch(
        "lauren_ai._agents._runner.AgentRunnerBase.run_stream",
        new=fake_run_stream,
    )


@pytest.fixture(scope="module")
def app():
    from app.app_module import AppModule
    from app.interceptors.timing_interceptor import TimingInterceptor
    from app.middlewares.cors_middleware import CorsMiddleware
    from app.middlewares.logging_middleware import LoggingMiddleware
    from lauren import LaurenFactory

    return LaurenFactory.create(
        AppModule,
        global_middlewares=[CorsMiddleware, LoggingMiddleware],
        global_interceptors=[TimingInterceptor],
    )


@pytest_asyncio.fixture()
async def client(app):
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Signature guard on banking endpoint
# ---------------------------------------------------------------------------


class TestBankingChatSignature:
    @pytest.mark.asyncio
    async def test_missing_signature_returns_401(self, client):
        body = _body()
        resp = await client.post(
            "/api/banking/chat",
            content=body,
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_signature_returns_401(self, client):
        body = _body()
        resp = await client.post(
            "/api/banking/chat",
            content=body,
            headers={"content-type": "application/json", "x-signature": "badc0ffee" * 7},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_body_returns_401(self, client):
        body = _body()
        sig = _sign(body)
        resp = await client.post(
            "/api/banking/chat",
            content=body + b"x",
            headers={"content-type": "application/json", "x-signature": sig},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Unknown / invalid users
# ---------------------------------------------------------------------------


class TestBankingChatInvalidUsers:
    @pytest.mark.asyncio
    async def test_unknown_user_returns_sse_error_event(self, client):
        body = _body(user_id="dave")
        resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        assert resp.status_code == 200
        events = _parse_sse(resp.content)
        assert any(e.get("event") == "error" for e in events)

    @pytest.mark.asyncio
    async def test_unknown_user_error_mentions_user_id(self, client):
        body = _body(user_id="hacker")
        resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        events = _parse_sse(resp.content)
        error_events = [e for e in events if e.get("event") == "error"]
        assert any("hacker" in e.get("data", "") for e in error_events)

    @pytest.mark.asyncio
    async def test_empty_user_id_rejected(self, client):
        # AuthenticatedUserGuard rejects unauthenticated requests at the HTTP layer.
        body = _body(user_id="")
        resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Valid users — streaming behaviour
# ---------------------------------------------------------------------------


class TestBankingChatValidUsers:
    @pytest.mark.asyncio
    async def test_alice_gets_200(self, client):
        body = _body(user_id="alice")
        with _patch_run_stream_with("Your balance is $5,000.00"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_bob_gets_200(self, client):
        body = _body(user_id="bob", content="Show my balance")
        with _patch_run_stream_with("Bob's balance is $3,200.00"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_charlie_gets_200(self, client):
        body = _body(user_id="charlie", content="How much do I have?")
        with _patch_run_stream_with("Charlie's balance is $1,800.00"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_is_event_stream(self, client):
        body = _body(user_id="alice")
        with _patch_run_stream_with("Hello Alice"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_tokens_stream_in_chunks(self, client):
        body = _body(user_id="alice")
        with _patch_run_stream_with("A" * 100):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = _parse_sse(resp.content)
        tokens = [e["data"] for e in events if e.get("event") == "token"]
        # run_stream yields the mocked content as a single chunk; concatenated
        # tokens equal the original content (real transports deliver many).
        assert "".join(tokens) == "A" * 100

    @pytest.mark.asyncio
    async def test_done_event_is_last(self, client):
        body = _body(user_id="alice")
        with _patch_run_stream_with("Balance: $5,000"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = [e for e in _parse_sse(resp.content) if "event" in e]
        assert events[-1]["event"] == "done"

    @pytest.mark.asyncio
    async def test_empty_response_yields_only_done(self, client):
        body = _body(user_id="alice")
        with _patch_run_stream_with(""):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = [e for e in _parse_sse(resp.content) if "event" in e]
        assert events == [{"event": "done", "data": ""}]

    @pytest.mark.asyncio
    async def test_runner_exception_emits_error_event(self, client):
        body = _body(user_id="alice")

        async def raising_run_stream(self, agent, prompt, **kwargs):
            raise RuntimeError("LLM exploded")

        with patch(
            "lauren_ai._agents._runner.AgentRunnerBase.run_stream",
            new=raising_run_stream,
        ):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = _parse_sse(resp.content)
        assert any(e.get("event") == "error" for e in events)

    @pytest.mark.asyncio
    async def test_conversation_id_forwarded_to_runner(self, client):
        body = _body(user_id="alice", conversation_id="conv-123")
        received_kwargs: list[dict] = []

        async def capture(self, agent, prompt, **kwargs):
            received_kwargs.append(kwargs)
            return _stream_text("ok")

        with patch("lauren_ai._agents._runner.AgentRunnerBase.run_stream", new=capture):
            await client.post("/api/banking/chat", content=body, headers=_signed(body))

        # The controller namespaces the conversation ID per-agent to prevent
        # tool-call history from one agent leaking into the other.
        assert received_kwargs[0].get("conversation_id", "").startswith("conv-123:")

    @pytest.mark.asyncio
    async def test_execution_context_passed_to_runner(self, client):
        """Runner must receive a real ExecutionContext (security anchor)."""
        from lauren.types import ExecutionContext

        body = _body(user_id="alice")
        received_kwargs: list[dict] = []

        async def capture(self, agent, prompt, **kwargs):
            received_kwargs.append(kwargs)
            return _stream_text("ok")

        with patch("lauren_ai._agents._runner.AgentRunnerBase.run_stream", new=capture):
            await client.post("/api/banking/chat", content=body, headers=_signed(body))

        exec_ctx = received_kwargs[0].get("execution_context")
        assert exec_ctx is not None
        assert isinstance(exec_ctx, ExecutionContext)

    @pytest.mark.asyncio
    async def test_banking_auth_prefix_injected_in_prompt(self, client):
        """[BANKING_AUTH:...] prefix is prepended to the LLM prompt."""
        body = _body(user_id="alice", content="What is my name?")
        received_prompts: list[str] = []

        async def capture(self, agent, prompt, **kwargs):
            received_prompts.append(prompt)
            return _stream_text("Alice Johnson")

        with patch("lauren_ai._agents._runner.AgentRunnerBase.run_stream", new=capture):
            await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert received_prompts
        assert "[BANKING_AUTH:" in received_prompts[0]
        assert "alice" in received_prompts[0].lower()

    @pytest.mark.asyncio
    async def test_x_response_time_header_present(self, client):
        body = _body(user_id="alice")
        with _patch_run_stream_with("ok"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert "x-response-time" in resp.headers

    @pytest.mark.asyncio
    async def test_tool_use_event_emitted_when_model_calls_tool(self, client):
        """Each tool call surfaces a tool_use SSE event with the tool name."""
        body = _body(user_id="alice")

        async def fake_run_stream(self, agent, prompt, **kwargs):
            async def gen():
                yield CompletionChunk(
                    tool_call_delta=ToolCallDelta(
                        tool_use_id="tu1",
                        name="get_balance_tool",
                        input_delta="{}",
                    ),
                )
                yield CompletionChunk(
                    delta="",
                    stop_reason="end_turn",
                    usage=TokenUsage(input_tokens=10, output_tokens=2),
                )

            return gen()

        with patch(
            "lauren_ai._agents._runner.AgentRunnerBase.run_stream",
            new=fake_run_stream,
        ):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = _parse_sse(resp.content)
        tool_use_events = [e for e in events if e.get("event") == "tool_use"]
        assert tool_use_events
        assert tool_use_events[0]["data"] == "get_balance_tool"

    @pytest.mark.asyncio
    async def test_two_hop_handoff_crm_response_not_lost(self, client):
        """CRM→Transfer→CRM: three token batches, two breaks, one done (last).

        Regression: the second handoff (Transfer→CRM) was silently dropped
        because generate() only detected one level of handoff.
        """
        from app.ai.tools.active_agent_store import ActiveAgentStore
        from app.ai.agent_names import AUTH_CRM_AGENT_NAME as CRM_AGENT_NAME, TRANSFER_AGENT_NAME

        conv_id = "conv-twohop"
        body = _body(user_id="alice", content="Transfer $100 to bob", conversation_id=conv_id)

        # Simulate get() returning the sequence of active agents.
        # `active` is looked up once before the loop, then after each run:
        #   call 1: before loop → CRM
        #   call 2: after CRM runs → Transfer (handoff detected)
        #   call 3: after Transfer runs → CRM (handoff back detected)
        #   call 4: after CRM 2nd run → CRM (no change — loop exits)
        get_seq = [
            CRM_AGENT_NAME,
            TRANSFER_AGENT_NAME,
            CRM_AGENT_NAME,
            CRM_AGENT_NAME,
        ]
        get_iter = iter(get_seq)
        call_count = 0

        async def mock_run_stream(self, agent, prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                content = "Handing you to Transfer Agent."
            elif call_count == 2:
                content = "Transfer complete. $100 sent to Bob."
            else:
                content = "Transfer confirmed. Anything else I can help with?"
            return _stream_text(content)

        with (
            patch.object(ActiveAgentStore, "get", side_effect=lambda *_: next(get_iter)),
            patch.object(
                ActiveAgentStore,
                "pop_pending_summary",
                return_value="Transfer of $100 to Bob done",
            ),
            patch(
                "lauren_ai._agents._runner.AgentRunnerBase.run_stream",
                new=mock_run_stream,
            ),
        ):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = _parse_sse(resp.content)
        token_data = "".join(e["data"] for e in events if e.get("event") == "token")
        break_events = [e for e in events if e.get("event") == "break"]
        done_events = [e for e in events if e.get("event") == "done"]

        assert "Transfer confirmed" in token_data  # CRM's third response is present
        assert len(break_events) == 2  # two agent switches emitted
        assert len(done_events) == 1  # exactly one done
        assert events[-1]["event"] == "done"  # done is always last
        assert call_count == 3  # all three agents ran
