"""CheckAuthModule — single owner of CheckAuthenticationTool.

Exported as a singleton so all three AgentModule instances can import it
and resolve the tool via the DI import chain without triggering a
ModuleExportViolation.
"""

from __future__ import annotations

from lauren import module

from app.ai.tools.check_auth_tool import CheckAuthenticationTool


@module(providers=[CheckAuthenticationTool], exports=[CheckAuthenticationTool])
class CheckAuthModule:
    """Provides CheckAuthenticationTool as a shared singleton across all agent modules."""
