"""Unit tests for DelegateToBankingTransfer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.banking_delegation import DelegateToBankingTransfer


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


def _make_tool(user_id: str = "alice") -> tuple[DelegateToBankingTransfer, MagicMock]:
    transfer_agent = MagicMock()
    mock_runner = MagicMock()
    mock_response = AsyncMock()
    mock_response.content = "Transfer complete"
    mock_response.turns = 2
    mock_response.stop_reason = "end_turn"
    mock_runner.run = AsyncMock(return_value=mock_response)
    return DelegateToBankingTransfer(transfer_agent=transfer_agent, runner=mock_runner), mock_runner


class TestDelegateToBankingTransfer:
    @pytest.mark.asyncio
    async def test_calls_agent_and_returns_result(self):
        tool, _ = _make_tool("bob")
        ctx = _make_ctx("bob")
        result = await tool.run(ctx=ctx, task="Transfer $50 to charlie")
        assert result["result"] == "Transfer complete"
        assert result["stop_reason"] == "end_turn"

    @pytest.mark.asyncio
    async def test_runner_called_with_execution_context(self):
        tool, mock_runner = _make_tool("alice")
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
