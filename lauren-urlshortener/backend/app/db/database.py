from __future__ import annotations

import os

import aiosqlite

from lauren import Scope, injectable, post_construct, pre_destruct

from app import paths


SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS urls (
        id          TEXT PRIMARY KEY,
        code        TEXT UNIQUE NOT NULL,
        original_url TEXT NOT NULL,
        title       TEXT DEFAULT '',
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at  TIMESTAMP,
        is_active   INTEGER DEFAULT 1,
        click_count INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_urls_code ON urls(code);
    CREATE INDEX IF NOT EXISTS idx_urls_active ON urls(is_active);

    CREATE TABLE IF NOT EXISTS clicks (
        id          TEXT PRIMARY KEY,
        url_code    TEXT NOT NULL REFERENCES urls(code) ON DELETE CASCADE,
        clicked_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address  TEXT,
        user_agent  TEXT,
        referer     TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_clicks_code ON clicks(url_code);
    CREATE INDEX IF NOT EXISTS idx_clicks_at   ON clicks(clicked_at);
"""


@injectable(scope=Scope.SINGLETON)
class DatabaseService:
    def __init__(self) -> None:
        self._db_path: str = os.environ.get("DATABASE_URL", "urlshortener.db")
        self._conn: aiosqlite.Connection | None = None

    @post_construct
    async def _open(self) -> None:
        if self._conn is not None:
            return
        paths.ensure_data_dir(self._db_path)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

    @pre_destruct
    async def _close(self) -> None:
        if self._conn is not None:
            try:
                await self._conn.close()
            finally:
                self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected; @post_construct has not run yet.")
        return self._conn

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        cursor = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cursor

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        cursor = await self.conn.execute(sql, params)
        row = await cursor.fetchone()
        return dict(row) if row is not None else None

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        cursor = await self.conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def fetch_count(self, sql: str, params: tuple = ()) -> int:
        cursor = await self.conn.execute(sql, params)
        row = await cursor.fetchone()
        return row[0] if row else 0
