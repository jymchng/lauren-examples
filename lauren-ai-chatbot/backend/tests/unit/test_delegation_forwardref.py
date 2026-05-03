"""Tests that the ForwardRef cycle-break in delegation tools works correctly.

With ``from __future__ import annotations`` the ``runner: AgentRunner | None``
constructor annotation becomes the PEP-563 string ``"AgentRunner | None"``.
Lauren's DI container evaluates that string to the union type
``AgentRunner | None``, which has **no registered provider token**.  The
container raises ``MissingProviderError``, the parameter default (``None``)
takes effect, and the cycle edge
``AgentRunner → ToolRegistry → DelegateToResearcher → AgentRunner``
is never formed.

After startup, ``DelegationWiring`` sets ``_runner`` on both tools so they
function correctly.
"""

# No ``from __future__ import annotations`` in this file: tool schemas and
# provider registration must see real types at decoration time.

import pytest

from lauren import LaurenFactory, Scope, injectable, module
from lauren.exceptions import CircularDependencyError
from lauren_ai import LLMConfig, tool
from lauren_ai._agents._runner import AgentRunner
from lauren_ai._module import AgentModule, LLMModule
from lauren_ai._tools._registry import ToolRegistry
from lauren_ai._transport._mock import MockTransport

from app.ai.code_agent import CodeAssistantAgent
from app.ai.delegation_tools import (
    DelegateToCodeAssistant,
    DelegateToResearcher,
    DelegationWiring,
)
from app.ai.research_agent import ResearchAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_llm_module() -> type:
    """LLMModule backed by MockTransport — no network calls."""
    cfg, mock = LLMConfig.for_testing()
    return LLMModule.for_root(cfg, transport_override=mock)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestForwardRefCycleBreak:
    """ForwardRef on ``runner: AgentRunner | None = None`` prevents CircularDependencyError."""

    def test_app_boots_without_circular_dependency_error(self) -> None:
        """LaurenFactory.create() must not raise CircularDependencyError.

        Without the ForwardRef cycle-break a plain ``runner: AgentRunner``
        constructor annotation would cause:
            CircularDependencyError:
              AgentRunner → ToolRegistry → DelegateToResearcher → AgentRunner
        """
        LLMProvider = _make_test_llm_module()
        AgentProvider = AgentModule.for_root(
            agents=[ResearchAgent, CodeAssistantAgent],
            tools=[DelegateToResearcher, DelegateToCodeAssistant],
            imports=LLMProvider,
        )

        @module(
            imports=[LLMProvider, AgentProvider],
            providers=[DelegationWiring],
        )
        class TestModule: ...

        # Must not raise CircularDependencyError
        app = LaurenFactory.create(TestModule)
        assert app is not None

    def test_runner_is_none_before_delegation_wiring(self) -> None:
        """Without DelegationWiring the runner defaults to None via ForwardRef."""
        # Build tools without DelegationWiring to confirm the ForwardRef default
        research = ResearchAgent()
        code = CodeAssistantAgent()
        delegate = DelegateToResearcher(research=research)
        assert delegate._runner is None

    def test_delegation_wiring_sets_runner(self) -> None:
        """DelegationWiring wires the AgentRunner into both delegation tools."""
        cfg, mock = LLMConfig.for_testing()
        registry = ToolRegistry()
        runner = AgentRunner(
            transport=mock,
            registry=registry,
            config=cfg,
        )

        research = ResearchAgent()
        code = CodeAssistantAgent()
        delegate_researcher = DelegateToResearcher(research=research)
        delegate_code = DelegateToCodeAssistant(code=code)

        # Before wiring
        assert delegate_researcher._runner is None
        assert delegate_code._runner is None

        # Wire
        DelegationWiring(
            runner=runner,
            delegate_researcher=delegate_researcher,
            delegate_code=delegate_code,
        )

        # After wiring
        assert delegate_researcher._runner is runner
        assert delegate_code._runner is runner

    @pytest.mark.asyncio
    async def test_full_module_graph_wires_runner_at_startup(self) -> None:
        """In a real module graph DelegationWiring fires during lifecycle startup."""
        LLMProvider = _make_test_llm_module()
        AgentProvider = AgentModule.for_root(
            agents=[ResearchAgent, CodeAssistantAgent],
            tools=[DelegateToResearcher, DelegateToCodeAssistant],
            imports=LLMProvider,
        )

        @module(
            imports=[LLMProvider, AgentProvider],
            providers=[DelegationWiring],
            exports=[DelegateToResearcher, DelegateToCodeAssistant],
        )
        class TestModule: ...

        app = LaurenFactory.create(TestModule)
        # startup() triggers the lifecycle scheduler which eagerly instantiates
        # DelegationWiring and wires AgentRunner into the delegation tools.
        await app.startup()

        tool_instance = await app.container.resolve(DelegateToResearcher)
        assert tool_instance._runner is not None, (
            "DelegationWiring should have set _runner during lifecycle startup"
        )
