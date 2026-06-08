# Lauren Eats

AI-powered Chinese restaurant platform built with **[Lauren](https://github.com/lauren-framework/lauren-framework)** and **[Lauren AI](https://github.com/lauren-framework/lauren-ai)**.

A full-stack example demonstrating multi-agent orchestration with real-time SSE streaming, specialist agent handoffs, and a production-ready restaurant management backend — all in one Lauren application.

---

## Features

**AI Chat**
- 6 specialist agents with typed tool calls and seamless handoffs between agents
- Real-time streaming via Server-Sent Events (SSE)
- Persistent conversation memory per session
- Provider-agnostic: works with any OpenAI-compatible API (OpenRouter, Anthropic, OpenAI)

**Restaurant Platform**
- Full menu catalogue — 42 dishes across 8 categories, with dietary flags, spice levels, allergens, and images
- Order management — dine-in, takeout, and delivery orders with live status tracking
- Table reservations — party size, occasion, special requests
- Admin dashboard — order stats, revenue metrics, and AI agent analytics
- Streaming AI insights — real-time report generation for the admin view

**Backend**
- Lauren module graph with three-scope DI (`SINGLETON` / `REQUEST` / `TRANSIENT`)
- Request-scoped interceptors for logging and timing
- SQLite database seeded with realistic restaurant data

---

## Architecture

```
lauren-eats/
├── backend/          # Python ASGI app — Lauren + Lauren AI
│   ├── app/
│   │   ├── agents/   # 6 @agent() classes + @tool() definitions
│   │   ├── controllers/
│   │   ├── services/
│   │   ├── db/
│   │   └── modules.py
│   ├── main.py
│   └── modal_deploy.py
└── frontend/         # Next.js 15 (App Router) — TypeScript + Tailwind
    └── src/
        ├── app/      # Pages: /, /menu, /orders, /reservation, /chat, /admin
        ├── components/
        ├── store/    # Zustand
        └── lib/api.ts
```

### Agent roster

| Agent | Registered name | Tools | Hands off to |
|---|---|---|---|
| Concierge | `Concierge` | `search_menu_tool`, `handoff_to` | All specialists |
| Food Expert | `Food Expert` | `search_menu_tool`, `get_menu_item_details_tool`, `handoff_to` | Ordering, Dietary, Reservation, Concierge |
| Dietary Guide | `Dietary Guide` | `check_dietary_info_tool`, `search_menu_tool`, `handoff_to` | Ordering, Food Expert, Reservation, Concierge |
| Order Assistant | `Order Assistant` | `create_order_tool`, `search_menu_tool`, `get_menu_item_details_tool`, `handoff_to` | Food Expert, Dietary, Support, Reservation |
| Reservation Desk | `Reservation Desk` | `create_reservation_tool`, `handoff_to` | Ordering, Food Expert, Concierge |
| Support | `Support` | `check_order_status_tool`, `handoff_to` | Ordering, Reservation, Concierge |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | [Lauren](https://lauren-py.dev) |
| AI agents | [Lauren AI](https://ai.lauren-py.dev) |
| LLM transport | Any OpenAI-compatible API (OpenRouter recommended) |
| Database | SQLite + aiosqlite |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| UI components | Radix UI, shadcn/ui |
| State management | Zustand + TanStack Query |
| Deployment | Modal (backend) · Netlify (frontend) |

---

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env    # set LLM_API_KEY and LLM_MODEL
uv sync
python main.py
```

The API starts at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

On first run the database is created automatically. Seed it with:

```bash
curl -X POST http://localhost:8000/api/seed
```

### Frontend

```bash
cd frontend
npm install             # or: bun install
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 npm run dev
```

The frontend starts at `http://localhost:3000`.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | | API key for the LLM provider |
| `LLM_API_BASE` | `https://openrouter.ai/api/v1` | OpenAI-compatible base URL |
| `LLM_MODEL` | `google/gemini-flash-1.5` | Model name |
| `DATABASE_URL` | `lauren_eats.db` | SQLite database path |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `FRONTEND_URL` | `http://localhost:3000` | Allowed CORS origin |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/menu` | List menu items (paginated, filterable by category) |
| `GET` | `/api/menu/{id}` | Get a single menu item |
| `PATCH` | `/api/menu/{id}` | Update a menu item |
| `GET` | `/api/categories` | List all categories with items |
| `GET` | `/api/orders` | List orders (filterable by status/type) |
| `POST` | `/api/orders` | Create a new order |
| `GET` | `/api/orders/{id}` | Get order details |
| `PUT` | `/api/orders/{id}` | Update order status |
| `GET` | `/api/reservations` | List reservations |
| `POST` | `/api/reservations` | Create a reservation |
| `PUT` | `/api/reservations/{id}` | Update reservation status |
| `POST` | `/api/chat` | AI chat — streams SSE events |
| `GET` | `/api/admin/stats` | Dashboard statistics |
| `GET` | `/api/admin/ai-insights` | Streaming AI-generated report |
| `POST` | `/api/seed` | Seed the database |

---

## Deployment

See [DEPLOY.md](./DEPLOY.md) for full instructions. Summary:

- **Backend** — deployed to [Modal](https://modal.com): `modal deploy backend/modal_deploy.py`
- **Frontend** — deployed to [Netlify](https://netlify.com): push to your configured branch; `netlify.toml` configures the build automatically

---

## Lauren Patterns Demonstrated

- `@agent()` + `@use_tools()` — declaring specialist agents with typed tool access
- `@tool()` class-form — DI-injected tools with database access
- `LLMModule.for_root()` + `AgentModule.for_root()` — wiring the AI layer into the module graph
- `EventStream` / SSE — real-time streaming from agent runs to the browser
- Three-scope DI — `SINGLETON` services (DB, tools), `REQUEST`-scoped interceptors
- `@injectable(scope=Scope.SINGLETON)` — shared database connection across the request graph
- `@module(imports=[...])` — composing feature modules (AI, database, controllers) cleanly
