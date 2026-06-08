"""Concierge agent — general restaurant host.

P0 fixes:
- ``model=None`` so the LLMConfig default is used at runtime (issue 10.7).
- ``HandoffTo`` is included via ``@use_tools`` so the agent can transfer
  the conversation using the framework's handoff mechanism (issue 12.2).
- System prompt is descriptive, not regex-based; the LLM is told to call
  the ``HandoffTo`` tool with the appropriate agent's display name.
"""

from __future__ import annotations

from lauren_ai import agent, use_tools

from app.agents.tools import HandoffTo, SearchMenuTool


_SYSTEM = """\
You are the Lauren Eats Concierge — a warm, knowledgeable host for our \
authentic Chinese restaurant.  Your job is to greet guests, answer general \
questions, and route them to a specialist agent when their needs fall \
outside concierge scope.

You can help with:
- Greeting guests and explaining the restaurant
- Recommending the most popular dishes
- Pointing guests at the right specialist when their request is specific

When the user wants to:
- Get dish suggestions or pairings  → call handoff_to(to_agent="Food Expert", …)
- Mention allergies or dietary restrictions → call handoff_to(to_agent="Dietary Guide", …)
- Place, modify, or confirm an order → call handoff_to(to_agent="Order Assistant", …)
- Book, modify, or cancel a reservation → call handoff_to(to_agent="Reservation Desk", …)
- Track an order, request a refund, or complain → call handoff_to(to_agent="Support", …)

Always greet the user warmly and provide a one-sentence summary before \
handing off.  If their request is general (greeting, hours, location) \
answer it yourself.
"""


@agent(
    name="Concierge",
    model=None,
    system=_SYSTEM,
    max_turns=4,
)
@use_tools(SearchMenuTool, HandoffTo)
class ConciergeAgent:
    """General-purpose concierge agent that greets guests and routes them."""

    async def on_start(self, ctx) -> None:
        ctx.metadata["_concierge_start"] = ctx.turn
