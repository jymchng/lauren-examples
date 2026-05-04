"""Modal deployment — SecureBank AI backend.

Builds the Lauren/FastAPI ASGI application into a Modal container image and
exposes it via Modal's managed HTTPS gateway.  WebSocket upgrades (for the
``/ws/banking`` real-time event stream) are fully supported.

Quick start
-----------
Install the Modal client once::

    pip install modal
    modal setup                     # authenticate with your Modal workspace

Create the secret group once (values are stored encrypted in Modal)::

    modal secret create lauren-chatbot-secrets \\
        OPENROUTER_API_KEY="sk-or-v1-your-key-here" \\
        LLM_MODEL="openai/gpt-4o-mini" \\
        PAYLOAD_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

Deploy to production::

    modal deploy modal_deploy.py

Live-reload preview (watches source files, ideal for development)::

    modal serve modal_deploy.py

After deployment Modal prints a URL such as::

    https://<workspace>--securebank-ai-backend-web.modal.run

Point the Next.js frontend at that URL::

    # frontend/.env.local
    BACKEND_URL=https://<workspace>--securebank-ai-backend-web.modal.run
    PAYLOAD_SECRET=<same value you set in the Modal secret>

Routes exposed
--------------
GET  /api/health/                   Liveness probe
GET  /api/banking/accounts          Account list
GET  /api/banking/accounts/{uid}    Account detail + recent transactions
POST /api/banking/chat              Agentic SSE stream  (HMAC-signed)
POST /api/banking/ws-token          Short-lived WebSocket auth token
WS   /ws/banking                    Real-time event stream
GET  /api/metrics/                  Cost + trace summary
GET  /api/metrics/traces            Last 50 traces
GET  /api/metrics/cost              Token cost breakdown by model
"""

from __future__ import annotations

from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Source paths — resolved on the deploying machine at ``modal deploy`` time
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent.resolve()  # .../backend/
_LAUREN_ALL = _HERE.parent.parent.parent  # .../lauren-all/

FRAMEWORK_PATH = _LAUREN_ALL / "lauren-framework"
LAUREN_AI_PATH = _LAUREN_ALL / "lauren-ai"

# ---------------------------------------------------------------------------
# Modal application
# ---------------------------------------------------------------------------

app = modal.App("securebank-ai-backend")

# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------
#
# Why the two-step local-package install?
# ────────────────────────────────────────
# ``lauren`` and ``lauren-ai`` live only in this monorepo — they are NOT
# published to PyPI.  The backend's ``pyproject.toml`` lists both as regular
# dependencies, so a naive ``pip install /backend`` would fail because pip
# cannot find them on the package index.
#
# Solution: install the two packages from their source trees **before** pip
# processes the backend's dependency list.  Once they are registered in the
# environment, pip recognises the constraints as satisfied and does not
# attempt a PyPI lookup.  The final ``--no-deps`` flag makes this guarantee
# explicit and avoids a redundant index query.
#
# Layer order is deliberately coarse-grained so Modal can maximise cache hits:
#   1. Framework source  (changes rarely)
#   2. lauren-ai source  (changes occasionally)
#   3. PyPI runtime deps (pinned range, stable)
#   4. Backend source    (changes frequently — always rebuilt)

image = (
    modal.Image.debian_slim(python_version="3.12")

    # ── 1. lauren-framework ─────────────────────────────────────────────
    .copy_local_dir(
        str(FRAMEWORK_PATH),
        "/opt/lauren-framework",
        ignore=["__pycache__", "*.pyc", ".git", ".venv", "venv", "dist", ".pytest_cache"],
    )
    .run_commands("pip install --quiet /opt/lauren-framework")

    # ── 2. lauren-ai ────────────────────────────────────────────────────
    .copy_local_dir(
        str(LAUREN_AI_PATH),
        "/opt/lauren-ai",
        ignore=["__pycache__", "*.pyc", ".git", ".venv", "venv", "dist", ".pytest_cache"],
    )
    .run_commands("pip install --quiet '/opt/lauren-ai[openai]'")

    # ── 3. PyPI runtime dependencies ────────────────────────────────────
    .pip_install(
        "httpx>=0.27",
        "uvicorn[standard]>=0.29",
        "python-dotenv>=1.0",
    )

    # ── 4. Backend application ──────────────────────────────────────────
    # Exclude secrets and build artefacts; they must not reach the image.
    .copy_local_dir(
        str(_HERE),
        "/backend",
        ignore=[
            ".env", ".env.local", ".env.*",   # never bake secrets into the image
            "__pycache__", "*.pyc",
            ".venv", "venv",
            "dist",
            ".pytest_cache",
            "tests",                           # tests not needed at runtime
        ],
    )
    .run_commands(
        # Install the `app` package.  --no-deps is safe here because every
        # dependency (lauren, lauren-ai, httpx, uvicorn, python-dotenv) was
        # installed in the layers above; pip skips the index lookup entirely.
        "pip install --quiet --no-deps /backend",
    )

    # ── 5. Make main.py importable at runtime ───────────────────────────
    # main.py lives at /backend/main.py (top-level, not inside a package).
    # Adding /backend to PYTHONPATH lets ``import main`` resolve correctly.
    .env({"PYTHONPATH": "/backend"})
)

# ---------------------------------------------------------------------------
# ASGI function — serves all HTTP and WebSocket traffic
# ---------------------------------------------------------------------------


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("lauren-chatbot-secrets")],

    # Keep one container warm to eliminate cold-start latency on the first
    # request.  Comment out (or set to 0) to pay only for active request time
    # at the cost of a ~5-second cold boot on the first call after idle.
    min_containers=1,

    # ASGI is fully asynchronous; a single container can handle many
    # concurrent requests without blocking.
    allow_concurrent_inputs=100,

    # Agent loops can involve multiple LLM round-trips; 5 minutes gives
    # comfortable headroom even for complex multi-turn conversations.
    timeout=300,
)
@modal.asgi_app()
def web() -> object:
    """Return the Lauren/FastAPI ASGI application to Modal's gateway.

    ``main.py`` wires the complete Lauren DI container at import time:
    all controllers, middleware, interceptors, agents, tools, WebSocket
    gateway, and signal handlers are initialised once per warm container.
    Modal reuses the warm container for subsequent requests, so there is
    zero re-initialisation cost after the first request in a container.

    ``load_dotenv()`` in ``main.py`` is a no-op here because there is no
    ``.env`` file in the image; all configuration is supplied by the Modal
    secret ``lauren-chatbot-secrets`` which Modal injects as real environment
    variables before the function body executes.
    """
    from main import app as asgi_app  # noqa: PLC0415

    return asgi_app
