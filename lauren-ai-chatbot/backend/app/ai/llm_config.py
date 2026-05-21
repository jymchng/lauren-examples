"""Shared LLMConfig singleton for the SecureBank chatbot.

Extracted from ``ai_module.py`` so agent files and guardrail constructors can
import it without creating a circular dependency (agent → ai_module → agent).
"""

from __future__ import annotations

import os

from lauren_ai import LLMConfig

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

if not API_KEY:
    raise ValueError("LLM API key not found. Please set the `OPENROUTER_API_KEY` environment variable.")

llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "poolside/laguna-xs.2:free"),
    api_key=API_KEY,
    base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
)
