"""LLMConfig factory for the Lauren Eats backend.

Returns the appropriate config based on the ``LLM_PROVIDER`` env var.
Defaults to ``openai`` to preserve the existing behaviour, but lets the
chatbot example pattern of using a single, central :class:`LLMConfig`
plus :func:`LLMModule.for_root` flow through every agent in the app.
"""

from __future__ import annotations

import os
from dataclasses import replace

from lauren_ai import LLMConfig


def _build_config() -> LLMConfig:
    """Build the LLMConfig for the current environment.

    Order of precedence:

    1. ``LLM_PROVIDER`` env var (``"openai"``, ``"anthropic"``, ``"ollama"``,
       ``"litellm"``).  Defaults to ``"openai"``.
    2. Provider-specific key env vars (``OPENAI_API_KEY`` etc.).
    3. Generic ``LLM_API_KEY`` / ``LLM_BASE_URL`` / ``LLM_MODEL`` as
       fallbacks for backwards compatibility with the previous
       hand-rolled ``httpx`` path.
    """
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("LLM_API_BASE")

    if provider == "anthropic":
        return LLMConfig.for_anthropic(model=model, api_key=api_key, base_url=base_url)
    if provider == "ollama":
        return LLMConfig.for_ollama(model=model, base_url=base_url or "http://localhost:11434")
    if provider == "litellm":
        return LLMConfig(provider="litellm", model=model, api_key=api_key, base_url=base_url)
    # openai (default)
    cfg = LLMConfig.for_openai(model=model, api_key=api_key, base_url=base_url)
    if base_url is None:
        return cfg
    return replace(cfg, base_url=base_url)


llm_config: LLMConfig = _build_config()
