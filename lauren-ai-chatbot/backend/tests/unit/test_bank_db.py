"""Unit tests for BankDatabase — the in-memory banking data store."""

from __future__ import annotations

import asyncio

import pytest

from app.banking.bank_db import BankAccount, BankDatabase, Transaction


@pytest.fixture()
def db() -> BankDatabase:
    """Fresh BankDatabase for each test (new singleton bypassed via direct instantiation)."""
    return BankDatabase()


# ---------------------------------------------------------------------------
# get_account
# ---------------------------------------------------------------------------


class TestGetAccount:
    def test_get_alice(self, db):
        acct = db.get_account("alice")
        assert acct is not None
        assert acct.user_id == "alice"
        assert acct.name == "Alice Johnson"
        assert acct.account_id == "ACC-001"
        assert acct.balance == 5_000.00

    def test_get_bob(self, db):
        acct = db.get_account("bob")
        assert acct is not None
        assert acct.user_id == "bob"

    def test_get_charlie(self, db):
        acct = db.get_account("charlie")
        assert acct is not None
        assert acct.user_id == "charlie"

    def test_unknown_user_returns_none(self, db):
        assert db.get_account("dave") is None

    def test_case_insensitive_lookup(self, db):
        assert db.get_account("ALICE") is not None
        assert db.get_account("Alice") is not None

    def test_empty_string_returns_none(self, db):
        assert db.get_account("") is None


# ---------------------------------------------------------------------------
# get_all_accounts
# ---------------------------------------------------------------------------


class TestGetAllAccounts:
    def test_returns_three_accounts(self, db):
        accounts = db.get_all_accounts()
        assert len(accounts) == 3

    def test_all_have_expected_fields(self, db):
        accounts = db.get_all_accounts()
        for a in accounts:
            assert isinstance(a, BankAccount)
            assert a.user_id
            assert a.name
            assert a.account_id
            assert a.balance >= 0
            assert a.avatar_color.startswith("#")

    def test_user_ids_are_alice_bob_charlie(self, db):
        ids = {a.user_id for a in db.get_all_accounts()}
        assert ids == {"alice", "bob", "charlie"}


# ---------------------------------------------------------------------------
# get_transactions
# ---------------------------------------------------------------------------


class TestGetTransactions:
    def test_empty_initially(self, db):
        assert db.get_transactions("alice") == []

    def test_after_transfer_appears_for_both_parties(self, db):
        db.transfer("alice", "bob", 100.0, "test")
        alice_txns = db.get_transactions("alice")
        bob_txns = db.get_transactions("bob")
        assert len(alice_txns) == 1
        assert len(bob_txns) == 1

    def test_unknown_user_returns_empty(self, db):
        assert db.get_transactions("dave") == []

    def test_limit_respected(self, db):
        for i in range(8):
            db.transfer("alice", "bob", 10.0, f"txn-{i}")
        txns = db.get_transactions("alice", limit=3)
        assert len(txns) == 3

    def test_transactions_in_reverse_chronological_order(self, db):
        db.transfer("alice", "bob", 10.0, "first")
        db.transfer("alice", "bob", 20.0, "second")
        txns = db.get_transactions("alice")
        assert txns[0].amount == 20.0
        assert txns[1].amount == 10.0

    def test_default_limit_is_10(self, db):
        for i in range(15):
            db.transfer("alice", "bob", 1.0, f"t{i}")
        txns = db.get_transactions("alice")
        assert len(txns) == 10


# ---------------------------------------------------------------------------
# transfer — success path
# ---------------------------------------------------------------------------


class TestTransferSuccess:
    def test_returns_transaction_object(self, db):
        result = db.transfer("alice", "bob", 500.0)
        assert isinstance(result, Transaction)

    def test_deducts_from_sender(self, db):
        db.transfer("alice", "bob", 200.0)
        assert db.get_account("alice").balance == 4_800.00

    def test_adds_to_recipient(self, db):
        db.transfer("alice", "bob", 200.0)
        assert db.get_account("bob").balance == 3_400.00

    def test_transaction_has_correct_fields(self, db):
        tx = db.transfer("alice", "bob", 123.45, "payment")
        assert isinstance(tx, Transaction)
        assert tx.from_user == "alice"
        assert tx.to_user == "bob"
        assert tx.amount == 123.45
        assert tx.description == "payment"
        assert tx.from_name == "Alice Johnson"
        assert tx.to_name == "Bob Smith"
        assert tx.tx_id.startswith("TXN-")

    def test_default_description_generated(self, db):
        tx = db.transfer("alice", "bob", 50.0)
        assert isinstance(tx, Transaction)
        assert "Bob Smith" in tx.description

    def test_balances_rounded_to_two_decimals(self, db):
        db.transfer("alice", "bob", 0.005)
        balance = db.get_account("alice").balance
        assert balance == round(balance, 2)

    def test_case_insensitive_user_ids(self, db):
        result = db.transfer("ALICE", "BOB", 100.0)
        assert isinstance(result, Transaction)


# ---------------------------------------------------------------------------
# transfer — error paths
# ---------------------------------------------------------------------------


class TestTransferErrors:
    def test_unknown_sender_returns_error_string(self, db):
        result = db.transfer("dave", "bob", 100.0)
        assert isinstance(result, str)
        assert "dave" in result

    def test_unknown_recipient_returns_error_string(self, db):
        result = db.transfer("alice", "dave", 100.0)
        assert isinstance(result, str)
        assert "dave" in result

    def test_self_transfer_rejected(self, db):
        result = db.transfer("alice", "alice", 100.0)
        assert isinstance(result, str)
        assert "own account" in result.lower()

    def test_zero_amount_rejected(self, db):
        result = db.transfer("alice", "bob", 0.0)
        assert isinstance(result, str)
        assert "greater than zero" in result.lower()

    def test_negative_amount_rejected(self, db):
        result = db.transfer("alice", "bob", -50.0)
        assert isinstance(result, str)

    def test_exceeds_100k_limit_rejected(self, db):
        result = db.transfer("alice", "bob", 100_001.0)
        assert isinstance(result, str)
        assert "100,000" in result

    def test_insufficient_funds_rejected(self, db):
        result = db.transfer("charlie", "alice", 10_000.0)
        assert isinstance(result, str)
        assert "insufficient" in result.lower()

    def test_balances_unchanged_on_error(self, db):
        alice_before = db.get_account("alice").balance
        db.transfer("alice", "dave", 100.0)  # unknown recipient
        assert db.get_account("alice").balance == alice_before


# ---------------------------------------------------------------------------
# transfer — listener callbacks
# ---------------------------------------------------------------------------


class TestTransferListeners:
    @pytest.mark.asyncio
    async def test_listener_called_after_successful_transfer(self, db):
        received = []

        async def listener(tx: Transaction, from_balance: float, to_balance: float):
            received.append((tx.from_user, tx.to_user, tx.amount, from_balance, to_balance))

        db.add_transfer_listener(listener)
        db.transfer("alice", "bob", 100.0)
        await asyncio.sleep(0.05)  # allow the scheduled task to run

        assert len(received) == 1
        uid_from, uid_to, amount, fb, tb = received[0]
        assert uid_from == "alice"
        assert uid_to == "bob"
        assert amount == 100.0
        assert fb == 4_900.00
        assert tb == 3_300.00

    @pytest.mark.asyncio
    async def test_listener_not_called_on_failed_transfer(self, db):
        received = []

        async def listener(tx, from_balance, to_balance):
            received.append(tx)

        db.add_transfer_listener(listener)
        db.transfer("alice", "unknown", 100.0)  # fails: unknown recipient
        await asyncio.sleep(0.05)

        assert received == []

    @pytest.mark.asyncio
    async def test_multiple_listeners_all_called(self, db):
        calls_a: list = []
        calls_b: list = []

        async def listener_a(tx, fb, tb):
            calls_a.append(tx.tx_id)

        async def listener_b(tx, fb, tb):
            calls_b.append(tx.tx_id)

        db.add_transfer_listener(listener_a)
        db.add_transfer_listener(listener_b)
        tx = db.transfer("alice", "bob", 50.0)
        await asyncio.sleep(0.05)

        assert len(calls_a) == 1 and calls_a[0] == tx.tx_id
        assert len(calls_b) == 1 and calls_b[0] == tx.tx_id

    @pytest.mark.asyncio
    async def test_listener_receives_post_transfer_balances(self, db):
        """Confirm that the listener sees updated (post-debit/credit) balances."""
        snapshots: list = []

        async def listener(tx, from_balance: float, to_balance: float):
            snapshots.append((from_balance, to_balance))

        db.add_transfer_listener(listener)
        db.transfer("alice", "bob", 500.0)
        await asyncio.sleep(0.05)

        assert len(snapshots) == 1
        from_bal, to_bal = snapshots[0]
        assert from_bal == 4_500.00
        assert to_bal == 3_700.00

    @pytest.mark.asyncio
    async def test_no_listeners_transfer_still_succeeds(self, db):
        result = db.transfer("alice", "bob", 1.0)
        assert isinstance(result, Transaction)
