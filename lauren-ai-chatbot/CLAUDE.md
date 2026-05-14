# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (run from `backend/`)

```bash
uv run python -m pytest tests/ -q                        # all tests
uv run python -m pytest tests/unit/ -q                   # unit tests only
uv run python -m pytest tests/integration/ -q            # integration tests only
uv run python -m pytest tests/unit/test_handoff.py -q    # handoff tool
uv run python -m pytest tests/unit/test_llm_scope_guard.py -q
uv run python -m pytest tests/integration/test_chatbot_guardrails_e2e.py -q
uv run ruff check app/                                   # lint
uv run ruff format --check app/                          # format check
uvicorn main:app --reload --port 8000                    # dev server (requires .env)
modal serve modal_deploy.py                              # Modal preview deployment
```

Required `.env` in `backend/`:
```
OPENROUTER_API_KEY=sk-or-...
PAYLOAD_SECRET=any-random-secret
LLM_MODEL=openai/gpt-4o-mini   # optional
```

### Frontend (run from `frontend/`)

```bash
npm run dev     # dev server on :3000
npm run build
npm run lint
```

Required `.env.local` in `frontend/`:
```
BACKEND_URL=http://localhost:8000
PAYLOAD_SECRET=<same as backend>
```

---

## Architecture

### Module Hierarchy

```
AppModule (root)
├── AIModule                  ← all agent logic lives here
│   ├── _UnauthCRMModule      ← owns UnauthenticatedCRMAgent
│   ├── _AuthCRMModule        ← owns AuthenticatedCRMAgent
│   ├── _TransferModule       ← owns BankTransferAgent
│   ├── _DisputesModule       ← owns DisputesAgent
│   ├── ApprovalModule        ← HITL approval queue + HTTP endpoints
│   ├── ActiveAgentModule     ← conversation → agent routing state
│   ├── CostTracker           ← accumulates ModelCallComplete signals
│   └── BankingChatController ← POST /api/banking/chat and /api/banking/chat/public (SSE)
├── BankingModule             ← BankDatabase (in-memory) + REST endpoints
├── WsModule                  ← WebSocket gateway + EventForwarder + public/auth token controllers
├── CryptoModule              ← HMAC-SHA256 sign/verify + SignatureGuard + AuthenticatedUserGuard
├── MetricsModule             ← traces + cost endpoints
└── HealthModule
```

### Agent System (`app/ai/`)

Four English-language agents, each with an isolated conversation store:

| Agent | Runner token | Tools |
|---|---|---|
| `UnauthenticatedCRMAgent` | `AgentRunner[UnauthenticatedCRMAgent]` | `CheckAuthenticationTool`, `HandoffToAuthenticatedCRM` |
| `AuthenticatedCRMAgent` | `AgentRunner[AuthenticatedCRMAgent]` | `GetBalanceTool`, `GetTransactionHistoryTool`, `CheckAuthenticationTool`, `HandoffTo[...]` |
| `BankTransferAgent` | `AgentRunner[BankTransferAgent]` | `ApprovalTool`, `TransferFundsTool`, `CheckAuthenticationTool`, `HandoffTo[...]` |
| `DisputesAgent` | `AgentRunner[DisputesAgent]` | `GetBalanceTool`, `GetTransactionHistoryTool`, `CheckAuthenticationTool`, `HandoffTo[...]` |

**Runner wiring:** `AgentModule.for_root(...)` synthesizes a runner type for each module. Controllers inject `AgentRunner[AgentClass]` directly; there is no separate handwritten `banking_delegation.py` anymore.

**Conversation isolation:** each agent declares its own `InMemoryConversationStore()`. Handoff context crosses agent boundaries only through the pending summary in `ActiveAgentStore`, not a shared transcript.

### `HandoffTo` Generic Tool (`app/ai/handoff_tool.py`)

`HandoffTo[AgentA, AgentB]` creates a distinct tool subclass at import time via `__class_getitem__`:

1. Reads the `@agent(name=...)` metadata from each passed class to get display names.
2. Builds a `run(ctx, to_agent: Literal["Name A", "Name B"], summary: str)` method — the `Literal` union becomes an `enum` in the JSON schema the LLM sees.
3. Re-applies `@tool()` and `@injectable()` so the subclass has its own DI token.
4. Caches the result in `HandoffTo._cache` keyed by `tuple(agent_classes)`.

The base `HandoffTo` class (without subscript) is used in `@use_tools(...)` on agent files; the concrete subscript is provided by the `AgentModule.for_root(tools=[HandoffTo[...]])` call in `ai_module.py`.

When invoked by the LLM:
- Sets `ActiveAgentStore[conversation_id] = to_agent`
- Stores a pending summary in `ActiveAgentStore`
- Emits a WebSocket `agent_handoff` event via `EventForwarder`
- Suppresses duplicate `agent_handoff` events when the active agent is already the destination

### Request Lifecycle & Security

```
Frontend → Next.js API route → HMAC-signs body → Backend
  → CorsMiddleware → LoggingMiddleware → TimingInterceptor
  → SignatureGuard: verifies X-Signature, pins user_id → request.state
  → BankingChatController: reads request.state.user_id (never raw body)
  → current_user_id ContextVar set before returning EventStream
  → ExecutionContext passed to AgentRunner.run_stream(execution_context=...)
  → ToolContext.execution_context.request.state.user_id used in tools
```

`user_id` never appears in any JSON schema the LLM receives. Tools read it from `ctx.execution_context.request.state`, which is server-side only.

### msgspec Payloads

- `ChatRequest`, `Message`, and `ChatResponse` in `app/ai/chat_schemas.py` are `msgspec.Struct` types.
- `ApprovalBody` and `WsTokenRequest` are also `msgspec.Struct`.
- `main.py` configures `LaurenFactory.create(..., json_encoder=MsgspecEncoder())`, so HTTP JSON, SSE payload encoding, and WebSocket JSON events all use the same encoder family.

### Controller Routing Loop (`app/ai/chat_banking_controller.py`)

The authenticated `/api/banking/chat` endpoint loops until the active agent stabilises:

```
while True:
    agent, runner = _agent_registry[active_agent_name]
    response = await runner.run(agent, prompt, conversation_id=..., execution_context=...)
    stream tokens to client
    new_active = active_agent_store.get(conversation_id)
    if new_active == active or handoffs >= max_handoffs: break
    yield SSE "break" event → frontend shows divider
    prepend [HANDOFF from X]: summary to next prompt
    active = new_active
```

The `_agent_registry` dict maps `UNAUTH_CRM_AGENT_NAME`, `AUTH_CRM_AGENT_NAME`,
`TRANSFER_AGENT_NAME`, and `DISPUTES_AGENT_NAME` to `(agent_instance, runner_instance)` tuples.

There is a second endpoint, `POST /api/banking/chat/public`, which always starts in `UnauthenticatedCRMAgent` and routes WebSocket events through the sentinel public user `__public__`.

### Guardrails

- `LLMScopeGuard` is attached to authenticated CRM, transfer, and disputes agents via `@use_guardrails(...)`.
- `GuardrailTriggered` is emitted for both blocked and clean evaluations.
- SSE may emit `guardrail_override` when a guardrail replaces the model output.
- WebSocket clients receive `guardrail_triggered` with `passed: true|false` so the live activity feed shows coverage, not only interventions.

### WebSocket Real-Time Events

```
BankingWsGateway (/ws/banking)  ←  authenticated via short-lived token
    ↑ registers consumer in EventForwarder
    ↑ receives: agent_handoff, token_usage, tool_started, tool_complete,
    │           run_complete, guardrail_triggered, balance_changed,
    │           transfer_approval_request
HandoffTo tool → EventForwarder.send_to_user(user_id, {...})
```

Authenticated clients obtain tokens via `POST /api/banking/ws-token` (HMAC-signed).
Guest/public chat uses `POST /api/banking/ws-token/public`, which binds the socket to `__public__`.

`EventForwarder` clears stale signal handlers in `__init__` so repeated `LaurenFactory.create(...)` calls in tests or hot reload do not duplicate WebSocket events.

### Observability

All token/cost data flows through a shared `signal_bus` singleton (`app/ai/signals.py`). `main.py` registers handlers for `AgentRunComplete` and `ModelCallComplete`. `CostTracker` accumulates per-model usage and is exposed via `GET /api/metrics/cost`.

### Test Conventions

- `tests/unit/` — import classes directly, no HTTP or event loop needed (unless async)
- `tests/integration/` — build a full `@module`, call `LaurenFactory.create`, drive via `lauren.testing.TestClient`
- `conftest.py` sets `PAYLOAD_SECRET` and `OPENROUTER_API_KEY` **before** any imports so singletons pick them up
- Integration tests for SSE: `TestClient` buffers the entire stream body; parse with a small helper rather than expecting per-frame behaviour
- Guardrail coverage lives in `tests/unit/test_agent_scope_guard.py`, `tests/unit/test_llm_scope_guard.py`, `tests/unit/test_guardrail_event_forwarder.py`, and `tests/integration/test_chatbot_guardrails_e2e.py`
- Coverage threshold: 90% (`--cov-fail-under=90`)
