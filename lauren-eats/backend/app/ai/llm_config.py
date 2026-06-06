"""LLMConfig factory for the Lauren Eats backend.

Returns the appropriate config based on the ``LLM_PROVIDER`` env var.
Defaults to ``openai`` to preserve the existing behaviour, but lets the
chatbot example pattern of using a single, central :class:`LLMConfig`
plus :func:`LLMModule.for_root` flow through every agent in the app.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from lauren_ai import LLMConfig

# Load .env with override=True so project settings always win over any
# shell env vars that may have leaked from other backend processes
# (e.g. a chatbot backend that exported LLM_BASE_URL to a different URL).
_env_path = Path(__file__).parents[2] / ".env"
load_dotenv(_env_path, override=True)


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(
            f"Required environment variable {name!r} is not set. "
            f"Add it to .env or export it before starting the server."
        )
    return value


def _build_config() -> LLMConfig:
    """Build the LLMConfig for the current environment.

    Required env vars: ``LLM_API_KEY``, ``LLM_API_BASE``, ``LLM_MODEL``.
    Optional: ``LLM_PROVIDER`` (defaults to ``"openai"``).
    """
    provider = _require("LLM_PROVIDER").lower()
    model = _require("LLM_MODEL")
    base_url = _require("LLM_API_BASE")

    if provider == "anthropic":
        api_key = _require("LLM_API_KEY")
        return LLMConfig.for_anthropic(model=model, api_key=api_key, base_url=base_url)
    if provider == "ollama":
        return LLMConfig.for_ollama(model=model, base_url=base_url)
    if provider == "litellm":
        api_key = _require("LLM_API_KEY")
        return LLMConfig(provider="litellm", model=model, api_key=api_key, base_url=base_url)
    # openai (default)
    api_key = _require("LLM_API_KEY")
    return LLMConfig.for_openai(model=model, api_key=api_key, base_url=base_url)


llm_config: LLMConfig = _build_config()
