"""Tests proving AgentRunner persists conversation history across .run() calls.

Each AgentRunner.run() invocation is a separate HTTP request.  Without a
ConversationStore the agent forgets every prior message.  These tests verify
that when a conversation_store is wired the history is loaded before the new
message and saved afterward, so the LLM sees full context on every turn.
"""

import pytest

from lauren_ai import LLMConfig, agent
from lauren_ai._memory._stores import InMemoryConversationStore
from lauren_ai._transport import Completion, TokenUsage


@agent(model=None, system="You are a helpful assistant.", max_turns=3)
class SimpleAgent:
    """Minimal agent used only for memory-persistence tests."""


def _completion(content: str, *, n: int = 1) -> Completion:
    return Completion(
        id=f"mock-{n}",
        model="mock",
        content=content,
        tool_calls=[],
        stop_reason="end_turn",
        usage=TokenUsage(input_tokens=10, output_tokens=5),
    )


class TestConversationMemoryPersistence:
    """AgentRunner stores and loads history via ConversationStore."""

    @pytest.mark.asyncio
    async def test_second_run_receives_prior_messages(self):
        """The second run's ShortTermMemory must contain the first exchange."""
        cfg, mock = LLMConfig.for_testing()
        store = InMemoryConversationStore()

        from lauren_ai._agents._runner import AgentRunner

        runner = AgentRunner(
            transport=mock,
            tools={},
            config=cfg,
            conversation_store=store,
        )

        agent_instance = SimpleAgent()
        conv_id = "test-conv-001"

        # ── Turn 1 ──────────────────────────────────────────────────────────
        mock.queue_response(_completion("Hello! How can I help?", n=1))
        resp1 = await runner.run(agent_instance, "Hi there", conversation_id=conv_id)
        assert resp1.content == "Hello! How can I help?"

        # History must have been saved
        saved = await store.load(conv_id)
        # user message + assistant message
        assert len(saved) == 2
        roles = [m["role"] for m in saved]
        assert roles == ["user", "assistant"]
        assert saved[0]["content"] == "Hi there"

        # ── Turn 2 ──────────────────────────────────────────────────────────
        # Capture the messages that the transport actually receives
        received_messages: list = []
        original_complete = mock.complete

        async def capturing_complete(messages, **kwargs):
            received_messages.extend(messages)
            return await original_complete(messages, **kwargs)

        mock.complete = capturing_complete
        mock.queue_response(_completion("Your name is Alice!", n=2))
        await runner.run(agent_instance, "What did I say?", conversation_id=conv_id)

        # The second run must include the first exchange plus the new message
        assert len(received_messages) == 3  # prior user, prior assistant, new user
        assert received_messages[0]["content"] == "Hi there"  # prior user
        assert received_messages[1]["content"] == "Hello! How can I help?"  # prior assistant
        assert received_messages[2]["content"] == "What did I say?"  # new user

    @pytest.mark.asyncio
    async def test_no_conversation_id_does_not_save(self):
        """Without a conversation_id the store is never written."""
        cfg, mock = LLMConfig.for_testing()
        store = InMemoryConversationStore()

        from lauren_ai._agents._runner import AgentRunner

        runner = AgentRunner(
            transport=mock,
            tools={},
            config=cfg,
            conversation_store=store,
        )

        mock.queue_response(_completion("OK", n=1))
        await runner.run(SimpleAgent(), "Hello")  # no conversation_id

        assert len(store) == 0

    @pytest.mark.asyncio
    async def test_different_conversation_ids_are_isolated(self):
        """Two sessions with different IDs do not bleed into each other."""
        cfg, mock = LLMConfig.for_testing()
        store = InMemoryConversationStore()

        from lauren_ai._agents._runner import AgentRunner

        runner = AgentRunner(
            transport=mock,
            tools={},
            config=cfg,
            conversation_store=store,
        )
        inst = SimpleAgent()

        mock.queue_response(_completion("Alice reply", n=1))
        await runner.run(inst, "Alice message", conversation_id="alice")

        mock.queue_response(_completion("Bob reply", n=2))
        await runner.run(inst, "Bob message", conversation_id="bob")

        alice_history = await store.load("alice")
        bob_history = await store.load("bob")

        assert all("Bob" not in str(m) for m in alice_history)
        assert all("Alice" not in str(m) for m in bob_history)

    @pytest.mark.asyncio
    async def test_history_grows_across_multiple_turns(self):
        """Each successive run appends to the stored history."""
        cfg, mock = LLMConfig.for_testing()
        store = InMemoryConversationStore()

        from lauren_ai._agents._runner import AgentRunner

        runner = AgentRunner(
            transport=mock,
            tools={},
            config=cfg,
            conversation_store=store,
        )
        inst = SimpleAgent()
        conv_id = "growing-conv"

        for i in range(3):
            mock.queue_response(_completion(f"Reply {i}", n=i))
            await runner.run(inst, f"Message {i}", conversation_id=conv_id)

        history = await store.load(conv_id)
        # 3 user messages + 3 assistant messages = 6 entries
        assert len(history) == 6
        user_msgs = [m for m in history if m["role"] == "user"]
        assert [m["content"] for m in user_msgs] == ["Message 0", "Message 1", "Message 2"]
