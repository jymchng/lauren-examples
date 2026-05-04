"""Unit tests for DelegateToBankingTransfer and BankingDelegationWiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.banking_delegation import BankingDelegationWiring, DelegateToBankingTransfer


def _make_ctx(user_id: str = "alice") -> MagicMock:
    state = MagicMock()
    state.get = lambda k, default=None: user_id if k == "user_id" else default
    request = MagicMock()
    request.state = state
    exec_ctx = MagicMock()
    exec_ctx.request = request
    ctx = MagicMock()
    ctx.execution_context = exec_ctx
    return ctx


class TestDelegateToBankingTransfer:
    @pytest.mark.asyncio
    async def test_no_runner_returns_unavailable_error(self):
        transfer_agent = MagicMock()
        tool = DelegateToBankingTransfer(transfer_agent=transfer_agent, runner=None)
        ctx = _make_ctx()
        result = await tool.run(ctx=ctx, task="Transfer $100 to bob")
        assert "error" in result
        assert "unavailable" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_with_runner_calls_agent_and_returns_result(self):
        transfer_agent = MagicMock()
        mock_runner = MagicMock()
        mock_response = AsyncMock()
        mock_response.content = "Transfer complete"
        mock_response.turns = 2
        mock_response.stop_reason = "end_turn"
        mock_runner.run = AsyncMock(return_value=mock_response)

        tool = DelegateToBankingTransfer(transfer_agent=transfer_agent, runner=mock_runner)
        ctx = _make_ctx("bob")
        result = await tool.run(ctx=ctx, task="Transfer $50 to charlie")

        assert result["result"] == "Transfer complete"
        assert result["stop_reason"] == "end_turn"

    @pytest.mark.asyncio
    async def test_runner_called_with_execution_context(self):
        transfer_agent = MagicMock()
        mock_runner = MagicMock()
        mock_response = AsyncMock()
        mock_response.content = "done"
        mock_response.turns = 1
        mock_response.stop_reason = "end_turn"
        mock_runner.run = AsyncMock(return_value=mock_response)

        tool = DelegateToBankingTransfer(transfer_agent=transfer_agent, runner=mock_runner)
        ctx = _make_ctx("alice")
        await tool.run(ctx=ctx, task="Check balance")

        call_kwargs = mock_runner.run.call_args.kwargs
        assert call_kwargs.get("execution_context") is ctx.execution_context

    @pytest.mark.asyncio
    async def test_runner_called_with_transfer_agent_instance(self):
        transfer_agent = MagicMock()
        mock_runner = MagicMock()
        mock_response = AsyncMock()
        mock_response.content = "ok"
        mock_response.turns = 1
        mock_response.stop_reason = "end_turn"
        mock_runner.run = AsyncMock(return_value=mock_response)

        tool = DelegateToBankingTransfer(transfer_agent=transfer_agent, runner=mock_runner)
        ctx = _make_ctx()
        await tool.run(ctx=ctx, task="Some task")

        call_args = mock_runner.run.call_args.args
        assert call_args[0] is transfer_agent

    def test_tool_meta_is_present(self):
        from lauren_ai._tools import TOOL_META
        assert hasattr(DelegateToBankingTransfer, TOOL_META)

    def test_tool_name_is_delegate_to_banking_transfer(self):
        from lauren_ai._tools import TOOL_META
        meta = getattr(DelegateToBankingTransfer, TOOL_META)
        assert meta.name == "delegate_to_banking_transfer"

    def test_tool_schema_has_task_parameter(self):
        from lauren_ai._tools import TOOL_META
        meta = getattr(DelegateToBankingTransfer, TOOL_META)
        schema = meta.parameters
        assert "task" in schema["input_schema"]["properties"]

    def test_tool_schema_does_not_expose_ctx(self):
        from lauren_ai._tools import TOOL_META
        meta = getattr(DelegateToBankingTransfer, TOOL_META)
        schema = meta.parameters
        assert "ctx" not in schema["input_schema"]["properties"]


class TestBankingDelegationWiring:
    def test_wiring_sets_runner_on_tool(self):
        transfer_agent = MagicMock()
        tool = DelegateToBankingTransfer(transfer_agent=transfer_agent, runner=None)
        assert tool._runner is None

        mock_runner = MagicMock()
        BankingDelegationWiring(runner=mock_runner, delegation_tool=tool)

        assert tool._runner is mock_runner

    def test_wiring_does_not_create_new_tool(self):
        transfer_agent = MagicMock()
        tool = DelegateToBankingTransfer(transfer_agent=transfer_agent, runner=None)
        original_id = id(tool)

        mock_runner = MagicMock()
        BankingDelegationWiring(runner=mock_runner, delegation_tool=tool)

        assert id(tool) == original_id
