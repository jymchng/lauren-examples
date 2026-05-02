"""HealthController — a simple liveness probe endpoint."""

from pydantic import BaseModel

from lauren import controller, get


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    framework: str = "lauren"


@controller("/api/health")
class HealthController:
    @get("/")
    async def health(self) -> HealthResponse:
        return HealthResponse(status="ok")
