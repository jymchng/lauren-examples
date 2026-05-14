"""HealthController — a simple liveness probe endpoint."""

import msgspec

from lauren import controller, get


class HealthResponse(msgspec.Struct):
    status: str
    version: str = "1.0.0"
    framework: str = "lauren"


@controller("/api/health")
class HealthController:
    @get("/")
    async def health(self) -> HealthResponse:
        return HealthResponse(status="ok")
