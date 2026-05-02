"""Integration tests for the chat SSE endpoint.

Mocks ChatService.stream_tokens so the tests don't need a real OpenRouter key.
Verifies the SSE wire format, event types, and streaming behaviour end-to-end.
"""

import json
import os
from typing import AsyncIterator
from unittest.mock import patch, AsyncMock

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

os.environ.setdefault("PAYLOAD_SECRET", "integration-test-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy-key")

from app.crypto.crypto_service import CryptoService

SECRET = os.environ.get("PAYLOAD_SECRET", "integration-test-secret")


def _sign(body: bytes) -> str:
    svc = CryptoService.__new__(CryptoService)
    svc._secret = SECRET.encode()
    return svc.sign(body)


def _chat_body(content: str = "Hello!", model: str = "openai/gpt-4o-mini") -> bytes:
    return json.dumps({
        "messages": [{"role": "user", "content": content}],
        "model": model,
    }).encode()


def _parse_sse(body: bytes) -> list[dict]:
    """Parse SSE wire format into a list of {event, data} dicts."""
    events = []
    current: dict = {}
    for line in body.decode().split("\n"):
        if line.startswith("event: "):
            current["event"] = line[7:].strip()
        elif line.startswith("data: "):
            current["data"] = line[6:]
        elif line == "" and current:
            events.append(current)
            current = {}
        elif line.startswith(": "):
            events.append({"comment": line[2:]})
    return events


async def _fake_stream(*tokens: str):
    for t in tokens:
        yield t


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


class TestChatSseWireFormat:
    @pytest.mark.asyncio
    async def test_sse_content_type(self, client):
        body = _chat_body()
        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=_fake_stream("hi"),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_emits_token_events(self, client):
        body = _chat_body()
        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=_fake_stream("Hello", ", ", "world!"),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        events = _parse_sse(resp.content)
        token_events = [e for e in events if e.get("event") == "token"]
        assert len(token_events) == 3
        assert token_events[0]["data"] == "Hello"
        assert token_events[1]["data"] == ", "
        assert token_events[2]["data"] == "world!"

    @pytest.mark.asyncio
    async def test_emits_done_event_at_end(self, client):
        body = _chat_body()
        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=_fake_stream("A", "B"),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        events = _parse_sse(resp.content)
        done_events = [e for e in events if e.get("event") == "done"]
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_done_event_is_last(self, client):
        body = _chat_body()
        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=_fake_stream("A"),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        events = [e for e in _parse_sse(resp.content) if "event" in e]
        assert events[-1]["event"] == "done"

    @pytest.mark.asyncio
    async def test_empty_stream_just_done(self, client):
        body = _chat_body()

        async def no_tokens():
            return
            yield  # make it an async generator

        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=no_tokens(),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        events = [e for e in _parse_sse(resp.content) if "event" in e]
        assert events == [{"event": "done", "data": ""}]

    @pytest.mark.asyncio
    async def test_error_in_stream_emits_error_event(self, client):
        body = _chat_body()

        async def failing_tokens():
            yield "partial"
            raise RuntimeError("OpenRouter down")

        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=failing_tokens(),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        events = _parse_sse(resp.content)
        named_events = [e for e in events if "event" in e]
        assert any(e["event"] == "error" for e in named_events)

    @pytest.mark.asyncio
    async def test_request_body_parsed_correctly(self, client):
        """Verify the controller deserializes the signed body into ChatRequest."""
        body = _chat_body("specific question", model="anthropic/claude-3-5-haiku")
        captured = []

        async def capture_and_yield(request):
            captured.append(request)
            yield "ok"

        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            side_effect=capture_and_yield,
        ):
            await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        assert captured[0].messages[0].content == "specific question"
        assert captured[0].model == "anthropic/claude-3-5-haiku"


class TestChatSseHeaders:
    @pytest.mark.asyncio
    async def test_cache_control_no_cache(self, client):
        body = _chat_body()
        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=_fake_stream(),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        assert resp.headers.get("cache-control") == "no-cache"

    @pytest.mark.asyncio
    async def test_x_response_time_present(self, client):
        body = _chat_body()
        with patch(
            "app.chat.chat_service.ChatService.stream_tokens",
            return_value=_fake_stream("hi"),
        ):
            resp = await client.post(
                "/api/chat/",
                content=body,
                headers={"content-type": "application/json", "x-signature": _sign(body)},
            )
        assert "x-response-time" in resp.headers
