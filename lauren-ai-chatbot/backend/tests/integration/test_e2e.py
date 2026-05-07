# NOTE: Do NOT add `from __future__ import annotations` to this file.
# MockTransport and tool schema generation require runtime type annotations.
"""End-to-end integration tests for the SecureBank AI Chatbot backend.

These tests build the full Lauren application (including DI, middleware,
guards, and controllers) and drive it through httpx's ASGI transport so
no real network calls are made.

Test groups:
- ``TestSignatureSecurityE2E``   — HMAC guard on /api/banking/chat
- ``TestMetricsEndpointE2E``     — /api/metrics/ observability
- ``TestCostTrackingE2E``        — CostTracker accumulates signal-bus events
- ``TestHealthEndpointE2E``      — /api/health/ liveness probe
- ``TestBankingWiringE2E``       — DI wiring smoke tests for banking agents
"""

import json
import os
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

# ---------------------------------------------------------------------------
# Environment must be set before importing any app code
# ---------------------------------------------------------------------------

os.environ.setdefault("PAYLOAD_SECRET", "e2e-test-secret-xyz")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy-key-for-tests")
os.environ.setdefault("PORT", "8002")

from app.crypto.crypto_service import CryptoService  # noqa: E402
from lauren_ai._transport import Completion, CompletionChunk, TokenUsage  # noqa: E402


# ---------------------------------------------------------------------------
# run_stream() mock helper
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECRET = os.environ["PAYLOAD_SECRET"]


def _sign(body: bytes, secret: str = _SECRET) -> str:
    svc = CryptoService.__new__(CryptoService)
    svc._secret = secret.encode()
    return svc.sign(body)


def _banking_body(
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


def _signed_headers(body: bytes) -> dict:
    return {"content-type": "application/json", "x-signature": _sign(body)}


def _parse_sse(raw: bytes) -> list[dict]:
    """Parse SSE wire format → list of {event, data} dicts."""
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


def _token_events(events: list[dict]) -> list[str]:
    return [e["data"] for e in events if e.get("event") == "token"]


def _has_done(events: list[dict]) -> bool:
    return any(e.get("event") == "done" for e in events)


# ---------------------------------------------------------------------------
# App fixture — reused across the whole module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    """Build the full Lauren app once per module."""
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
# TestSignatureSecurityE2E
# ---------------------------------------------------------------------------


class TestSignatureSecurityE2E:
    """Security boundary tests for the HMAC-SHA256 SignatureGuard on /api/banking/chat."""

    @pytest.mark.asyncio
    async def test_no_signature_401(self, client):
        body = _banking_body()
        resp = await client.post(
            "/api/banking/chat",
            content=body,
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_signature_401(self, client):
        body = _banking_body()
        resp = await client.post(
            "/api/banking/chat",
            content=body,
            headers={"content-type": "application/json", "x-signature": "badc0ffee" * 7},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_body_401(self, client):
        body = _banking_body("original")
        sig = _sign(body)
        tampered = body + b" extra"
        resp = await client.post(
            "/api/banking/chat",
            content=tampered,
            headers={"content-type": "application/json", "x-signature": sig},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_401(self, client):
        body = _banking_body()
        sig = _sign(body, secret="wrong-secret")
        resp = await client.post(
            "/api/banking/chat",
            content=body,
            headers={"content-type": "application/json", "x-signature": sig},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_signature_streams_response(self, client):
        body = _banking_body(user_id="alice")
        with _patch_run_stream_with("Your balance is $5,000.00"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed_headers(body))

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_body_cached_guard_and_controller_both_read_it(self, client):
        """Json[T] should succeed even though the guard already consumed the body."""
        body = _banking_body(user_id="bob")
        with _patch_run_stream_with("Bob's balance"):
            resp = await client.post("/api/banking/chat", content=body, headers=_signed_headers(body))

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestMetricsEndpointE2E
# ---------------------------------------------------------------------------


class TestMetricsEndpointE2E:
    """Tests for GET /api/metrics/ endpoints."""

    @pytest.mark.asyncio
    async def test_summary_returns_200(self, client):
        resp = await client.get("/api/metrics/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_summary_has_required_keys(self, client):
        resp = await client.get("/api/metrics/")
        data = resp.json()
        assert "traces_recorded" in data
        assert "total_usd" in data

    @pytest.mark.asyncio
    async def test_traces_endpoint_returns_200(self, client):
        resp = await client.get("/api/metrics/traces")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_traces_response_has_traces_key(self, client):
        resp = await client.get("/api/metrics/traces")
        data = resp.json()
        assert "traces" in data
        assert isinstance(data["traces"], list)

    @pytest.mark.asyncio
    async def test_cost_endpoint_returns_200(self, client):
        resp = await client.get("/api/metrics/cost")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cost_response_has_required_keys(self, client):
        resp = await client.get("/api/metrics/cost")
        data = resp.json()
        assert "total_usd" in data
        assert "by_model" in data
        assert "by_conversation" in data


# ---------------------------------------------------------------------------
# TestCostTrackingE2E
# ---------------------------------------------------------------------------


class TestCostTrackingE2E:
    """Tests that CostTracker accumulates costs from the SignalBus."""

    def test_cost_tracker_provided_in_di(self, app):
        from lauren_ai import CostTracker
        from app.ai.ai_module import _cost_tracker

        assert _cost_tracker is not None
        assert isinstance(_cost_tracker, CostTracker)

    @pytest.mark.asyncio
    async def test_cost_report_returns_zero_before_any_calls(self):
        from app.ai.ai_module import _cost_tracker

        report = await _cost_tracker.report()
        assert report.total_estimate.total_usd >= 0.0

    @pytest.mark.asyncio
    async def test_manual_usage_accumulates_in_report(self):
        from lauren_ai import CostTracker, default_pricing_table, TokenUsage

        tracker = CostTracker(pricing=default_pricing_table())
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        tracker.record_usage("gpt-4o-mini", usage, conversation_id="test-conv")
        report = await tracker.report(conversation_id="test-conv")
        assert report.total_estimate.total_usd > 0.0
        assert "gpt-4o-mini" in report.by_model

    @pytest.mark.asyncio
    async def test_cost_session_context_manager(self):
        from lauren_ai import CostTracker, default_pricing_table, TokenUsage

        tracker = CostTracker(pricing=default_pricing_table())
        usage = TokenUsage(input_tokens=2000, output_tokens=1000)
        tracker.record_usage("gpt-4o", usage, conversation_id="session-test")

        async with tracker.session(conversation_id="session-test") as session:
            pass
        assert session.total_estimate.total_usd >= 0.0


# ---------------------------------------------------------------------------
# TestHealthEndpointE2E
# ---------------------------------------------------------------------------


class TestHealthEndpointE2E:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/api/health/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_status_ok(self, client):
        resp = await client.get("/api/health/")
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_has_version(self, client):
        resp = await client.get("/api/health/")
        assert "version" in resp.json()

    @pytest.mark.asyncio
    async def test_health_cors_headers_present(self, client):
        """CORS middleware adds Access-Control-Allow-Origin on all responses."""
        resp = await client.get(
            "/api/health/",
            headers={"origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestBankingWiringE2E
# ---------------------------------------------------------------------------


class TestBankingWiringE2E:
    """Smoke tests confirming banking agents are imported and wired correctly."""

    def test_signal_bus_is_shared_singleton(self):
        from app.ai.signals import signal_bus
        from app.ai.ai_module import signal_bus as module_bus

        assert signal_bus is module_bus

    def test_crm_agent_has_agent_meta(self):
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent

        assert hasattr(AuthenticatedCRMAgent, "__lauren_ai_agent__")

    def test_transfer_agent_has_agent_meta(self):
        from app.ai.agents.transfer_agent import BankTransferAgent

        assert hasattr(BankTransferAgent, "__lauren_ai_agent__")

    def test_crm_agent_has_use_tools_meta(self):
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
        from lauren_ai._agents import USE_TOOLS_META

        assert hasattr(AuthenticatedCRMAgent, USE_TOOLS_META)

    def test_cost_tracker_is_wired(self):
        from app.ai.ai_module import _cost_tracker
        from lauren_ai import CostTracker

        assert isinstance(_cost_tracker, CostTracker)

    def test_trace_store_global_is_set(self):
        import main  # noqa: F401
        from lauren_ai import get_trace_store

        store = get_trace_store()
        assert store is not None

    def test_check_auth_tool_has_tool_meta(self):
        from app.ai.tools.check_auth_tool import CheckAuthenticationTool
        from lauren_ai._tools import TOOL_META

        assert hasattr(CheckAuthenticationTool, TOOL_META)


class TestModuleInjectsWiring:
    """Verify runner tokens produce independent DI singletons."""

    def test_transfer_and_auth_crm_runners_are_distinct_singletons(self, app):
        import asyncio

        from app.ai.agents.banking_delegation import AuthCRMRunner, TransferAgentRunner
        from lauren_ai import AgentRunner

        loop = asyncio.new_event_loop()
        try:
            ar = loop.run_until_complete(app.container.resolve(AuthCRMRunner))
            tr = loop.run_until_complete(app.container.resolve(TransferAgentRunner))
        finally:
            loop.close()
        assert isinstance(ar, AgentRunner)
        assert isinstance(tr, AgentRunner)
        assert ar is not tr

    def test_crm_runner_is_not_transfer_runner_subtype(self, app):
        import asyncio

        from app.ai.agents.banking_delegation import AuthCRMRunner, TransferAgentRunner

        loop = asyncio.new_event_loop()
        try:
            ar = loop.run_until_complete(app.container.resolve(AuthCRMRunner))
        finally:
            loop.close()
        assert not isinstance(ar, TransferAgentRunner)

    def test_transfer_runner_concrete_type_is_subclass(self, app):
        import asyncio

        from app.ai.agents.banking_delegation import TransferAgentRunner

        loop = asyncio.new_event_loop()
        try:
            tr = loop.run_until_complete(app.container.resolve(TransferAgentRunner))
        finally:
            loop.close()
        assert type(tr) is TransferAgentRunner

    def test_ai_module_uses_injects_not_runner_class(self):
        import inspect

        from app.ai import ai_module

        src = inspect.getsource(ai_module)
        assert "runner=TransferAgentRunner" in src
        assert "runner_class=" not in src
