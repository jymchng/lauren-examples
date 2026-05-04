"""Unit tests for Pydantic schemas (ChatRequest, Message)."""

import pytest
from pydantic import ValidationError

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
        with pytest.raises(ValidationError):
            Message(role="unknown", content="x")

    def test_missing_role_raises(self):
        with pytest.raises(ValidationError):
            Message(content="hi")  # type: ignore[call-arg]

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

    def test_empty_messages_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

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

    def test_model_dump(self):
        req = ChatRequest(messages=[Message(role="user", content="test")])
        d = req.model_dump()
        assert "messages" in d
        assert "model" in d
        assert d["messages"][0]["role"] == "user"
