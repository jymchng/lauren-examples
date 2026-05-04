# NOTE: Do NOT add `from __future__ import annotations` to this file.
"""End-to-end tests for POST /api/banking/chat — the BankingChatController."""

import json
import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

os.environ.setdefault("PAYLOAD_SECRET", "banking-e2e-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")
os.environ.setdefault("PORT", "8003")

from app.crypto.crypto_service import CryptoService  # noqa: E402

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
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Signature guard on banking endpoint
# ---------------------------------------------------------------------------

class TestBankingChatSignature:
    @pytest.mark.asyncio
    async def test_missing_signature_returns_401(self, client):
        body = _body()
        resp = await client.post(
            "/api/banking/chat", content=body,
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_signature_returns_401(self, client):
        body = _body()
        resp = await client.post(
            "/api/banking/chat", content=body,
            headers={"content-type": "application/json", "x-signature": "badc0ffee" * 7},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_body_returns_401(self, client):
        body = _body()
        sig = _sign(body)
        resp = await client.post(
            "/api/banking/chat", content=body + b"x",
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
        body = _body(user_id="")
        resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))
        assert resp.status_code == 200
        events = _parse_sse(resp.content)
        assert any(e.get("event") == "error" for e in events)


# ---------------------------------------------------------------------------
# Valid users — streaming behaviour
# ---------------------------------------------------------------------------

class TestBankingChatValidUsers:
    @pytest.mark.asyncio
    async def test_alice_gets_200(self, client):
        body = _body(user_id="alice")
        mock_response = AsyncMock()
        mock_response.content = "Your balance is $5,000.00"

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_bob_gets_200(self, client):
        body = _body(user_id="bob", content="Show my balance")
        mock_response = AsyncMock()
        mock_response.content = "Bob's balance is $3,200.00"

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_charlie_gets_200(self, client):
        body = _body(user_id="charlie", content="How much do I have?")
        mock_response = AsyncMock()
        mock_response.content = "Charlie's balance is $1,800.00"

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_is_event_stream(self, client):
        body = _body(user_id="alice")
        mock_response = AsyncMock()
        mock_response.content = "Hello Alice"

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_tokens_stream_in_chunks(self, client):
        body = _body(user_id="alice")
        mock_response = AsyncMock()
        mock_response.content = "A" * 100  # long enough to produce multiple chunks

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = _parse_sse(resp.content)
        tokens = [e["data"] for e in events if e.get("event") == "token"]
        assert len(tokens) > 1
        assert "".join(tokens) == "A" * 100

    @pytest.mark.asyncio
    async def test_done_event_is_last(self, client):
        body = _body(user_id="alice")
        mock_response = AsyncMock()
        mock_response.content = "Balance: $5,000"

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = [e for e in _parse_sse(resp.content) if "event" in e]
        assert events[-1]["event"] == "done"

    @pytest.mark.asyncio
    async def test_empty_response_yields_only_done(self, client):
        body = _body(user_id="alice")
        mock_response = AsyncMock()
        mock_response.content = ""

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = [e for e in _parse_sse(resp.content) if "event" in e]
        assert events == [{"event": "done", "data": ""}]

    @pytest.mark.asyncio
    async def test_runner_exception_emits_error_event(self, client):
        body = _body(user_id="alice")

        with patch(
            "lauren_ai._agents._runner.AgentRunner.run",
            side_effect=RuntimeError("LLM exploded"),
        ):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        events = _parse_sse(resp.content)
        assert any(e.get("event") == "error" for e in events)

    @pytest.mark.asyncio
    async def test_conversation_id_forwarded_to_runner(self, client):
        body = _body(user_id="alice", conversation_id="conv-123")
        received_kwargs: list[dict] = []

        async def capture(agent, prompt, **kwargs):
            received_kwargs.append(kwargs)
            m = AsyncMock()
            m.content = "ok"
            return m

        with patch("lauren_ai._agents._runner.AgentRunner.run", side_effect=capture):
            await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert received_kwargs[0].get("conversation_id") == "conv-123"

    @pytest.mark.asyncio
    async def test_execution_context_passed_to_runner(self, client):
        """Runner must receive a real ExecutionContext (security anchor)."""
        from lauren.types import ExecutionContext

        body = _body(user_id="alice")
        received_kwargs: list[dict] = []

        async def capture(agent, prompt, **kwargs):
            received_kwargs.append(kwargs)
            m = AsyncMock()
            m.content = "ok"
            return m

        with patch("lauren_ai._agents._runner.AgentRunner.run", side_effect=capture):
            await client.post("/api/banking/chat", content=body, headers=_signed(body))

        exec_ctx = received_kwargs[0].get("execution_context")
        assert exec_ctx is not None
        assert isinstance(exec_ctx, ExecutionContext)

    @pytest.mark.asyncio
    async def test_banking_auth_prefix_injected_in_prompt(self, client):
        """[BANKING_AUTH:...] prefix is prepended to the LLM prompt."""
        body = _body(user_id="alice", content="What is my name?")
        received_prompts: list[str] = []

        async def capture(agent, prompt, **kwargs):
            received_prompts.append(prompt)
            m = AsyncMock()
            m.content = "Alice Johnson"
            return m

        with patch("lauren_ai._agents._runner.AgentRunner.run", side_effect=capture):
            await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert received_prompts
        assert "[BANKING_AUTH:" in received_prompts[0]
        assert "alice" in received_prompts[0].lower()

    @pytest.mark.asyncio
    async def test_x_response_time_header_present(self, client):
        body = _body(user_id="alice")
        mock_response = AsyncMock()
        mock_response.content = "ok"

        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed(body))

        assert "x-response-time" in resp.headers
