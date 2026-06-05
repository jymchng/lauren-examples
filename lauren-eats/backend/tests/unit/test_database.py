"""Unit tests for :class:`app.db.database.DatabaseService`.

Covers the P0 lifecycle refactor: connection opened in ``@post_construct``,
closed in ``@pre_destruct``, schema initialised once.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.db.database import DatabaseService, SCHEMA_SQL
from app.paths import ensure_data_dir, is_in_memory


class TestDatabaseServiceLifecycle:
    async def test_post_construct_opens_connection(self, db):
        """The DI container's ``@post_construct`` hook opens the connection."""
        assert db._conn is not None
        assert db.conn is db._conn

    async def test_schema_initialised(self, db):
        """All expected tables exist after ``@post_construct`` runs."""
        rows = await db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        names = {r["name"] for r in rows}
        for required in (
            "users",
            "categories",
            "menu_items",
            "orders",
            "order_items",
            "reservations",
            "conversations",
            "agent_messages",
            "feedback",
        ):
            assert required in names, f"Missing table: {required}"

    async def test_execute_commits_immediately(self, clean_db):
        await clean_db.execute(
            "INSERT INTO categories (id, name, slug) VALUES (?, ?, ?)",
            ("c1", "Appetizers", "appetizers"),
        )
        row = await clean_db.fetch_one("SELECT name FROM categories WHERE id = ?", ("c1",))
        assert row is not None
        assert row["name"] == "Appetizers"

    async def test_fetch_one_returns_none_for_missing_row(self, db):
        row = await db.fetch_one("SELECT * FROM users WHERE id = ?", ("missing",))
        assert row is None

    async def test_fetch_all_returns_empty_list(self, db):
        rows = await db.fetch_all("SELECT * FROM users")
        assert rows == []

    async def test_fetch_count_returns_int(self, db):
        n = await db.fetch_count("SELECT COUNT(*) FROM users")
        assert n == 0
        assert isinstance(n, int)

    async def test_conn_property_raises_when_disconnected(self):
        """Construct a service, never open it, then assert the property raises."""
        svc = DatabaseService()
        with pytest.raises(RuntimeError, match="not connected"):
            _ = svc.conn

    async def test_re_open_is_idempotent(self, clean_db):
        """Calling ``_open`` twice is a no-op — connection already exists."""
        original = clean_db._conn
        await clean_db._open()
        assert clean_db._conn is original

    async def test_close_sets_conn_to_none(self, clean_db):
        await clean_db._close()
        assert clean_db._conn is None

    async def test_close_when_never_opened_is_safe(self):
        svc = DatabaseService()
        await svc._close()  # no-op
        assert svc._conn is None


class TestPaths:
    def test_ensure_data_dir_creates_parent(self, tmp_path: Path):
        target = tmp_path / "sub" / "db.sqlite"
        ensure_data_dir(str(target))
        assert target.parent.exists()

    def test_ensure_data_dir_skips_memory(self):
        ensure_data_dir(":memory:")  # must not raise

    def test_ensure_data_dir_skips_empty(self):
        ensure_data_dir("")  # must not raise

    def test_ensure_data_dir_idempotent(self, tmp_path: Path):
        target = tmp_path / "db.sqlite"
        ensure_data_dir(str(target))
        ensure_data_dir(str(target))  # second call must not raise
        assert target.parent.exists()

    def test_is_in_memory(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", ":memory:")
        assert is_in_memory() is True

    def test_is_in_memory_false(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "/tmp/x.db")
        assert is_in_memory() is False

    def test_is_in_memory_default(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert is_in_memory() is False
