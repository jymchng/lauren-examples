"""URL shortener service — create, read, update, delete, and redirect."""

from __future__ import annotations

import secrets
import string
import uuid
from datetime import datetime, timezone

from lauren import Scope, injectable

from app.db.database import DatabaseService
from app.models.url import CreateUrlRequest, UpdateUrlRequest, UrlRecord, row_to_url_record

_ALPHABET = string.ascii_letters + string.digits
_CODE_LENGTH = 7


def _new_id() -> str:
    return uuid.uuid4().hex


def _generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))


class UrlNotFound(LookupError):
    """Raised when a short code does not exist or is inactive."""


class UrlCodeConflict(ValueError):
    """Raised when a custom code is already taken."""


class UrlExpired(ValueError):
    """Raised when a short URL has passed its expiry date."""


@injectable(scope=Scope.SINGLETON)
class UrlService:
    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(self, req: CreateUrlRequest) -> UrlRecord:
        if req.custom_code:
            code = req.custom_code
            existing = await self._db.fetch_one("SELECT id FROM urls WHERE code = ?", (code,))
            if existing:
                raise UrlCodeConflict(f"Code {code!r} is already taken.")
        else:
            code = await self._unique_code()

        row_id = _new_id()
        expires_at = req.expires_at or None
        await self._db.execute(
            """
            INSERT INTO urls (id, code, original_url, title, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (row_id, code, req.url, req.title, expires_at),
        )
        row = await self._db.fetch_one("SELECT * FROM urls WHERE id = ?", (row_id,))
        assert row is not None
        return row_to_url_record(row)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_code(self, code: str) -> UrlRecord:
        row = await self._db.fetch_one("SELECT * FROM urls WHERE code = ? AND is_active = 1", (code,))
        if row is None:
            raise UrlNotFound(code)
        return row_to_url_record(row)

    async def list_urls(
        self,
        page: int = 1,
        limit: int = 20,
        search: str = "",
    ) -> dict:
        limit = min(100, max(1, limit))
        offset = (page - 1) * limit

        if search:
            where = "WHERE (original_url LIKE ? OR title LIKE ? OR code LIKE ?) AND is_active = 1"
            pat = f"%{search}%"
            count_params: tuple = (pat, pat, pat)
            data_params: tuple = (pat, pat, pat, limit, offset)
        else:
            where = "WHERE is_active = 1"
            count_params = ()
            data_params = (limit, offset)

        total = await self._db.fetch_count(f"SELECT COUNT(*) FROM urls {where}", count_params)
        rows = await self._db.fetch_all(
            f"SELECT * FROM urls {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            data_params,
        )
        total_pages = (total + limit - 1) // limit if limit else 0
        return {
            "data": [row_to_url_record(r).__dict__ for r in rows],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_more": page < total_pages,
            },
        }

    async def get_stats(self, code: str) -> dict:
        url = await self.get_by_code(code)
        clicks = await self._db.fetch_all(
            "SELECT * FROM clicks WHERE url_code = ? ORDER BY clicked_at DESC LIMIT 100",
            (code,),
        )
        last_clicked = clicks[0]["clicked_at"] if clicks else None
        return {
            "url": url.__dict__,
            "click_count": url.click_count,
            "last_clicked_at": last_clicked,
            "recent_clicks": clicks,
        }

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(self, code: str, req: UpdateUrlRequest) -> UrlRecord:
        existing = await self.get_by_code(code)
        sets: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
        params: list = []

        if req.title != "":
            sets.append("title = ?")
            params.append(req.title)
        if req.expires_at != "":
            sets.append("expires_at = ?")
            params.append(req.expires_at or None)

        params.append(existing.code)
        await self._db.execute(
            f"UPDATE urls SET {', '.join(sets)} WHERE code = ?",
            tuple(params),
        )
        return await self.get_by_code(code)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, code: str) -> None:
        await self.get_by_code(code)  # raises UrlNotFound if missing
        await self._db.execute("UPDATE urls SET is_active = 0 WHERE code = ?", (code,))

    # ------------------------------------------------------------------
    # Redirect — records a click and returns the target URL
    # ------------------------------------------------------------------

    async def record_redirect(
        self,
        code: str,
        ip: str = "",
        user_agent: str = "",
        referer: str = "",
    ) -> str:
        url = await self.get_by_code(code)
        if url.expires_at:
            try:
                exp = datetime.fromisoformat(url.expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                expired = datetime.now(timezone.utc) > exp
            except ValueError:
                expired = False  # malformed expires_at — treat as not expired
            if expired:
                raise UrlExpired(code)

        await self._db.execute(
            "INSERT INTO clicks (id, url_code, ip_address, user_agent, referer) VALUES (?, ?, ?, ?, ?)",
            (_new_id(), code, ip, user_agent, referer),
        )
        await self._db.execute(
            "UPDATE urls SET click_count = click_count + 1 WHERE code = ?",
            (code,),
        )
        return url.original_url

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _unique_code(self) -> str:
        for _ in range(10):
            code = _generate_code()
            row = await self._db.fetch_one("SELECT id FROM urls WHERE code = ?", (code,))
            if row is None:
                return code
        raise RuntimeError("Failed to generate a unique short code after 10 attempts.")
