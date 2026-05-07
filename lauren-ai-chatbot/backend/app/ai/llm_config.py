"""Shared LLMConfig singleton for the SecureBank chatbot.

Extracted from ``ai_module.py`` so agent files and guardrail constructors can
import it without creating a circular dependency (agent → ai_module → agent).
"""

from __future__ import annotations

import os

from lauren_ai import LLMConfig

llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "poolside/laguna-xs.2:free"),
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)
