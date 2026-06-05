"""Lauren Eats Backend — AI-Powered Chinese Restaurant Platform.

P0 fixes:
- Issue 4.5: ``startup_init()`` is gone.  Database connection is opened by
  the framework via ``@post_construct`` on :class:`DatabaseService`.
- Issue 4.4: database lifecycle is owned by the DI container, not by
  ad-hoc ``asyncio.run`` calls.
- Issue 5.1: ``CorsMiddleware`` is installed as a global middleware via
  :func:`LaurenFactory.create(global_middlewares=...)` — the broken
  ``try/except ImportError`` block that called a non-existent
  ``app.add_middleware`` API is gone.
- Issue 7.2: ``default_logger`` is wired in via the ``logger=`` kwarg.
- Issue 7.3: ``TimingInterceptor`` is registered as a global interceptor.

The :class:`LaurenApp.container` is registered with the chat runner
resolver so :class:`ChatService` can resolve
``AgentRunner[ConciergeAgent]`` lazily.
"""

from __future__ import annotations

import os

from lauren import LaurenFactory
from lauren.logging import default_logger

from app.ai.signals import signal_bus
from app.interceptors.timing_interceptor import TimingInterceptor
from app.middlewares.cors_middleware import CorsMiddleware
from app.modules import AppModule
from app.services.runner_resolver import register_container


def create_app():
    """Create and configure the Lauren ASGI application."""
    app = LaurenFactory.create(
        AppModule,
        global_middlewares=[CorsMiddleware],
        global_interceptors=[TimingInterceptor],
        logger=default_logger(),
        signals=signal_bus,
        docs_url="/docs",
        openapi_info={
            "title": "Lauren Eats API",
            "version": "1.0.0",
            "description": "AI-Powered Chinese Restaurant Platform API",
        },
    )
    # Make the DI container available to the lazy ``AgentRunner[X]``
    # resolver used by ``ChatService``.
    register_container(app.container)
    return app


# ASGI app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
