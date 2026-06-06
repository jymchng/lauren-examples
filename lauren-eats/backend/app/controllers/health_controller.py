"""Health check controller."""

from lauren import controller, get


@controller("/api/health", tags=["health"])
class HealthController:
    @get("/")
    async def health(self) -> dict:
        from datetime import datetime, timezone

        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
