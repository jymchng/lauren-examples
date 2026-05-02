"""Unit tests for ChatService — mocking via MockTransport instead of raw httpx."""

from __future__ import annotations

import pytest

from lauren_ai import InMemoryConversationStore, LLMConfig
from lauren_ai._module import LLMService
from lauren_ai._transport import Completion, CompletionChunk, TokenUsage
from lauren_ai._transport._mock import MockTransport

from app.chat.chat_service import ChatService
from app.chat.schemas import ChatRequest, Message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    content: str = "Hello!",
    model: str = "openai/gpt-4o-mini",
    conversation_id: str | None = None,
) -> ChatRequest:
    return ChatRequest(
        messages=[Message(role="user", content=content)],
        model=model,
        conversation_id=conversation_id,
    )


def _make_service(mock: MockTransport | None = None) -> tuple[ChatService, MockTransport]:
    """Build a ChatService backed by a MockTransport."""
    transport = mock or MockTransport()
    cfg = LLMConfig(provider="anthropic", model="mock-model", api_key="test")
    llm = LLMService(transport=transport, config=cfg)
    svc = ChatService(llm_service=llm)
    return svc, transport


def _queue_stream(mock: MockTransport, *tokens: str) -> None:
    """Queue a stream of text chunks on the mock transport."""
    chunks = [CompletionChunk(delta=t) for t in tokens]
    chunks.append(CompletionChunk(delta="", stop_reason="end_turn", usage=TokenUsage(10, 5)))
    mock.queue_stream(chunks)


def _queue_completion(mock: MockTransport, content: str = "Hello!") -> None:
    """Queue a single non-streaming completion on the mock transport."""
    mock.queue_response(
        Completion(
            id="c1",
            model="mock-model",
            content=content,
            tool_calls=[],
            stop_reason="end_turn",
            usage=TokenUsage(10, 5),
        )
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestChatServiceInit:
    def test_accepts_llm_service(self):
        svc, _ = _make_service()
        assert isinstance(svc._llm, LLMService)

    def test_creates_conversation_store(self):
        svc, _ = _make_service()
        assert isinstance(svc._store, InMemoryConversationStore)


# ---------------------------------------------------------------------------
# stream_tokens — basic streaming
# ---------------------------------------------------------------------------


class TestStreamTokens:
    @pytest.mark.asyncio
    async def test_yields_tokens_from_stream(self):
        svc, mock = _make_service()
        _queue_stream(mock, "Hello", ", ", "world!")
        tokens = []
        async for tok in svc.stream_tokens(_make_request()):
            tokens.append(tok)
        assert tokens == ["Hello", ", ", "world!"]

    @pytest.mark.asyncio
    async def test_empty_delta_chunks_not_yielded(self):
        """CompletionChunks with empty delta (e.g. final stop chunk) are not yielded."""
        svc, mock = _make_service()
        _queue_stream(mock, "hi")
        tokens = []
        async for tok in svc.stream_tokens(_make_request()):
            tokens.append(tok)
        assert tokens == ["hi"]

    @pytest.mark.asyncio
    async def test_single_token(self):
        svc, mock = _make_service()
        _queue_stream(mock, "done")
        tokens = []
        async for tok in svc.stream_tokens(_make_request()):
            tokens.append(tok)
        assert tokens == ["done"]

    @pytest.mark.asyncio
    async def test_multiple_messages_forwarded(self):
        """All user/assistant messages in the request are forwarded to LLMService."""
        svc, mock = _make_service()
        _queue_stream(mock, "ok")
        req = ChatRequest(
            messages=[
                Message(role="user", content="first"),
                Message(role="assistant", content="reply"),
                Message(role="user", content="second"),
            ],
            model="openai/gpt-4o-mini",
        )
        async for _ in svc.stream_tokens(req):
            pass
        assert len(mock.calls) == 1
        call = mock.calls[0]
        assert len(call.messages) == 3

    @pytest.mark.asyncio
    async def test_system_messages_excluded_from_transport(self):
        """System-role messages in ChatRequest are not forwarded (transport doesn't support them)."""
        svc, mock = _make_service()
        _queue_stream(mock, "ok")
        req = ChatRequest(
            messages=[
                Message(role="system", content="You are helpful."),
                Message(role="user", content="hello"),
            ],
            model="openai/gpt-4o-mini",
        )
        async for _ in svc.stream_tokens(req):
            pass
        call = mock.calls[0]
        # Only the user message should be forwarded; system role is filtered
        assert all(m.role in ("user", "assistant") for m in call.messages)
        assert any(m.content == "hello" for m in call.messages)

    @pytest.mark.asyncio
    async def test_model_forwarded_to_transport(self):
        svc, mock = _make_service()
        _queue_stream(mock, "ok")
        await _consume(svc.stream_tokens(_make_request(model="anthropic/claude-3-5-haiku")))
        assert mock.calls[0].model == "anthropic/claude-3-5-haiku"

    @pytest.mark.asyncio
    async def test_streaming_flag_set(self):
        svc, mock = _make_service()
        _queue_stream(mock, "ok")
        await _consume(svc.stream_tokens(_make_request()))
        assert mock.calls[0].stream is True


# ---------------------------------------------------------------------------
# Conversation memory
# ---------------------------------------------------------------------------


class TestConversationMemory:
    @pytest.mark.asyncio
    async def test_no_conversation_id_no_history_loaded(self):
        """Without conversation_id, only the current request messages are sent."""
        svc, mock = _make_service()
        _queue_stream(mock, "reply")
        await _consume(svc.stream_tokens(_make_request(content="hi")))
        call = mock.calls[0]
        assert len(call.messages) == 1
        assert call.messages[0].content == "hi"

    @pytest.mark.asyncio
    async def test_conversation_id_history_prepended(self):
        """Prior history is loaded from the store and prepended to the current messages."""
        svc, mock = _make_service()
        # Manually seed the store with a prior exchange.
        await svc._store.save(
            "session-1",
            [
                {"role": "user", "content": "what is 2+2?"},
                {"role": "assistant", "content": "4"},
            ],
        )
        _queue_stream(mock, "sure")
        req = _make_request(content="thanks", conversation_id="session-1")
        await _consume(svc.stream_tokens(req))
        call = mock.calls[0]
        # 2 history + 1 new = 3 messages
        assert len(call.messages) == 3
        assert call.messages[0].content == "what is 2+2?"
        assert call.messages[1].content == "4"
        assert call.messages[2].content == "thanks"

    @pytest.mark.asyncio
    async def test_history_saved_after_stream(self):
        """After streaming, the updated history (including assistant reply) is saved."""
        svc, mock = _make_service()
        _queue_stream(mock, "Hello", " there")
        req = _make_request(content="hi", conversation_id="new-session")
        await _consume(svc.stream_tokens(req))
        saved = await svc._store.load("new-session")
        assert len(saved) == 2  # user turn + assistant reply
        assert saved[0]["role"] == "user"
        assert saved[0]["content"] == "hi"
        assert saved[1]["role"] == "assistant"
        assert saved[1]["content"] == "Hello there"

    @pytest.mark.asyncio
    async def test_no_save_without_conversation_id(self):
        """Without conversation_id, nothing is saved to the store."""
        svc, mock = _make_service()
        _queue_stream(mock, "ok")
        await _consume(svc.stream_tokens(_make_request()))
        assert len(svc._store) == 0

    @pytest.mark.asyncio
    async def test_subsequent_turn_accumulates_history(self):
        """Two turns with the same conversation_id accumulate history correctly."""
        svc, mock = _make_service()
        # Turn 1
        _queue_stream(mock, "I am fine.")
        req1 = _make_request(content="How are you?", conversation_id="conv-2")
        await _consume(svc.stream_tokens(req1))
        # Turn 2
        _queue_stream(mock, "Sure!")
        req2 = _make_request(content="Great, help me then.", conversation_id="conv-2")
        await _consume(svc.stream_tokens(req2))

        call2 = mock.calls[1]
        # turn1: user + assistant (2 messages saved), plus turn2 user = 3
        assert len(call2.messages) == 3
        assert call2.messages[0].content == "How are you?"
        assert call2.messages[1].content == "I am fine."
        assert call2.messages[2].content == "Great, help me then."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _consume(ait):
    """Drain an async iterator to completion."""
    async for _ in ait:
        pass
