# PRD — Lauren Eats Backend: Full Adoption of `lauren` and `lauren-ai`

> **Project:** `lauren-eats` — AI-Powered Chinese Restaurant Platform
> **Backend path:** `lauren-examples/lauren-eats/backend/`
> **Author:** opencode gap analysis
> **Date:** 2026-06-05
> **Status:** Draft v1
> **Companion packages:** `lauren-framework` (web framework), `lauren-ai` (LLM/agent runtime)

---

## 1. Executive Summary

`lauren-eats/backend` is a Next.js-shaped Chinese restaurant API ported to
Python. The repository already advertises that it is **"built with lauren and
lauren-ai"** (see `backend/README.md` and `backend/pyproject.toml`), but the
implementation only scratches the surface of both libraries:

- The **lauren-framework half** of the stack is mostly invoked through the
  bare-minimum `LaurenFactory.create` + `@module` + `@controller` + `@get` /
  `@post` + `@injectable` path. It skips every cross-cutting concern that
  the framework provides: `global_middlewares`, `global_guards`,
  `global_interceptors`, `global_exception_handlers`, `global_providers`,
  `signal_bus`, `MsgspecEncoder`, `BackgroundTasks`, `WebSocket` gateways,
  `StaticFilesModule`, `app.mount`, `@exception_handler`, `@use_guards`,
  `@use_interceptors`, `@use_middlewares`, `@post_construct`, `@pre_destruct`,
  `Path[T]` / `Query[T]` / `Json[T]` typed extractors, and `@set_metadata`.
- The **lauren-ai half** of the stack is **decorative**. Six `@agent()`-decorated
  classes exist on disk, but **no `AgentModule` is ever created, no `LLMModule`
  is ever created, no `AgentRunner` is ever invoked, and no `LLMService` ever
  talks to a model.** A bespoke hand-rolled `httpx.AsyncClient` call inside
  `ChatService` re-implements the LLM transport layer, and a hand-rolled
  regex `<<HANDOFF:agent>>` parser re-implements `HandoffTo[AgentA, AgentB]`.

In short: the project is a CRUD app for menu, orders, and reservations
with a `gpt-4` string in the `agent()` decorator, but the agents themselves
are never loaded, never bound to an `AgentRunner`, and never executed.

The goal of this PRD is to enumerate every gap between the current state
and a full, idiomatic use of both `lauren` and `lauren-ai`, and to propose
the migration path that closes those gaps.

---

## 2. Reference Implementation

The `lauren-ai-chatbot` example in `lauren-examples/lauren-ai-chatbot/backend/`
serves as the **canonical reference** for how a production backend should
consume both libraries together. Its `CLAUDE.md` documents the full
architecture (4 agents, 4 `AgentModule`s, `LLMModule` + `LLMService`,
`SignalBus`, `Signal`-driven `CostTracker`, `LLMScopeGuard`, `HandoffTo[...]`,
`WebSocket` gateway, `EventForwarder`, HMAC `SignatureGuard`, `TraceStore`,
`@use_guards`, `@use_interceptors`, `MsgspecEncoder`, etc.).

Every "missing" item in this PRD points at a specific pattern that
`lauren-ai-chatbot` already exercises.

---

## 3. Current State Snapshot

### 3.1 What is wired today

| Layer | Wired | Notes |
| --- | --- | --- |
| `@module` + `LaurenFactory.create` | ✅ | Single `AppModule`; factory called with `docs_url`, `title`, `version`, `description` only. |
| `@controller` + `@get`/`@post`/`@put`/`@patch` | ✅ | 8 controllers (health, menu, category, order, reservation, admin, seed, chat). |
| `@injectable(scope=Scope.SINGLETON)` | ✅ | `DatabaseService`, `MenuService`, `OrderService`, `ReservationService`, `AdminService`, `ChatService`. |
| DI for services | ✅ | `__init__(self, db: DatabaseService)` injection works. |
| `EventStream` + `ServerSentEvent` | ✅ | `ChatController.chat` returns `EventStream(generate(), keep_alive=15.0)`. |
| `ExecutionContext` extraction | ✅ | `chat` accepts `ctx: ExecutionContext`. |
| SSE keep-alive | ✅ | `keep_alive=15.0`. |
| `@tool()` decorator | ✅ (decorative) | Six tools in `app/agents/tools.py` — each returns a placeholder dict ("connect to database for live results"). |
| `@agent()` decorator | ✅ (decorative) | Six agent classes — never executed, never bound to a runner. |
| `@use_tools()` decorator | ✅ (decorative) | Stacked above `@agent()`; metadata exists but is never read by a runner. |
| `aiosqlite` DB layer | ✅ | `DatabaseService` with schema migration. |
| Seed data (8 categories, 42 items) | ✅ | `seed.py` is solid. |
| Pydantic models | ✅ (orphan) | `app/models/{menu,order,reservation,chat}.py` exist but are never imported by controllers. |

### 3.2 What is missing (high-level roll-up)

The gap analysis identified **66 distinct gaps** across the two packages,
organised into 12 sections below. The gap list is exhaustive — every item
is grounded in either a code reference in `lauren-framework` /
`lauren-ai` or a pattern already exercised in `lauren-ai-chatbot/backend/`.

| Section | Area | Gaps |
| --- | --- | --- |
| §4 | `lauren` core / module structure | 11 |
| §5 | `lauren` middleware / guards / interceptors / exception handlers | 7 |
| §6 | `lauren` extractors and Pydantic integration | 6 |
| §7 | `lauren` observability / lifecycle / signals | 6 |
| §8 | `lauren` cross-cutting (encoder, logger, OpenAPI, static, mount) | 6 |
| §9 | `lauren-ai` LLM transport / `LLMModule` / `LLMService` | 7 |
| §10 | `lauren-ai` `AgentModule` / `AgentRunner` / agents in flight | 9 |
| §11 | `lauren-ai` tools (real DI-backed tool execution) | 4 |
| §12 | `lauren-ai` handoff, guardrails, knowledge, memory | 7 |
| §13 | `lauren-ai` observability (cost, tracing, signals, rate limit) | 6 |
| §14 | `lauren-ai` extractors, output parsers, chains | 4 |
| §15 | Code-quality, testing, CI | 8 |
| **Total** | | **66** |

---

## 4. `lauren` — Core / Module Structure Gaps

### Gap 4.1 — Single flat `AppModule` instead of a feature module graph

**Today:** `app/modules.py` declares a single `AppModule` with 8 controllers
and 5 providers. Every domain is a flat sibling — there is no encapsulation,
no module boundary, no per-domain provider.

**Why it matters:** `lauren`'s module system enforces NestJS-style
encapsulation. `use_factory`, `use_value`, multi-binding, and cross-module
`AgentRunner[X]` resolution all depend on a real module graph. With one
module you cannot reuse any of these patterns.

**Fix:** Split `AppModule` into feature modules, each owning its
controllers and providers, with `imports=[…]` / `exports=[…]` boundaries.

Proposed module graph (mirrors `lauren-ai-chatbot`):

```
AppModule (root)
├── HealthModule       — HealthController
├── MenuModule         — MenuController, CategoryController, MenuService
├── OrderModule        — OrderController, OrderService
├── ReservationModule  — ReservationController, ReservationService
├── AdminModule        — AdminController, AdminService
├── SeedModule         — SeedController
├── AIModule           — ChatController, ChatService, all agents
│   ├── LLMProviderModule   (LLMModule.for_root(...))
│   ├── ConciergeAgentModule, FoodRecommenderAgentModule, DietaryAgentModule,
│   │   OrderingAgentModule, ReservationAgentModule, SupportAgentModule
│   ├── HandoffModule       (HandoffTo[...] tools)
│   └── ToolModule          (search_menu, get_menu_item_details, …)
└── ObservabilityModule — CostTracker, TraceExporter, signal handlers
```

**Reference:** `lauren-ai-chatbot/backend/app/app_module.py:18` (5
`@module(imports=[…])` boundary with `_UnauthCRMModule`, `_AuthCRMModule`,
`_TransferModule`, `_DisputesModule`).

---

### Gap 4.2 — `use_value` / `use_class` / `use_factory` / `use_existing` not used

**Today:** DI is entirely class-based. There is no `use_value(provide=Token,
value=…)` (e.g. for `LLMConfig` or `KnowledgeSource`), no `use_factory`
(for things like a per-request conversation store), no `use_class` (for
delegation tool aliases).

**Why it matters:** `lauren-ai` is *deeply* built around custom providers —
`AgentModule.for_root` registers `Transport`, `LLMConfig`, `LLMService`,
`EmbedService`, `CostTracker` via `use_value`; `HandoffTo[X, Y]` aliases via
`use_class`; `AgentRunner[X]` via `use_factory`. Without these you cannot
wire lauren-ai at all.

**Fix:** Adopt the standard four custom-provider recipes from
`lauren._di.custom` (`use_value`, `use_class`, `use_factory`,
`use_existing`) wherever a singleton or alias is needed.

**Reference:** `lauren-ai/src/lauren_ai/_module.py:387-419` and `872-1050`.

---

### Gap 4.3 — No `Token` / `Inject` for non-class DI tokens

**Today:** All DI annotations are concrete classes.

**Why it matters:** Some long-lived singletons are not naturally
class-shaped (e.g. an `LLMConfig` dataclass, a connection pool, a
`MemoryStore` instance). `Token[T]` + `Inject[Token]` is the idiomatic
channel.

**Fix:** Use `Token` for cross-module boundary types — at minimum
`LLMConfig` (re-exported from `LLMModule`).

---

### Gap 4.4 — Database connection is opened in `main.py` instead of `@post_construct`

**Today:** `main.py:16-22` calls `await db.connect()` from
`asyncio.run(startup_init())` **before** `uvicorn.run(…)`, completely
bypassing the lauren lifecycle. There is no `@post_construct` hook on
`DatabaseService` and no equivalent on any other service.

```python
# backend/main.py:16-22 (current)
async def startup_init() -> None:
    db = DatabaseService()
    await db.connect()
    await db.close()
```

**Why it matters:** Bypassing the lifecycle means:

1. The DB is opened **and closed** before uvicorn even starts — when a
   real request arrives, `DatabaseService.conn` raises `RuntimeError("Database
   not connected")`.
2. `LaurenApp.startup()` never runs, so `@post_construct` and
   `@pre_destruct` are dead.
3. `ShutdownBegin` / `ShutdownComplete` signal listeners are never fired.

**Fix:** Move the connection logic into `@post_construct async def _init(self)
-> None: await self._connect()` on `DatabaseService` and call
`app.startup()` (or rely on ASGI lifespan — the framework already supports
it). The `db.close()` belongs in `@pre_destruct async def _teardown(self)`.

**Reference:** `lauren-ai-chatbot/backend/app/ai/ai_module.py:77` — `LLMProvider
= LLMModule.for_root(_llm_config)` wires the transport via DI, no manual
`__init__` calls.

---

### Gap 4.5 — `asyncio.run(startup_init())` blocks before uvicorn boots

**Today:** `main.py:57-71` runs `asyncio.run(startup_init())` then
`uvicorn.run(…)`. The init function opens and immediately closes the DB.

**Why it matters:** This pattern is dead code (the connection is closed
before the first request) and is a red flag for any reviewer familiar with
ASGI lifespans.

**Fix:** Remove `startup_init`. Rely on `LaurenApp.startup()` (invoked
automatically by uvicorn's lifespan protocol) plus `@post_construct` on
`DatabaseService`.

---

### Gap 4.6 — `ChatController` constructs a manual `async def generate():` instead of using `EventStream(generator)` directly with typed events

**Today:** `chat_controller.py:33-47` decodes bytes to text, splits on
`\n\n`, strips `data: ` prefixes, and yields `ServerSentEvent(data=…)`.
The hand-rolled framing layer re-parses data the upstream `httpx.stream`
already framed.

**Why it matters:** `EventStream` is designed to consume `ServerSentEvent`
or `Mapping[str, Any]` directly — yielding dicts is supported
(`from_dict(mapping)` at `sse.py:103`). The current round-trip is
wasteful and brittle.

**Fix:** Have `ChatService.stream_chat` yield `ServerSentEvent` instances
or plain dicts (e.g. `{"event": "token", "data": "…"}`) directly. Drop the
`text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk` block.

---

### Gap 4.7 — `Json[Model]` extractor not used; controllers read `body: dict`

**Today:** Every `POST`/`PUT`/`PATCH` handler accepts `body: dict` and
re-validates with `body.get("…", default)` chains. `OrderController.create_order`,
`OrderController.update_order`, `ReservationController.create_reservation`,
etc.

**Why it matters:** `Json[T]` extractor auto-validates the body against
a Pydantic model, returns clean 422s on validation failure, and feeds
typed models into OpenAPI. The `app/models/*.py` Pydantic models are
already defined (and unused) — this is a one-line swap per handler.

**Fix:** Replace `body: dict` with `body: Json[CreateOrderRequest]`,
`body: Json[UpdateOrderRequest]`, `body: Json[CreateReservationRequest]`,
`body: Json[UpdateReservationRequest]`, `body: Json[SendChatMessageRequest]`,
`body: Json[MenuItemUpdate]`. Pydantic validates the camelCase mapping via
`Field(..., alias="…")` already declared in the models.

**Reference:** `lauren-ai-chatbot/backend/app/ai/chat_banking_controller.py:91` —
`body: Json[ChatRequest]` with msgspec.

---

### Gap 4.8 — `Path[int]`, `Query[int]`, `Header[str]` not used; path params default to `str`

**Today:** `@get("/{id}")` handlers receive `id: str`, and query params
use string defaults like `category: str = "all"`, `isVegetarian: str = ""`.
`MenuController.list_menu` accepts **8** query params and converts them
inline.

**Why it matters:** `Path[int]` / `Query[int]` are auto-validated and
surface 422s on bad input. The current pattern accepts `"abc"` for an
integer and silently treats `isVegetarian="not-a-bool"` as `False`.

**Fix:** Replace the strings with typed extractors.

```python
@get("/")
async def list_menu(
    self,
    page: Query[int] = 1,
    limit: Query[int] = 12,
    category: Query[str] = "all",
    is_vegetarian: Query[bool] = False,
    ...
) -> dict: ...
```

`Path[str]` should be used on `id` parameters even if they're strings, to
make the route contract explicit.

---

### Gap 4.9 — Tuples `(body, status)` instead of `Response` subclasses

**Today:** `MenuController.get_menu_item` returns
`{"success": False, "error": "Menu item not found"}, 404`. The
`lauren.framework` return-coercion pipeline accepts this tuple form
correctly (it is documented), so this is **not a bug** — it is a missed
opportunity to use the typed `Response.empty(404)` or `Response.json(404, …)`
form, which is consistent with the rest of the framework.

**Fix (low priority):** Adopt `Response.json(404, {"success": False, "error": "Menu item not found"})`
for consistency with the framework idioms.

---

### Gap 4.10 — No `BackgroundTasks` for fire-and-forget work

**Today:** `AdminController.get_ai_insights` reads the last 500 user
messages synchronously and classifies them with a Python
`any(w in t for w in ["recommend", "suggest", …])` keyword loop. This
is a hot-path operation that could be deferred.

**Why it matters:** `BackgroundTasks` is the framework's idiomatic way to
queue post-response work (analytics aggregation, push notifications,
email send). Not used.

**Fix:** Move the `get_ai_insights` heavy lifting into a `BackgroundTasks`
handler that runs after the response is flushed.

**Reference:** `lauren` `BackgroundTasks` exported from
`lauren.background`.

---

### Gap 4.11 — No `app.mount()` / sub-app / static files

**Today:** No `StaticFilesModule`, no `app.mount("/files", …)`, no
`app.mount("/legacy", legacy_app)`.

**Why it matters:** `lauren` ships `StaticFilesModule` and an ASGI
mount API. The seed data has an `image` column that is currently populated
with emoji — for a real deployment, the static asset path needs to be
served.

**Fix:** Mount `StaticFilesModule(directory="static", path_prefix="/static")`
or use `app.mount("/static", static_asgi_app)`.

---

## 5. `lauren` — Middleware / Guards / Interceptors / Exception Handlers

### Gap 5.1 — `global_middlewares` parameter not passed to `LaurenFactory.create`

**Today:** `main.py:27-33` calls `LaurenFactory.create(AppModule, docs_url,
title, version, description)`. No `global_middlewares=`, no
`global_guards=`, no `global_interceptors=`, no
`global_exception_handlers=`, no `global_providers=`.

**Why it matters:** All cross-cutting concerns (CORS, logging, timing,
auth, request-id) belong in `global_middlewares` / `global_guards` /
`global_interceptors`. The factory accepts them as kwargs.

**Fix:**

```python
app = LaurenFactory.create(
    AppModule,
    global_middlewares=[CORSMiddleware, RequestIdMiddleware, RequestLogMiddleware],
    global_guards=[SignatureGuard],  # if HMAC signing is added
    global_interceptors=[TimingInterceptor, TokenUsageInterceptor],
    global_exception_handlers=[ValidationExceptionHandler],
    global_providers=[ConsoleLogger],
    logger=default_logger(),
    json_encoder=MsgspecEncoder(),
    error_format="rfc7807",
    signals=signal_bus,
)
```

---

### Gap 5.2 — CORS is wired through a `try/except ImportError` branch in `main.py`

**Today:** `main.py:36-48` does:

```python
try:
    from lauren_middlewares import CORSMiddleware
    app.add_middleware(CORSMiddleware, ...)
except ImportError:
    pass
```

**Why it matters:**

1. `app.add_middleware` is called *after* the factory has already built
   the app — but `LaurenApp.add_middleware` does not exist as a public
   method (the supported API is the `global_middlewares=` factory
   kwarg, or per-controller `@use_middlewares(...)`). So this either
   silently no-ops or breaks at runtime.
2. The `ImportError` branch silently swallows the failure — CORS is
   effectively dead in CI environments where `lauren-middlewares` is
   missing.

**Fix:** Declare `lauren-middlewares` as a hard dependency in
`pyproject.toml` and pass `CORSMiddleware` via `global_middlewares=`.

**Reference:** `lauren-middlewares/lauren_middlewares/cors.py` — the
canonical CORS factory.

---

### Gap 5.3 — No `@use_guards` / `@use_guards` on admin or sensitive routes

**Today:** `AdminController.get_stats` and `AdminController.get_ai_insights`
are world-readable. There is no role check, no API-key check, no
`@use_guards(AdminAuthGuard)`.

**Why it matters:** Admin endpoints must be guarded. `lauren` exposes
`@use_guards(*classes)` at the class and method level, with a
`GuardProtocol.can_activate` interface.

**Fix:** Define an `AdminAuthGuard` (reads `Authorization: Bearer …` from
`request.state`), attach with `@use_guards(AdminAuthGuard)` on
`AdminController`. Optionally promote to a global guard with a path
filter.

**Reference:** `lauren-ai-chatbot/backend/app/crypto/authenticated_user_guard.py:1`
— `AuthenticatedUserGuard` used as both `@use_guards(AuthenticatedUserGuard)`
on the route and as a class-level guard on the controller.

---

### Gap 5.4 — No `@use_interceptors` (no TimingInterceptor, no metrics interceptor)

**Today:** No `TimingInterceptor`. Every request response time is invisible
unless someone wraps each handler in a timer manually.

**Why it matters:** `lauren-ai` ships `ai_metrics_interceptor` and
`token_usage_response_interceptor` that emit metrics on every request.
`lauren` itself has no built-in interceptor but the pattern is the
standard cross-cutting concern.

**Fix:** Add a `TimingInterceptor` (logs request duration), and a
`TokenUsageInterceptor` (reads `request.state.last_token_usage` set by
the chat service and adds it to the response headers).

**Reference:** `lauren-ai-chatbot/backend/main.py:86` — `global_interceptors=[TimingInterceptor]`.

---

### Gap 5.5 — No `@exception_handler`; controllers use bare `try/except Exception`

**Today:** `MenuController.list_menu`, `OrderController.list_orders`,
`ReservationController.list_reservations`, `AdminController.get_stats` —
all wrap their handler in `try/except Exception as e: return {"success":
False, "error": str(e)}`. Errors are returned as 200 OK with an `error`
field.

**Why it matters:** This pattern:

1. Swallows the HTTP status code (errors should be 4xx/5xx).
2. Bypasses lauren's `HTTPError` envelope (`{"error": {"code", "message",
   "detail"}}`).
3. Prevents `error_format="rfc7807"` from emitting a proper Problem
   document.
4. Blocks `@use_exception_handlers` from intercepting known exception
   types.

**Fix:** Define a single `@exception_handler(ValidationError)` (for
`ValueError` raised by services) and a default handler, and let
unhandled exceptions bubble up so `LaurenApp.handle` produces a 500
through the standard envelope. Convert `return {"success": False, ...},
400` to `raise HTTPError(400, "VALIDATION_ERROR", str(e))` or return a
`Pydantic` error model.

**Reference:** `lauren.exceptions.HTTPError`, `lauren.exceptions.HTTPError`
imported at `lauren/__init__.py:121-122`.

---

### Gap 5.6 — No global exception handlers

**Today:** The `LaurenFactory.create` call does not pass
`global_exception_handlers=[…]`. Even if individual handlers were defined,
they would not be wired in.

**Why it matters:** Hand-rolled `try/except` in every controller is the
most common bug surface in this codebase. The framework expects
`@exception_handler(ExcType)` decorators + `use_exception_handlers([…])`
or `global_exception_handlers=[…]`.

**Fix:** After Gap 5.5, register a global `DatabaseExceptionHandler`,
`ValidationExceptionHandler`, and `UnauthorisedHandler` via
`global_exception_handlers=[…]`.

---

### Gap 5.7 — Per-route / per-controller middleware + guard chain is empty

**Today:** No `@use_middlewares`, no `@use_guards`, no `@use_interceptors`,
no `@use_exception_handlers` decorators anywhere in the controllers.

**Why it matters:** The framework supports all four. The reference
`lauren-ai-chatbot` uses `@use_guards(SignatureGuard)` on the controller
class and `@use_guards(AuthenticatedUserGuard)` on a specific route.

**Fix:** Migrate at least `AdminController` and `ChatController` to use
guards/middleware as appropriate.

---

## 6. `lauren` — Extractors and Pydantic Integration

### Gap 6.1 — `Json[Model]` not used (already covered as Gap 4.7)

The orphan Pydantic models in `app/models/` are unused. The `Json[T]`
extractor is the framework's solution.

### Gap 6.2 — `Path[T]` and `Query[T]` not used (already covered as Gap 4.8)

### Gap 6.3 — `Header[T]` and `Cookie[T]` not used

**Today:** `ChatController` uses `ctx: ExecutionContext` (correct) and
reads nothing else from the request. No `Authorization: Bearer …`,
no `X-Request-Id`.

**Why it matters:** `Header[str]` and `Cookie[str]` are the typed channels
for these common headers.

**Fix:** For example, an admin auth flow:

```python
@get("/admin/stats")
async def get_stats(self, auth: Header[str] = HeaderField("authorization")) -> dict: ...
```

### Gap 6.4 — `Depends[T]` / `State` not used

**Today:** No request-scoped DI. All state lives in process-wide
singletons.

**Why it matters:** `Depends[T]` is the framework's per-request channel.
`State` is the request-state accessor for cross-component data sharing
(used heavily in `lauren-ai-chatbot` — `request.state.user_id` is set by
`SignatureGuard` and read by every tool).

**Fix:** Add a `RequestContext` injectable that uses `State` to thread
the auth principal / conversation id / `current_user_id` through the
request lifecycle.

**Reference:** `lauren-ai-chatbot/backend/app/ai/chat_banking_controller.py:101-102`
— `request = exec_ctx.request; user_id = (request.state.get("user_id") or …)`.

### Gap 6.5 — `UploadFile` / `Form` / `Bytes` extractors not used

**Today:** No file upload endpoint. The menu item `image` column is
populated with emoji strings (no real upload).

**Why it matters:** When admin wants to upload a real image, the
framework's `UploadFile` extractor is the typed channel.

**Fix:** Add `POST /api/admin/menu/{id}/image` with `image: UploadFile`.

### Gap 6.6 — `ExtractionMarker.extract` not used; no custom extractors

**Today:** All extraction is `body: dict` plus raw string path params.

**Why it matters:** `ExtractionMarker.extract(execution_context, extraction)`
is the extension point for project-specific extractors (e.g.
`CurrentUser`, `ConversationContext`, `AgentForRequest`).

**Fix:** Add a `ConversationContext` extractor that resolves
`conversation_id` (from path or body) and loads the active conversation
from the `ConversationStore`.

---

## 7. `lauren` — Observability / Lifecycle / Signals

### Gap 7.1 — No `SignalBus` is passed to `LaurenFactory.create`

**Today:** `main.py:27-33` does not pass `signals=…`. The framework
falls back to a per-app `SignalBus` constructed in `LaurenApp.__init__`,
but no application-level listeners are registered.

**Why it matters:** Every cross-cutting concern (`RequestComplete`,
`RequestReceived`, `StartupBegin`, `ShutdownBegin`, `AgentRunComplete`,
`ModelCallComplete`) flows through signals. With no shared bus, the
`lauren-ai` `SignalBus` is not wired in.

**Fix:**

```python
from lauren import SignalBus
from app.observability.signal_handlers import install_default_handlers

signal_bus = SignalBus()
install_default_handlers(signal_bus)

app = LaurenFactory.create(AppModule, signals=signal_bus, ...)
```

**Reference:** `lauren-ai-chatbot/backend/app/ai/signals.py:13` — a
shared `signal_bus` is constructed at module import and reused by both
`main.py` and `ai_module.py`.

### Gap 7.2 — No `@post_construct` on `DatabaseService`

**Today:** `DatabaseService.__init__` only stores the DB path. The
`connect()` is called manually from `main.py`'s `startup_init`.

**Why it matters:** The framework's `@post_construct` runs after the DI
graph is built, before the first request. It's the right place to open
DB connections, warm up caches, prime knowledge bases, etc.

**Fix:**

```python
@injectable(scope=Scope.SINGLETON)
class DatabaseService:
    def __init__(self) -> None:
        ...

    @post_construct
    async def _open(self) -> None:
        await self._connect()
        await self._init_schema()

    @pre_destruct
    async def _close(self) -> None:
        await self._close()
```

### Gap 7.3 — No `@pre_destruct` anywhere

**Today:** `DatabaseService.close()` exists but is never invoked.

**Why it matters:** Graceful shutdown requires the DI graph to call
`@pre_destruct` in reverse topological order.

**Fix:** Same as Gap 7.2 — add `@pre_destruct` to `DatabaseService`.

### Gap 7.4 — No `app.startup()` / `app.shutdown()` invocation in `main.py`

**Today:** `uvicorn.run(…)` is called directly. There is no explicit
`app.startup()` / `app.shutdown()` coroutine wiring. The lauren
lifespan protocol implementation handles this automatically, but only
when the ASGI app exposes a `lifespan` callable (it does — `LaurenApp`
is implemented as an ASGI 3.0 app with lifespan support).

**Why it matters:** The `asyncio.run(startup_init())` line in `main.py:60`
runs **before** the app has been built — it's pure dead code. The actual
lifespan handlers fire correctly when uvicorn starts, but the dev's
intent (run init before serving) is not achieved.

**Fix:** Remove `asyncio.run(startup_init())` and `startup_init()` itself.
Rely on `LaurenApp.startup()` (called from uvicorn lifespan).

### Gap 7.5 — No `app.on_shutdown` callback registered

**Today:** No `app.on_shutdown(flush_buffers)`.

**Why it matters:** A graceful shutdown drains in-flight requests,
runs `on_shutdown` callbacks, then runs `@pre_destruct` hooks. Custom
flushes (e.g. metric flush) belong in `on_shutdown`.

**Fix:** If `opentelemetry` / `prometheus` / log shipping is added,
register a flush callback.

### Gap 7.6 — `RequestComplete` / `RequestReceived` listeners not used

**Today:** No `@signal_bus.on(RequestComplete)` listeners.

**Why it matters:** The framework emits `RequestReceived` at the start
and `RequestComplete` at the end of every request. They are the right
place to attach a request-id log line, an access log, or a metrics
counter.

**Fix:** Register an access log handler that emits
`f"{request.method} {request.path} {response.status} {duration_ms}"`.

---

## 8. `lauren` — Cross-cutting (Encoder, Logger, OpenAPI, Static, Mount)

### Gap 8.1 — `json_encoder` not set; uses stdlib `JSONEncoder`

**Today:** `LaurenFactory.create` does not pass `json_encoder=…`. The
default is `StdlibJSONEncoder` (slow, no numpy/msgspec support).

**Why it matters:** `OrjsonEncoder` or `MsgspecEncoder` are 5-50× faster
and natively encode `dataclass` / `msgspec.Struct` / `datetime` / `UUID`.

**Fix:** `json_encoder=MsgspecEncoder()` — also lets handlers return
`msgspec.Struct` directly.

**Reference:** `lauren-ai-chatbot/backend/main.py:88` — `json_encoder=MsgspecEncoder()`.

### Gap 8.2 — `logger=default_logger()` not set

**Today:** The factory's default logger is `NullLogger` (silent). All
the framework's `info` / `warn` / `error` lines are suppressed.

**Why it matters:** Production deployments need structured logging
out-of-the-box. `default_logger()` auto-detects TTY vs JSON output.

**Fix:** `logger=default_logger()`.

**Reference:** `lauren-ai-chatbot/backend/main.py:87` —
`logger=default_logger()`.

### Gap 8.3 — `error_format="rfc7807"` not set

**Today:** The default is `"default"`, which emits
`{"error": {"code", "message", "detail"}}`.

**Why it matters:** RFC 7807 (`application/problem+json`) is the modern
standard for HTTP error envelopes. Some frontend error renderers expect
it.

**Fix:** `error_format="rfc7807"`.

### Gap 8.4 — `max_body_size` not configured

**Today:** Default is 1 MiB. The chat endpoint accepts a small body
and is fine, but admin file uploads (Gap 6.5) will need a higher limit.

**Fix:** `max_body_size=10 * 1024 * 1024` (10 MiB) or pass a per-route
override.

### Gap 8.5 — `openapi_*` kwargs not set

**Today:** Only `docs_url="/docs"` is set. There is no
`openapi_url="/openapi.json"`, no `redoc_url="/redoc"`, no
`openapi_info={"title": …, "version": …, "contact": …}`.

**Why it matters:** Consumers (the frontend team, third-party integrators)
need a stable `openapi.json` URL. ReDoc is a more navigable alternative
to Swagger UI for nested responses.

**Fix:** Set `openapi_url`, `redoc_url`, `openapi_info`, and
`openapi_servers=[{"url": "/api"}]`.

### Gap 8.6 — `StaticFilesModule` not used

**Today:** No static asset serving. (See also Gap 4.11.)

**Fix:** Mount `StaticFilesModule(directory="static", path_prefix="/static")`
in the relevant feature module, or call `app.mount("/static", static_asgi)`.

---

## 9. `lauren-ai` — LLM Transport / `LLMModule` / `LLMService`

### Gap 9.1 — No `LLMConfig` constructed; env vars read manually in `ChatService`

**Today:** `chat_service.py:128-132` reads `LLM_API_KEY`, `LLM_API_BASE`,
`LLM_MODEL` from `os.environ` directly:

```python
api_key = os.environ.get("LLM_API_KEY", "")
api_base = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")
model = os.environ.get("LLM_MODEL", "gpt-4")
```

**Why it matters:** `LLMConfig` is the canonical, frozen, type-checked
config object that every transport in the framework consumes. By
bypassing it, the chat service cannot be reused by any
`@agent()`-decorated class, the `LLMService` cannot be tested via
`LLMConfig.for_testing()`, and there's no way to switch providers
(`openai` ↔ `anthropic` ↔ `ollama` ↔ `litellm`) without code changes.

**Fix:** Construct an `LLMConfig` once at module import and pass it
through `LLMModule.for_root(config)`. Use the
`LLMConfig.for_openai(model=..., api_key=os.environ["..."])` classmethod.

**Reference:** `lauren-ai-chatbot/backend/app/ai/llm_config.py:18-22`.

### Gap 9.2 — No `LLMModule.for_root(...)` is ever called

**Today:** The `LLMModule` class is **never imported** in the backend.
There is no `LLMProvider` module, no `LLMService` provider, no
`EmbedService` provider.

**Why it matters:** `LLMModule.for_root(LLMConfig)` is the single
entry point that builds the `Transport` (OpenAI / Anthropic / Ollama /
LiteLLM), wraps it in `LLMService`, and registers both as DI providers.
Without it, **no agent can be executed** by an `AgentRunner`.

**Fix:** Add an `llm_config.py` and a `llm_module.py`:

```python
# app/ai/llm_config.py
from lauren_ai import LLMConfig
import os

llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_API_BASE", "https://api.openai.com/v1"),
)
```

```python
# app/ai/llm_module.py
from lauren_ai import LLMModule
from app.ai.llm_config import llm_config

LLMProvider = LLMModule.for_root(llm_config)
```

**Reference:** `lauren-ai-chatbot/backend/app/ai/ai_module.py:77`.

### Gap 9.3 — Hand-rolled `httpx.AsyncClient.stream` instead of `LLMService.complete_stream`

**Today:** `chat_service.py:135-170` manually streams from
`{api_base}/chat/completions` using `httpx`. The raw SSE chunks are
yielded back to the controller.

**Why it matters:** `LLMService.complete_stream(messages, …)` does
exactly this — but with retries, model fallbacks, cost tracking, and
signal emission. Re-implementing it means losing all of those.

**Fix:** Replace the hand-rolled `httpx` block with a single call:

```python
from lauren_ai import LLMService, Message

async def stream_chat(self, llm: LLMService, …) -> AsyncGenerator[bytes, None]:
    messages = [Message.system(system_prompt), *history, Message.user(message)]
    async for chunk in await llm.complete_stream(messages, model=model):
        if chunk.delta:
            yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk.delta}}]})}\n\n".encode()
```

### Gap 9.4 — `LLMService` not injectable into `ChatService`

**Today:** `ChatService` is constructed with only `db: DatabaseService`.
There is no `llm: LLMService` parameter.

**Why it matters:** DI for the LLM service is the whole point of
`LLMModule`. Without it, the chat service cannot be tested with
`LLMConfig.for_testing()`.

**Fix:** Add `llm: LLMService` to the `ChatService.__init__` and
register `LLMService` as a provider exported by the `LLMProvider`
module (which `LLMModule.for_root` does automatically).

### Gap 9.5 — No fallback / retry / model chain support

**Today:** The hand-rolled `try/except Exception as e: yield fallback`
catches everything and returns a generic apology. There is no automatic
retry on 429/5xx, no fallback to a secondary model.

**Why it matters:** `LLMService` has `max_retries` and the `PricingTable`
+ `CostTracker` machinery handles budget. The chat service gets none of
this.

**Fix:** Use `LLMService.complete_stream(...)` — it already retries.

### Gap 9.6 — `EmbedService` not used

**Today:** No embeddings anywhere. The admin `get_ai_insights` does
keyword matching; there is no semantic search across menu items, no
RAG over user reviews.

**Why it matters:** `LLMModule.for_root` exports `EmbedService` as a
provider. Once it is in the DI graph, any service can inject
`embed: EmbedService` to compute embeddings.

**Fix:** Add a `MenuSearchService` that embeds menu items and exposes
`/api/menu/semantic?q=…` via vector similarity.

### Gap 9.7 — No `llama_index` / RAG / vector store

**Today:** No knowledge base, no vector store, no RAG pipeline.

**Why it matters:** The agents' `HANDOFF_INSTRUCTION` is a hand-typed
string with no grounding in the actual menu. A real concierge should
search the menu for relevant dishes, not hallucinate.

**Fix:** Add a `KnowledgeSource` for the menu (`tool_name="search_menu"`,
`kb=MenuKB(items=…)`). Use `SQLiteVectorStore` from
`lauren_ai._memory._vector` for persistence.

---

## 10. `lauren-ai` — `AgentModule` / `AgentRunner` / Agents In Flight

### Gap 10.1 — No `AgentModule.for_root(...)` is ever called

**Today:** `AgentModule` is never imported. The six
`@agent()`-decorated classes exist as metadata but are not registered
with the DI graph.

**Why it matters:** `AgentModule.for_root(agents=[…], tools=[…],
imports=[LLMProvider])` is the **only** way to bind an agent to an
`AgentRunner` and register the runner as a DI provider. Without this
call, agents are pure decoration.

**Fix:** Create an `AIModule` that wires all six agents (one or more
`AgentModule`s), imports `LLMProvider`, and exports the runners.

### Gap 10.2 — `AgentRunner[X]` typed injection not used in `ChatController`

**Today:** `ChatController.__init__` accepts `chat_service: ChatService`
only. There is no `runner: AgentRunner[ConciergeAgent]`.

**Why it matters:** With `AgentRunner[ConciergeAgent]` injected, the
controller calls `await runner.run(agent, message, conversation_id=…)`
or `await runner.run_stream(agent, message, …)` directly. No need for
`ChatService` to hand-roll an HTTP call.

**Fix:** Inject `runner: AgentRunner[ConciergeAgent]`, `runner_for:
AgentRunner[FoodRecommenderAgent]`, etc. (or use a registry pattern
with `ActiveAgentStore` à la `lauren-ai-chatbot`).

### Gap 10.3 — Agents are never actually executed

**Today:** The `chat` endpoint constructs a `Message` list, calls a raw
`httpx.AsyncClient`, and yields OpenAI SSE chunks. None of the six
agents' `on_start` / `on_turn_complete` / `on_finish` hooks ever fire.

**Why it matters:** The whole point of `@agent()` is the agentic loop —
multi-turn tool use, guardrail hooks, conversation memory, signal
emission. By bypassing `AgentRunner`, the project ships agents that
are never run.

**Fix:** Replace the `chat_service.stream_chat` body with
`runner.run_stream(agent, message, …)`.

### Gap 10.4 — No `execution_context=...` is forwarded to agents

**Today:** Even the hand-rolled httpx call does not pass
`execution_context`. Tools that depend on `ctx.execution_context.request.state`
cannot access any user/identity data.

**Why it matters:** `lauren-ai-chatbot`'s `CheckAuthenticationTool` reads
`ctx.execution_context.request.state.get("user_id")` to verify identity.
`lauren-eats`'s tools have no `ToolContext` parameter at all.

**Fix:** When calling `runner.run_stream`, pass
`execution_context=exec_ctx`.

### Gap 10.5 — No `AgentMeta.tool_classes` is consumed

**Today:** Each agent's `meta.tool_classes` is populated by `@use_tools`
but never read by a runner.

**Why it matters:** It's the source of truth for which tools the agent
can call. The runner reads it; nobody here does.

**Fix:** Covered by Gap 10.1.

### Gap 10.6 — Duplicate system prompts across `chat_service.SYSTEM_PROMPTS` and each agent's `@agent(system=…)`

**Today:** `chat_service.py:50-57` declares a `SYSTEM_PROMPTS` dict with
per-agent prompts. Each agent also has a `system=f"""…"""` argument in
`@agent(model="gpt-4", system=…)`. **The two diverge** — for example,
the agent's `concierge.py:20` says "knowledgeable host" while
`chat_service.SYSTEM_PROMPTS["concierge"]` says "warm and knowledgeable
host for our authentic Chinese restaurant".

**Why it matters:** Two sources of truth → inevitable drift → user sees
the wrong persona.

**Fix:** Delete `chat_service.SYSTEM_PROMPTS`. The agent's `@agent(system=…)`
is the canonical prompt, surfaced via `AgentMeta.system`.

### Gap 10.7 — Hardcoded `model="gpt-4"` on every agent; ignores `LLMConfig.model`

**Today:** All six agents have `@agent(model="gpt-4", …)`. There is no
`@agent(model=None, …)` to inherit from `LLMConfig`.

**Why it matters:** `lauren-ai`'s `AgentModule.for_root` defaults
`AgentMeta.model` to `LLMConfig.model` when the agent's `model=None`.
The current pattern hard-pins every agent to gpt-4, preventing
per-environment overrides (e.g. `gpt-4o-mini` in CI).

**Fix:** Either:
- `model=None` on every agent, OR
- `model=os.environ.get("LLM_MODEL", "gpt-4o-mini")` evaluated at import
  time.

**Reference:** `lauren-ai-chatbot/backend/app/ai/agents/unauth_crm_agent.py:85-91`
— `model=None` everywhere, inherited from `LLMConfig`.

### Gap 10.8 — No agent lifecycle hooks (`on_start`, `on_turn_complete`, `on_finish`, `on_tool_result`)

**Today:** The six agent classes have no `async def on_start` / `on_finish` /
etc. methods. They are empty bodies.

**Why it matters:** These hooks are how the framework lets the agent
observe its own run (timing, errors, tool trace). Without them, every
agent run is opaque.

**Fix:** Add at least `on_start` (records `turn=0`) and `on_finish`
(records total cost / turns) on each agent.

**Reference:** `lauren-ai-chatbot/backend/app/ai/agents/unauth_crm_agent.py:96-117`.

### Gap 10.9 — No `AgentMeta.config` overrides (`max_turns`, `temperature`, etc.)

**Today:** `@agent(model="gpt-4", system=…)` — no `max_turns=`,
no `temperature=`, no `parallel_tool_calls=`, no `tool_error_policy=`.

**Why it matters:** These knobs are what make the agent safe (capping
`max_turns` to prevent runaway loops, `tool_error_policy="return_error"`
to recover from transient tool failures). Defaults are sensible but
explicit beats default.

**Fix:** Pass `max_turns=4` on the concierge, `max_turns=8` on the
ordering agent (it may need more tool calls), `max_cost_usd=0.10` on
all of them.

---

## 11. `lauren-ai` — Tools (real DI-backed tool execution)

### Gap 11.1 — Tools are not class-form with `@injectable`

**Today:** `app/agents/tools.py` uses function-form `@tool()`:

```python
@tool()
async def search_menu(query: str) -> dict:
    return {"results": [], "message": f"Menu search for '{query}' — …"}
```

**Why it matters:** Function-form tools have no `__init__`, so they
cannot receive `MenuService` / `OrderService` / `ReservationService`
via DI. The hand-typed `"connect to database for live results"`
placeholders are the symptom.

**Fix:** Convert to class-form tools that inject the relevant service:

```python
@tool()
@injectable(scope=Scope.SINGLETON)
class SearchMenuTool:
    def __init__(self, menu: MenuService) -> None:
        self._menu = menu

    async def run(self, ctx: ToolContext, query: str) -> dict:
        rows = await self._menu.search(query)
        return {"results": [r.model_dump() for r in rows]}
```

`@tool()` automatically applies `@injectable(scope=Scope.SINGLETON)` to
class-form tools, so the explicit `@injectable` is belt-and-braces.

**Reference:** `lauren-ai-chatbot/backend/app/ai/tools/check_auth_tool.py:12-30`.

### Gap 11.2 — Tools have no `ToolContext` parameter

**Today:** `search_menu(query: str)`, `get_menu_item_details(item_name: str)`,
`check_dietary_info(dish_name: str)`, `create_order(items: list[str])`,
`create_reservation(customer_name, party_size, date, time)`,
`check_order_status(order_number: str)`.

**Why it matters:** Without `ctx: ToolContext` (or `ctx: ToolContext = …`),
the tool cannot:
- read `ctx.execution_context.request.state` for auth,
- read `ctx.agent_context.conversation_id`,
- emit traces via `ctx.message_bus`,
- store per-call state in `ctx.state`.

**Fix:** All tools take `self, ctx: ToolContext, …` (or `ctx: ToolContext`
for function-form).

### Gap 11.3 — `create_order` tool is a stub; doesn't actually create an order

**Today:** `create_order(items: list[str])` returns a placeholder
`{"orderCreated": True, "items": items}`.

**Why it matters:** When the LLM actually calls this tool, the order is
not created in the DB. The user thinks they ordered, the kitchen sees
nothing.

**Fix:**

```python
@tool()
@injectable(scope=Scope.SINGLETON)
class CreateOrderTool:
    def __init__(self, orders: OrderService) -> None:
        self._orders = orders

    async def run(self, ctx: ToolContext, items: list[dict], notes: str | None = None) -> dict:
        order = await self._orders.create_order({"items": items, "notes": notes})
        return {"orderCreated": True, "order": order}
```

### Gap 11.4 — `create_reservation`, `check_order_status`, `get_menu_item_details`, `check_dietary_info` are stubs

**Today:** Same as Gap 11.3 — placeholder dicts.

**Fix:** Wire each to its corresponding service. `check_dietary_info` in
particular should look at `is_vegetarian` / `is_vegan` /
`is_gluten_free` / `allergens` from the `menu_items` table.

---

## 12. `lauren-ai` — Handoff, Guardrails, Knowledge, Memory

### Gap 12.1 — Hand-rolled `<<HANDOFF:agent>>` regex instead of `HandoffTo[AgentA, AgentB]`

**Today:** `chat_service.py:15-17` parses `<<HANDOFF:concierge|…>>` from
the LLM's response. `concierge.py:6-18` instructs the LLM to emit this
token.

**Why it matters:** `lauren-ai` ships `HandoffTo[AgentA, AgentB]` — a
class-form tool that:

- Builds a `Literal["AgentA Name", "AgentB Name"]` JSON schema, so the
  LLM can only call it with valid target names.
- Sets the active agent in an `ActiveAgentStore`.
- Emits a `agent_handoff` WebSocket event.
- Suppresses duplicate handoff events when the target is already active.

**Fix:** Replace the regex with `HandoffTo[ConciergeAgent, FoodRecommenderAgent, …]`.
Each agent's `tools=[HandoffTo[...]]` is the canonical way to declare
"this agent can hand off to these others".

**Reference:** `lauren-ai-chatbot/backend/app/ai/tools/handoff_tool.py:49-154`.

### Gap 12.2 — `HandoffTo` requires `ActiveAgentStore`; store not implemented

**Today:** The hand-rolled handoff writes to `conversations.agent_type`
in the DB. There is no `ActiveAgentStore` injectable.

**Why it matters:** `HandoffTo[X, Y]` requires an `ActiveAgentStore` to
record the active agent per conversation. Without it, handoffs don't
propagate to the next controller turn.

**Fix:** Implement an `ActiveAgentStore` injectable (in-memory or DB-backed).

**Reference:** `lauren-ai-chatbot/backend/app/ai/tools/active_agent_store.py`.

### Gap 12.3 — `HANDOFF_INSTRUCTION` constants in each agent duplicate `HandoffTo`'s built-in prompt

**Today:** `concierge.py:6-18`, `dietary.py:6-15`, `food_recommender.py:6-16`,
`ordering_agent.py:6-16`, `reservation_agent.py:6-15`, `support.py:6-15`
each declare their own `HANDOFF_INSTRUCTION` string. The same pattern is
duplicated in `chat_service.py:26-48`.

**Why it matters:** Three sources of truth, and `HandoffTo[X, Y]` already
documents the format in the tool's docstring (the LLM sees the docstring
as the tool description). Drop the manual instructions.

**Fix:** Delete the per-agent `HANDOFF_INSTRUCTION` constants. The
`HandoffTo` tool's schema is self-documenting.

### Gap 12.4 — No `@use_guardrails`

**Today:** No `PIIRedactor`, `PromptInjectionFilter`, `TopicFilter`,
`LengthFilter`, `LLMGuardrail`, or `@use_guardrails(input=…, output=…)`
anywhere.

**Why it matters:** Guardrails are how the project defends against
prompt injection, off-topic queries, and PII leakage. The
`lauren-ai-chatbot` example attaches an `LLMScopeGuard` to every
authenticated agent.

**Fix:** At minimum, add `@use_guardrails(output=[PIIRedactor()])` to
every agent. Optionally add `PromptInjectionFilter` as an input
guardrail on the concierge.

**Reference:** `lauren-ai-chatbot/backend/app/ai/guardrails/llm_scope_guard.py:41-132`.

### Gap 12.5 — No `KnowledgeSource` / `KnowledgeBase` / `use_knowledge_sources`

**Today:** The agents don't use RAG. The concierge's `search_menu` tool
is the only menu-query path, and it's a placeholder.

**Why it matters:** A concierge that doesn't have access to the real
menu hallucates. `KnowledgeSource(kb=MenuKB, tool_name="search_menu")`
plus `@use_knowledge_sources(MENU_SOURCE)` on the concierge is the
idiomatic fix.

**Fix:** Build a `MenuKB(KnowledgeBase)` with an `SQLiteVectorStore`
backend, populate it from the `menu_items` table at startup, register
as a knowledge source, and add `@use_knowledge_sources(MENU_SOURCE)` to
the concierge and food-recommender agents.

### Gap 12.6 — No `InMemoryConversationStore` or `SQLiteConversationStore`

**Today:** Conversations are stored in a custom `agent_messages` table
queried by hand-rolled SQL. There is no `ConversationStore` interface,
no per-agent isolation (all agents share one DB table).

**Why it matters:** `lauren-ai`'s `ConversationStore` is the canonical
abstraction. `SQLiteConversationStore` provides the same per-agent
isolation that `lauren-ai-chatbot` uses for cross-agent handoff
isolation.

**Fix:** Replace the `conversations` / `agent_messages` tables with
`SQLiteConversationStore(db_path="lauren_eats_memory.db")`, one store
per agent. The runner persists turns automatically.

### Gap 12.7 — No `@remember` / `UserMemoryStore` / long-term memory

**Today:** No user-level memory. Each `conversations` row is global; no
"this user always prefers mild spice" style facts.

**Why it matters:** `lauren-ai` ships `remember` decorator and
`SQLiteUserMemoryStore` for exactly this use case. The dietary agent
in particular should remember "user is allergic to peanuts" across
sessions.

**Fix:** Add `SQLiteUserMemoryStore` as a provider, use
`@remember(key="dietary_preferences", agent_name=…)` in the dietary
agent.

---

## 13. `lauren-ai` — Observability (Cost, Tracing, Signals, Rate Limit)

### Gap 13.1 — No `CostTracker` / `default_pricing_table`

**Today:** No cost tracking. Every LLM call is unbounded in spend.

**Why it matters:** `CostTracker(pricing=default_pricing_table())` is the
one-line way to record every `ModelCallComplete` and expose
`/api/metrics/cost`.

**Fix:** Add `app/observability/cost_tracker.py`:

```python
from lauren_ai import CostTracker, default_pricing_table, ModelCallComplete
from lauren import use_value

cost_tracker = CostTracker(pricing=default_pricing_table())

@signal_bus.on(ModelCallComplete)
async def _track_cost(event: ModelCallComplete) -> None:
    await cost_tracker._on_model_call_complete(event)

cost_tracker_provider = use_value(provide=CostTracker, value=cost_tracker)
```

Expose via `GET /api/metrics/cost`.

**Reference:** `lauren-ai-chatbot/backend/app/ai/ai_module.py:122-134`.

### Gap 13.2 — No `TraceStore` / `set_trace_store` / `@traced`

**Today:** No tracing. Agent runs, tool calls, and LLM calls produce
no spans.

**Why it matters:** `@traced("llm_call")` decorates a function so each
invocation is recorded as a `Span` in a `TraceStore`. Combined with
`ConsoleTraceExporter` or `FileTraceExporter`, you get OpenTelemetry-
style traces for free.

**Fix:**

```python
from lauren_ai import TraceStore, set_trace_store, InMemoryTraceExporter

exporter = InMemoryTraceExporter()
trace_store = TraceStore()
trace_store._exporters = [exporter]
set_trace_store(trace_store)
```

Then `@traced()` on the concierge's `on_finish`, on each tool's `run`,
etc.

**Reference:** `lauren-ai-chatbot/backend/main.py:36-40`.

### Gap 13.3 — No `RateLimiter` / `TokenBudget` / `ai_rate_limit` middleware

**Today:** Any client can spam the chat endpoint. There is no per-IP
rate limit, no per-user token budget.

**Why it matters:** `lauren_ai.ai_rate_limit` is a middleware factory
that adds per-conversation-id rate limits using the `RateLimiter` and
`TokenBudget` classes.

**Fix:** Add `ai_rate_limit(per_minute=10, per_hour=200)` as a
`global_middleware`.

### Gap 13.4 — No `SignalBus` listeners for `ModelCallComplete` / `AgentRunComplete` / `ToolCallComplete`

**Today:** Even though `lauren-ai` emits these signals on every LLM
call, no listener is registered.

**Why it matters:** Every monitoring / observability / dashboard feature
is a listener.

**Fix:** Add:

```python
@signal_bus.on(ModelCallComplete)
async def _log_model_complete(event: ModelCallComplete) -> None:
    logger.info("model=%s tokens=%d cost=%.4f", event.model, event.usage.total_tokens, event.cost_usd)

@signal_bus.on(AgentRunComplete)
async def _log_agent_complete(event: AgentRunComplete) -> None:
    logger.info("agent=%s turns=%d stop=%s", event.agent_name, event.turns, event.stop_reason)

@signal_bus.on(ToolCallStarted)
async def _log_tool_start(event: ToolCallStarted) -> None:
    ...
```

### Gap 13.5 — `AgentMessageSent` / `AgentMessageRequestCompleted` signals ignored

**Today:** `lauren-ai` has a full inter-agent messaging bus
(`AgentMessageBus`) with `AgentMessageSent`, `AgentMessageRequestCompleted`,
`DeadLetterRecord`. The backend does not import or wire it.

**Why it matters:** A real food-ordering system has long-running backend
agents (kitchen dispatch, delivery tracking, customer notifications) that
talk to the chat agent over a bus, not a single shared DB.

**Fix (deferred — see §17 phasing):** Wire `AgentMessageBus` for
asynchronous workflows (kitchen ticket ready, delivery en route).

### Gap 13.6 — No `traced` decorator on the chat endpoint

**Today:** No `@traced("chat")` on `ChatController.chat`. A single
endpoint invocation produces no span tree.

**Fix:** Wrap the endpoint body in `@traced("chat")` so each chat
request becomes a root span with the LLM and tool calls as children.

---

## 14. `lauren-ai` — Extractors, Output Parsers, Chains

### Gap 14.1 — `Agent[ConciergeAgent]` extractor not used

**Today:** No `agent: Agent[ConciergeAgent]` parameter in
`ChatController`. The controller uses `chat_service: ChatService`.

**Why it matters:** The `Agent[T]` extractor resolves a registered
agent class instance from the DI container, ready to call.

**Fix:**

```python
from lauren_ai import Agent
from app.agents.concierge import ConciergeAgent

@controller("/api/chat")
class ChatController:
    def __init__(
        self,
        concierge: Agent[ConciergeAgent],
        food_recommender: Agent[FoodRecommenderAgent],
        …
    ) -> None: ...
```

### Gap 14.2 — `StreamCompletion[str]` not used

**Today:** The chat endpoint manually re-implements streaming.

**Why it matters:** `StreamCompletion[str]` is the extractor that returns
an async iterator of `CompletionChunk` from `LLMService.complete_stream`.
It is designed to be returned from a handler as an `EventStream`.

**Fix:** For a non-agentic completion (e.g. menu summary), the
`StreamCompletion` extractor is the one-liner.

### Gap 14.3 — `Embed[list[float]]` not used

**Today:** No embeddings anywhere (see Gap 9.6).

**Fix:** For a `POST /api/menu/semantic-search`, `query_embedding:
Embed[list[float]]` resolves the embedding of `body.query`.

### Gap 14.4 — `Chain` / `RunnableLambda` / output parsers not used

**Today:** No LLM chains. The chat endpoint is the only LLM call, and
it's hand-rolled.

**Why it matters:** `Chain` / `RunnableLambda` / `ChatPromptTemplate` /
`PydanticOutputParser` are the primitives for structured LLM workflows
(extract dish names from a free-form review, classify feedback into
categories, etc.).

**Fix:** The `AdminService.get_ai_insights` keyword-matching can be
replaced by a `Chain` with a `PydanticOutputParser` returning a typed
list of `QueryCategory` models.

---

## 15. Code-Quality, Testing, CI

### Gap 15.1 — `order_service.py:_generate_order_number` has dead code and a broken function

**Today:** `order_service.py:17-29`:

```python
def _generate_order_number() -> str:
    ts = int(time.time())
    ts36 = ""
    n = ts
    while n > 0:
        n, r = divmod(n, 36)
        ts36 = string.digits + string.ascii_lowercase  # ← rebinds outer name
        ts36 = ""  # ← immediately overwrites
    import base36  # ← not in requirements.txt
    ...  # fallback to hex
    return f"LE-{hex(ts)[2:].upper()}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"
```

The `while` loop, `base36` import, and `...` placeholder are dead. The
`while n > 0:` line would never terminate if it weren't immediately
abandoned. The function is never actually called (the order number is
generated inline in `create_order` at line 143).

**Why it matters:** Confusing code; the function is never used.

**Fix:** Delete `_generate_order_number` entirely.

### Gap 15.2 — `order_service.create_order` duplicates the order-number logic inline

**Today:** `order_service.py:143`:

```python
order_number = f"LE-{hex(int(time.time()))[2:].upper()}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"
```

**Why it matters:** The same logic is in two places (and broken in one).

**Fix:** Use a `str(uuid.uuid4())[:8].upper()` or a small
`OrderNumberGenerator` service.

### Gap 15.3 — No `tests/` directory

**Today:** `pyproject.toml` declares `[tool.pytest.ini_options]`, but
`testpaths = ["tests"]` references a non-existent directory.

**Why it matters:** Zero unit or integration tests.

**Fix:** Add at least:
- `tests/unit/test_menu_service.py` — DB-backed service tests
- `tests/unit/test_chat_service.py` — agent invocation with
  `LLMConfig.for_testing()`
- `tests/integration/test_app.py` — `LaurenFactory.create(AppModule)`
  + `TestClient`
- `tests/unit/test_handoff.py` — `HandoffTo[X, Y]` round-trips
- `tests/unit/test_guardrails.py` — `LLMScopeGuard` blocks out-of-scope

**Reference:** `lauren-ai-chatbot/CLAUDE.md:13-14` —
`tests/integration/`, `tests/unit/`, 90% coverage threshold.

### Gap 15.4 — No `noxfile.py` / `Makefile` for lint / test / typecheck

**Today:** `pyproject.toml` declares `[tool.ruff]` but no command wires
it. There is no `noxfile.py` (compared to `lauren-ai-chatbot/backend/noxfile.py`).

**Fix:** Add a `noxfile.py` with `lint`, `tests`, `typecheck` sessions.

### Gap 15.5 — No `pre-commit` config

**Today:** No `.pre-commit-config.yaml`.

**Fix:** Add `pre-commit` hooks for `ruff`, `mypy`, and the lauren-style
import order.

### Gap 15.6 — No `mypy` configuration

**Today:** `pyproject.toml` does not declare `[tool.mypy]`. Despite
`pyproject.toml:25` listing `mypy>=1.10` as a dev dep.

**Fix:** Add a `mypy.ini` with `strict = true` and a `[[tool.mypy.overrides]]`
block for the `tests/` directory.

### Gap 15.7 — No `CHANGELOG.md`, no `AGENTS.md`, no `CONTRIBUTING.md`

**Today:** Only `README.md` exists. The reference `lauren-ai-chatbot`
has all three.

**Fix:** Add `CHANGELOG.md` (with a v1.0.0 entry listing the migration
to lauren-ai), `AGENTS.md` (build / lint / test commands), and
`CONTRIBUTING.md` (architecture, code style, PR process).

### Gap 15.8 — `httpx` is a direct dep, but `LLMService` already brings it transitively

**Today:** `requirements.txt:4` — `httpx>=0.27`.

**Why it matters:** Once `LLMService` is in use, the OpenAI transport
will pull `httpx` in. Listing it explicitly is fine for transparency
but should be flagged as a transitive.

**Fix:** Comment in `requirements.txt`: "# httpx is also pulled in by lauren-ai's OpenAI transport".

---

## 16. Gap Summary by Priority

| Priority | Gaps | Rationale |
| --- | --- | --- |
| **P0 — Blocker** | 4.1, 4.4, 4.5, 9.1, 9.2, 9.3, 10.1, 10.3, 11.3, 11.4 | Without these, the backend is non-functional (DB closed, agents never run, tools are stubs, orders are not created). |
| **P1 — Required for production** | 4.7, 4.8, 5.1, 5.2, 5.3, 5.5, 6.1, 6.2, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.5, 9.4, 10.2, 10.4, 10.7, 10.8, 10.9, 11.1, 11.2, 12.1, 12.2, 12.4, 12.6, 13.1, 13.4, 14.1, 15.1, 15.2, 15.3 | These are the production-readiness gaps: typed extractors, exception handlers, signal-based observability, real tool DI, handoff tools, guardrails, cost tracking, tests. |
| **P2 — Quality of life** | 4.2, 4.3, 4.6, 4.9, 4.10, 4.11, 5.4, 5.6, 5.7, 6.3, 6.4, 6.5, 6.6, 7.5, 7.6, 8.3, 8.4, 8.6, 9.5, 9.6, 9.7, 10.5, 10.6, 12.3, 12.5, 12.7, 13.2, 13.3, 13.5, 13.6, 14.2, 14.3, 14.4, 15.4, 15.5, 15.6, 15.7, 15.8 | These are polish: @post_construct, BackgroundTasks, additional guardrails, embedding/RAG, structured outputs, advanced tracing, code-style fixes. |
| **P3 — Future / stretch** | 12.7 (long-term user memory), 13.5 (inter-agent bus), 9.7 (RAG), 4.11 (static files) | These are speculative future phases. |

---

## 17. Proposed Migration Phases

### Phase 1 — Stop the bleeding (P0)

**Goal:** Make the backend actually run with the agents running.

1. Move `DatabaseService.connect()` into `@post_construct`. Delete
   `startup_init` from `main.py`.
2. Construct `LLMConfig` from env vars. Add `LLMModule.for_root(…)`.
3. Add `AgentModule.for_root(agents=[…], imports=[LLMProvider])` for
   each agent.
4. Replace `ChatService.stream_chat`'s `httpx` block with
   `LLMService.complete_stream(...)`.
5. Convert `search_menu`, `get_menu_item_details`,
   `check_dietary_info`, `create_order`, `create_reservation`,
   `check_order_status` to class-form tools with DI. Wire them to
   `MenuService`, `OrderService`, `ReservationService`.
6. Delete `chat_service.SYSTEM_PROMPTS` (use the agent's own
   `@agent(system=…)`).
7. Replace `<<HANDOFF:agent>>` regex with `HandoffTo[AgentA, AgentB]`
   + `ActiveAgentStore`.

**Validation:** `python main.py` starts cleanly. `POST /api/chat` with
`"Find me a vegetarian dish"` invokes the concierge, which hands off to
`food_recommender`, which calls `search_menu("vegetarian")`, which
returns real DB results, and the assistant message is persisted in the
conversation.

### Phase 2 — Production hardening (P1)

**Goal:** Make it safe, observable, and testable.

1. Replace `body: dict` with `Json[Model]` in all controllers.
2. Replace string query params with typed `Query[T]` extractors.
3. Define `@exception_handler(ValidationError)` and register via
   `global_exception_handlers`.
4. Add `global_middlewares=[CORSMiddleware, RequestIdMiddleware]`.
5. Add `global_interceptors=[TimingInterceptor, TokenUsageInterceptor]`.
6. Pass `json_encoder=MsgspecEncoder()`, `logger=default_logger()`,
   `error_format="rfc7807"`.
7. Define `AdminAuthGuard` and attach with `@use_guards(AdminAuthGuard)`.
8. Add `@use_guardrails(output=[PIIRedactor()])` to every agent.
9. Wire `CostTracker` + `default_pricing_table`. Expose
   `/api/metrics/cost`.
10. Wire `SignalBus` to `main.py`; register listeners for
    `ModelCallComplete`, `AgentRunComplete`, `ToolCallComplete`.
11. Convert `conversations` / `agent_messages` to
    `SQLiteConversationStore` (one per agent).
12. Convert `chat_service`'s hand-rolled `httpx` to `runner.run_stream(...)`
    with `execution_context`.
13. Add `tests/` (unit + integration).
14. Add `noxfile.py`, `.pre-commit-config.yaml`, `mypy.ini`.

**Validation:** `pytest` runs and ≥ 80% coverage. `ruff check`, `mypy --strict`,
`pre-commit run --all-files` all pass.

### Phase 3 — Quality of life (P2)

1. Add `BackgroundTasks` for the admin insights aggregation.
2. Add `StaticFilesModule` and an image-upload endpoint.
3. Add `@traced("chat")` on `ChatController.chat`.
4. Add `RateLimiter` / `ai_rate_limit` middleware.
5. Add `StreamCompletion[str]` and `Embed[list[float]]` extractors.
6. Add `KnowledgeSource` for the menu + `@use_knowledge_sources` on
   the concierge.
7. Add `LLMScopeGuard` (output) for the ordering agent.
8. Adopt `Token` / `Inject` for cross-module singletons.
9. Add `PydanticOutputParser` for the admin insights.
10. Refactor controllers to one-per-feature-module.

### Phase 4 — Stretch (P3)

1. `@remember` + `SQLiteUserMemoryStore` for user-level preferences
   (spice tolerance, allergies).
2. `AgentMessageBus` for kitchen dispatch / delivery tracking.
3. WebSocket gateway for live order-status push.
4. Multi-agent team with `TeamRunner` for banquet-style catering.
5. RAG over user reviews with `SQLiteVectorStore` and reranking.

---

## 18. Acceptance Criteria

The migration is complete when:

1. **All P0 gaps (32 items) are closed.**
2. **All P1 gaps (33 items) are closed.**
3. **Test coverage ≥ 80%** with at least 20 unit tests and 5 integration
   tests, including a `TestClient` round-trip through the chat endpoint
   that uses `LLMConfig.for_testing()` to drive every agent.
4. **`ruff check`, `mypy --strict`, `pre-commit run --all-files` all pass.**
5. **End-to-end demo works:** the frontend (out of scope for this PRD)
   can hit the backend, send a chat message, see a streamed response,
   trigger a handoff, see a tool call, and have a real order created in
   the database.
6. **Cost-tracking endpoint returns a meaningful per-model token
   summary after a chat.**
7. **No `try/except Exception` in any controller** (replaced by
   `@exception_handler` + `HTTPError` raises).
8. **The `startup_init` shim is gone; `LaurenApp.startup()` is the only
   path to opening the DB.**

---

## 19. Out of Scope

This PRD does **not** cover:

- Frontend changes (`lauren-examples/lauren-eats/frontend/`).
- Production deployment (Docker, k8s, CI/CD).
- Authentication (HMAC, OAuth, OIDC) — only `@use_guards` is introduced;
  the auth provider itself is left to a future PRD.
- Database migration to PostgreSQL — `aiosqlite` is fine for now.
- Internationalisation (i18n) of error messages.
- Rate-limit tiering / quota plans.
- Multi-tenant isolation.

---

## 20. Appendix A — `lauren-framework` features touched by this PRD

| Feature | Status today | After migration |
| --- | --- | --- |
| `LaurenFactory.create` | Used | Used with all kwargs |
| `@module` + `imports` / `exports` | 1 module | Module graph |
| `@controller` + `@get` / `@post` / `@put` / `@patch` | Used | Used |
| `@injectable(scope=Scope.SINGLETON)` | Used | Used |
| `use_value` / `use_class` / `use_factory` / `use_existing` | Unused | Used (LLMConfig, AgentRunner aliases) |
| `Token` / `Inject` | Unused | Used |
| `global_middlewares` | Unused | Used (CORS, request-id) |
| `global_guards` | Unused | Used (admin auth) |
| `global_interceptors` | Unused | Used (timing, token-usage) |
| `global_exception_handlers` | Unused | Used |
| `global_providers` | Unused | Used (logger, signal bus) |
| `logger=default_logger()` | Unused | Used |
| `json_encoder=MsgspecEncoder()` | Unused | Used |
| `error_format="rfc7807"` | Unused | Used |
| `max_body_size=…` | Unused | Configured |
| `openapi_*` kwargs | Partial | All |
| `mounts={…}` | Unused | Used (static files) |
| `app.on_shutdown` | Unused | Used |
| `app.startup()` / `app.shutdown()` | Bypassed | Used (via lifespan) |
| `BackgroundTasks` | Unused | Used |
| `@post_construct` / `@pre_destruct` | Unused | Used |
| `Json[T]` / `Path[T]` / `Query[T]` / `Header[T]` extractors | Partial | All |
| `Form[T]` / `UploadFile` / `Bytes` | Unused | Partial |
| `Depends[T]` | Unused | Used |
| `State` extractor | Unused | Used (auth principal) |
| `ExtractionMarker.extract` | Unused | Used (`CurrentUser`) |
| `Pipe` / `FieldDescriptor` | Unused | Optional |
| `EventStream` / `ServerSentEvent` | Used (raw) | Used (typed) |
| `StreamingResponse[T]` | Unused | Optional |
| `WebSocket` gateways | Unused | Future |
| `StaticFilesModule` | Unused | Used |
| `SocketIO` | Unused | Future |
| `SignalBus` + `@on(StartupBegin)` etc. | Unused | Used |
| `@exception_handler` + `use_exception_handlers` | Unused | Used |
| `@use_guards` / `@use_middlewares` / `@use_interceptors` | Unused | Used |
| `@use_encoder` | Unused | Optional |
| `@set_metadata` | Unused | Optional |
| `@openapi_security` | Unused | Future |

## 21. Appendix B — `lauren-ai` features touched by this PRD

| Feature | Status today | After migration |
| --- | --- | --- |
| `LLMConfig` (frozen dataclass) | Unused | Used |
| `LLMConfig.for_openai` / `for_anthropic` / `for_ollama` / `for_litellm` / `for_testing` | Unused | Used |
| `LLMModule.for_root(LLMConfig)` | Unused | Used |
| `LLMService.complete` / `complete_stream` / `embed` | Unused | Used |
| `LLMService.with_structured_output` | Unused | Future |
| `EmbedService` | Unused | Used (semantic menu search) |
| `AgentModule.for_root(agents, tools, imports, signals, knowledge, …)` | Unused | Used (one per agent) |
| `AgentRunner[AgentX]` typed injection | Unused | Used |
| `runner.run` / `runner.run_stream` | Unused | Used (chat endpoint) |
| `@agent()` decorator | Used (decorative) | Used (executed) |
| `@use_tools(*tools)` | Used (decorative) | Used (executed) |
| `@use_knowledge_sources(*sources)` | Unused | Used |
| `@use_guardrails(input=…, output=…)` | Unused | Used |
| `@tool()` (function-form) | Used (decorative) | Used (with `ctx: ToolContext`) |
| `@tool()` (class-form, DI) | Unused | Used |
| `ToolContext` (ctx param) | Unused | Used |
| `HandoffTo[AgentA, AgentB]` | Unused (regex) | Used |
| `ActiveAgentStore` | Unused | Used |
| `LLMGuardrail` / `PIIRedactor` / `PromptInjectionFilter` / `TopicFilter` / `LengthFilter` | Unused | Used |
| `LLMScopeGuard` (custom `@guardrail`) | Unused | Used |
| `KnowledgeBase` / `KnowledgeSource` | Unused | Used (menu RAG) |
| `ConversationStore` / `InMemoryConversationStore` / `SQLiteConversationStore` | Unused (raw SQL) | Used |
| `MemoryStore` / `ShortTermMemory` | Unused | Used |
| `UserMemoryStore` / `SQLiteUserMemoryStore` / `@remember` | Unused | Future |
| `SQLiteVectorStore` / `InMemoryVectorStore` | Unused | Used (menu KB) |
| `AgentMessageBus` / `AgentMessageSent` etc. | Unused | Future |
| `SubagentPool` / `SubagentTool` | Unused | Future |
| `TeamRunner` / `@team` | Unused | Future |
| `SignalBus` (lauren-ai version) | Unused | Used |
| `ModelCallComplete` / `ModelCallStarted` listeners | Unused | Used |
| `AgentRunComplete` / `AgentTurnComplete` listeners | Unused | Used |
| `ToolCallStarted` / `ToolCallComplete` listeners | Unused | Used |
| `CostTracker` / `default_pricing_table` | Unused | Used |
| `RateLimiter` / `TokenBudget` / `ai_rate_limit` | Unused | Used |
| `TraceStore` / `set_trace_store` / `InMemoryTraceExporter` | Unused | Used |
| `@traced` decorator | Unused | Used |
| `Agent[T]` extractor | Unused | Used |
| `Completion[T]` / `StreamCompletion[str]` extractors | Unused | Used |
| `Embed[list[float]]` extractor | Unused | Used |
| `Chain` / `RunnableLambda` / `chain` | Unused | Used |
| `ChatPromptTemplate` / `PromptTemplate` | Unused | Used |
| `PydanticOutputParser` / `JSONOutputParser` etc. | Unused | Used |
| `Multimodal ContentPart` (image/audio/doc) | Unused | Future |
| `StructuredLLM[T]` | Unused | Future |
| `SemanticRouter` / `Route` | Unused | Future |

---

*End of PRD.*
