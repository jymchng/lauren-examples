"""WebSocket context variable for the current authenticated user.

Set by ``BankingChatController`` *on the handler task* before returning
``EventStream``.  Signal handlers in ``EventForwarder`` read this via
``current_user_id.get()`` to route agent lifecycle events to the right
WebSocket connections.
"""

from __future__ import annotations

from contextvars import ContextVar

# Holds the authenticated user_id for the current agent run.
#
# CRITICAL: must be set on the *handler task* — i.e. directly in the
# controller method body BEFORE returning ``EventStream(...)``, NOT
# inside the ``async def generate():`` SSE generator.
#
# Why: Lauren's SSE framing loop wraps each ``iterator.__anext__()``
# call in ``asyncio.ensure_future(...)``.  Each such task copies its
# context from the *handler task* (PEP 567), not from the previous
# ``__anext__()`` task.  So a ``set(...)`` inside the generator only
# affects the first chunk's task; every subsequent chunk runs in a
# fresh task whose ContextVar is the original handler-task default
# (``None``).  ``asyncio.gather()`` inside ``SignalBus.emit`` then
# copies that ``None`` into every signal handler, and they early-return
# without forwarding the event.
#
# Setting the var on the handler task once means every spawned task
# inherits the populated value automatically.
current_user_id: ContextVar[str | None] = ContextVar("ws_current_user_id", default=None)
