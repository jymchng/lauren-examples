"""Database connection and schema management using aiosqlite.

P0 fix: connection lifecycle is owned by the Lauren DI container via
``@post_construct`` and ``@pre_destruct`` (issue 4.4) — not by ad-hoc
``asyncio.run`` in :mod:`main` (issue 4.5).
"""

from __future__ import annotations

import os

import aiosqlite

from lauren import Scope, injectable, post_construct, pre_destruct

from app import paths


@injectable(scope=Scope.SINGLETON)
class DatabaseService:
    """Singleton database service managing the aiosqlite connection.

    The connection is opened by :meth:`_open` (a :func:`@post_construct` hook)
    when the Lauren DI container builds the singleton — *after* the
    ``AppModule`` graph is fully resolved and *before* the first HTTP
    request is handled.  It is closed by :meth:`_close` (a
    :func:`@pre_destruct` hook) on application shutdown.
    """

    def __init__(self) -> None:
        # Read the path eagerly so config errors surface at construction time.
        self._db_path: str = os.environ.get("DATABASE_URL", "lauren_eats.db")
        self._conn: aiosqlite.Connection | None = None

    @post_construct
    async def _open(self) -> None:
        """Open the connection and initialise the schema.

        Runs once at app startup.  Safe to invoke a second time — the
        second call is a no-op.
        """
        if self._conn is not None:
            return
        paths.ensure_data_dir(self._db_path)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._init_schema()
        await self._conn.commit()

    @pre_destruct
    async def _close(self) -> None:
        """Close the connection on app shutdown.

        :func:`@pre_destruct` hooks fire in reverse-dependency order during
        Lauren ASGI lifespan shutdown (after uvicorn's ``SIGTERM`` handler
        but before the event loop closes).
        """
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
        if row is None:
            return None
        return dict(row)

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        cursor = await self.conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def fetch_count(self, sql: str, params: tuple = ()) -> int:
        cursor = await self.conn.execute(sql, params)
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def _init_schema(self) -> None:
        """Create all tables if they don't exist."""
        await self.conn.executescript(SCHEMA_SQL)
        await self.conn.commit()


SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT,
        phone TEXT,
        avatar TEXT,
        role TEXT DEFAULT 'customer',
        preferences TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        name_zh TEXT,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        icon TEXT,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS menu_items (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        name_zh TEXT,
        description TEXT,
        price REAL NOT NULL,
        image TEXT,
        category_id TEXT NOT NULL REFERENCES categories(id),
        spicy_level INTEGER DEFAULT 0,
        is_vegetarian INTEGER DEFAULT 0,
        is_vegan INTEGER DEFAULT 0,
        is_gluten_free INTEGER DEFAULT 0,
        is_popular INTEGER DEFAULT 0,
        is_available INTEGER DEFAULT 1,
        calories INTEGER,
        preparation_time INTEGER,
        ingredients TEXT,
        allergens TEXT,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category_id);
    CREATE INDEX IF NOT EXISTS idx_menu_items_popular ON menu_items(is_popular);
    CREATE INDEX IF NOT EXISTS idx_menu_items_available ON menu_items(is_available);

    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id),
        order_number TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'pending',
        total_amount REAL NOT NULL,
        subtotal REAL NOT NULL,
        tax REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        notes TEXT,
        type TEXT DEFAULT 'dine_in',
        table_number TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
    CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
    CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);

    CREATE TABLE IF NOT EXISTS order_items (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        menu_item_id TEXT NOT NULL REFERENCES menu_items(id),
        quantity INTEGER DEFAULT 1,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
    CREATE INDEX IF NOT EXISTS idx_order_items_menu ON order_items(menu_item_id);

    CREATE TABLE IF NOT EXISTS reservations (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id),
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_email TEXT,
        party_size INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        table_number TEXT,
        special_requests TEXT,
        occasion TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_reservations_user ON reservations(user_id);
    CREATE INDEX IF NOT EXISTS idx_reservations_date ON reservations(date);
    CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);

    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id),
        title TEXT,
        agent_type TEXT,
        status TEXT DEFAULT 'active',
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS agent_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        agent_type TEXT,
        tool_calls TEXT,
        tool_results TEXT,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_agent_messages_conv ON agent_messages(conversation_id);
    CREATE INDEX IF NOT EXISTS idx_agent_messages_created ON agent_messages(created_at);

    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id),
        rating INTEGER NOT NULL,
        comment TEXT,
        category TEXT,
        order_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);
    CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);
"""
