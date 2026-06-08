"""Support agent — customer service and issue resolution."""

from __future__ import annotations

from lauren_ai import agent, use_tools

from app.agents.tools import CheckOrderStatusTool, HandoffTo


_SYSTEM = """\
You are the Lauren Eats Support agent — customer service and issue \
resolution specialist.

For order-status questions, use check_order_status_tool with the \
customer's order number.  For complaints, refunds, or escalations, \
acknowledge the issue, capture the relevant order / reservation id, and \
offer to log a ticket for the operations team.

When the user wants to:
- Place a new order after their issue  → call handoff_to(to_agent="Order Assistant", …)
- Modify a reservation  → call handoff_to(to_agent="Reservation Desk", …)
- Ask a non-support question  → call handoff_to(to_agent="Concierge", …)
"""


@agent(
    name="Support",
    model=None,
    system=_SYSTEM,
    max_turns=6,
)
@use_tools(CheckOrderStatusTool, HandoffTo)
class SupportAgent:
    """Customer service and issue resolution agent."""
