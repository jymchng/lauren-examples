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
    NEXT_PUBLIC_WS_URL=wss://<workspace>--securebank-ai-backend-web.modal.run
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

import atexit
import shutil
import subprocess
import tempfile
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
# Build wheels locally before constructing the Modal image
# ---------------------------------------------------------------------------
#
# ``uv build --wheel`` runs entirely on the deploying machine — no build step
# needed inside the container.  Modal derives each layer's cache key from the
# wheel file's content hash, so a layer is only rebuilt when the corresponding
# package actually changed.  This gives better granularity than hashing a
# whole source tree and keeps the image clean (no source files, no tests, no
# docs — just the installable artifact).
#
# ``modal.is_local()`` guards the build so that wheels are never rebuilt when
# this module is imported inside a running container.


def _build_wheel(source_dir: Path, out_dir: Path) -> Path:
    """Build a wheel for the package at *source_dir* into *out_dir*."""
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=source_dir,
        check=True,
    )
    wheels = list(out_dir.glob("*.whl"))
    if not wheels:
        raise RuntimeError(f"No wheel produced for {source_dir}")
    return wheels[0]


# ---------------------------------------------------------------------------
# Modal application
# ---------------------------------------------------------------------------

app = modal.App("securebank-ai-backend")

# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------
#
# Layer order maximises Modal cache hits:
#   1. PyPI runtime deps          (pinned ranges — very stable)
#   2. lauren-framework wheel     (changes rarely)
#   3. lauren-ai wheel            (changes occasionally)
#   4. backend wheel + main.py    (changes frequently — always rebuilt)
#
# The backend wheel only bundles the ``app`` package (see pyproject.toml
# ``[tool.setuptools.packages.find]``).  ``main.py`` is added as a separate
# file and made importable via PYTHONPATH so Modal's entry-point works.
#
# ``--no-deps`` on the backend install is safe because every declared
# dependency (lauren, lauren-ai, httpx, uvicorn, python-dotenv) is already
# present from the layers above; pip skips the index lookup entirely.

if modal.is_local():
    _dist = Path(tempfile.mkdtemp(prefix="modal-wheels-"))
    atexit.register(shutil.rmtree, _dist, ignore_errors=True)

    _framework_whl = _build_wheel(FRAMEWORK_PATH, _dist / "framework")
    _lauren_ai_whl = _build_wheel(LAUREN_AI_PATH, _dist / "lauren-ai")
    _backend_whl   = _build_wheel(_HERE,          _dist / "backend")

    image = (
        modal.Image.debian_slim(python_version="3.12")

        # ── 1. PyPI runtime dependencies ─────────────────────────────────
        .pip_install(
            "httpx>=0.27",
            "uvicorn[standard]>=0.29",
            "python-dotenv>=1.0",
        )

        # ── 2. lauren-framework ──────────────────────────────────────────
        .add_local_file(
            str(_framework_whl),
            f"/opt/wheels/{_framework_whl.name}",
            copy=True,
        )
        .run_commands(f"pip install --quiet /opt/wheels/{_framework_whl.name}")

        # ── 3. lauren-ai ────────────────────────────────────────────────
        .add_local_file(
            str(_lauren_ai_whl),
            f"/opt/wheels/{_lauren_ai_whl.name}",
            copy=True,
        )
        .run_commands(f"pip install --quiet '/opt/wheels/{_lauren_ai_whl.name}[openai]'")

        # ── 4. Backend application ───────────────────────────────────────
        .add_local_file(
            str(_backend_whl),
            f"/opt/wheels/{_backend_whl.name}",
            copy=True,
        )
        .add_local_file(str(_HERE / "main.py"), "/backend/main.py", copy=True)
        .run_commands(
            f"pip install --quiet --no-deps /opt/wheels/{_backend_whl.name}",
        )

        # ── 5. Knowledge-base content ───────────────────────────────────
        #
        # ``app/ai/knowledge/`` holds the public-info markdown files used by
        # the unauthenticated CRM agent's RAG tool.  The directory has no
        # ``__init__.py`` (it is content, not code), so setuptools does NOT
        # include the ``.md`` files in the backend wheel.  Copy them into
        # the installed ``app.ai.knowledge`` location so
        # ``Path(__file__).parent / "knowledge"`` resolves at runtime.
        #
        # The destination path is tied to ``python_version="3.12"`` above —
        # if the Python version changes, update this path to match.
        .add_local_dir(
            str(_HERE / "app" / "ai" / "knowledge"),
            "/usr/local/lib/python3.12/site-packages/app/ai/knowledge",
            copy=True,
        )

        # ── 6. Make main.py importable at runtime ────────────────────────
        .env({"PYTHONPATH": "/backend"})
    )
else:
    # Inside the container the image is already baked; this branch is never
    # used to build anything — it just satisfies the @app.function decorator.
    image = modal.Image.debian_slim(python_version="3.12")

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

    # Agent loops can involve multiple LLM round-trips; 5 minutes gives
    # comfortable headroom even for complex multi-turn conversations.
    timeout=300,
)
@modal.concurrent(max_inputs=100)
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
