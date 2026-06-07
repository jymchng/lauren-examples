"""Smoke-test-local fixtures that shadow the root conftest.

The root conftest._open_db_once is session-scoped and requests the session-
scoped `app` fixture (which spins up the real DB-backed Lauren app).  Smoke
tests define their own module-scoped `app` fixture — a lightweight in-memory
Lauren instance with no database.  Pytest would raise ScopeMismatch if the
session fixture tried to resolve the module-scoped one.

Override _open_db_once here with a no-op session fixture so the scope
hierarchy stays consistent while smoke tests are collected.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
async def _open_db_once():  # noqa: PT004
    """No-op — smoke tests use a standalone Lauren app, not the real DB app."""
    yield


def pytest_configure(config) -> None:
    """Disable coverage collection for smoke runs.

    The .coverage database is root-owned in this repo; smoke tests do not
    exercise app/ at all so coverage is meaningless here anyway.  Targeted
    smoke runs should always be invoked without coverage overhead.
    """
    if hasattr(config.option, "no_cov"):
        config.option.no_cov = True
