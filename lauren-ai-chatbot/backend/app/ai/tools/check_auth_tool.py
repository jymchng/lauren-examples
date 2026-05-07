
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""CheckAuthenticationTool — server-side session authentication check.

Identity is read exclusively from the server-side execution context set by
``SignatureGuard``.  The LLM never supplies or influences identity values.
"""

from lauren_ai import ToolContext, tool


@tool()
class CheckAuthenticationTool:
    """Check whether the current user session is authenticated.

    Returns the authenticated status and identity from the verified server-side
    execution context.  The LLM never supplies identity — only the server can
    confirm it.

    Args:
        (none — identity is read from server-side context only)
    """

    async def run(self, ctx: ToolContext) -> dict:
        if ctx.execution_context and ctx.execution_context.request and ctx.execution_context.request.state:
            uid = ctx.execution_context.request.state.get("user_id")
            name = ctx.execution_context.request.state.get("user_name")
            if uid:
                return {"authenticated": True, "user_id": uid, "user_name": name}
        return {"authenticated": False}
