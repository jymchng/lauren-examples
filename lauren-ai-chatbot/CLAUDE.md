# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (run from `backend/`)

```bash
uv run python -m pytest tests/ -q                        # all tests
uv run python -m pytest tests/unit/ -q                   # unit tests only
uv run python -m pytest tests/integration/ -q            # integration tests only
uv run python -m pytest tests/unit/test_handoff.py -q    # single file
uv run ruff check app/                                   # lint
uv run ruff format --check app/                          # format check
uvicorn main:app --reload --port 8000                    # dev server (requires .env)
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
│   ├── _CRMAgentModule       ← owns BankingCRMAgentEN + BankingCRMAgentZH
│   ├── _TransferAgentModule  ← owns BankingTransferAgentEN + BankingTransferAgentZH
│   ├── ApprovalModule        ← HITL approval queue + HTTP endpoints
│   ├── ActiveAgentModule     ← conversation → agent routing state
│   ├── CostTracker           ← accumulates ModelCallComplete signals
│   └── BankingChatController ← POST /api/banking/chat  (SSE)
├── BankingModule             ← BankDatabase (in-memory) + REST endpoints
├── WsModule                  ← WebSocket gateway + EventForwarder + token auth
├── CryptoModule              ← HMAC-SHA256 sign/verify + SignatureGuard
├── MetricsModule             ← traces + cost endpoints
└── HealthModule
```

### Agent System (`app/ai/`)

Four agents in two language pairs (EN/ZH × CRM/Transfer) share two runners:

| Agent | Runner token | Tools |
|---|---|---|
| `BankingCRMAgentEN` | `CRMAgentRunner` | `GetBalanceTool`, `GetTransactionHistoryTool`, `HandoffTo[TransferEN, TransferZH]` |
| `BankingCRMAgentZH` | `CRMAgentRunner` | same |
| `BankingTransferAgentEN` | `TransferAgentRunner` | `ApprovalTool`, `TransferFundsTool`, `HandoffTo[CRMEN, CRMZH]` |
| `BankingTransferAgentZH` | `TransferAgentRunner` | same |

**Why two runner tokens, not four:** `AgentRunner.run(agent, prompt, ...)` is stateless — same runner instance serves both language variants. `banking_delegation.py` defines `CRMAgentRunner` and `TransferAgentRunner` as distinct injectable subclasses of `AgentRunnerBase` so the DI container can resolve them independently.

**Why two `AgentModule` instances, not four:** `AgentModule.for_root()` auto-registers every tool class found in `@use_tools` on its agents as a DI provider. The same tool class cannot belong to two modules (`ModuleExportViolation`). Putting both CRM language variants in `_CRMAgentModule` and both Transfer variants in `_TransferAgentModule` means each tool is owned by exactly one module.

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

### Request Lifecycle & Security

```
Frontend → Next.js API route → HMAC-signs body → Backend
  → CorsMiddleware → LoggingMiddleware → TimingInterceptor
  → SignatureGuard: verifies X-Signature, pins user_id → request.state
  → BankingChatController: reads request.state.user_id (never raw body)
  → ExecutionContext passed to AgentRunner.run(execution_context=...)
  → ToolContext.execution_context.request.state.user_id used in tools
```

`user_id` never appears in any JSON schema the LLM receives. Tools read it from `ctx.execution_context.request.state`, which is server-side only.

### Controller Routing Loop (`app/ai/chat_banking_controller.py`)

The `/api/banking/chat` endpoint loops until the active agent stabilises:

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

The `_agent_registry` dict maps `CRM_AGENT_NAME_EN/ZH` and `TRANSFER_AGENT_NAME_EN/ZH` to `(agent_instance, runner_instance)` tuples.

### WebSocket Real-Time Events

```
BankingWsGateway (/ws/banking)  ←  authenticated via short-lived token
    ↑ registers consumer in EventForwarder
    ↑ receives: agent_handoff, balance_changed, transfer_approval_request
HandoffTo tool → EventForwarder.send_to_user(user_id, {...})
```

The WS token is obtained by the frontend via `POST /api/banking/ws-token` (HMAC-signed), then passed as `?token=` on the WS URL.

### Observability

All token/cost data flows through a shared `signal_bus` singleton (`app/ai/signals.py`). `main.py` registers handlers for `AgentRunComplete` and `ModelCallComplete`. `CostTracker` accumulates per-model usage and is exposed via `GET /api/metrics/cost`.

### Test Conventions

- `tests/unit/` — import classes directly, no HTTP or event loop needed (unless async)
- `tests/integration/` — build a full `@module`, call `LaurenFactory.create`, drive via `lauren.testing.TestClient`
- `conftest.py` sets `PAYLOAD_SECRET` and `OPENROUTER_API_KEY` **before** any imports so singletons pick them up
- Integration tests for SSE: `TestClient` buffers the entire stream body; parse with a small helper rather than expecting per-frame behaviour
- Coverage threshold: 90% (`--cov-fail-under=90`)
