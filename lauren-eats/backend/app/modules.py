"""Application module graph — composes all feature modules.

P0 fix (issue 4.1): the backend used to be a single flat
``@module(controllers=[...], providers=[...])`` that coupled every
feature into one import scope.  The result was a 50-line ``AppModule``
that imported every controller, service, and agent in the project —
testing one feature required resolving the entire graph.

This module splits the application into four feature modules plus a
shared ``AIModule``:

* :class:`DatabaseModule` — owns the ``DatabaseService`` singleton.
* :class:`MenuModule`     — menu + category controllers and services.
* :class:`OrderModule`    — order + reservation controllers and services.
* :class:`ChatModule`     — chat controller + chat service.
* :class:`AIModule`       — LLM stack + all six agents (re-exported).
* :class:`AppModule`      — root module that imports all the above.

The graph mirrors the structure of :mod:`lauren_ai` and the lauren-ai
chatbot example: each feature is independently testable, and only the
root module needs to know about the cross-cutting middleware,
interceptor, and logger configuration.
"""

from __future__ import annotations

from lauren import module

from app.ai.ai_module import AIModule
from app.controllers.admin_controller import AdminController
from app.controllers.category_controller import CategoryController
from app.controllers.chat_controller import ChatController
from app.controllers.health_controller import HealthController
from app.controllers.menu_controller import MenuController
from app.controllers.order_controller import OrderController
from app.controllers.reservation_controller import ReservationController
from app.controllers.seed_controller import SeedController
from app.db.database_module import DatabaseModule
from app.services.admin_service import AdminService
from app.services.chat_service import ChatService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.reservation_service import ReservationService


# Re-exported so callers can ``from app.modules import DatabaseModule``.
__all__ = [
    "AppModule",
    "DatabaseModule",
    "MenuModule",
    "OrderModule",
    "ChatModule",
    "AdminModule",
    "HealthModule",
]


# ---------------------------------------------------------------------------
# MenuModule
# ---------------------------------------------------------------------------


@module(
    imports=[DatabaseModule],
    controllers=[MenuController, CategoryController],
    providers=[MenuService],
    exports=[MenuService],
)
class MenuModule:
    """Menu browsing and category listing."""


# ---------------------------------------------------------------------------
# OrderModule
# ---------------------------------------------------------------------------


@module(
    imports=[DatabaseModule],
    controllers=[OrderController, ReservationController],
    providers=[OrderService, ReservationService],
    exports=[OrderService, ReservationService],
)
class OrderModule:
    """Order placement, status tracking, and reservation management."""


# ---------------------------------------------------------------------------
# ChatModule
# ---------------------------------------------------------------------------


@module(
    imports=[AIModule, DatabaseModule],
    controllers=[ChatController],
    providers=[ChatService],
    exports=[ChatService],
)
class ChatModule:
    """AI-powered streaming chat with multi-agent handoff."""


# ---------------------------------------------------------------------------
# AdminModule
# ---------------------------------------------------------------------------


@module(
    imports=[DatabaseModule, MenuModule, OrderModule],
    controllers=[AdminController, SeedController],
    providers=[AdminService],
    exports=[AdminService],
)
class AdminModule:
    """Admin stats, AI insights, and database seeding."""


# ---------------------------------------------------------------------------
# HealthModule
# ---------------------------------------------------------------------------


@module(controllers=[HealthController])
class HealthModule:
    """Liveness probe used by orchestrators and CI."""


# ---------------------------------------------------------------------------
# AppModule — root
# ---------------------------------------------------------------------------


@module(
    imports=[
        DatabaseModule,
        MenuModule,
        OrderModule,
        ChatModule,
        AdminModule,
        HealthModule,
        AIModule,
    ],
)
class AppModule:
    """Root application module for the Lauren Eats backend.

    Composes every feature module.  Cross-cutting concerns
    (CORS middleware, timing interceptor, default logger, signal bus)
    are configured in :mod:`main` via :func:`LaurenFactory.create` kwargs,
    not here.
    """
