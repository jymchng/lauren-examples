"""Database module — owns the :class:`DatabaseService` singleton.

Lives in its own file to break the import cycle between
:mod:`app.modules` (which imports :mod:`app.ai.ai_module` which needs
:class:`DatabaseModule`).
"""

from __future__ import annotations

from lauren import module

from app.db.database import DatabaseService


@module(providers=[DatabaseService], exports=[DatabaseService])
class DatabaseModule:
    """Owns the ``DatabaseService`` singleton.

    The :func:`@post_construct` hook on :class:`DatabaseService` opens the
    connection when the singleton is first resolved, which happens during
    the root ``AppModule`` build, before the first HTTP request is handled.
    """
