# Lauren Eats Backend

AI-Powered Chinese Restaurant Platform — Python Backend built with **lauren** and **lauren-ai**.

## Architecture

- **Framework**: [lauren](https://lauren-py.dev) — metadata-first ASGI web framework with decorator-driven routing, DI, and modules
- **AI Agents**: [lauren-ai](https://ai.lauren-py.dev) — `@agent()`, `@tool()`, `AgentModule`, `LLMModule`
- **Database**: SQLite via aiosqlite
- **Streaming**: SSE (Server-Sent Events) for real-time AI chat

## Quick Start

```bash
# Install dependencies
pip install -e .

# Or using requirements.txt
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your LLM API key

# Initialize database and start server
python main.py
```

The API will be available at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check |
| GET | /api/menu | List menu items (paginated, filterable) |
| GET | /api/menu/{id} | Get menu item details |
| PATCH | /api/menu/{id} | Update menu item |
| GET | /api/categories | List all categories with items |
| GET | /api/orders | List orders (filterable) |
| POST | /api/orders | Create new order |
| GET | /api/orders/{id} | Get order details |
| PUT | /api/orders/{id} | Update order status |
| GET | /api/reservations | List reservations |
| POST | /api/reservations | Create reservation |
| PUT | /api/reservations/{id} | Update reservation status |
| POST | /api/chat | AI chat (SSE streaming) |
| GET | /api/admin/stats | Admin dashboard stats |
| GET | /api/admin/ai-insights | AI agent analytics |
| POST | /api/seed | Seed database |

## AI Agents

6 specialized agents with handoff capability:

| Agent | Role | Handoff Triggers |
|-------|------|------------------|
| Concierge 🎩 | General host & router | Routes to specialists |
| Food Expert 🍜 | Dish recommendations | User wants to order → ordering |
| Dietary Guide 🥬 | Allergy/diet specialist | User wants to order → ordering |
| Order Assistant 🛒 | Order building | User wants recs → food_recommender |
| Reservation Desk 📅 | Table booking | User wants menu → food_recommender |
| Support 🛟 | Customer service | User wants new order → ordering |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | lauren_eats.db | SQLite database path |
| LLM_API_KEY | | OpenAI-compatible API key |
| LLM_API_BASE | https://api.openai.com/v1 | LLM API base URL |
| LLM_MODEL | gpt-4 | Model name |
| HOST | 0.0.0.0 | Server host |
| PORT | 8000 | Server port |
| FRONTEND_URL | http://localhost:3000 | Frontend URL for CORS |

## Seed Data

The database comes pre-loaded with:
- **8 categories** of Chinese cuisine
- **42 menu items** with full details (allergens, dietary info, spice levels)
- **8 sample orders** across various statuses
