from lauren import module

from app.health.health_controller import HealthController


@module(controllers=[HealthController])
class HealthModule:
    pass
