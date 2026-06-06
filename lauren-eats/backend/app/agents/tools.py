"""Agent tools for the Lauren Eats restaurant platform.

P0 fixes:
- All tools are class-form with DI constructor injection (issues 11.1, 11.2).
- All tools execute against the live database — no more stubs (issues 11.3, 11.4).
- Handoff uses the framework's :class:`HandoffTo` tool (issue 12.1), not
  a regex-based ``<<HANDOFF:agent_type>>`` extraction.

Tools depend only on :class:`DatabaseService` (in :mod:`app.db.database`)
so :class:`app.ai.ai_module.AIModule` only needs to import
:class:`app.modules.DatabaseModule` — no cross-feature coupling.
"""

from __future__ import annotations

import json
from typing import ClassVar

from lauren import Scope, injectable
from lauren_ai import ToolContext, tool

from app.db.database import DatabaseService


# ---------------------------------------------------------------------------
# Menu tools
# ---------------------------------------------------------------------------


@tool()
@injectable(scope=Scope.SINGLETON)
class SearchMenuTool:
    """Search the menu for dishes matching a query.

    Args:
        query: Free-text search applied to name, Chinese name, and description.
        category: Optional category slug (``"appetizers"``, ``"dim-sum"`` …).
        limit: Maximum number of items to return.  Defaults to ``8``.
    """

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def run(
        self,
        ctx: ToolContext,
        query: str = "",
        category: str = "",
        limit: int = 8,
    ) -> dict:
        if not query and not category:
            return {
                "query": query,
                "category": category or None,
                "count": 0,
                "items": [],
                "message": "Provide a search query or category.",
            }

        conditions = ["mi.is_available = 1"]
        params: list = []

        if category and category != "all":
            conditions.append("c.slug = ?")
            params.append(category)
        if query:
            conditions.append("(mi.name LIKE ? OR mi.name_zh LIKE ? OR mi.description LIKE ?)")
            params.extend([f"%{query}%"] * 3)

        where = " AND ".join(conditions)
        max_items = max(1, min(50, int(limit)))
        sql = f"""
            SELECT mi.id, mi.name, mi.name_zh, mi.description, mi.price,
                   mi.spicy_level, mi.is_vegetarian, mi.is_vegan,
                   mi.is_gluten_free, mi.is_popular, mi.image
            FROM menu_items mi
            LEFT JOIN categories c ON mi.category_id = c.id
            WHERE {where}
            ORDER BY mi.is_popular DESC, mi.name ASC
            LIMIT ?
        """
        rows = await self._db.fetch_all(sql, tuple(params + [max_items]))
        return {
            "query": query,
            "category": category or None,
            "count": len(rows),
            "items": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "nameZh": r["name_zh"],
                    "description": r.get("description", ""),
                    "price": r["price"],
                    "spicyLevel": r.get("spicy_level", 0),
                    "isVegetarian": bool(r.get("is_vegetarian", 0)),
                    "isVegan": bool(r.get("is_vegan", 0)),
                    "isGlutenFree": bool(r.get("is_gluten_free", 0)),
                    "isPopular": bool(r.get("is_popular", 0)),
                    "image": r.get("image"),
                }
                for r in rows
            ],
        }


@tool()
@injectable(scope=Scope.SINGLETON)
class GetMenuItemDetailsTool:
    """Look up a single menu item by id or by exact name.

    Args:
        item_id: Menu item id (preferred).
        item_name: Menu item name — used as a fallback when *item_id* is
            empty and resolved via case-insensitive match.
    """

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def run(
        self,
        ctx: ToolContext,
        item_id: str = "",
        item_name: str = "",
    ) -> dict:
        if not item_id and not item_name:
            return {"error": "Provide either item_id or item_name."}

        if item_id:
            row = await self._db.fetch_one(
                "SELECT mi.*, c.name AS cat_name, c.name_zh AS cat_name_zh, "
                "c.slug AS cat_slug FROM menu_items mi "
                "LEFT JOIN categories c ON mi.category_id = c.id "
                "WHERE mi.id = ?",
                (item_id,),
            )
            if row is None:
                return {"error": f"No menu item with id {item_id!r}."}
            return {"item": _row_to_item(row)}

        # Fallback: case-insensitive name match.
        row = await self._db.fetch_one(
            "SELECT mi.*, c.name AS cat_name, c.name_zh AS cat_name_zh, "
            "c.slug AS cat_slug FROM menu_items mi "
            "LEFT JOIN categories c ON mi.category_id = c.id "
            "WHERE LOWER(mi.name) = LOWER(?) OR LOWER(mi.name_zh) = LOWER(?) "
            "ORDER BY mi.is_popular DESC LIMIT 1",
            (item_name, item_name),
        )
        if row is None:
            # Last-ditch fuzzy match.
            row = await self._db.fetch_one(
                "SELECT mi.*, c.name AS cat_name, c.name_zh AS cat_name_zh, "
                "c.slug AS cat_slug FROM menu_items mi "
                "LEFT JOIN categories c ON mi.category_id = c.id "
                "WHERE mi.name LIKE ? OR mi.name_zh LIKE ? "
                "ORDER BY mi.is_popular DESC LIMIT 1",
                (f"%{item_name}%", f"%{item_name}%"),
            )
        if row is None:
            return {"error": f"No menu item found for name {item_name!r}."}
        return {"item": _row_to_item(row)}


@tool()
@injectable(scope=Scope.SINGLETON)
class CheckDietaryInfoTool:
    """Return allergen / dietary flags for a dish.

    Args:
        dish_name: Name of the dish to check.
    """

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def run(self, ctx: ToolContext, dish_name: str) -> dict:
        if not dish_name:
            return {"error": "dish_name is required."}
        row = await self._db.fetch_one(
            "SELECT name, name_zh, is_vegetarian, is_vegan, is_gluten_free, "
            "spicy_level, calories, preparation_time, ingredients, allergens, tags "
            "FROM menu_items WHERE LOWER(name) = LOWER(?) OR LOWER(name_zh) = LOWER(?) "
            "OR name LIKE ? OR name_zh LIKE ? "
            "ORDER BY is_popular DESC LIMIT 1",
            (dish_name, dish_name, f"%{dish_name}%", f"%{dish_name}%"),
        )
        if row is None:
            return {
                "dish": dish_name,
                "found": False,
                "message": "Dish not found in menu.",
            }
        return {
            "dish": row["name"],
            "nameZh": row["name_zh"],
            "found": True,
            "isVegetarian": bool(row.get("is_vegetarian", 0)),
            "isVegan": bool(row.get("is_vegan", 0)),
            "isGlutenFree": bool(row.get("is_gluten_free", 0)),
            "spicyLevel": row.get("spicy_level", 0),
            "calories": row.get("calories"),
            "preparationTime": row.get("preparation_time"),
            "ingredients": _safe_json(row.get("ingredients")),
            "allergens": _safe_json(row.get("allergens")),
            "tags": _safe_json(row.get("tags")),
        }


# ---------------------------------------------------------------------------
# Order tools
# ---------------------------------------------------------------------------


@tool()
@injectable(scope=Scope.SINGLETON)
class CreateOrderTool:
    """Create a new order.

    Args:
        items: Order items.  Each entry is a ``{"menuItemId": str,
            "quantity": int, "notes": str}`` dict.
        order_type: One of ``"dine_in"``, ``"takeout"``, ``"delivery"``.
        table_number: Table number (for ``dine_in`` orders).
        notes: Free-text notes for the kitchen.
    """

    _ORDER_TYPES = ("dine_in", "takeout", "delivery")

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def run(
        self,
        ctx: ToolContext,
        items: list[dict],
        order_type: str = "dine_in",
        table_number: str = "",
        notes: str = "",
    ) -> dict:
        if not items:
            return {"error": "Order must contain at least one item."}
        if order_type not in self._ORDER_TYPES:
            return {"error": f"Invalid order type {order_type!r}. Valid: {self._ORDER_TYPES}"}

        # Normalise + validate menu item ids.
        order_items: list[dict] = []
        for raw in items:
            mid = raw.get("menuItemId") or raw.get("menu_item_id")
            if not mid:
                return {"error": "Each item needs a `menuItemId`."}
            qty = int(raw.get("quantity", 1))
            if qty < 1:
                return {"error": f"Quantity must be >= 1 (got {qty})."}
            order_items.append(
                {
                    "id": _new_id(),
                    "menu_item_id": mid,
                    "quantity": qty,
                    "notes": raw.get("notes"),
                }
            )

        # Look up menu items (preserves order).
        menu_item_ids = [oi["menu_item_id"] for oi in order_items]
        placeholders = ",".join(["?"] * len(menu_item_ids))
        rows = await self._db.fetch_all(
            f"SELECT id, price, is_available FROM menu_items WHERE id IN ({placeholders})",
            tuple(menu_item_ids),
        )
        menu_map = {r["id"]: r for r in rows}
        if len(rows) != len(menu_item_ids):
            missing = set(menu_item_ids) - set(menu_map.keys())
            return {"error": f"Menu items not found: {sorted(missing)}"}
        for r in rows:
            if not r.get("is_available", 1):
                return {"error": f"Menu item {r['id']!r} is unavailable."}

        # Build order items with prices.
        for oi in order_items:
            mi = menu_map[oi["menu_item_id"]]
            oi["unit_price"] = mi["price"]
            oi["total_price"] = round(mi["price"] * oi["quantity"], 2)

        subtotal = round(sum(oi["total_price"] for oi in order_items), 2)
        tax = round(subtotal * 0.08, 2)
        total_amount = round(subtotal + tax, 2)

        order_id = _new_id()
        order_number = _new_order_number()
        await self._db.execute(
            "INSERT INTO orders (id, order_number, status, total_amount, "
            "subtotal, tax, discount, notes, type, table_number) "
            "VALUES (?, ?, 'pending', ?, ?, ?, 0, ?, ?, ?)",
            (
                order_id,
                order_number,
                total_amount,
                subtotal,
                tax,
                notes or None,
                order_type,
                table_number or None,
            ),
        )
        for oi in order_items:
            await self._db.execute(
                "INSERT INTO order_items (id, order_id, menu_item_id, quantity, "
                "unit_price, total_price, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    oi["id"],
                    order_id,
                    oi["menu_item_id"],
                    oi["quantity"],
                    oi["unit_price"],
                    oi["total_price"],
                    oi.get("notes"),
                ),
            )
        return {
            "orderCreated": True,
            "orderId": order_id,
            "orderNumber": order_number,
            "totalAmount": total_amount,
            "subtotal": subtotal,
            "tax": tax,
            "status": "pending",
        }


@tool()
@injectable(scope=Scope.SINGLETON)
class CheckOrderStatusTool:
    """Look up an order by its order number (e.g. ``LE-XXXX-AB12``).

    Args:
        order_number: The order number to look up.
    """

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def run(self, ctx: ToolContext, order_number: str) -> dict:
        if not order_number:
            return {"error": "order_number is required."}
        row = await self._db.fetch_one(
            "SELECT id, order_number, status, type, total_amount, created_at "
            "FROM orders WHERE order_number = ?",
            (order_number,),
        )
        if row is None:
            return {
                "orderNumber": order_number,
                "found": False,
                "message": "Order not found.",
            }
        return {
            "orderNumber": row["order_number"],
            "status": row["status"],
            "type": row["type"],
            "totalAmount": row["total_amount"],
            "createdAt": row["created_at"],
            "found": True,
        }


# ---------------------------------------------------------------------------
# Reservation tool
# ---------------------------------------------------------------------------


_VALID_OCCASIONS = ("birthday", "anniversary", "business", "casual")
_DATE_RE = None
_TIME_RE = None


def _date_re():
    import re

    global _DATE_RE
    if _DATE_RE is None:
        _DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    return _DATE_RE


def _time_re():
    import re

    global _TIME_RE
    if _TIME_RE is None:
        _TIME_RE = re.compile(r"^\d{2}:\d{2}$")
    return _TIME_RE


@tool()
@injectable(scope=Scope.SINGLETON)
class CreateReservationTool:
    """Create a table reservation.

    Args:
        customer_name: Guest name.
        customer_phone: Guest phone number.
        party_size: Number of guests (1–20).
        date: Reservation date in ``YYYY-MM-DD`` format.
        time: Reservation time in ``HH:MM`` (24-hour) format.
        customer_email: Optional email.
        occasion: Optional — ``birthday``, ``anniversary``, ``business``,
            ``casual``.
        special_requests: Free-text special requests.
    """

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def run(
        self,
        ctx: ToolContext,
        customer_name: str,
        customer_phone: str,
        party_size: int,
        date: str,
        time: str,
        customer_email: str = "",
        occasion: str = "",
        special_requests: str = "",
    ) -> dict:
        if not customer_name:
            return {"error": "customer_name is required."}
        if not customer_phone:
            return {"error": "customer_phone is required."}
        try:
            party_size_int = int(party_size)
        except (TypeError, ValueError):
            return {"error": "party_size must be an integer."}
        if party_size_int < 1 or party_size_int > 20:
            return {"error": "party_size must be between 1 and 20."}
        if not _date_re().match(date or ""):
            return {"error": "date must be in YYYY-MM-DD format."}
        if not _time_re().match(time or ""):
            return {"error": "time must be in HH:MM format."}
        if occasion and occasion not in _VALID_OCCASIONS:
            return {"error": f"Invalid occasion {occasion!r}. Valid: {list(_VALID_OCCASIONS)}"}

        reservation_id = _new_id()
        await self._db.execute(
            "INSERT INTO reservations (id, customer_name, customer_phone, "
            "customer_email, party_size, date, time, status, "
            "special_requests, occasion) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (
                reservation_id,
                customer_name,
                customer_phone,
                customer_email or None,
                party_size_int,
                date,
                time,
                special_requests or None,
                occasion or None,
            ),
        )
        return {
            "reservationCreated": True,
            "reservationId": reservation_id,
            "status": "pending",
            "customerName": customer_name,
            "partySize": party_size_int,
            "date": date,
            "time": time,
        }


# ---------------------------------------------------------------------------
# Handoff tool — replaces <<HANDOFF:agent_type>> regex (P0 12.1)
# ---------------------------------------------------------------------------


_DISPLAY_NAMES: dict[str, str] = {
    "concierge": "Concierge",
    "food_recommender": "Food Expert",
    "dietary": "Dietary Guide",
    "ordering": "Order Assistant",
    "reservation": "Reservation Desk",
    "support": "Support",
}


@tool()
@injectable(scope=Scope.SINGLETON)
class HandoffTo:
    """Hand the conversation off to a specialist agent.

    Args:
        to_agent: The display name of the agent to hand off to.  Must be
            one of the values listed in the schema.
        summary: Brief summary of the conversation so far.
    """

    _target_names: ClassVar[tuple[str, ...]] = tuple(_DISPLAY_NAMES.values())
    _by_name: ClassVar[dict[str, str]] = {v: k for k, v in _DISPLAY_NAMES.items()}

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def run(self, ctx: ToolContext, to_agent: str, summary: str) -> dict:
        if to_agent not in self._target_names:
            return {
                "error": f"Unknown agent {to_agent!r}. Valid choices: {list(self._target_names)}",
            }

        agent_type = self._by_name[to_agent]
        conversation_id = ""
        if ctx.agent_context is not None and ctx.agent_context.metadata:
            conversation_id = ctx.agent_context.metadata.get("conversation_id", "")

        if conversation_id:
            await self._db.execute(
                "UPDATE conversations SET agent_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (agent_type, conversation_id),
            )
        return {
            "status": "handed_off",
            "to_agent": to_agent,
            "summary": summary,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


import secrets
import string
import uuid


def _new_id() -> str:
    return uuid.uuid4().hex[:25]


def _new_order_number() -> str:
    """Generate a unique order number of the form ``LE-HEX-XXXX``."""
    import time as _time

    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"LE-{hex(int(_time.time()))[2:].upper()}-{suffix}"


def _safe_json(value):
    """Decode a JSON-encoded column or return the value as-is."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def _row_to_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "nameZh": row.get("name_zh"),
        "description": row.get("description", ""),
        "price": row.get("price"),
        "image": row.get("image"),
        "spicyLevel": row.get("spicy_level", 0),
        "isVegetarian": bool(row.get("is_vegetarian", 0)),
        "isVegan": bool(row.get("is_vegan", 0)),
        "isGlutenFree": bool(row.get("is_gluten_free", 0)),
        "isPopular": bool(row.get("is_popular", 0)),
        "isAvailable": bool(row.get("is_available", 1)),
        "calories": row.get("calories"),
        "preparationTime": row.get("preparation_time"),
        "category": {
            "name": row.get("cat_name"),
            "nameZh": row.get("cat_name_zh"),
            "slug": row.get("cat_slug"),
        }
        if row.get("cat_name") is not None
        else None,
    }


# Re-export the field that ``AgentModule.for_root`` reads from the class.
TOOL_REGISTRY = (
    SearchMenuTool,
    GetMenuItemDetailsTool,
    CheckDietaryInfoTool,
    CreateOrderTool,
    CheckOrderStatusTool,
    CreateReservationTool,
    HandoffTo,
)

__all__ = [
    "SearchMenuTool",
    "GetMenuItemDetailsTool",
    "CheckDietaryInfoTool",
    "CreateOrderTool",
    "CheckOrderStatusTool",
    "CreateReservationTool",
    "HandoffTo",
    "TOOL_REGISTRY",
]
