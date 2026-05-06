# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""HandoffToAuthenticatedCRM — auth-enforced handoff to the Authenticated CRM Agent.

Subclasses HandoffTo to reuse ActiveAgentStore and EventForwarder DI deps.
Re-applies @tool() to get its own TOOL_META and DI token (strict-inheritance rule).
"""

from lauren_ai import ToolContext, tool

from app.ai.agent_names import AUTH_CRM_AGENT_NAME
from app.ai.tools.handoff_tool import HandoffTo


@tool()
class HandoffToAuthenticatedCRM(HandoffTo):
    """Transfer the conversation to the Authenticated CRM Agent.

    Only succeeds when the current session is authenticated.  If the user has
    not logged in, returns an instruction to the agent to guide the user to
    authenticate first — no handoff is performed.

    Args:
        summary: Brief summary of the conversation so far and why handing off.
    """

    _target_names = (AUTH_CRM_AGENT_NAME,)

    async def run(self, ctx: ToolContext, summary: str) -> dict:
        uid = (
            ctx.execution_context.request.state.get("user_id")
            if ctx.execution_context
            and ctx.execution_context.request
            and ctx.execution_context.request.state
            else None
        )
        if not uid:
            return {
                "status": "auth_required",
                "message": "The user is not authenticated. Ask them to log in before transferring.",
            }
        return await self._run_handoff(ctx, AUTH_CRM_AGENT_NAME, summary)
