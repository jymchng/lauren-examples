"""Integration tests for the chat controller.

The :class:`ChatService` is exercised end-to-end with the
:class:`MockTransport` — the framework routes ``runner.run_stream`` to
the mock instead of real OpenAI, and the controller's SSE response is
parsed back into a single string.
"""

from __future__ import annotations

import json

import pytest
from lauren_ai._transport import CompletionChunk

from app.services.chat_service import ChatService


# ---------------------------------------------------------------------------
# TestClient chat: end-to-end via SSE
# ---------------------------------------------------------------------------


class TestChatE2E:
    async def test_post_chat_streams_sse(self, client, mock_transport):
        # queue a stream of two deltas + finish
        mock_transport.queue_stream(
            [CompletionChunk(delta="Hello"), CompletionChunk(delta=" world"), CompletionChunk(delta="")]
        )
        resp = client.post(
            "/api/chat/",
            json={"message": "Hi", "agent_type": "concierge"},
        )
        assert resp.status_code == 200
        # SSE responses have text/event-stream
        body = resp.text
        assert "Hello" in body
        assert "world" in body
        assert "data: [DONE]" in body

    async def test_post_chat_empty_message_returns_400(self, client):
        resp = client.post(
            "/api/chat/",
            json={"message": "", "agent_type": "concierge"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["success"] is False
        assert "non-empty" in body["error"]

    async def test_post_chat_whitespace_message_returns_400(self, client):
        resp = client.post(
            "/api/chat/",
            json={"message": "   ", "agent_type": "concierge"},
        )
        assert resp.status_code == 400

    async def test_post_chat_meta_event_includes_conversation_id(self, client, mock_transport):
        mock_transport.queue_stream([CompletionChunk(delta="ok")])
        resp = client.post(
            "/api/chat/",
            json={"message": "Hi", "agent_type": "concierge"},
        )
        assert resp.status_code == 200
        body = resp.text
        # The meta event is the first `data: {...}` line
        meta = None
        for line in body.split("\n\n"):
            if line.startswith("data: ") and '"type": "meta"' in line:
                meta = json.loads(line[6:])
                break
        assert meta is not None
        assert "conversationId" in meta
        assert len(meta["conversationId"]) > 0

    async def test_post_chat_continues_conversation(self, client, mock_transport):
        mock_transport.queue_stream([CompletionChunk(delta="first")])
        r1 = client.post(
            "/api/chat/",
            json={"message": "first", "agent_type": "concierge"},
        )
        assert r1.status_code == 200
        # The chat service persists both messages; subsequent calls reuse
        # the conversation id by reading it back from history.
        mock_transport.queue_stream([CompletionChunk(delta="second")])
        r2 = client.post(
            "/api/chat/",
            json={"message": "second", "agent_type": "concierge"},
        )
        assert r2.status_code == 200


# ---------------------------------------------------------------------------
# ChatService unit tests
# ---------------------------------------------------------------------------


class TestChatServiceComplete:
    async def test_complete_returns_final_text(self, app, mock_transport):
        mock_transport.queue_stream([CompletionChunk(delta="Hi"), CompletionChunk(delta=" there")])
        svc = await app.container.resolve(ChatService)
        text = await svc.complete("hello")
        assert text == "Hi there"

    async def test_complete_persists_user_and_assistant(self, app, clean_db, mock_transport):
        mock_transport.queue_stream([CompletionChunk(delta="ack")])
        svc = await app.container.resolve(ChatService)
        await svc.complete("hello")
        rows = await clean_db.fetch_all("SELECT role, content FROM agent_messages ORDER BY created_at ASC")
        assert [r["role"] for r in rows] == ["user", "assistant"]
        assert rows[0]["content"] == "hello"
        assert rows[1]["content"] == "ack"

    async def test_complete_creates_conversation(self, app, clean_db, mock_transport):
        mock_transport.queue_stream([CompletionChunk(delta="ack")])
        svc = await app.container.resolve(ChatService)
        await svc.complete("hi", agent_type="food_recommender")
        row = await clean_db.fetch_one("SELECT * FROM conversations")
        assert row is not None
        assert row["agent_type"] == "food_recommender"
        assert row["status"] == "active"
        assert row["title"] == "hi"

    async def test_complete_reuses_conversation(self, app, clean_db, mock_transport):
        mock_transport.queue_stream([CompletionChunk(delta="ack1")])
        svc = await app.container.resolve(ChatService)
        conv_id = await svc._ensure_conversation(None, "concierge", "first")
        mock_transport.queue_stream([CompletionChunk(delta="ack2")])
        await svc.complete("second", conversation_id=conv_id)
        rows = await clean_db.fetch_all("SELECT id FROM conversations")
        assert len(rows) == 1

    async def test_complete_unknown_agent_falls_back_to_concierge(self, app, mock_transport):
        mock_transport.queue_stream([CompletionChunk(delta="fallback")])
        svc = await app.container.resolve(ChatService)
        text = await svc.complete("hello", agent_type="nonexistent")
        assert text == "fallback"

    async def test_ensure_conversation_creates_with_explicit_id(self, app, clean_db):
        svc = await app.container.resolve(ChatService)
        conv_id = await svc._ensure_conversation("my-conv", "concierge", "hi")
        assert conv_id == "my-conv"
        row = await clean_db.fetch_one("SELECT * FROM conversations WHERE id = ?", ("my-conv",))
        assert row is not None

    async def test_ensure_conversation_returns_existing(self, app, clean_db):
        await clean_db.execute(
            "INSERT INTO conversations (id, agent_type, status) VALUES ('c1', 'concierge', 'active')"
        )
        svc = await app.container.resolve(ChatService)
        conv_id = await svc._ensure_conversation("c1", "concierge", "hi")
        assert conv_id == "c1"
        # Should not have inserted a second row.
        rows = await clean_db.fetch_all("SELECT id FROM conversations")
        assert len(rows) == 1

    async def test_load_history(self, app, clean_db):
        await clean_db.execute(
            "INSERT INTO conversations (id, agent_type, status) VALUES ('c1', 'concierge', 'active')"
        )
        await clean_db.execute(
            "INSERT INTO agent_messages (id, conversation_id, role, content) VALUES ('m1', 'c1', 'user', 'hi')"
        )
        await clean_db.execute(
            "INSERT INTO agent_messages (id, conversation_id, role, content) VALUES ('m2', 'c1', 'assistant', 'hello')"
        )
        svc = await app.container.resolve(ChatService)
        history = await svc._load_history("c1")
        assert [m.content for m in history] == ["hi", "hello"]

    async def test_load_history_excludes_tool_messages(self, app, clean_db):
        await clean_db.execute(
            "INSERT INTO conversations (id, agent_type, status) VALUES ('c1', 'concierge', 'active')"
        )
        await clean_db.execute(
            "INSERT INTO agent_messages (id, conversation_id, role, content) VALUES ('m1', 'c1', 'user', 'hi')"
        )
        await clean_db.execute(
            "INSERT INTO agent_messages (id, conversation_id, role, content) VALUES ('m2', 'c1', 'tool', 'x')"
        )
        svc = await app.container.resolve(ChatService)
        history = await svc._load_history("c1")
        assert [m.role for m in history] == ["user"]


class TestHandoffInfo:
    """Unit tests for the SSE-side handoff detector in :mod:`chat_service`."""

    def test_ignores_chunks_with_no_tool_delta(self):
        from app.services.chat_service import _HandoffInfo
        from lauren_ai._transport import CompletionChunk

        h = _HandoffInfo()
        h.observe(CompletionChunk(delta="hi"))
        assert h.to_agent is None

    def test_detects_handoff_to_food_expert(self):
        from app.services.chat_service import _HandoffInfo
        from lauren_ai._transport import CompletionChunk, ToolCallDelta

        h = _HandoffInfo()
        h.observe(
            CompletionChunk(tool_call_delta=ToolCallDelta(tool_use_id="t1", name="HandoffTo", input_delta=""))
        )
        h.observe(
            CompletionChunk(
                tool_call_delta=ToolCallDelta(tool_use_id="t1", name=None, input_delta='{"to_agent"')
            )
        )
        h.observe(
            CompletionChunk(
                tool_call_delta=ToolCallDelta(tool_use_id="t1", name=None, input_delta=': "Food Expert"}')
            )
        )
        assert h.to_agent == "Food Expert"

    def test_to_sse_payload_shape(self):
        from app.services.chat_service import _HandoffInfo

        h = _HandoffInfo()
        h.to_agent = "Order Assistant"
        payload = h.to_sse("concierge")
        assert payload["type"] == "handoff"
        assert payload["fromAgent"] == "concierge"
        assert payload["toAgent"] == "ordering"
        assert payload["fromAgentName"] == "Concierge"
        assert payload["toAgentName"] == "Order Assistant"
        assert payload["fromAgentEmoji"] == "🎩"
        assert payload["toAgentEmoji"] == "🛒"
        assert "Order Assistant" in payload["reason"]

    def test_to_sse_returns_none_without_target(self):
        from app.services.chat_service import _HandoffInfo

        h = _HandoffInfo()
        assert h.to_sse("concierge") is None

    def test_stream_chat_emits_handoff_event(self, client, mock_transport):
        """End-to-end: concierge calls HandoffTo → SSE carries type:handoff."""
        from lauren_ai._transport import CompletionChunk, ToolCallDelta

        mock_transport.queue_stream(
            [
                CompletionChunk(delta="Let me connect you..."),
                CompletionChunk(
                    tool_call_delta=ToolCallDelta(
                        tool_use_id="t1",
                        name="HandoffTo",
                        input_delta='{"to_agent": "Reservation Desk", "summary": "books"}',
                    )
                ),
            ]
        )
        resp = client.post(
            "/api/chat/",
            json={"message": "Book a table for tonight", "agent_type": "concierge"},
        )
        assert resp.status_code == 200
        body = resp.text
        assert '"type": "handoff"' in body
        assert '"toAgent": "reservation"' in body
        assert '"toAgentName": "Reservation Desk"' in body
        assert "data: [DONE]" in body

    async def test_stream_chat_yields_meta_then_deltas_then_done(self, app, mock_transport):
        mock_transport.queue_stream(
            [CompletionChunk(delta="a"), CompletionChunk(delta="b"), CompletionChunk(delta="c")]
        )
        svc = await app.container.resolve(ChatService)
        chunks = []
        async for chunk in svc.stream_chat("hi"):
            chunks.append(chunk)
        assert len(chunks) >= 2
        # First is the meta event
        assert b'"type": "meta"' in chunks[0]
        # Last is [DONE]
        assert chunks[-1] == b"data: [DONE]\n\n"
        # In between: SSE chunks for "a", "b", "c"
        sse_chunks = chunks[1:-1]
        assert len(sse_chunks) == 3
        assert b'"content": "a"' in sse_chunks[0]
        assert b'"content": "b"' in sse_chunks[1]
        assert b'"content": "c"' in sse_chunks[2]


# ---------------------------------------------------------------------------
# Runner resolver
# ---------------------------------------------------------------------------


class TestRunnerResolver:
    async def test_resolve_concierge_returns_constructor_runner(self, app):
        from app.agents.concierge import ConciergeAgent
        from app.services.runner_resolver import resolve_runner
        from app.services.chat_service import ChatService

        svc = await app.container.resolve(ChatService)
        runner = await resolve_runner(ConciergeAgent)
        assert runner is svc._concierge_runner

    async def test_resolve_other_agent_lazy_resolves(self, app):
        from app.agents.food_recommender import FoodRecommenderAgent
        from app.services.runner_resolver import resolve_runner

        runner = await resolve_runner(FoodRecommenderAgent)
        assert runner is not None
        # Idempotent
        runner2 = await resolve_runner(FoodRecommenderAgent)
        assert runner is runner2

    async def test_resolve_without_register_raises(self):
        import app.services.runner_resolver as rr

        rr._container = None
        from app.agents.dietary import DietaryAgent

        with pytest.raises(RuntimeError, match="container"):
            await rr.resolve_runner(DietaryAgent)
