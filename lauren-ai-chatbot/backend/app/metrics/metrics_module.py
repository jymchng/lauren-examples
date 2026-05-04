"""MetricsModule — wires MetricsController into the DI container."""

from __future__ import annotations

from lauren import module

from app.ai.ai_module import AIModule
from app.metrics.metrics_controller import MetricsController


@module(
    imports=[AIModule],
    controllers=[MetricsController],
)
class MetricsModule:
    """Exposes /api/metrics/* observability endpoints."""
