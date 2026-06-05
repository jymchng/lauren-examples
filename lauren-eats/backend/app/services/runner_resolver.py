"""Resolve per-agent ``AgentRunner`` instances from the DI container.

This module exists to break the import cycle between
:mod:`app.services.chat_service` (which depends on a runner) and the
agent module graph (which is constructed by :func:`LaurenFactory.create`).

Strategy: we cache the container that was created during the most
recent :func:`LaurenFactory.create` call (the framework exposes it as
:attr:`LaurenApp.container`).  :func:`register_container` is called by
:mod:`main` after the app is built.
"""

from __future__ import annotations

from typing import Any

_container: Any = None


def register_container(container: Any) -> None:
    """Stash a reference to the active DI container.

    Called once at app boot from :mod:`main`.  The container is the
    live DI graph backing the running :class:`lauren.app.LaurenApp`.
    """
    global _container
    _container = container


def resolve_runner(agent_cls: type) -> Any:
    """Resolve ``AgentRunner[agent_cls]`` from the cached container.

    Raises :class:`RuntimeError` if no container has been registered —
    the caller is expected to be a long-lived singleton, not a test
    that builds the app standalone.
    """
    if _container is None:
        raise RuntimeError(
            "DI container has not been registered; call register_container() "
            "in main.py after LaurenFactory.create()."
        )
    from lauren_ai import AgentRunner

    return _container.resolve(AgentRunner[agent_cls])
