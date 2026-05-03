"""BankingController — REST endpoints for account information.

GET /api/banking/accounts          → list of all accounts (name, id, balance)
GET /api/banking/accounts/{user_id} → single account with recent transactions
"""

from __future__ import annotations

from lauren import Path, controller, get

from app.banking.bank_db import BankDatabase


@controller("/api/banking")
class BankingController:
    """Serves account information for the banking demo."""

    def __init__(self, db: BankDatabase) -> None:
        self._db = db

    @get("/accounts")
    def list_accounts(self) -> dict:
        """Return all accounts (for the user-selector panel)."""
        return {
            "accounts": [
                {
                    "user_id": a.user_id,
                    "name": a.name,
                    "account_id": a.account_id,
                    "balance": a.balance,
                    "avatar_color": a.avatar_color,
                }
                for a in self._db.get_all_accounts()
            ]
        }

    @get("/accounts/{user_id}")
    def get_account(self, user_id: Path[str]) -> dict:
        """Return a single account with recent transactions."""
        account = self._db.get_account(user_id)
        if not account:
            from lauren.exceptions import NotFoundError

            raise NotFoundError(f"Account not found: {user_id}")

        transactions = self._db.get_transactions(user_id, limit=5)
        return {
            "user_id": account.user_id,
            "name": account.name,
            "account_id": account.account_id,
            "balance": account.balance,
            "avatar_color": account.avatar_color,
            "transactions": [
                {
                    "tx_id": t.tx_id,
                    "type": "debit" if t.from_user == user_id.lower() else "credit",
                    "counterparty_id": t.to_user if t.from_user == user_id.lower() else t.from_user,
                    "counterparty_name": t.to_name if t.from_user == user_id.lower() else t.from_name,
                    "amount": t.amount,
                    "description": t.description,
                    "timestamp": t.timestamp,
                }
                for t in transactions
            ],
        }
