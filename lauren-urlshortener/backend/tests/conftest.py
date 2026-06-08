"""Shared pytest fixtures for the URL shortener backend."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio

os.environ.setdefault("DATABASE_URL", ":memory:")

import sys  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session", autouse=True)
def _preload_lauren():
    """Pre-import Lauren while pydantic is still available.

    This ensures _PYDANTIC_AVAILABLE is True before any test can block pydantic.
    Tests that need a no-pydantic environment use their own module-scoped
    _no_pydantic fixture which evicts pydantic after Lauren is already loaded.
    """
    import lauren  # noqa: F401
    import lauren.extractors  # noqa: F401
    import lauren.streaming  # noqa: F401


@pytest.fixture(scope="session")
def app():
    """Build the full Lauren app once per session against an in-memory DB."""
    from lauren import LaurenFactory
    from app.modules import AppModule

    return LaurenFactory.create(AppModule, docs_url="/docs")


@pytest.fixture(scope="session")
def client(app):
    from lauren.testing import TestClient

    return TestClient(app)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _open_db_once(app):
    """Open the in-memory DB connection once; TestClient doesn't drive lifespan."""
    from app.db.database import DatabaseService

    db_svc = await app.container.resolve(DatabaseService)
    if db_svc._conn is None:
        await db_svc._open()
    yield


@pytest_asyncio.fixture()
async def db(app):
    from app.db.database import DatabaseService

    db_svc = await app.container.resolve(DatabaseService)
    if db_svc._conn is None:
        await db_svc._open()
    return db_svc


@pytest_asyncio.fixture()
async def clean_db(db):
    """Truncate all tables before yielding — gives each test a clean slate."""
    for table in ("clicks", "urls"):
        try:
            await db.execute(f"DELETE FROM {table}")
        except Exception:
            pass
    return db


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = str(item.fspath)
        if "/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in path:
            item.add_marker(pytest.mark.e2e)
