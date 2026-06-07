"""Shared pytest fixtures for the lauren-eats backend tests.

Boots a real ``LaurenApp`` once per test session in front of an
in-memory SQLite database and a ``MockTransport`` so tests run with zero
network calls.  Tests that need a clean DB call :func:`reset_db`; the
``db`` fixture just resolves the singleton.

The :func:`app` fixture monkey-patches :class:`LLMModule.for_root` to
substitute the ``MockTransport`` for the real HTTP transport, so the
``AIModule`` (and its agents) see deterministic completions.
"""

from __future__ import annotations

import importlib
import os

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Environment setup — must run before any app imports so the LLMConfig
# factory picks up the right values.
# ---------------------------------------------------------------------------

os.environ.setdefault("DATABASE_URL", "file::memory:?cache=shared")
os.environ.setdefault("LLM_API_KEY", "test-key-12345")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")
os.environ.setdefault("PYTHONHASHSEED", "0")

import sys  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session", autouse=True)
def _preload_lauren():
    """Pre-import Lauren with all optional deps available.

    This must run before any test that blocks pydantic; otherwise
    _PYDANTIC_AVAILABLE is permanently False for the whole session.
    """
    import lauren  # noqa: F401
    import lauren.extractors  # noqa: F401
    import lauren.streaming  # noqa: F401


_TABLES_TO_RESET = (
    "agent_messages",
    "conversations",
    "order_items",
    "orders",
    "reservations",
    "menu_items",
    "categories",
    "users",
    "feedback",
)


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mock_transport():
    """The ``MockTransport`` paired with the test LLMConfig.

    Tests can ``mock_transport.queue_response(...)`` or
    ``mock_transport.queue_stream(...)`` to script deterministic
    completions.
    """
    from lauren_ai import LLMConfig

    _, transport = LLMConfig.for_testing()
    return transport


@pytest.fixture(scope="session")
def app(mock_transport):
    """Build the full Lauren app once per session.

    Patches :class:`LLMModule.for_root` to use the
    :class:`MockTransport` so the ``AIModule`` (and its agents) see
    deterministic completions.
    """
    from lauren import LaurenFactory
    from lauren_ai._module import LLMModule
    from app.interceptors.timing_interceptor import TimingInterceptor
    from app.middlewares.cors_middleware import CorsMiddleware
    from app.services.runner_resolver import register_container

    # Patch the unbound function so the ``cls`` argument (which is the
    # implicit classmethod ``cls``) is still bound when called.
    _original_for_root = LLMModule.__dict__["for_root"].__func__

    def patched_for_root(cls, config, *, transport_override=None):
        return _original_for_root(cls, config, transport_override=mock_transport)

    LLMModule.for_root = classmethod(patched_for_root)  # type: ignore[assignment]

    # Reload the AIModule so it picks up the patched factory.
    import app.ai.ai_module as ai_mod

    importlib.reload(ai_mod)

    # Reload the app module so it imports the freshly reloaded AIModule.
    import app.modules as mod_mod

    importlib.reload(mod_mod)

    a = LaurenFactory.create(
        mod_mod.AppModule,
        global_middlewares=[CorsMiddleware],
        global_interceptors=[TimingInterceptor],
    )
    register_container(a.container)
    return a


@pytest.fixture(scope="session")
def client(app):
    """A sync test client backed by the in-process ASGI app."""
    from lauren.testing import TestClient

    return TestClient(app)


# ---------------------------------------------------------------------------
# Function-scoped fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _open_db_once(app):
    """Open the in-memory DB connection once per session for every test.

    The framework's :func:`@post_construct` is normally fired by the ASGI
    lifespan at boot, but :class:`lauren.testing.TestClient` does not
    drive the lifespan.  Tests that don't explicitly request
    ``db``/``clean_db`` still get a working connection because
    :class:`DatabaseService` and every service that depends on it
    (e.g. :class:`ChatService`) would otherwise raise
    ``RuntimeError: Database not connected``.
    """
    from app.db.database import DatabaseService

    db_svc = await app.container.resolve(DatabaseService)
    if db_svc._conn is None:
        await db_svc._open()
    yield


@pytest.fixture(autouse=True)
def _reset_mock_transport(mock_transport):
    """Clear any queued mock responses between tests.

    The ``mock_transport`` fixture is session-scoped, so queued
    completions leak between tests if not reset.  Without this fixture,
    a test that expects ``text == "fallback"`` would receive whatever
    the previous test dequeued.
    """
    mock_transport.reset()
    yield


@pytest_asyncio.fixture()
async def db(app):
    """Resolve the ``DatabaseService`` singleton and yield it.

    The framework's ``@post_construct`` is normally fired by the ASGI
    lifespan at boot.  The :class:`lauren.testing.TestClient` does not
    drive the lifespan, so we open the connection ourselves here.  This
    is idempotent — calling ``_open`` on an already-open service is a
    no-op.
    """
    from app.db.database import DatabaseService

    db_svc = await app.container.resolve(DatabaseService)
    if db_svc._conn is None:
        await db_svc._open()
    return db_svc


@pytest_asyncio.fixture()
async def clean_db(db):
    """Like :func:`db` but with every table truncated first."""
    await reset_db(db)
    return db


async def reset_db(db_svc) -> None:
    """Truncate every lauren-eats table.  Errors on missing tables are ignored."""
    for table in _TABLES_TO_RESET:
        try:
            await db_svc.execute(f"DELETE FROM {table}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config, items):
    """Auto-tag tests based on their file path."""
    for item in items:
        path = str(item.fspath)
        if "/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/unit/" in path:
            item.add_marker(pytest.mark.unit)
