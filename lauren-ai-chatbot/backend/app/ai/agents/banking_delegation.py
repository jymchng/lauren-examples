# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""Runner DI tokens for the four banking agents.

Each AgentModule.for_root() call requires its own dedicated runner subclass as
a distinct DI token so the DI container can resolve them independently:

  UnauthCRMRunner     → UnauthenticatedCRMAgent
  AuthCRMRunner       → AuthenticatedCRMAgent
  TransferAgentRunner → BankTransferAgent
  DisputesAgentRunner → DisputesAgent
"""

from lauren import injectable, Scope
from lauren_ai import AgentRunnerBase


@injectable(scope=Scope.SINGLETON)
class UnauthCRMRunner(AgentRunnerBase):
    """Distinct DI token for the UnauthenticatedCRMAgent's runner."""


@injectable(scope=Scope.SINGLETON)
class AuthCRMRunner(AgentRunnerBase):
    """Distinct DI token for the AuthenticatedCRMAgent's runner."""


@injectable(scope=Scope.SINGLETON)
class TransferAgentRunner(AgentRunnerBase):
    """Distinct DI token for the BankTransferAgent's runner."""


@injectable(scope=Scope.SINGLETON)
class DisputesAgentRunner(AgentRunnerBase):
    """Distinct DI token for the DisputesAgent's runner."""
