"""Application module graph."""

from __future__ import annotations

from lauren import module

from app.controllers.health_controller import HealthController
from app.controllers.redirect_controller import RedirectController
from app.controllers.url_controller import UrlController
from app.db.database_module import DatabaseModule
from app.services.url_service import UrlService


@module(
    imports=[DatabaseModule],
    controllers=[UrlController, RedirectController],
    providers=[UrlService],
    exports=[UrlService],
)
class UrlModule:
    """URL CRUD and redirect handling."""


@module(controllers=[HealthController])
class HealthModule:
    """Liveness probe."""


@module(imports=[DatabaseModule, UrlModule, HealthModule])
class AppModule:
    """Root application module."""
