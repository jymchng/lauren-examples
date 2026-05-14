# WebSocket Event Feed

## Contents
- Architecture overview
- BankingWsGateway — @ws_controller with token authentication
- WsTokenService — short-lived token issue/verify
- EventForwarder — user_id → WebSocket fan-out + SignalBus handlers
- ContextVar routing (current_user_id)
- Public-session routing (`__public__`)
- Event type reference

## Architecture overview

```
HTTP handler task (BankingChatController.stream)
  │  current_user_id.set(user_id)     ← ContextVar set before EventStream returned
  │
  AgentRunner.run_stream()
    │
    SignalBus.emit(ModelCallComplete | ToolCallStarted | ...)
      │  asyncio.gather() copies ContextVar state into each spawned handler task
      │
      EventForwarder signal handler
        │  current_user_id.get()      ← reads the HTTP handler's user_id
        │
        EventForwarder.send_to_user(user_id, payload)
          └── ws.send_json(payload)   for each WebSocket in _connections[user_id]
```

Balance-change events skip the ContextVar path and use `broadcast()` — they are
relevant to every connected user, not just the one who initiated the transfer.
Public chat also uses this pipeline: the controller sets `current_user_id` to
the sentinel `__public__` before returning `EventStream(...)`.

## BankingWsGateway

```python
# app/ws/ws_gateway.py
@ws_controller("/ws/banking")
class BankingWsGateway:
    def __init__(self, forwarder: EventForwarder, token_service: WsTokenService) -> None:
        self._forwarder = forwarder
        self._token_service = token_service
        self._user_id: str | None = None

    @on_connect
    async def connect(self, ws: WebSocket, token: Query[str]) -> None:
        user_id = self._token_service.verify_token(token)
        if not user_id:
            await ws.close(code=4401, reason="invalid or expired token")
            raise WebSocketDisconnect("unauthorized", close_code=4401)
        self._user_id = user_id
        await self._forwarder.register(user_id, ws)

    @on_disconnect
    async def disconnect(self, ws: WebSocket) -> None:
        if self._user_id:
            await self._forwarder.unregister(self._user_id, ws)
```

`@ws_controller` defaults to `Scope.REQUEST`, so each connection gets its own
gateway instance — `self._user_id` is per-connection state, not shared.

Clients connect as: `ws://host/ws/banking?token=<token>`

## WsTokenService

Issues HMAC-signed tokens with a configurable TTL (default 120 seconds).

Two controllers issue tokens:
- `WsTokenController` — POST `/api/banking/ws-token` — requires `SignatureGuard + AuthenticatedUserGuard`; issues a token for the authenticated user
- `WsPublicTokenController` — POST `/api/banking/ws-token/public` — no auth required; issues a token identifying the connection as `__public__`

The browser fetches the token immediately before opening the WebSocket connection
so the 120-second TTL is not a practical constraint.

## EventForwarder

```python
# app/ws/event_forwarder.py
@injectable(scope=Scope.SINGLETON)
class EventForwarder:
    def __init__(self, db: BankDatabase) -> None:
        # Clear stale handlers from prior app instances (hot-reload / test isolation).
        # EventForwarder is the sole subscriber for these types so clearing is safe.
        for et in (ModelCallComplete, ToolCallStarted, ToolCallComplete,
                   AgentRunComplete, GuardrailTriggered):
            signal_bus.clear(et)

        signal_bus.on(ModelCallComplete)(self._on_model_complete)
        signal_bus.on(ToolCallStarted)(self._on_tool_started)
        signal_bus.on(ToolCallComplete)(self._on_tool_complete)
        signal_bus.on(AgentRunComplete)(self._on_run_complete)
        signal_bus.on(GuardrailTriggered)(self._on_guardrail_triggered)
        db.add_transfer_listener(self._on_transfer)

    async def register(self, user_id: str, ws: WebSocket) -> None: ...
    async def unregister(self, user_id: str, ws: WebSocket) -> None: ...
    async def send_to_user(self, user_id: str, payload: dict) -> None: ...
    async def broadcast(self, payload: dict) -> None: ...
```

`signal_bus.clear(event_type)` prevents N-times handler duplication when
`LaurenFactory.create()` is called more than once in the same Python process
(dev hot-reload, multiple test fixtures in the same pytest session).

Dead WebSocket connections are pruned automatically: `send_to_user` catches any
send exception and removes the offending `WebSocket` from `_connections`.

## ContextVar routing

```python
# app/ws/context.py
from contextvars import ContextVar
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
```

The chat controller sets `current_user_id.set(user_id)` **before** returning
the `EventStream`, not inside the async generator:

```python
# Correct — set on the handler task
if user_id:
    current_user_id.set(user_id)
return EventStream(generate(), keep_alive=15.0)

# Wrong — set inside generate()
async def generate():
    current_user_id.set(user_id)   # only affects the first __anext__() task
    ...
```

`asyncio.gather` (used internally by `SignalBus.emit`) copies ContextVar state
into each spawned coroutine. Setting the var inside the generator only affects
the first `__anext__()` task; subsequent chunk advances see `None` and events
are silently dropped.

## Event type reference

| `type` | Trigger | Key fields |
|---|---|---|
| `token_usage` | After each LLM call | `model`, `input_tokens`, `output_tokens`, `cost_usd`, `duration_ms` |
| `tool_started` | Tool call dispatched | `tool_name`, `tool_use_id` |
| `tool_complete` | Tool call finished | `tool_name`, `tool_use_id`, `success`, `duration_ms`, `error` |
| `run_complete` | Full agent run done | `turns`, `total_cost_usd`, `total_tokens` |
| `agent_handoff` | `HandoffTo` executes | `from_agent`, `to_agent`, `summary` |
| `balance_changed` | Transfer executes | `from_user`, `to_user`, `amount`, `balances` (broadcast to ALL users) |
| `transfer_approval_request` | `ApprovalTool` fires | `approval_id`, `from_user`, `to_user`, `amount_usd`, `description`, `created_at` |
| `guardrail_triggered` | Output guardrail evaluates a response | `guardrail_name`, `agent_name`, `violation`, `passed` |

`passed=True` means the response was evaluated and allowed through unchanged.
`passed=False` means the guardrail fired and replaced the response. The live
activity feed shows both so operators can see coverage, not just blocks.
