"""Generic output guardrail that prevents specialist agents from emitting
hallucinated off-topic responses.
"""

from __future__ import annotations

from lauren_ai import GuardrailContext, GuardrailDecision, guardrail

from app.ai.signals import GuardrailTriggered, signal_bus as _default_bus


@guardrail(kind="output")
class AgentScopeGuard:
    """Configurable output guardrail for agent scope enforcement.

    When an agent's response contains any of the ``off_topic_phrases``, the
    guardrail replaces it with ``redirect_message`` and emits a
    ``GuardrailTriggered`` signal so the live activity feed can be updated.

    Construct one instance per agent and pass it to ``@use_guardrails``::

        @use_guardrails(output=[AgentScopeGuard(
            off_topic_phrases=_TRANSFER_OFF_TOPIC,
            redirect_message=_TRANSFER_REDIRECT,
            guardrail_name="TransferScopeGuard",
            agent_name="Transfer Agent",
        )])

    Args:
        off_topic_phrases: Lowercase substrings that indicate an off-topic
            response.  Matched against the lowercased response text.
        redirect_message: User-facing replacement text (action="modify").
        guardrail_name: Label shown in the live activity feed.
        agent_name: Agent label included in the emitted signal.
    """

    def __init__(
        self,
        off_topic_phrases: tuple[str, ...],
        redirect_message: str,
        guardrail_name: str = "AgentScopeGuard",
        agent_name: str = "Agent",
    ) -> None:
        self._phrases = off_topic_phrases
        self._redirect = redirect_message
        self._guardrail_name = guardrail_name
        self._agent_name = agent_name

    async def check(self, response: str, ctx: GuardrailContext) -> GuardrailDecision:
        lower = response.lower()
        for phrase in self._phrases:
            if phrase in lower:
                violation = f"Off-topic phrase detected: '{phrase}'"
                try:
                    await _default_bus.emit(
                        GuardrailTriggered(
                            guardrail_name=self._guardrail_name,
                            agent_name=self._agent_name,
                            violation=violation,
                        )
                    )
                except Exception:  # noqa: BLE001
                    pass  # signal emission is best-effort; never crash the guardrail
                return GuardrailDecision(
                    action="modify",
                    modified_content=self._redirect,
                    violation=violation,
                    guardrail_name=self._guardrail_name,
                )
        # No phrase matched — emit a "passed" signal so the activity feed shows
        # every guardrail evaluation, not just interventions.
        # Skip when _phrases is empty (no actual evaluation performed).
        if self._phrases:
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
        return GuardrailDecision(action="pass", guardrail_name=self._guardrail_name)
