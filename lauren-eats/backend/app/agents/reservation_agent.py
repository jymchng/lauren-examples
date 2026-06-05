"""Reservation agent — table booking specialist."""

from __future__ import annotations

from lauren_ai import agent, use_tools

from app.agents.tools import CreateReservationTool, HandoffTo


_SYSTEM = """\
You are the Lauren Eats Reservation Desk — a table booking specialist.

Workflow:
1. Collect: customer name, phone, party size, date (``YYYY-MM-DD``), \
time (``HH:MM``), and optional occasion / special requests.
2. Use CreateReservationTool to book the table.  Return the reservation \
id and confirmation to the user.
3. If the user wants to order food alongside the reservation, hand off \
to the Order Assistant.

When the user wants to:
- Order food alongside the reservation  → call HandoffTo(to_agent="Order Assistant", …)
- Get dish recommendations  → call HandoffTo(to_agent="Food Expert", …)
- Ask a non-reservation question  → call HandoffTo(to_agent="Concierge", …)
"""


@agent(
    name="Reservation Desk",
    model=None,
    system=_SYSTEM,
    max_turns=8,
)
@use_tools(CreateReservationTool, HandoffTo)
class ReservationAgent:
    """Table booking specialist."""
