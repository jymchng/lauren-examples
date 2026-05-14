# Security Model

## Contents
- HMAC-SHA256 request signing
- SignatureGuard — verify and pin identity
- AuthenticatedUserGuard
- Identity trust chain (guard → controller → runner → tool)
- Cross-user approval forgery protection
- WebSocket token authentication
- Public chat and public WebSocket sessions

## HMAC-SHA256 request signing

Every chat request passes through a Next.js API route that signs the body before
forwarding it to the Lauren backend:

```typescript
// frontend/src/app/api/banking/chat/route.ts
const body = JSON.stringify({ messages, user_id, conversation_id });
const sig = createHmac("sha256", process.env.PAYLOAD_SECRET!).update(body).digest("hex");

const res = await fetch(`${process.env.BACKEND_URL}/api/banking/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Signature": sig },
    body,
});
```

`PAYLOAD_SECRET` lives only on the Next.js server. The browser never touches it.
The Lauren backend verifies that `HMAC-SHA256(body, PAYLOAD_SECRET) == X-Signature`
before trusting any field in the body.

## SignatureGuard

```python
# app/crypto/signature_guard.py
@injectable(scope=Scope.SINGLETON)
class SignatureGuard:
    def __init__(self, crypto: CryptoService) -> None:
        self._crypto = crypto

    async def can_activate(self, ctx: ExecutionContext) -> bool:
        signature = ctx.request.headers.get("x-signature")
        if not signature:
            raise UnauthorizedError("Missing X-Signature header")

        body_bytes = await ctx.request.body()
        if not self._crypto.verify(body_bytes, signature):
            raise UnauthorizedError("Invalid payload signature")

        # Body is HMAC-verified — user_id cannot have been tampered with.
        # Pin it to request.state so all downstream code reads identity from here.
        payload = json.loads(body_bytes)
        user_id = str(payload.get("user_id", "")).strip().lower()
        if user_id:
            ctx.request.state.user_id = user_id

        return True
```

Applied at the controller level so every route is automatically protected:

```python
@use_guards(SignatureGuard)
@controller("/api/banking")
class BankingChatController: ...
```

## AuthenticatedUserGuard

`SignatureGuard` accepts both authenticated and unauthenticated requests (public
chat has no `user_id`). `AuthenticatedUserGuard` is applied on routes that
**require** a logged-in user:

```python
@injectable(scope=Scope.SINGLETON)
class AuthenticatedUserGuard:
    async def can_activate(self, ctx: ExecutionContext) -> bool:
        if not ctx.request.state.get("user_id", ""):
            raise UnauthorizedError("Authentication required")
        return True
```

```python
# Route-level guard — stacks on top of the controller-level SignatureGuard
@use_guards(AuthenticatedUserGuard)
@post("/chat")
async def stream(self, body: Json[ChatRequest], exec_ctx: ExecutionContext) -> EventStream: ...
```

That split is intentional:

- `POST /api/banking/chat` and `POST /api/banking/ws-token` require `AuthenticatedUserGuard`
- `POST /api/banking/chat/public` and `POST /api/banking/ws-token/public` do not

## Identity trust chain

```
HTTP body (HMAC-signed by Next.js proxy)
  └─► SignatureGuard.can_activate()
        verifies X-Signature
        request.state.user_id = <verified>    ← set once, immutable after this point
              │
  BankingChatController.stream()
        reads request.state.user_id           ← never trusts raw body field
        passes ExecutionContext to runner
              │
  AgentRunner.run_stream(..., execution_context=exec_ctx)
        AgentContext.execution_context = exec_ctx   ← forwarded intact, not copied
              │
  ToolContext.execution_context               ← forwarded intact
        tool reads:
          ctx.execution_context.request.state.get("user_id")
              │
  BankDatabase.transfer(from_user=auth_uid)   ← always the guard-verified identity
```

The LLM is completely outside this chain. Even if the model outputs a different
`user_id` as a tool argument, the tool ignores it and reads from `request.state`.

## Cross-user approval forgery protection

`ApprovalService.create(approval_id, user_id, ...)` records the `user_id` at
creation time. `ApprovalService.resolve(approval_id, resolver_user_id, approved)`
checks:

```python
if meta["user_id"] != resolver_user_id:
    return False   # wrong user — silently reject
```

The `resolver_user_id` comes from `request.state` (set by `SignatureGuard`),
so a different authenticated user cannot approve another user's pending transfer
even if they know the `approval_id`.

## WebSocket token authentication

```python
# app/ws/ws_gateway.py  —  @on_connect handler
user_id = self._token_service.verify_token(token)
if not user_id:
    await ws.close(code=4401, reason="invalid or expired token")
    raise WebSocketDisconnect("unauthorized", close_code=4401)
```

Tokens are HMAC-signed with a 120-second TTL, issued by:
- `WsTokenController` — POST `/api/banking/ws-token` — requires `SignatureGuard + AuthenticatedUserGuard`
- `WsPublicTokenController` — POST `/api/banking/ws-token/public` — no auth; identifies connection as `__public__`

The frontend fetches the token immediately before calling `new WebSocket(url)` so
the short TTL is not a practical constraint under normal usage.

Connecting without a valid token causes the gateway to close with code `4401`
before any messages are accepted — no events are ever forwarded to an
unauthenticated connection.

## Public chat and public WebSocket sessions

Unauthenticated visitors use a separate path:

- `POST /api/banking/chat/public` routes only to `UnauthenticatedCRMAgent`
- `POST /api/banking/ws-token/public` issues a short-lived token for the sentinel user `__public__`
- `BankingChatController.stream_public()` sets `current_user_id` to `__public__` before returning `EventStream(...)`, so public agent events still reach the live activity feed without impersonating a real account
