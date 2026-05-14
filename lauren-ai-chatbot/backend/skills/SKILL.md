---
name: building-securebank-chatbot
description: Builds a production-grade multi-agent banking chatbot backend using Lauren (web framework) and Lauren AI (agent orchestration). Covers four-agent routing with HandoffTo, human-in-the-loop transfer approval via asyncio.Future, real-time WebSocket events via SignalBus, and HMAC-SHA256 request signing. Use when building AI chatbot backends with agentic routing, streaming SSE responses, WebSocket event feeds, or security-enforced identity.
---

# SecureBank AI Chatbot — Backend Skill

Production-grade banking chatbot backend. Four independent agents route conversations via `HandoffTo[...]`, a human-in-the-loop approval gate blocks fund transfers until the browser confirms, and every agent lifecycle event is fanned out over WebSocket in real time.

## Project layout

```
backend/
├── main.py                    # Lauren app bootstrap, global middleware, signal handlers
├── app/
│   ├── app_module.py          # Root @module — imports all feature modules
│   ├── ai/
│   │   ├── ai_module.py       # Four AgentModules wired together + BankingChatController
│   │   ├── agents/            # @agent classes: unauth_crm, auth_crm, transfer, disputes
│   │   ├── tools/             # banking tools, HandoffTo, CheckAuth, ActiveAgentStore
│   │   └── approval/          # ApprovalService + ApprovalTool (human-in-the-loop)
│   ├── ws/                    # BankingWsGateway, EventForwarder, WsTokenController
│   └── crypto/                # SignatureGuard, CryptoService (HMAC-SHA256)
```

## Feature guides

- **Multi-agent routing**: four agents with typed `HandoffTo[...]` and per-agent conversation isolation → [multi-agent-routing.md](multi-agent-routing.md)
- **Human-in-the-loop approval**: `asyncio.Future`-based transfer gate, browser confirm/decline → [human-in-the-loop.md](human-in-the-loop.md)
- **WebSocket events**: `SignalBus` → `EventForwarder` → per-user WS fan-out → [websocket-events.md](websocket-events.md)
- **Security model**: HMAC-SHA256 signed requests, `SignatureGuard` pins identity → [security-model.md](security-model.md)

## Quick start

### Bootstrap

```python
# main.py
from lauren import Lauren
from app.app_module import AppModule
from app.middlewares.cors_middleware import CorsMiddleware
from app.middlewares.logging_middleware import LoggingMiddleware

app = Lauren(AppModule, global_middlewares=[CorsMiddleware, LoggingMiddleware])
```

### Root module

```python
# app/app_module.py
from lauren import module
from app.ai.ai_module import AIModule
from app.banking.banking_module import BankingModule
from app.ws.ws_module import WsModule
from app.health.health_controller import HealthController

@module(imports=[BankingModule, AIModule, WsModule], controllers=[HealthController])
class AppModule: ...
```

### Minimal agent

```python
from lauren_ai import agent, use_tools
from lauren_ai._memory._stores import InMemoryConversationStore

@agent(
    name="Banking CRM Agent (Authenticated)",
    model=None,            # inherits from LLMModule.for_root(config)
    system=_SYSTEM,
    max_turns=8,
    conversation_store=InMemoryConversationStore(),
)
@use_tools(GetBalanceTool, HandoffTo, CheckAuthenticationTool)
class AuthenticatedCRMAgent: ...
```

### AgentModule wiring

```python
from lauren_ai._module import AgentModule

_AuthCRMModule = AgentModule.for_root(
    agents=[AuthenticatedCRMAgent],
    tools=[HandoffTo[BankTransferAgent, DisputesAgent]],
    imports=[LLMProvider, CheckAuthModule, BankingModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool, GetBalanceTool],  # prevents DI duplication
    signals=signal_bus,
)
```

### Streaming controller

```python
from lauren import EventStream, Json, ServerSentEvent, controller, post, use_guards
from lauren.types import ExecutionContext
from lauren_ai import AgentRunner

@use_guards(SignatureGuard)
@controller("/api/banking")
class BankingChatController:
    def __init__(
        self,
        unauth_runner: AgentRunner[UnauthenticatedCRMAgent],
        auth_runner: AgentRunner[AuthenticatedCRMAgent],
        active_agent_store: ActiveAgentStore,
    ) -> None: ...

    @use_guards(AuthenticatedUserGuard)
    @post("/chat")
    async def stream(self, body: Json[ChatRequest], exec_ctx: ExecutionContext) -> EventStream:
        async def generate():
            while True:
                agent, runner = _resolve_agent(active)
                async for chunk in await runner.run_stream(
                    agent, prompt,
                    conversation_id=f"{conv_id}:{active}",
                    execution_context=exec_ctx,
                    metadata={"conversation_id": conv_id},
                ):
                    if chunk.delta:
                        yield ServerSentEvent(event="token", data=chunk.delta)
                new_active = active_agent_store.get(conv_id, default_agent)
                if new_active == active:
                    break
                yield ServerSentEvent(event="break", data=new_active)
                active = new_active
            yield ServerSentEvent(event="done", data="")
        return EventStream(generate(), keep_alive=15.0)
```

## Observability

```python
from lauren_ai import CostTracker, ModelCallComplete, default_pricing_table

_cost_tracker = CostTracker(pricing=default_pricing_table())

@signal_bus.on(ModelCallComplete)
async def _track_cost(event: ModelCallComplete) -> None:
    await _cost_tracker._on_model_call_complete(event)

# Expose via @get("/api/metrics/cost") injecting CostTracker
```

## Environment variables

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | LLM provider API key |
| `LLM_MODEL` | Model slug (e.g. `openai/gpt-4o-mini`) |
| `PAYLOAD_SECRET` | HMAC-SHA256 secret shared with the Next.js frontend proxy |
