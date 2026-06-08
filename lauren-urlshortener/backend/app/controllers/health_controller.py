from __future__ import annotations

from lauren import controller, get


@controller("/api/health", tags=["health"])
class HealthController:
    @get("/")
    async def health(self) -> dict:
        return {"status": "ok", "service": "lauren-urlshortener"}
