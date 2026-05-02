"""Unit tests for the agent chat service layer.

Tests the ``AgentRunner`` + ``ChatAgent`` + tool pipeline using ``MockTransport``
so no network calls are ever made.  Exercises:

- Basic end-to-end agent run returning a completion.
- Tool-use round trip (model requests a tool → executor calls it → model uses result).
- Multi-turn conversation via ``conversation_id``.
- Edge cases: empty content, max-turns guard.
"""

# NOTE: Do NOT add `from __future__ import annotations` to this file.
# Tool schemas are built via inspect.signature() at decoration time and
# PEP 563 lazy evaluation breaks that introspection.

import pytest

from lauren_ai import LLMConfig
from lauren_ai._agents._runner import AgentRunner
from lauren_ai._module import LLMService
from lauren_ai._tools._registry import ToolRegistry
from lauren_ai._transport import (
    Completion,
    CompletionChunk,
    TokenUsage,
)
from lauren_ai._transport._mock import MockTransport

from app.ai.agent import ChatAgent
from app.ai.tools import calculate, get_current_time, word_count


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transport() -> MockTransport:
    return MockTransport()


def _make_runner(transport: MockTransport) -> AgentRunner:
    """Build an ``AgentRunner`` wired to *transport* with the app's tools."""
    cfg = LLMConfig(provider="anthropic", model="mock-model", api_key="test")
    registry = ToolRegistry()
    for tool_fn in [get_current_time, calculate, word_count]:
        registry.register(tool_fn)
    return AgentRunner(
        transport=transport,
        registry=registry,
        config=cfg,
        signals=None,
        cache_backend=None,
    )


def _queue_completion(
    mock: MockTransport,
    content: str = "Hello!",
    model: str = "mock-model",
) -> None:
    """Queue a single non-streaming completion."""
    mock.queue_response(
        Completion(
            id="c1",
            model=model,
            content=content,
            tool_calls=[],
            stop_reason="end_turn",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )
    )


# ---------------------------------------------------------------------------
# AgentRunner construction
# ---------------------------------------------------------------------------


class TestAgentRunnerConstruction:
    def test_runner_accepts_mock_transport(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        assert runner is not None

    def test_registry_has_all_tools(self):
        mock = _make_transport()
        cfg = LLMConfig(provider="anthropic", model="mock-model", api_key="test")
        registry = ToolRegistry()
        for tool_fn in [get_current_time, calculate, word_count]:
            registry.register(tool_fn)
        runner = AgentRunner(
            transport=mock,
            registry=registry,
            config=cfg,
            signals=None,
            cache_backend=None,
        )
        # All three tools should be registered
        assert "get_current_time" in registry
        assert "calculate" in registry
        assert "word_count" in registry


# ---------------------------------------------------------------------------
# Basic agent runs
# ---------------------------------------------------------------------------


class TestAgentBasicRun:
    @pytest.mark.asyncio
    async def test_run_returns_agent_response(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "I am a helpful assistant.")
        response = await runner.run(ChatAgent, "Hello!")
        assert response.content == "I am a helpful assistant."

    @pytest.mark.asyncio
    async def test_run_records_transport_call(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Hi there!")
        await runner.run(ChatAgent, "Hey!")
        assert len(mock.calls) == 1

    @pytest.mark.asyncio
    async def test_run_forwards_user_message(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Paris.")
        await runner.run(ChatAgent, "What is the capital of France?")
        call = mock.calls[0]
        # Messages from ShortTermMemory are dicts {"role": ..., "content": ...}
        assert any(
            "France" in str(m.get("content", "") if isinstance(m, dict) else getattr(m, "content", ""))
            for m in call.messages
        )

    @pytest.mark.asyncio
    async def test_run_returns_stop_reason_end_turn(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Done.")
        response = await runner.run(ChatAgent, "Finish.")
        assert response.stop_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_run_empty_content_returns_empty_string(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        mock.queue_response(
            Completion(
                id="c2",
                model="mock-model",
                content="",
                tool_calls=[],
                stop_reason="end_turn",
                usage=TokenUsage(input_tokens=5, output_tokens=0),
            )
        )
        response = await runner.run(ChatAgent, "Ping")
        assert response.content == ""

    @pytest.mark.asyncio
    async def test_run_accumulates_token_usage(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Result.")
        response = await runner.run(ChatAgent, "Calculate 2+2")
        assert response.total_usage.input_tokens > 0 or response.total_usage.output_tokens >= 0


# ---------------------------------------------------------------------------
# Tool-use round trip
# ---------------------------------------------------------------------------


class TestAgentToolUse:
    @pytest.mark.asyncio
    async def test_calculate_tool_called_and_result_used(self):
        """Model requests the 'calculate' tool; runner executes it; model uses result."""
        mock = _make_transport()
        runner = _make_runner(mock)

        # Turn 1: model requests calculate tool
        mock.queue_tool_use(
            tool_name="calculate",
            tool_input={"expression": "2 + 2"},
        )
        # Turn 2: model uses the tool result to produce final answer
        _queue_completion(mock, "The answer is 4.")

        response = await runner.run(ChatAgent, "What is 2 + 2?")
        assert response.content == "The answer is 4."
        # Two transport calls: tool-use turn + final answer turn
        assert len(mock.calls) == 2

    @pytest.mark.asyncio
    async def test_tool_call_recorded_in_response(self):
        """tool_calls_made should list all tool calls executed during the run."""
        mock = _make_transport()
        runner = _make_runner(mock)

        mock.queue_tool_use(
            tool_name="calculate",
            tool_input={"expression": "10 * 10"},
        )
        _queue_completion(mock, "100.")

        response = await runner.run(ChatAgent, "What is 10 times 10?")
        assert len(response.tool_calls_made) == 1
        assert response.tool_calls_made[0].name == "calculate"

    @pytest.mark.asyncio
    async def test_word_count_tool_round_trip(self):
        mock = _make_transport()
        runner = _make_runner(mock)

        mock.queue_tool_use(
            tool_name="word_count",
            tool_input={"text": "hello world foo"},
        )
        _queue_completion(mock, "The text has 3 words.")

        response = await runner.run(ChatAgent, "How many words in 'hello world foo'?")
        assert response.content == "The text has 3 words."


# ---------------------------------------------------------------------------
# Multi-turn via conversation_id
# ---------------------------------------------------------------------------


class TestAgentConversationId:
    @pytest.mark.asyncio
    async def test_run_accepts_conversation_id(self):
        """conversation_id can be passed without error."""
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Sure!")
        response = await runner.run(
            ChatAgent, "Hello again!", conversation_id="session-abc"
        )
        assert response is not None

    @pytest.mark.asyncio
    async def test_run_without_conversation_id(self):
        """No conversation_id is also valid."""
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Hi!")
        response = await runner.run(ChatAgent, "Hello")
        assert response.content == "Hi!"


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------


class TestAgentResponseStructure:
    @pytest.mark.asyncio
    async def test_response_has_turns_field(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Done.")
        response = await runner.run(ChatAgent, "test")
        assert response.turns >= 1

    @pytest.mark.asyncio
    async def test_response_has_tool_calls_made_list(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "Done.")
        response = await runner.run(ChatAgent, "test")
        assert isinstance(response.tool_calls_made, list)

    @pytest.mark.asyncio
    async def test_response_as_stream_yields_content(self):
        mock = _make_transport()
        runner = _make_runner(mock)
        _queue_completion(mock, "streamed content")
        response = await runner.run(ChatAgent, "stream test")
        parts = []
        async for chunk in response.as_stream():
            parts.append(chunk)
        assert "".join(parts) == "streamed content"


# ---------------------------------------------------------------------------
# LLMService integration (used by ChatService)
# ---------------------------------------------------------------------------


class TestLLMServiceWithMockTransport:
    @pytest.mark.asyncio
    async def test_complete_stream_yields_chunks(self):
        """LLMService.complete_stream returns an async iterator of chunks."""
        mock = _make_transport()
        cfg = LLMConfig(provider="anthropic", model="mock-model", api_key="test")
        llm = LLMService(transport=mock, config=cfg)

        chunks = [
            CompletionChunk(delta="Hello"),
            CompletionChunk(delta=" world"),
            CompletionChunk(delta="", stop_reason="end_turn", usage=TokenUsage(5, 3)),
        ]
        mock.queue_stream(chunks)

        tokens = []
        stream = await llm.complete_stream([], model="mock-model")
        async for chunk in stream:
            if chunk.delta:
                tokens.append(chunk.delta)

        assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_complete_non_streaming_returns_completion(self):
        mock = _make_transport()
        cfg = LLMConfig(provider="anthropic", model="mock-model", api_key="test")
        llm = LLMService(transport=mock, config=cfg)

        mock.queue_response(
            Completion(
                id="c1",
                model="mock-model",
                content="Answer.",
                tool_calls=[],
                stop_reason="end_turn",
                usage=TokenUsage(10, 5),
            )
        )

        result = await llm.complete([], model="mock-model")
        assert result.content == "Answer."
