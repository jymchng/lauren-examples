"""Unit tests for ActiveAgentStore and the generic HandoffTo tool."""

from __future__ import annotations

import pytest

from app.ai.tools.active_agent_store import ActiveAgentStore
from app.ai.agent_names import AUTH_CRM_AGENT_NAME as CRM_AGENT_NAME, TRANSFER_AGENT_NAME
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

    def test_pop_pending_summary_returns_and_clears(self):
        store = ActiveAgentStore()
        store.set_pending_summary("conv-1", "Transfer done")
        assert store.pop_pending_summary("conv-1") == "Transfer done"
        assert store.pop_pending_summary("conv-1") == ""  # consumed

    def test_pop_pending_summary_missing_key_returns_empty(self):
        store = ActiveAgentStore()
        assert store.pop_pending_summary("nonexistent") == ""

    def test_pending_summary_independent_per_conversation(self):
        store = ActiveAgentStore()
        store.set_pending_summary("conv-a", "Summary A")
        store.set_pending_summary("conv-b", "Summary B")
        assert store.pop_pending_summary("conv-a") == "Summary A"
        assert store.pop_pending_summary("conv-b") == "Summary B"


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
# HandoffTo — CRM → Transfer direction
# ---------------------------------------------------------------------------


class TestHandoffToTransfer:
    @pytest.mark.asyncio
    async def test_sets_transfer_agent_in_store(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)
        result = await tool.run(
            _make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id="alice"),
            to_agent=TRANSFER_AGENT_NAME,
            summary="Customer wants a transfer",
        )

        assert store.get("conv-1", CRM_AGENT_NAME) == TRANSFER_AGENT_NAME
        assert result["status"] == "handed_off"
        assert result["to_agent"] == TRANSFER_AGENT_NAME

    @pytest.mark.asyncio
    async def test_emits_agent_handoff_event(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)
        await tool.run(
            _make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id="alice"),
            to_agent=TRANSFER_AGENT_NAME,
            summary="Transfer needed",
        )

        assert len(fwd.sent) == 1
        user_id, payload = fwd.sent[0]
        assert user_id == "alice"
        assert payload["type"] == "agent_handoff"
        assert payload["to_agent"] == TRANSFER_AGENT_NAME
        assert payload["summary"] == "Transfer needed"

    @pytest.mark.asyncio
    async def test_no_event_without_user_id(self):
        """Event is always sent; user_id="" when execution_context has no user."""
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)
        await tool.run(
            _make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id=None),
            to_agent=TRANSFER_AGENT_NAME,
            summary="No user",
        )

        assert len(fwd.sent) == 1
        user_id, payload = fwd.sent[0]
        assert user_id == ""
        assert store.get("conv-1", CRM_AGENT_NAME) == TRANSFER_AGENT_NAME

    @pytest.mark.asyncio
    async def test_no_store_update_without_conversation_id(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)
        await tool.run(
            _make_tool_ctx("", CRM_AGENT_NAME, user_id="alice"),
            to_agent=TRANSFER_AGENT_NAME,
            summary="No conv id",
        )

        assert store.get("", CRM_AGENT_NAME) == CRM_AGENT_NAME

    @pytest.mark.asyncio
    async def test_invalid_to_agent_returns_error(self):
        """Passing an agent name not in _target_names returns an error dict."""
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)
        result = await tool.run(
            _make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id="alice"),
            to_agent="NonExistentAgent",
            summary="Should fail",
        )

        assert "error" in result
        assert store.get("conv-1", CRM_AGENT_NAME) == CRM_AGENT_NAME  # store untouched
        assert len(fwd.sent) == 0  # no event emitted


# ---------------------------------------------------------------------------
# HandoffTo — Transfer → CRM direction
# ---------------------------------------------------------------------------


class TestHandoffBackToCRM:
    @pytest.mark.asyncio
    async def test_sets_store_to_crm(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent

        store = ActiveAgentStore()
        store.set("conv-1", TRANSFER_AGENT_NAME)
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingCRMAgent](active_agent_store=store, event_forwarder=fwd)
        result = await tool.run(
            _make_tool_ctx("conv-1", TRANSFER_AGENT_NAME),
            to_agent=CRM_AGENT_NAME,
            summary="Transfer of $100 to bob completed",
        )

        assert store.get("conv-1", CRM_AGENT_NAME) == CRM_AGENT_NAME
        assert result["status"] == "handed_off"
        assert result["to_agent"] == CRM_AGENT_NAME

    @pytest.mark.asyncio
    async def test_emits_reverse_handoff_event(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent

        store = ActiveAgentStore()
        store.set("conv-1", TRANSFER_AGENT_NAME)
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingCRMAgent](active_agent_store=store, event_forwarder=fwd)
        await tool.run(
            _make_tool_ctx("conv-1", TRANSFER_AGENT_NAME),
            to_agent=CRM_AGENT_NAME,
            summary="Done",
        )

        assert len(fwd.sent) == 1
        user_id, payload = fwd.sent[0]
        assert user_id == "alice"
        assert payload["type"] == "agent_handoff"
        assert payload["to_agent"] == CRM_AGENT_NAME
        assert payload["summary"] == "Done"

    @pytest.mark.asyncio
    async def test_to_crm_writes_summary_to_store(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent

        store = ActiveAgentStore()
        store.set("conv-1", TRANSFER_AGENT_NAME)
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingCRMAgent](active_agent_store=store, event_forwarder=fwd)
        await tool.run(
            _make_tool_ctx("conv-1", TRANSFER_AGENT_NAME),
            to_agent=CRM_AGENT_NAME,
            summary="Transfer of $100 to Bob completed",
        )

        assert store.pop_pending_summary("conv-1") == "Transfer of $100 to Bob completed"


# ---------------------------------------------------------------------------
# HandoffTo — CRM → Transfer: summary written to store
# ---------------------------------------------------------------------------


class TestHandoffToTransferSummary:
    @pytest.mark.asyncio
    async def test_to_transfer_writes_summary_to_store(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)
        await tool.run(
            _make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id="alice"),
            to_agent=TRANSFER_AGENT_NAME,
            summary="Customer wants to transfer $50 to charlie",
        )

        assert store.pop_pending_summary("conv-1") == "Customer wants to transfer $50 to charlie"

    @pytest.mark.asyncio
    async def test_no_summary_without_conversation_id(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)
        await tool.run(
            _make_tool_ctx("", CRM_AGENT_NAME, user_id="alice"),
            to_agent=TRANSFER_AGENT_NAME,
            summary="ignored",
        )

        assert store.pop_pending_summary("") == ""


# ---------------------------------------------------------------------------
# HandoffTo — __class_getitem__ caching and N-target behaviour
# ---------------------------------------------------------------------------


class TestHandoffToClassGetitem:
    def test_same_subscript_returns_cached_class(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent

        cls_a = HandoffTo[BankingCRMAgent]
        cls_b = HandoffTo[BankingCRMAgent]
        assert cls_a is cls_b

    def test_different_subscripts_are_distinct_classes(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        cls_crm = HandoffTo[BankingCRMAgent]
        cls_transfer = HandoffTo[BankingTransferAgent]
        assert cls_crm is not cls_transfer

    def test_single_target_has_correct_target_names(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        cls = HandoffTo[BankingTransferAgent]
        assert cls._target_names == (TRANSFER_AGENT_NAME,)

    def test_multi_target_has_all_names(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        cls = HandoffTo[BankingCRMAgent, BankingTransferAgent]
        assert CRM_AGENT_NAME in cls._target_names
        assert TRANSFER_AGENT_NAME in cls._target_names
        assert len(cls._target_names) == 2

    @pytest.mark.asyncio
    async def test_multi_target_can_handoff_to_either(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent
        from app.ai.agents.transfer_agent import BankTransferAgent as BankingTransferAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingCRMAgent, BankingTransferAgent](active_agent_store=store, event_forwarder=fwd)

        result = await tool.run(
            _make_tool_ctx("conv-1", CRM_AGENT_NAME, user_id="alice"),
            to_agent=TRANSFER_AGENT_NAME,
            summary="Handing to transfer",
        )
        assert result["status"] == "handed_off"
        assert store.get("conv-1", CRM_AGENT_NAME) == TRANSFER_AGENT_NAME

        result2 = await tool.run(
            _make_tool_ctx("conv-1", TRANSFER_AGENT_NAME, user_id="alice"),
            to_agent=CRM_AGENT_NAME,
            summary="Back to CRM",
        )
        assert result2["status"] == "handed_off"
        assert store.get("conv-1", TRANSFER_AGENT_NAME) == CRM_AGENT_NAME

    @pytest.mark.asyncio
    async def test_invalid_agent_returns_error_without_side_effects(self):
        from app.ai.tools.handoff_tool import HandoffTo
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent as BankingCRMAgent

        store = ActiveAgentStore()
        fwd = _FakeForwarder()
        tool = HandoffTo[BankingCRMAgent](active_agent_store=store, event_forwarder=fwd)

        result = await tool.run(
            _make_tool_ctx("conv-1", TRANSFER_AGENT_NAME, user_id="alice"),
            to_agent="UnknownAgent",
            summary="Bad call",
        )

        assert "error" in result
        assert len(fwd.sent) == 0
        assert store.get("conv-1", CRM_AGENT_NAME) == CRM_AGENT_NAME
