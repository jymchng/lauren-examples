# Lauren AI Chatbot

A full-stack AI chatbot that showcases the core features of **[Lauren](https://github.com/lauren-framework/lauren-framework)** and **[Lauren AI](https://github.com/lauren-framework/lauren-ai)** in a production-ready application.

![Lauren AI Chatbot](https://raw.githubusercontent.com/lauren-framework/lauren-examples/main/lauren-ai-chatbot/assets/lauren-ai-chatbot.PNG)

---

## What It Demonstrates

This example is intentionally a complete, non-trivial app — not a hello-world. It exercises the full Lauren and Lauren AI feature set end-to-end:

### Lauren Framework

| Feature | Where |
|---------|-------|
| **Modular architecture** — `@module` with `imports`, `providers`, `controllers`, `exports` | `app/chat/chat_module.py`, `app/ai/ai_module.py`, `app/crypto/crypto_module.py` |
| **Dependency injection** — constructor injection, singleton/request scopes | Every service and controller |
| **Decorator-based routing** — `@controller`, `@post`, `@get` | `chat_controller.py`, `agent_controller.py`, `health_controller.py` |
| **Guards** — `@use_guards`, `CanActivate` interface | `SignatureGuard` on all chat endpoints |
| **Interceptors** — `NestInterceptor`-style before/after wrapping | `TimingInterceptor` → `X-Response-Time` header |
| **Middleware** — global request/response pipeline | `CorsMiddleware`, `LoggingMiddleware` |
| **Server-Sent Events** — `EventStream` + `ServerSentEvent` | Both `/api/chat/` and `/api/agent/` |
| **Request body parsing** — `Json[T]` extractor with Pydantic validation | `ChatRequest` schema |

### Lauren AI

| Feature | Where |
|---------|-------|
| **LLM provider abstraction** — `LLMModule.for_root()`, `LLMService` | `app/ai/ai_module.py` |
| **Streaming completions** — async token-by-token streaming | `ChatService.stream_tokens()` |
| **Agentic loop** — `@agent`, `AgentRunner`, multi-turn tool use | `app/ai/agent.py`, `AgentController` |
| **Tool registry** — `@use_tools`, typed tool functions | `get_current_time`, `calculate`, `word_count` |
| **Input guardrails** — `@guardrail(input=[...])`, `PromptInjectionFilter` | `ChatAgent` |
| **Output guardrails** — `@guardrail(output=[...])`, `LengthFilter` | `ChatAgent` |
| **Conversation memory** — `InMemoryConversationStore`, `conversation_id` | `ChatService` |
| **Observability / tracing** — `InMemoryTraceExporter`, `TraceStore` | `main.py`, `MetricsController` |
| **Cost tracking** — `CostTracker`, per-model cost breakdown | `app/ai/ai_module.py`, `/api/metrics/cost` |
| **Signal bus** — `SignalBus`, `ModelCallComplete` events | `app/ai/signals.py`, `main.py` |

### Security

HMAC-SHA256 request signing ties the frontend and backend together without exposing API keys to the browser. Every chat request from the Next.js frontend is signed with a shared secret; the `SignatureGuard` verifies the signature before any handler runs.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js Frontend (TypeScript)                              │
│                                                             │
│  ChatInterface  →  POST /api/chat  (HMAC-signed)           │
│       │              SSE stream ←  token / done / error    │
│  StreamingMessage  →  ReactMarkdown + SyntaxHighlighter    │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP  (X-Signature header)
┌──────────────────────────▼──────────────────────────────────┐
│  Next.js API Route  /api/chat/route.ts                      │
│  Signs payload with HMAC-SHA256 and proxies to backend      │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP
┌──────────────────────────▼──────────────────────────────────┐
│  Lauren Backend  (Python · uvicorn · port 8000)             │
│                                                             │
│  CorsMiddleware → LoggingMiddleware → TimingInterceptor     │
│                                                             │
│  POST /api/chat/   ← SignatureGuard                        │
│    ChatController → ChatService → LLMService               │
│                     (streaming tokens via EventStream)      │
│                                                             │
│  POST /api/agent/  ← SignatureGuard                        │
│    AgentController → AgentRunner → ChatAgent               │
│                       ├─ PromptInjectionFilter (input)      │
│                       ├─ get_current_time tool              │
│                       ├─ calculate tool                     │
│                       ├─ word_count tool                    │
│                       └─ LengthFilter (output)             │
│                                                             │
│  GET  /api/health/                                          │
│  GET  /api/metrics/   (traces · cost · token usage)        │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
lauren-ai-chatbot/
├── backend/
│   ├── main.py                  # App bootstrap, middleware, interceptors, signals
│   ├── pyproject.toml
│   └── app/
│       ├── app_module.py        # Root module
│       ├── chat/
│       │   ├── chat_module.py
│       │   ├── chat_controller.py   # POST /api/chat/  (SSE streaming)
│       │   ├── agent_controller.py  # POST /api/agent/ (agentic SSE)
│       │   ├── chat_service.py      # LLM streaming + conversation memory
│       │   └── schemas.py           # ChatRequest, Message, ChatResponse
│       ├── ai/
│       │   ├── ai_module.py         # LLMModule, AgentRunner, tools wiring
│       │   ├── agent.py             # ChatAgent with guardrails + tools
│       │   ├── tools.py             # get_current_time, calculate, word_count
│       │   └── signals.py           # Shared SignalBus singleton
│       ├── crypto/
│       │   ├── crypto_module.py
│       │   ├── crypto_service.py    # HMAC-SHA256 sign / verify
│       │   └── signature_guard.py   # Guard: verifies X-Signature header
│       ├── health/
│       │   └── health_controller.py # GET /api/health/
│       ├── metrics/
│       │   └── metrics_controller.py # GET /api/metrics/ (traces + cost)
│       ├── middlewares/
│       │   ├── cors_middleware.py
│       │   └── logging_middleware.py
│       └── interceptors/
│           └── timing_interceptor.py # Adds X-Response-Time to every response
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx             # Main page layout
    │   │   └── api/chat/route.ts    # Next.js proxy route (signs + forwards)
    │   ├── components/
    │   │   ├── ChatInterface.tsx    # Input, SSE consumption, state
    │   │   ├── MessageBubble.tsx    # Markdown rendering with SyntaxHighlighter
    │   │   └── StreamingMessage.tsx # Live streaming bubble with cursor
    │   └── lib/
    │       └── prism-theme.ts       # VS Code Dark+ syntax highlight theme
    └── package.json
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env:
#   OPENROUTER_API_KEY=sk-or-...
#   LLM_MODEL=openai/gpt-4o-mini        # optional
#   PAYLOAD_SECRET=any-random-secret

uv sync
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
# Edit .env.local:
#   BACKEND_URL=http://localhost:8000
#   PAYLOAD_SECRET=<same secret as backend>

npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/` | Streaming LLM completions (SSE). Requires `X-Signature` header. |
| `POST` | `/api/agent/` | Agentic chat with tool use (SSE). Requires `X-Signature` header. |
| `GET`  | `/api/health/` | Health check — `{status, version, framework}` |
| `GET`  | `/api/metrics/` | Summary of traces and total cost |
| `GET`  | `/api/metrics/traces` | Last 50 traces with span details |
| `GET`  | `/api/metrics/cost` | Cost breakdown by model and conversation |

### SSE Event Format

```
event: token
data: Hello, world

event: done
data:

event: error
data: Something went wrong
```

---

## Agent Tools

The `ChatAgent` has access to three tools at runtime:

| Tool | Description |
|------|-------------|
| `get_current_time(timezone)` | Current date and time in any IANA timezone |
| `calculate(expression)` | Safe AST-based math evaluator (`+`, `-`, `*`, `/`, `**`, etc.) |
| `word_count(text)` | Word, character, and sentence counts for any text |
