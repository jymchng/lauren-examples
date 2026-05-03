"""BankingModule — provides BankDatabase and the account REST endpoints."""

from __future__ import annotations

from lauren import module, use_value

from app.banking.bank_db import BankDatabase
from app.banking.banking_controller import BankingController

# Bind the process-level singleton so every DI scope that imports this module
# receives the exact same BankDatabase object (not a freshly constructed copy).


@module(
    providers=[BankDatabase],
    exports=[BankDatabase],
    controllers=[BankingController],
)
class BankingModule:
    """Provides the in-memory bank database and account REST endpoints."""
