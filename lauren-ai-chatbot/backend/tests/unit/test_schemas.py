"""Unit tests for msgspec schemas (ChatRequest, Message)."""

import msgspec
import pytest

from app.ai.chat_schemas import ChatRequest, Message


class TestMessage:
    def test_valid_user(self):
        m = Message(role="user", content="hi")
        assert m.role == "user"
        assert m.content == "hi"

    def test_valid_assistant(self):
        m = Message(role="assistant", content="Hello!")
        assert m.role == "assistant"

    def test_valid_system(self):
        m = Message(role="system", content="You are helpful.")
        assert m.role == "system"

    def test_invalid_role_raises(self):
        with pytest.raises((msgspec.ValidationError, TypeError)):
            msgspec.convert({"role": "unknown", "content": "x"}, Message)

    def test_missing_role_raises(self):
        with pytest.raises((msgspec.ValidationError, TypeError)):
            msgspec.convert({"content": "hi"}, Message)

    def test_empty_content_is_valid(self):
        m = Message(role="user", content="")
        assert m.content == ""


class TestChatRequest:
    def test_minimal_valid(self):
        req = ChatRequest(messages=[Message(role="user", content="hi")])
        assert len(req.messages) == 1
        assert req.model == "openai/gpt-4o-mini"

    def test_custom_model(self):
        req = ChatRequest(
            messages=[Message(role="user", content="hi")],
            model="anthropic/claude-3-5-haiku",
        )
        assert req.model == "anthropic/claude-3-5-haiku"

    def test_empty_messages_is_valid(self):
        # msgspec does not enforce min_length; empty list is structurally valid
        req = ChatRequest(messages=[])
        assert req.messages == []

    def test_multiple_messages(self):
        req = ChatRequest(
            messages=[
                Message(role="system", content="Be concise."),
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi!"),
                Message(role="user", content="Thanks"),
            ]
        )
        assert len(req.messages) == 4

    def test_serializes_to_json_via_msgspec(self):
        req = ChatRequest(messages=[Message(role="user", content="test")])
        data = msgspec.json.decode(msgspec.json.encode(req), type=dict)
        assert "messages" in data
        assert "model" in data
        assert data["messages"][0]["role"] == "user"
