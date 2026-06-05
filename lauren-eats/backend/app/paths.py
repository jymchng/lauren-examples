"""Filesystem paths used by the application.

Centralised so tests can override ``DATABASE_URL`` (e.g. to a tempfile)
and have the data directory created automatically.
"""

from __future__ import annotations

import os
from pathlib import Path


def ensure_data_dir(db_path: str) -> None:
    """Create the parent directory of *db_path* if missing.

    :func:`@post_construct` hooks run before any other code touches the
    filesystem, so the directory must exist by the time the connection is
    opened.  No-op when the path is ``":memory:"`` (used by tests).
    """
    if db_path == ":memory:" or not db_path:
        return
    parent = Path(db_path).expanduser().parent
    if parent and str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def is_in_memory() -> bool:
    """``True`` when the current ``DATABASE_URL`` is an in-memory SQLite path."""
    return os.environ.get("DATABASE_URL", "lauren_eats.db") == ":memory:"
