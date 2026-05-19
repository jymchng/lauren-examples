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

PYTHON = "3.12"

def _install_dev(session: nox.Session) -> None:
    """Install all local editable packages plus dev extras in one pip call."""
    session.run(
        "uv",
        "pip",
        "install",
        "lauren",
        "lauren-ai[openai]",
    )


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
        "--cov=app",
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
    session.run("ruff", "format", "app/", "tests/")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


@nox.session(python=PYTHON)
def build(session: nox.Session) -> None:
    """Build a source distribution and wheel into dist/."""
    session.install("build")
    session.run("python", "-m", "build", "--outdir", "dist/")


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
        "--host",
        "0.0.0.0",
        "--port",
        port,
        "--reload",
        external=True,
    )


@nox.session(name="clean", python=PYTHON)
def clean(session: nox.Session) -> None:
    """Remove build artifacts and common junk files recursively."""
    import shutil
    from pathlib import Path

    ROOT = Path.cwd()

    # Directories to remove entirely
    DIR_TARGETS = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".nox",
        ".tox",
        "dist",
        "build",
        "htmlcov",
        ".eggs",
        "*.egg-info",
        "node_modules",   # if present anywhere
        ".cache",
        "tmp",
    }

    # File patterns to remove
    FILE_TARGETS = {
        "*.pyc",
        "*.pyo",
        "*.log",
        "*.tmp",
        "*.swp",
        ".coverage",
    }

    # Remove directories
    for pattern in DIR_TARGETS:
        for path in ROOT.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    # Remove files
    for pattern in FILE_TARGETS:
        for path in ROOT.rglob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)

    session.log("Aggressively cleaned project junk.")