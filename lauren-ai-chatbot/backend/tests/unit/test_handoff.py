"""Unit tests for ActiveAgentStore and the consolidated HandoffBackTo tool."""

from __future__ import annotations

import pytest

from app.ai.active_agent_store import ActiveAgentStore
from app.ai.agent_names import CRM_AGENT_NAME, TRANSFER_AGENT_NAME
from app.ws.context import current_user_id


# ---------------------------------------------------------------------------
# ActiveAgentStore
# ---------------------------------------------------------------------------


class TestActiveAgentStore:
    def test_default_returns_provided_default(self):
        store = ActiveAgentStore()
        assert store.get("conv-1", CRM_AGENT_NAME) == CRM_AGENT_NAME

    def test_set_and_get(self):
        store = ActiveAgentStore()
        store.set("conv-1", TRANSFER_AGENT_NAME)
        assert store.get("conv-1", CRM_AGENT_NAME) == TRANSFER_AGENT_NAME

    def test_reset_removes_entry(self):
        store = ActiveAgentStore()
        store.set("conv-1", TRANSFER_AGENT_NAME)
        store.reset("conv-1")
        assert store.get("conv-1", CRM_AGENT_NAME) == CRM_AGENT_NAME

    def test_reset_missing_key_is_noop(self):
        store = ActiveAgentStore()
        store.reset("nonexistent")  # must not raise
        assert store.get("nonexistent", CRM_AGENT_NAME) == CRM_AGENT_NAME

    def test_independent_conversations(self):
        store = ActiveAgentStore()
        store.set("conv-a", TRANSFER_AGENT_NAME)
        assert store.get("conv-a", CRM_AGENT_NAME) == TRANSFER_AGENT_NAME
        assert store.get("conv-b", CRM_AGENT_NAME) == CRM_AGENT_NAME

    def test_overwrite_existing_entry(self):
        store = ActiveAgentStore()
        store.set("conv-1", TRANSFER_AGENT_NAME)
        store.set("conv-1", CRM_AGENT_NAME)
        assert store.get("conv-1", "fallback") == CRM_AGENT_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeForwarder:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        self.sent.append((user_id, payload))


def _make_agent_context(conversation_id: str = "conv-1", agent_name: str = CRM_AGENT_NAME):
    class _Meta:
        name = agent_name

    class _AgentClass:
        from lauren_ai._agents import AGENT_META as _AGENT_META
        __name__ = agent_name

    _AgentClass.__lauren_ai_agent__ = _Meta()

    class _Ctx:
        agent_class = _AgentClass
        metadata = {"conversation_id": conversation_id}

        @property
        def agent_name(self) -> str:
            from lauren_ai._agents import AGENT_META
            meta = getattr(self.agent_class, AGENT_META, None)
            if meta and meta.name:
                return meta.name
            return self.agent_class.__name__

    return _Ctx()


def _make_exec_ctx(user_id: str | None = "alice"):
    class _State:
        def get(self, key: str, default=None):
            if key == "user_id":
                return user_id
            return default

    class _Request:
        state = _State()

    class _ExecCtx:
        request = _Request()

    return _ExecCtx()


def _make_tool_ctx(
    conversation_id: str = "conv-1",
    agent_name: str = CRM_AGENT_NAME,
    user_id: str | None = "alice",
):
    class _ToolCtx:
        agent_context = _make_agent_context(conversation_id, agent_name)
        execution_context = _make_exec_ctx(user_id)

    return _ToolCtx()


# ---------------------------------------------------------------------------
# HandoffBackTo — CRM → Transfer direction
# ---------------------------------------------------------------------------


class TestHandoffToTransfer:
    @pytest.mark.asyncio
    async def test_sets_transfer_agent_in_store(self):
        from app.ai.handoff_tool import HandoffBackTo

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffBackTo(active_agent_store=store, event_forwarder=fwd)
        result = await tool.run(_make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id="alice"), summary="Customer wants a transfer")

        assert store.get("conv-1", CRM_AGENT_NAME) == TRANSFER_AGENT_NAME
        assert result["status"] == "handed_back"
        assert result["to_agent"] == TRANSFER_AGENT_NAME

    @pytest.mark.asyncio
    async def test_emits_agent_handoff_event(self):
        from app.ai.handoff_tool import HandoffBackTo

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffBackTo(active_agent_store=store, event_forwarder=fwd)
        await tool.run(_make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id="alice"), summary="Transfer needed")

        assert len(fwd.sent) == 1
        user_id, payload = fwd.sent[0]
        assert user_id == "alice"
        assert payload["type"] == "agent_handoff"
        assert payload["to_agent"] == TRANSFER_AGENT_NAME
        assert payload["summary"] == "Transfer needed"

    @pytest.mark.asyncio
    async def test_no_event_without_user_id(self):
        """Event is always sent; user_id="" when execution_context has no user."""
        from app.ai.handoff_tool import HandoffBackTo

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffBackTo(active_agent_store=store, event_forwarder=fwd)
        await tool.run(_make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id=None), summary="No user")

        assert len(fwd.sent) == 1
        user_id, payload = fwd.sent[0]
        assert user_id == ""
        assert store.get("conv-1", CRM_AGENT_NAME) == TRANSFER_AGENT_NAME

    @pytest.mark.asyncio
    async def test_no_store_update_without_conversation_id(self):
        from app.ai.handoff_tool import HandoffBackTo

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffBackTo(active_agent_store=store, event_forwarder=fwd)
        await tool.run(_make_tool_ctx("", CRM_AGENT_NAME, user_id="alice"), summary="No conv id")

        assert store.get("", CRM_AGENT_NAME) == CRM_AGENT_NAME


# ---------------------------------------------------------------------------
# HandoffBackTo — Transfer → CRM direction
# ---------------------------------------------------------------------------


class TestHandoffBackToCRM:
    @pytest.mark.asyncio
    async def test_resets_store_to_crm(self):
        from app.ai.handoff_tool import HandoffBackTo

        tok = current_user_id.set("alice")
        try:
            store = ActiveAgentStore()
            store.set("conv-1", TRANSFER_AGENT_NAME)
            fwd = _FakeForwarder()
            tool = HandoffBackTo(active_agent_store=store, event_forwarder=fwd)
            result = await tool.run(
                _make_tool_ctx("conv-1", TRANSFER_AGENT_NAME),
                summary="Transfer of $100 to bob completed",
            )
        finally:
            current_user_id.reset(tok)

        assert store.get("conv-1", CRM_AGENT_NAME) == CRM_AGENT_NAME
        assert result["status"] == "handed_back"
        assert result["to_agent"] == CRM_AGENT_NAME

    @pytest.mark.asyncio
    async def test_emits_reverse_handoff_event(self):
        from app.ai.handoff_tool import HandoffBackTo

        tok = current_user_id.set("alice")
        try:
            store = ActiveAgentStore()
            store.set("conv-1", TRANSFER_AGENT_NAME)
            fwd = _FakeForwarder()
            tool = HandoffBackTo(active_agent_store=store, event_forwarder=fwd)
            await tool.run(
                _make_tool_ctx("conv-1", TRANSFER_AGENT_NAME),
                summary="Done",
            )
        finally:
            current_user_id.reset(tok)

        assert len(fwd.sent) == 1
        user_id, payload = fwd.sent[0]
        assert user_id == "alice"
        assert payload["type"] == "agent_handoff"
        assert payload["to_agent"] == CRM_AGENT_NAME
        assert payload["summary"] == "Done"
