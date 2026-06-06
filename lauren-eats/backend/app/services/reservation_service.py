"""Reservation service — CRUD operations for reservations."""

from __future__ import annotations

import uuid
from lauren import injectable, Scope
from app.db.database import DatabaseService


def _new_id() -> str:
    return uuid.uuid4().hex[:25]


def _row_to_reservation(row: dict) -> dict:
    return {
        "id": row.get("id", ""),
        "userId": row.get("user_id"),
        "customerName": row.get("customer_name", ""),
        "customerPhone": row.get("customer_phone", ""),
        "customerEmail": row.get("customer_email"),
        "partySize": row.get("party_size", 0),
        "date": row.get("date", ""),
        "time": row.get("time", ""),
        "status": row.get("status", "pending"),
        "tableNumber": row.get("table_number"),
        "specialRequests": row.get("special_requests"),
        "occasion": row.get("occasion"),
        "createdAt": row.get("created_at", ""),
        "updatedAt": row.get("updated_at", ""),
    }


@injectable(scope=Scope.SINGLETON)
class ReservationService:
    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def list_reservations(self, date: str | None = None, status: str | None = None) -> list[dict]:
        conditions = []
        params: list = []
        if date:
            conditions.append("r.date = ?")
            params.append(date)
        if status:
            conditions.append("r.status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT r.* FROM reservations r {where} ORDER BY r.date ASC, r.time ASC"
        rows = await self._db.fetch_all(sql, tuple(params))
        reservations = [_row_to_reservation(r) for r in rows]

        for res in reservations:
            res["user"] = await self._get_reservation_user(res.get("userId"))

        return reservations

    async def get_reservation(self, reservation_id: str) -> dict | None:
        row = await self._db.fetch_one("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
        if row is None:
            return None
        res = _row_to_reservation(row)
        res["user"] = await self._get_reservation_user(res.get("userId"))
        return res

    async def create_reservation(self, data: dict) -> dict:
        # Accept both camelCase (Pydantic with by_alias=True) and
        # snake_case (hand-rolled dicts in tests).
        def _g(*keys: str, default=None):
            for k in keys:
                v = data.get(k)
                if v is not None:
                    return v
            return default

        required_pairs = [
            ("customerName", "customer_name"),
            ("customerPhone", "customer_phone"),
            ("partySize", "party_size"),
            ("date", "date"),
            ("time", "time"),
        ]
        for keys in required_pairs:
            if not _g(*keys):
                raise ValueError(f"Missing required field: {keys[0]}")

        party_size = int(_g("partySize", "party_size", default=0))
        if party_size < 1 or party_size > 20:
            raise ValueError("Party size must be between 1 and 20")

        import re

        date = _g("date")
        time = _g("time")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date or ""):
            raise ValueError("Date must be in YYYY-MM-DD format")
        if not re.match(r"^\d{2}:\d{2}$", time or ""):
            raise ValueError("Time must be in HH:MM format")

        occasion = _g("occasion")
        valid_occasions = ["birthday", "anniversary", "business", "casual"]
        if occasion and occasion not in valid_occasions:
            raise ValueError(f"Invalid occasion. Valid options: {', '.join(valid_occasions)}")

        res_id = _new_id()
        await self._db.execute(
            """INSERT INTO reservations
               (id, user_id, customer_name, customer_phone, customer_email, party_size,
                date, time, status, table_number, special_requests, occasion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (
                res_id,
                _g("userId", "user_id"),
                _g("customerName", "customer_name"),
                _g("customerPhone", "customer_phone"),
                _g("customerEmail", "customer_email"),
                party_size,
                date,
                time,
                _g("tableNumber", "table_number"),
                _g("specialRequests", "special_requests"),
                occasion,
            ),
        )
        return await self.get_reservation(res_id)  # type: ignore

    async def update_reservation_status(self, reservation_id: str, status: str) -> dict | None:
        valid = {"pending", "confirmed", "cancelled", "completed"}
        if status not in valid:
            raise ValueError(f"Valid status is required ({', '.join(valid)})")

        existing = await self._db.fetch_one("SELECT id FROM reservations WHERE id = ?", (reservation_id,))
        if existing is None:
            return None

        await self._db.execute(
            "UPDATE reservations SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, reservation_id),
        )
        return await self.get_reservation(reservation_id)

    async def _get_reservation_user(self, user_id: str | None) -> dict | None:
        if not user_id:
            return None
        row = await self._db.fetch_one("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
        if row is None:
            return None
        return {"id": row["id"], "name": row["name"], "email": row["email"]}
