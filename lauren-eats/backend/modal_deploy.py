"""Modal.com deployment for the Lauren Eats backend.

Deploys the FastAPI-style ASGI application defined in ``main:app`` to
Modal's serverless platform.  The container image bundles:

* The project's own ``app/`` package (controllers, services, agents, …)
* A vendored copy of the ``lauren`` / ``lauren-ai`` / ``lauren-logging``
  framework packages (not on PyPI yet — pulled in from the sibling
  checkouts at deploy time)
* Runtime dependencies declared in ``pyproject.toml``

State:

* The SQLite database is persisted in a Modal Volume named
  ``lauren-eats-data`` mounted at ``/data``.  Survives restarts and
  container rebuilds.
* LLM credentials live in a Modal Secret named ``lauren-eats-secrets``
  with at least ``LLM_API_KEY`` set.

Usage::

    # 1. Create the secret once (never commit the value)
    modal secret create lauren-eats-secrets LLM_API_KEY=sk-...

    # 2. Create the persistent volume
    modal volume create lauren-eats-data

    # 3. Deploy
    modal deploy modal_deploy.py

    # 4. Tail logs / inspect
    modal app logs lauren-eats

The deployed endpoint URL is printed by ``modal deploy`` and is what
the frontend's ``NEXT_PUBLIC_BACKEND_URL`` env var should point at.
"""

from __future__ import annotations

import modal

# ---------------------------------------------------------------------------
# Image definition
# ---------------------------------------------------------------------------

# Resolve the project root — Modal runs this file from the directory that
# contains it, so ``./`` is the ``backend/`` folder.
PROJECT_ROOT = "/root"

# Path of the lauren monorepo relative to the project root.  Override
# with the ``LAUREN_MONOREPO`` env var if the deployment host has a
# different layout.
LAUREN_MONOREPO = PROJECT_ROOT + "/python_projects/lauren-all"

image = (
    modal.Image.debian_slim(python_version="3.12")
    # System packages
    .apt_install("build-essential", "libsqlite3-dev")
    # Third-party deps from pyproject.toml — kept in sync with the
    # ``[project.dependencies]`` list in pyproject.toml.
    .pip_install(
        "aiosqlite>=0.20",
        "httpx>=0.27",
        "pydantic>=2.7",
        "uvicorn[standard]>=0.29",
        "fastapi>=0.110",  # required by some lauren-ai transports
    )
    # Vendored framework packages — these are not on PyPI yet, so we
    # install them directly from the sibling checkouts in the monorepo.
    # The order matters: lauren-logging has no deps, lauren-framework
    # depends on lauren-logging, lauren-ai depends on lauren-framework.
    .pip_install(f"{LAUREN_MONOREPO}/lauren-logging")
    .pip_install(f"{LAUREN_MONOREPO}/lauren-framework")
    .pip_install(f"{LAUREN_MONOREPO}/lauren-ai")
    # The project's own package.  ``add_local_dir`` copies the source
    # into the image at ``/app``; we add it to PYTHONPATH so ``import
    # app.*`` resolves.
    .add_local_dir("app", remote_path="/root/app")
    .env({"PYTHONPATH": "/root"})
    # Force production-like defaults; secrets are layered on top by
    # ``modal deploy`` from the named secret.
    .env(
        {
            "DATABASE_URL": "/data/lauren_eats.db",
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4o-mini",
            "PYTHONHASHSEED": "0",
        }
    )
)

# ---------------------------------------------------------------------------
# Persistent storage
# ---------------------------------------------------------------------------

volume = modal.Volume.from_name("lauren-eats-data", create_if_missing=True)

# ---------------------------------------------------------------------------
# ASGI app entrypoint
# ---------------------------------------------------------------------------

app = modal.App("lauren-eats")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("lauren-eats-secrets", required=True)],
    volumes={"/data": volume},
    # Cold-start friendly: keep one warm instance so the SSE chat
    # endpoint doesn't pay the 4–6 s cold-start tax on first message.
    min_containers=1,
    # Generous timeout — agent completions can be slow with handoffs.
    timeout=120,
    # 4 vCPUs / 2 GB is plenty for the SSE + agent workload; bump if
    # analytics endpoints start to lag.
    cpu=4,
    memory=2048,
    # Concurrency: the EventStream SSE handler holds a long-lived
    # connection per request, so cap at 8 in-flight requests per
    # container to keep memory bounded.
    allow_concurrent_inputs=8,
)
@modal.asgi()
def serve() -> object:
    """Return the ASGI app instance for Modal to serve."""
    # Imports happen inside the function so the framework can wire up
    # its lifespan hooks on the right event loop.  Keeping them at
    # module top-level also works, but doing it here makes the cold
    # path explicit and side-effect free.
    from main import app as asgi_app

    return asgi_app


# ---------------------------------------------------------------------------
# Local entrypoint: seed the database once
# ---------------------------------------------------------------------------


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("lauren-eats-secrets", required=True)],
    volumes={"/data": volume},
    timeout=120,
)
def seed() -> dict:
    """POST /api/seed against the deployed app.  Run after first deploy.

    Returns the seed response payload (categories, items, orders counts).

    Usage::

        modal run modal_deploy.py::seed
    """
    import httpx

    from main import create_app

    # The ``create_app()`` factory wires up the framework in-process; we
    # use its :class:`LaurenApp` directly to issue a synthetic request
    # rather than round-trip through HTTP (which would require a public
    # URL the first time).
    asgi_app = create_app()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/seed",
        "raw_path": b"/api/seed",
        "query_string": b"",
        "headers": [(b"host", b"modal")],
    }

    sent = False

    async def receive() -> dict:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": b"", "more_body": False}

    status_holder = {"status": 500}
    body_holder = bytearray()

    async def send(msg: dict) -> None:
        if msg["type"] == "http.response.start":
            status_holder["status"] = msg["status"]
        elif msg["type"] == "http.response.body":
            body_holder.extend(msg.get("body", b""))

    import asyncio

    asyncio.run(asgi_app(scope, receive, send))
    import json

    return {"status": status_holder["status"], "body": json.loads(body_holder or b"{}")}


# ---------------------------------------------------------------------------
# Scheduled nightly snapshot (optional)
# ---------------------------------------------------------------------------


@app.function(
    image=image,
    schedule=modal.Period(days=1),
    secrets=[modal.Secret.from_name("lauren-eats-secrets", required=True)],
    volumes={"/data": volume},
)
def nightly_snapshot() -> None:
    """Touch the volume so the data directory is committed at least once a day.

    Modal volumes are backed by S3 snapshots — frequent commits keep RPO
    tight without paying the cost on every write.  The database already
    commits on each ``execute()`` call, so this is purely belt-and-braces.
    """
    volume.commit()
