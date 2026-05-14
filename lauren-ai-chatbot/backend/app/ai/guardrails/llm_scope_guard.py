"""LLM-based output guardrail for agent scope enforcement.

Uses a secondary LLM call to judge whether an agent's response is out of scope or
contains hallucinated facts.  More accurate than keyword matching because the judge
understands context — it catches fabricated URLs, invented phone numbers, and subtle
scope creep that fixed keyword lists miss.
"""

from __future__ import annotations

from lauren_ai import GuardrailContext, GuardrailDecision, LLMConfig, LLMGuardrail, guardrail
from lauren_ai._module import LLMService, _build_transport

from app.ai.signals import GuardrailTriggered, signal_bus as _default_bus

_JUDGE_SYSTEM = "You are a content safety auditor for a banking AI. Answer with YES or NO only."

_JUDGE_PROMPT = """\
AGENT ROLE: {agent_role}

The agent is ONLY permitted to discuss:
{allowed_scope}

The agent MUST NOT:
- Provide specific data it cannot verify (branch hours, URLs, phone numbers,
  interest rates, fees, or product details not from a real tool result)
- Fabricate websites, portals, application links, or contact details
- Answer questions clearly outside its defined role

Response to audit:
---
{content}
---

Does this response contain information the agent cannot verify, or does it answer
a question outside the agent's defined scope?
Answer YES or NO only.\
"""


@guardrail(kind="output")
class LLMScopeGuard:
    """Output guardrail that uses a secondary LLM call to detect hallucinated or
    out-of-scope responses.

    Builds on the enhanced ``LLMGuardrail`` (``action="modify"``, ``max_tokens=5``,
    ``temperature=0.0``) and adds chatbot-specific signal emission via
    ``GuardrailTriggered`` → ``EventForwarder`` → live activity feed.

    Typical usage::

        from app.ai.guardrails import LLMScopeGuard
        from app.ai.llm_config import llm_config

        @use_guardrails(output=[LLMScopeGuard(
            llm_config=llm_config,
            agent_role="Transfer Agent — executes fund transfers",
            allowed_scope=\"\"\"
            • Gathering transfer details (recipient, amount) from the customer
            • Requesting human approval via ApprovalTool
            • Executing the transfer via TransferFundsTool\"\"\",
            redirect_message="I only handle transfers. Let me transfer you to CRM.",
            guardrail_name="TransferScopeGuard",
            agent_name="Transfer Agent",
        )])

    Args:
        llm_config: LLMConfig used to build the judge's LLMService.  The same
            config (and model) as the chatbot is used; set ``max_tokens=5`` and
            ``temperature=0.0`` keep judge calls cheap and deterministic.
        agent_role: One-line description of the agent shown to the judge LLM.
        allowed_scope: Bullet-list of what the agent is allowed to say / do.
        redirect_message: User-facing replacement text returned when the guard
            fires (replaces the hallucinated response).
        guardrail_name: Label shown in the live activity feed.
        agent_name: Agent label included in the ``GuardrailTriggered`` signal.
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        agent_role: str,
        allowed_scope: str,
        redirect_message: str,
        guardrail_name: str = "LLMScopeGuard",
        agent_name: str = "Agent",
    ) -> None:
        self._guardrail_name = guardrail_name
        self._agent_name = agent_name

        _llm_service = LLMService(
            transport=_build_transport(llm_config),
            config=llm_config,
        )
        self._inner = LLMGuardrail(
            llm=_llm_service,
            prompt=_JUDGE_PROMPT.replace("{agent_role}", agent_role).replace("{allowed_scope}", allowed_scope),
            block_if="YES",
            action="modify",  # graceful redirect — no SSE error event
            violation_message=redirect_message,
            system=_JUDGE_SYSTEM,
            max_tokens=5,  # YES/NO needs at most 1 token
            temperature=0.0,  # deterministic
            guardrail_name=guardrail_name,
        )

    async def check(self, response: str, ctx: GuardrailContext) -> GuardrailDecision:
        decision = await self._inner.check(response, ctx)
        if decision.action == "modify":
            await _default_bus.emit(
                GuardrailTriggered(
                    guardrail_name=self._guardrail_name,
                    agent_name=self._agent_name,
                    violation=decision.violation or "LLM judge: out-of-scope response",
                    passed=False,
                )
            )
        else:
            # Guard evaluated but response was clean — still emit so the
            # activity feed shows every evaluation, not only interventions.
            try:
                await _default_bus.emit(
                    GuardrailTriggered(
                        guardrail_name=self._guardrail_name,
                        agent_name=self._agent_name,
                        violation="",
                        passed=True,
                    )
                )
            except Exception:  # noqa: BLE001
                pass
        return decision
