"""Order service — CRUD operations for orders."""

from __future__ import annotations

import uuid
import time
import random
import string
from lauren import injectable, Scope
from app.db.database import DatabaseService


def _new_id() -> str:
    return uuid.uuid4().hex[:25]


def _generate_order_number() -> str:
    ts = int(time.time())
    ts36 = ""
    n = ts
    while n > 0:
        n, r = divmod(n, 36)
        ts36 = string.digits + string.ascii_lowercase
        ts36 = ""
    # Simpler approach
    import base36
    ...  # fallback to hex
    return f"LE-{hex(ts)[2:].upper()}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"


def _row_to_order(row: dict) -> dict:
    return {
        "id": row.get("id", ""),
        "userId": row.get("user_id"),
        "orderNumber": row.get("order_number", ""),
        "status": row.get("status", "pending"),
        "totalAmount": row.get("total_amount", 0),
        "subtotal": row.get("subtotal", 0),
        "tax": row.get("tax", 0),
        "discount": row.get("discount", 0),
        "notes": row.get("notes"),
        "type": row.get("type", "dine_in"),
        "tableNumber": row.get("table_number"),
        "createdAt": row.get("created_at", ""),
        "updatedAt": row.get("updated_at", ""),
    }


def _row_to_order_item(row: dict) -> dict:
    return {
        "id": row.get("id", ""),
        "orderId": row.get("order_id", ""),
        "menuItemId": row.get("menu_item_id", ""),
        "quantity": row.get("quantity", 1),
        "unitPrice": row.get("unit_price", 0),
        "totalPrice": row.get("total_price", 0),
        "notes": row.get("notes"),
        "createdAt": row.get("created_at", ""),
    }


@injectable(scope=Scope.SINGLETON)
class OrderService:
    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def list_orders(self, status: str | None = None, user_id: str | None = None) -> list[dict]:
        conditions = []
        params: list = []
        if status:
            conditions.append("o.status = ?")
            params.append(status)
        if user_id:
            conditions.append("o.user_id = ?")
            params.append(user_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT o.* FROM orders o
            {where}
            ORDER BY o.created_at DESC
        """
        rows = await self._db.fetch_all(sql, tuple(params))
        orders = [_row_to_order(r) for r in rows]

        for order in orders:
            order["orderItems"] = await self._get_order_items(order["id"])
            order["user"] = await self._get_order_user(order.get("userId"))

        return orders

    async def get_order(self, order_id: str) -> dict | None:
        row = await self._db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        if row is None:
            return None
        order = _row_to_order(row)
        order["orderItems"] = await self._get_order_items(order_id)
        order["user"] = await self._get_order_user(order.get("userId"))
        return order

    async def create_order(self, data: dict) -> dict:
        items = data.get("items", [])
        order_type = data.get("type", "dine_in")

        if not items:
            raise ValueError("Order must contain at least one item")
        if order_type not in ("dine_in", "takeout", "delivery"):
            raise ValueError("Valid order type is required")

        # Fetch menu items — keys may be camelCase (from Pydantic by_alias)
        # or snake_case (from a hand-rolled dict).
        def _item_id(it: dict) -> str:
            return it.get("menuItemId") or it.get("menu_item_id")

        menu_item_ids = [_item_id(it) for it in items]
        if any(mid is None for mid in menu_item_ids):
            raise ValueError("Each item needs a `menuItemId`")
        placeholders = ",".join(["?"] * len(menu_item_ids))
        menu_rows = await self._db.fetch_all(
            f"SELECT * FROM menu_items WHERE id IN ({placeholders}) AND is_available = 1",
            tuple(menu_item_ids),
        )
        menu_map = {r["id"]: r for r in menu_rows}

        if len(menu_rows) != len(menu_item_ids):
            raise ValueError("One or more menu items are unavailable")

        # Build order items
        order_items_data = []
        for it in items:
            mi = menu_map[_item_id(it)]
            qty = it.get("quantity", 1)
            total_price = round(mi["price"] * qty, 2)
            order_items_data.append({
                "id": _new_id(),
                "menu_item_id": _item_id(it),
                "quantity": qty,
                "unit_price": mi["price"],
                "total_price": total_price,
                "notes": it.get("notes"),
            })

        subtotal = round(sum(oi["total_price"] for oi in order_items_data), 2)
        tax = round(subtotal * 0.08, 2)
        total_amount = round(subtotal + tax, 2)

        order_id = _new_id()
        order_number = f"LE-{hex(int(time.time()))[2:].upper()}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

        await self._db.execute(
            """INSERT INTO orders (id, user_id, order_number, status, total_amount, subtotal, tax, discount, notes, type, table_number)
               VALUES (?, ?, ?, 'pending', ?, ?, ?, 0, ?, ?, ?)""",
            (order_id, data.get("userId") or data.get("user_id"), order_number, total_amount, subtotal, tax,
             data.get("notes"), order_type, data.get("tableNumber") or data.get("table_number")),
        )

        for oi in order_items_data:
            await self._db.execute(
                """INSERT INTO order_items (id, order_id, menu_item_id, quantity, unit_price, total_price, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (oi["id"], order_id, oi["menu_item_id"], oi["quantity"],
                 oi["unit_price"], oi["total_price"], oi.get("notes")),
            )

        return await self.get_order(order_id)  # type: ignore

    async def update_order_status(self, order_id: str, status: str) -> dict | None:
        valid = {"pending", "confirmed", "preparing", "ready", "delivered", "cancelled"}
        if status not in valid:
            raise ValueError(f"Valid status is required ({', '.join(valid)})")

        existing = await self._db.fetch_one("SELECT id FROM orders WHERE id = ?", (order_id,))
        if existing is None:
            return None

        await self._db.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, order_id),
        )
        return await self.get_order(order_id)

    async def _get_order_items(self, order_id: str) -> list[dict]:
        rows = await self._db.fetch_all(
            """SELECT oi.*, mi.name as mi_name, mi.name_zh as mi_name_zh, mi.price as mi_price,
                      mi.image as mi_image, mi.description as mi_desc
               FROM order_items oi
               LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
               WHERE oi.order_id = ?""",
            (order_id,),
        )
        items = []
        for row in rows:
            item = _row_to_order_item(row)
            item["menuItem"] = {
                "id": row.get("menu_item_id", ""),
                "name": row.get("mi_name", ""),
                "nameZh": row.get("mi_name_zh"),
                "price": row.get("mi_price", 0),
                "image": row.get("mi_image"),
                "description": row.get("mi_desc", ""),
            }
            items.append(item)
        return items

    async def _get_order_user(self, user_id: str | None) -> dict | None:
        if not user_id:
            return None
        row = await self._db.fetch_one("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
        if row is None:
            return None
        return {"id": row["id"], "name": row["name"], "email": row["email"]}
