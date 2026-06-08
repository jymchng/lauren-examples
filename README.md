# Lauren Examples

Production-ready example applications built with **[Lauren](https://github.com/lauren-framework/lauren-framework)** and **[Lauren AI](https://github.com/lauren-framework/lauren-ai)** — a modular Python backend framework and its AI extension layer.

Each example is a self-contained, full-stack project demonstrating real patterns you'd use in production: dependency injection, guards, interceptors, middleware, streaming, agentic AI, and more.

---

## Examples

| Example | Description | Stack |
|---------|-------------|-------|
| [**lauren-ai-chatbot**](./lauren-ai-chatbot/) | Full-stack AI chatbot with public and authenticated agent routing, SSE streaming, HMAC-signed requests, `msgspec` payloads, guardrails, live WebSocket telemetry, and HITL transfer approval | Python · Lauren · Lauren AI · Next.js · OpenRouter · msgspec |
| [**lauren-eats**](./lauren-eats/) | AI-powered Chinese restaurant platform with 6 specialist agents, agent handoffs, SSE streaming, menu browsing, order management, table reservations, and an admin dashboard with AI-generated insights | Python · Lauren · Lauren AI · Next.js · SQLite · OpenRouter |
| [**lauren-urlshortener**](./lauren-urlshortener/) | Minimal URL shortener — create short codes, redirect, list, and deactivate links. Demonstrates Lauren without Pydantic using only stdlib types and `dataclass` models | Python · Lauren · SQLite |

---

## What is Lauren?

**Lauren** is a Python backend framework inspired by NestJS — built around a first-class dependency injection container, decorator-based routing, and a modular architecture. Think FastAPI for structure, NestJS for DX.

**Lauren AI** extends Lauren with everything needed to build production AI features: LLM provider abstraction, agent runners, tool registries, guardrails, conversation memory, tracing, cost tracking, and an event/signal bus.

---

## Running an Example

Each example has its own `README.md` with full setup instructions. Some examples also ship local agent context packs in `backend/skills/` and deployment helpers such as `modal_deploy.py`. The general pattern is:

```bash
# Backend
cd <example>/backend
cp .env.example .env   # fill in API keys
uv sync
uvicorn main:app --reload --port 8000

# Frontend
cd <example>/frontend
npm install
npm run dev
```

---

## Contributing

New examples are welcome. Each example should:

- Live in its own top-level directory
- Be fully self-contained (backend + frontend if applicable)
- Demonstrate at least one Lauren or Lauren AI feature clearly
- Include a `README.md` with a screenshot, feature list, and setup steps
