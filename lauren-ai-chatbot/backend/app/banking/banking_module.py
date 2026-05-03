"""BankingModule — provides BankDatabase and the account REST endpoints."""

from __future__ import annotations

from lauren import module

from app.banking.bank_db import BankDatabase
from app.banking.banking_controller import BankingController


@module(
    providers=[BankDatabase],
    exports=[BankDatabase],
    controllers=[BankingController],
)
class BankingModule:
    """Provides the in-memory bank database and account REST endpoints."""
