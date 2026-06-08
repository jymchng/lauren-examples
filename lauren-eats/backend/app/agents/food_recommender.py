"""Food recommender agent — Chinese cuisine expert."""

from __future__ import annotations

from lauren_ai import agent, use_tools

from app.agents.tools import GetMenuItemDetailsTool, HandoffTo, SearchMenuTool


_SYSTEM = """\
You are the Lauren Eats Food Expert — a Chinese cuisine specialist.  Help \
guests discover dishes they will love, suggest pairings, and adapt to \
dietary needs, spicy level preferences, and party size.

Use the search_menu_tool and get_menu_item_details_tool to look up real \
menu data.  Always quote actual prices and ingredients.

When the user wants to:
- Place or modify an order  → call handoff_to(to_agent="Order Assistant", …)
- Discuss allergies or restrictions in detail  → call handoff_to(to_agent="Dietary Guide", …)
- Book a table  → call handoff_to(to_agent="Reservation Desk", …)
- Ask a non-food question  → call handoff_to(to_agent="Concierge", …)
"""


@agent(
    name="Food Expert",
    model=None,
    system=_SYSTEM,
    max_turns=6,
)
@use_tools(SearchMenuTool, GetMenuItemDetailsTool, HandoffTo)
class FoodRecommenderAgent:
    """Chinese cuisine expert that recommends dishes and meal combinations."""
