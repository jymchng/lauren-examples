"""Nox sessions for the Lauren AI Chatbot backend.

Usage:
    nox -s tests          # run full test suite (default)
    nox -s tests_unit     # unit tests only
    nox -s tests_int      # integration tests only
    nox -s lint           # ruff check
    nox -s format         # ruff format --check
    nox -s run            # start uvicorn dev server
"""

from __future__ import annotations

import os

import nox

# Use a user-writable directory so ai-slave can write the venv.
nox.options.envdir = os.path.join(os.path.expanduser("~"), ".cache", "nox", "lauren-chatbot")
nox.options.sessions = ["tests"]

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
# backend → lauren-ai-chatbot → lauren-examples → lauren-all
_LAUREN_ALL = _os.path.dirname(_os.path.dirname(_os.path.dirname(_HERE)))
FRAMEWORK_PATH = _os.path.join(_LAUREN_ALL, "lauren-framework")
LAUREN_AI_PATH = _os.path.join(_LAUREN_ALL, "lauren-ai")

PYTHON = "3.12"


def _install_dev(session: nox.Session) -> None:
    """Install all local editable packages plus dev extras in one pip call."""
    session.run(
        "uv", "pip", "install", "-e", FRAMEWORK_PATH,
        "-e", f"{LAUREN_AI_PATH}[openai]",
        "-e", ".[dev]",
    )
    # session.install(
    #     "-e", FRAMEWORK_PATH,
    #     "-e", f"{LAUREN_AI_PATH}[openai]",
    #     "-e", ".[dev]",
    # )


# ---------------------------------------------------------------------------
# Test sessions
# ---------------------------------------------------------------------------


@nox.session(python=PYTHON)
def tests(session: nox.Session) -> None:
    """Run the full test suite with coverage."""
    _install_dev(session)
    session.run(
        "pytest",
        "tests/",
        "-q",
        "--tb=short",
        f"--cov=app",
        "--cov-report=term-missing",
        "--cov-fail-under=90",
        *session.posargs,
    )


@nox.session(python=PYTHON)
def tests_unit(session: nox.Session) -> None:
    """Run unit tests only."""
    _install_dev(session)
    session.run("pytest", "tests/unit/", "-q", "--tb=short", *session.posargs)


@nox.session(python=PYTHON)
def tests_int(session: nox.Session) -> None:
    """Run integration tests only."""
    _install_dev(session)
    session.run("pytest", "tests/integration/", "-q", "--tb=short", *session.posargs)


# ---------------------------------------------------------------------------
# Lint / format
# ---------------------------------------------------------------------------


@nox.session(python=PYTHON)
def lint(session: nox.Session) -> None:
    """Lint with ruff."""
    session.install("ruff")
    session.run("ruff", "check", "app/", "tests/", "--select=E,F,I")


@nox.session(python=PYTHON)
def format(session: nox.Session) -> None:
    """Check formatting with ruff."""
    session.install("ruff")
    session.run("ruff", "format", "--check", "app/", "tests/")


# ---------------------------------------------------------------------------
# Dev server
# ---------------------------------------------------------------------------


@nox.session(python=PYTHON)
def run(session: nox.Session) -> None:
    """Start the uvicorn development server (requires OPENROUTER_API_KEY env var)."""
    _install_dev(session)
    port = os.environ.get("PORT", "8000")
    session.run(
        "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", port,
        "--reload",
        external=True,
    )
