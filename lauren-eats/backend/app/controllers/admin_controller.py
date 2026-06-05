"""Admin controller — stats and AI insights."""

from __future__ import annotations

import logging

from lauren import controller, get

from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)


@controller("/api/admin", tags=["admin"])
class AdminController:
    def __init__(self, admin_service: AdminService) -> None:
        self._svc = admin_service

    @get("/stats")
    async def get_stats(self) -> dict:
        stats = await self._svc.get_stats()
        return {"success": True, "data": stats}

    @get("/ai-insights")
    async def get_ai_insights(self) -> dict:
        insights = await self._svc.get_ai_insights()
        return {"success": True, "data": insights}
