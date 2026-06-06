# Deployment

This directory contains the Lauren Eats monorepo:

```
lauren-eats/
├── backend/         # Python ASGI app (Modal)
│   ├── modal_deploy.py    ← deploy with `modal deploy modal_deploy.py`
│   └── ...
└── frontend/        # Next.js 16 + Turbopack (Netlify)
    ├── netlify.toml       ← Netlify reads this automatically
    └── ...
```

## Backend — Modal

The backend is a Python ASGI application built on the `lauren` framework
and the `lauren-ai` LLM toolkit.  It is deployed to
[Modal.com](https://modal.com).

### One-time setup

```bash
# 1. Install the Modal CLI
pip install modal

# 2. Authenticate
modal setup

# 3. Create a secret for the LLM API key
modal secret create lauren-eats-secrets LLM_API_KEY=sk-...

# 4. Create the persistent volume for the SQLite database
modal volume create lauren-eats-data
```

### Deploy

```bash
cd backend
modal deploy modal_deploy.py
```

The deploy output ends with a URL of the form
`https://<workspace>--lauren-eats-serve.modal.run` — that is the
**production backend URL**.

### Seed the database (first deploy only)

```bash
modal run modal_deploy.py::seed
```

This populates the SQLite database with categories, menu items, and
sample orders.  Re-run it to reset the database to its seeded state.

### Inspect / debug

```bash
modal app logs lauren-eats           # tail logs
modal app history lauren-eats        # list recent deploys
modal volume ls lauren-eats-data     # list files in the volume
```

## Frontend — Netlify

The frontend is a Next.js 16 app with the App Router and standalone
output mode.

### One-time setup

1. Push the repo to GitHub / GitLab.
2. Create a new site in Netlify pointing at the repo, with the base
   directory set to `frontend/`.
3. In **Site settings → Environment variables**, set:

   | Key                      | Value                                             |
   |--------------------------|---------------------------------------------------|
   | `NEXT_PUBLIC_BACKEND_URL`| The `https://...modal.run` URL from the deploy    |

### Deploy

Netlify builds automatically on every push to the configured branch.
Manual deploys are also possible from the Netlify UI.

The `netlify.toml` file at the frontend root configures:

* **Build command** — `bun run build` (also `npm run build` works)
* **Publish directory** — `.next`
* **Node version** — 22
* **Security headers** — CSP-friendly defaults, HSTS, etc.
* **Asset caching** — 1-year immutable cache for `/_next/static/*`

### Local development

```bash
cd frontend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 bun run dev
```

(The internal Next.js API routes are a Prisma-based fallback that is
only used when `NEXT_PUBLIC_BACKEND_URL` is empty.  Setting the env
var routes all `src/lib/api.ts` calls to the Python backend.)
