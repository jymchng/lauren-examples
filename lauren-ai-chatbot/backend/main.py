"""Lauren AI Chatbot — entry point.

Run with:
    uvicorn main:app --reload --port 8000
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

from app.app_module import AppModule  # noqa: E402 — after load_dotenv
from app.ai.signals import signal_bus  # noqa: E402 — shared bus
from app.interceptors.timing_interceptor import TimingInterceptor
from app.middlewares.cors_middleware import CorsMiddleware
from app.middlewares.logging_middleware import LoggingMiddleware
from lauren import LaurenFactory
from lauren.logging import default_logger
from lauren_ai import (  # noqa: E402
    AgentRunComplete,
    InMemoryTraceExporter,
    ModelCallComplete,
    TraceStore,
    set_trace_store,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tracing — global store so @traced() functions export spans automatically
# ---------------------------------------------------------------------------

trace_exporter = InMemoryTraceExporter()
trace_store = TraceStore()
# Attach the in-memory exporter so @traced() decorator can find it.
trace_store._exporters = [trace_exporter]  # type: ignore[attr-defined]
set_trace_store(trace_store)

# ---------------------------------------------------------------------------
# SignalBus — token usage logging
# ---------------------------------------------------------------------------


@signal_bus.on(AgentRunComplete)
async def _log_agent_run_complete(event: AgentRunComplete) -> None:
    """Log final cost and turn count after every agent run completes."""
    logger.info(
        "AgentRunComplete agent_class=%s turns=%d total_cost_usd=%.6f stop_reason=%s",
        getattr(event.agent_class, "__name__", str(event.agent_class)),
        event.turns,
        event.total_cost_usd,
        event.stop_reason,
    )


@signal_bus.on(ModelCallComplete)
async def _log_token_usage(event: ModelCallComplete) -> None:
    """Log token usage and estimated cost after every model call."""
    usage = event.usage
    if usage is not None:
        logger.info(
            "ModelCallComplete model=%s input_tokens=%d output_tokens=%d cost_usd=%.6f duration_ms=%.1f stop_reason=%s",
            event.model,
            usage.input_tokens,
            usage.output_tokens,
            event.cost_usd,
            event.duration_ms,
            event.stop_reason,
        )
    else:
        logger.info(
            "ModelCallComplete model=%s cost_usd=%.6f duration_ms=%.1f stop_reason=%s",
            event.model,
            event.cost_usd,
            event.duration_ms,
            event.stop_reason,
        )


app = LaurenFactory.create(
    AppModule,
    global_middlewares=[CorsMiddleware, LoggingMiddleware],
    global_interceptors=[TimingInterceptor],
    logger=default_logger(),
)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
