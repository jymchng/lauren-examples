"""Knowledge sources for the SecureBank chatbot.

Hoisted to a dedicated module so both ``ai_module.py`` (which lists them
in ``AgentModule.for_root(knowledge=[...])``) and the agent files (which
opt-in via ``@use_knowledge_sources(...)``) can import without circular
references.
"""

from __future__ import annotations

from pathlib import Path

from lauren_ai._knowledge import (
    KnowledgeBase,
    KnowledgeSource,
    SentenceChunker,
    TextLoader,
)
from lauren_ai._memory._vector import InMemoryVectorStore

_PUBLIC_KB_DIR = Path(__file__).parent / "knowledge"

#: Public-info knowledge base (products, rates, fees, branch hours,
#: account-opening, security).  Visible only to agents that opt-in via
#: ``@use_knowledge_sources(PUBLIC_KB_SOURCE)`` — the
#: ``UnauthenticatedCRMAgent`` is the canonical consumer.
PUBLIC_KB_SOURCE = KnowledgeSource(
    kb=KnowledgeBase(
        store=InMemoryVectorStore(),
        chunker=SentenceChunker(max_chunk_size=600),
    ),
    tool_name="search_public_info",
    top_k=3,
    loaders=[TextLoader(str(p)) for p in sorted(_PUBLIC_KB_DIR.glob("*.md"))],
)
