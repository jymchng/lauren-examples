"""Shared pytest fixtures for the Lauren AI Chatbot backend tests.

Sets required environment variables before any imports so that singleton
services (CryptoService, ChatService) read a deterministic config.
"""

import os

import pytest

# Must be set before importing the app modules so singletons pick up test values
os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("PORT", "8001")

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, "/root/python_projects/lauren-all/lauren-framework")


@pytest.fixture(scope="session")
def payload_secret() -> str:
    return os.environ["PAYLOAD_SECRET"]
