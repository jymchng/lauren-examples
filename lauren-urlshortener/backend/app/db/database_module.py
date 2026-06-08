from __future__ import annotations

from lauren import module

from app.db.database import DatabaseService


@module(providers=[DatabaseService], exports=[DatabaseService])
class DatabaseModule:
    """Owns the DatabaseService singleton."""
