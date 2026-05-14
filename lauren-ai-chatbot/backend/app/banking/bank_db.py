"""In-memory banking database for the SecureBank demo.

Holds three accounts (Alice, Bob, Charlie) and a transaction ledger.
All mutations are protected by a threading.Lock so concurrent requests
cannot corrupt balances.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import Callable, Awaitable
from datetime import datetime, timezone
from typing import Any

import msgspec

from lauren import injectable, Scope


class BankAccount(msgspec.Struct):
    user_id: str
    name: str
    account_id: str
    balance: float
    avatar_color: str = "#6366f1"


class Transaction(msgspec.Struct):
    tx_id: str
    from_user: str
    to_user: str
    amount: float
    timestamp: str
    description: str
    from_name: str = ""
    to_name: str = ""


@injectable(scope=Scope.SINGLETON)
class BankDatabase:
    """Thread-safe in-memory banking database.

    Holds accounts for Alice Johnson, Bob Smith, and Charlie Brown.
    Provides balance lookup, fund transfer, and transaction history.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._transfer_listeners: list[Callable[..., Awaitable[Any]]] = []
        self._accounts: dict[str, BankAccount] = {
            "alice": BankAccount(
                user_id="alice",
                name="Alice Johnson",
                account_id="ACC-001",
                balance=5_000.00,
                avatar_color="#10b981",
            ),
            "bob": BankAccount(
                user_id="bob",
                name="Bob Smith",
                account_id="ACC-002",
                balance=3_200.00,
                avatar_color="#3b82f6",
            ),
            "charlie": BankAccount(
                user_id="charlie",
                name="Charlie Brown",
                account_id="ACC-003",
                balance=1_800.00,
                avatar_color="#f59e0b",
            ),
        }
        self._transactions: list[Transaction] = []

    # ── Listener registration ─────────────────────────────────────────────────

    def add_transfer_listener(self, fn: Callable[..., Awaitable[Any]]) -> None:
        """Register an async callback invoked after every successful transfer.

        The callback signature is ``fn(tx: Transaction, from_balance: float,
        to_balance: float)``.  It is scheduled as a new asyncio task so it
        does not block the transfer itself.
        """
        self._transfer_listeners.append(fn)

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_account(self, user_id: str) -> BankAccount | None:
        return self._accounts.get(user_id.lower())

    def get_all_accounts(self) -> list[BankAccount]:
        return list(self._accounts.values())

    def get_transactions(self, user_id: str, limit: int = 10) -> list[Transaction]:
        uid = user_id.lower()
        relevant = [t for t in self._transactions if t.from_user == uid or t.to_user == uid]
        return list(reversed(relevant))[:limit]

    # ── Mutations ─────────────────────────────────────────────────────────────

    def transfer(
        self,
        from_user: str,
        to_user: str,
        amount: float,
        description: str = "",
    ) -> Transaction | str:
        """Transfer *amount* from *from_user* to *to_user*.

        Returns a :class:`Transaction` on success or an error string on failure.
        """
        with self._lock:
            from_acct = self._accounts.get(from_user.lower())
            to_acct = self._accounts.get(to_user.lower())

            if not from_acct:
                return f"Unknown account holder: {from_user}"
            if not to_acct:
                return f"Unknown recipient: {to_user}"
            if from_user.lower() == to_user.lower():
                return "Cannot transfer to your own account"
            if amount <= 0:
                return "Transfer amount must be greater than zero"
            if amount > 100_000:
                return "Transfer amount exceeds the $100,000 single-transaction limit"
            if from_acct.balance < amount:
                return f"Insufficient funds. Available: ${from_acct.balance:,.2f}, requested: ${amount:,.2f}"

            from_acct.balance = round(from_acct.balance - amount, 2)
            to_acct.balance = round(to_acct.balance + amount, 2)

            tx = Transaction(
                tx_id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                from_user=from_user.lower(),
                to_user=to_user.lower(),
                amount=amount,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description=description or f"Transfer to {to_acct.name}",
                from_name=from_acct.name,
                to_name=to_acct.name,
            )
            self._transactions.append(tx)
            from_balance = from_acct.balance
            to_balance = to_acct.balance

        # Fire transfer listeners outside the lock (they are async)
        if self._transfer_listeners:
            try:
                loop = asyncio.get_running_loop()
                for cb in self._transfer_listeners:
                    loop.create_task(cb(tx, from_balance, to_balance))
            except RuntimeError:
                pass  # No running event loop (e.g. during unit tests)

        return tx
