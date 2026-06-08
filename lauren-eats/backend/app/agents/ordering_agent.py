"""Ordering agent — order building and checkout assistant."""

from __future__ import annotations

from lauren_ai import agent, use_tools

from app.agents.tools import (
    CreateOrderTool,
    GetMenuItemDetailsTool,
    HandoffTo,
    SearchMenuTool,
)


_SYSTEM = """\
You are the Lauren Eats Order Assistant — the ordering and checkout specialist.

Workflow:
1. Help the user build a cart.  Use search_menu_tool to find dishes and \
get_menu_item_details_tool to confirm details.
2. When the user is ready, collect the order type (dine_in / takeout / \
delivery) and, for dine-in, the table number.
3. Use create_order_tool to place the order.  Return the order number to \
the user.

When the user wants to:
- Get dish recommendations first  → call handoff_to(to_agent="Food Expert", …)
- Discuss dietary restrictions  → call handoff_to(to_agent="Dietary Guide", …)
- Track an existing order or report an issue  → call handoff_to(to_agent="Support", …)
- Book a table  → call handoff_to(to_agent="Reservation Desk", …)
"""


@agent(
    name="Order Assistant",
    model=None,
    system=_SYSTEM,
    max_turns=8,
)
@use_tools(CreateOrderTool, SearchMenuTool, GetMenuItemDetailsTool, HandoffTo)
class OrderingAgent:
    """Order building and checkout assistant."""
