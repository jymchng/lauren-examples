"""MetricsController — exposes tracing and cost data for observability.

Endpoints
---------
GET /api/metrics/         — summary: trace count + total cost
GET /api/metrics/traces   — recent spans from the global TraceStore
GET /api/metrics/cost     — per-model and per-conversation cost report
"""

from __future__ import annotations

from lauren import controller, get
from lauren_ai import CostTracker, get_trace_store


def _estimate_to_dict(est) -> dict:  # type: ignore[no-untyped-def]
    return {
        "total_usd": est.total_usd,
        "input_usd": est.input_usd,
        "output_usd": est.output_usd,
    }


@controller("/api/metrics")
class MetricsController:
    """Observability dashboard endpoints."""

    def __init__(self, cost_tracker: CostTracker) -> None:
        self._cost = cost_tracker

    @get("/")
    async def summary(self) -> dict:
        """Return a high-level summary of traces and cost."""
        store = get_trace_store()
        trace_count = len(store) if store is not None else 0
        report = await self._cost.report()
        return {
            "traces_recorded": trace_count,
            **_estimate_to_dict(report.total_estimate),
        }

    @get("/traces")
    async def traces(self) -> dict:
        """Return the 50 most recent traces."""
        store = get_trace_store()
        if store is None:
            return {"traces": []}

        recent = await store.last(50)
        return {
            "traces": [
                {
                    "run_id": t.run_id,
                    "trace_id": t.trace_id,
                    "span_count": len(t.spans),
                    "spans": [
                        {
                            "name": s.name,
                            "kind": s.kind.value if hasattr(s.kind, "value") else str(s.kind),
                            "status": "error" if s.error else "ok",
                            "duration_ms": round(s.duration_ms, 2) if s.duration_ms is not None else None,
                            "error": s.error,
                        }
                        for s in t.spans
                    ],
                }
                for t in recent
            ]
        }

    @get("/cost")
    async def cost(self) -> dict:
        """Return a full cost report broken down by model and conversation."""
        report = await self._cost.report()
        return {
            **_estimate_to_dict(report.total_estimate),
            "by_model": {
                model: _estimate_to_dict(est)
                for model, est in report.by_model.items()
            },
            "by_conversation": {
                cid: _estimate_to_dict(est)
                for cid, est in report.by_conversation.items()
            },
        }
