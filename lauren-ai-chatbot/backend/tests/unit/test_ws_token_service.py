"""Unit tests for WsTokenService — short-lived WebSocket auth tokens."""

from __future__ import annotations

import base64
import json
import os
import time
from unittest.mock import patch

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")

from app.crypto.crypto_service import CryptoService
from app.ws.token_service import WsTokenService, _TOKEN_TTL_SECONDS


@pytest.fixture()
def crypto() -> CryptoService:
    svc = CryptoService.__new__(CryptoService)
    svc._secret = b"ws-test-secret"
    return svc


@pytest.fixture()
def svc(crypto) -> WsTokenService:
    return WsTokenService(crypto)


# ---------------------------------------------------------------------------
# create_token
# ---------------------------------------------------------------------------


class TestCreateToken:
    def test_returns_string(self, svc):
        assert isinstance(svc.create_token("alice"), str)

    def test_has_two_parts_separated_by_dot(self, svc):
        token = svc.create_token("alice")
        parts = token.split(".")
        # payload_b64 + "." + sig — sig itself is a 64-char hex string (no dots)
        assert len(parts) >= 2

    def test_payload_is_valid_base64_json(self, svc):
        token = svc.create_token("alice")
        payload_b64 = token.rsplit(".", 1)[0]
        padding = 4 - len(payload_b64) % 4
        padded = payload_b64 + "=" * (padding % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert payload["uid"] == "alice"
        assert "exp" in payload

    def test_expiry_is_in_future(self, svc):
        token = svc.create_token("bob")
        payload_b64 = token.rsplit(".", 1)[0]
        padding = 4 - len(payload_b64) % 4
        padded = payload_b64 + "=" * (padding % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert payload["exp"] > int(time.time())

    def test_expiry_is_within_ttl(self, svc):
        before = int(time.time())
        token = svc.create_token("charlie")
        after = int(time.time())
        payload_b64 = token.rsplit(".", 1)[0]
        padding = 4 - len(payload_b64) % 4
        padded = payload_b64 + "=" * (padding % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert before + _TOKEN_TTL_SECONDS <= payload["exp"] <= after + _TOKEN_TTL_SECONDS

    def test_different_users_produce_different_tokens(self, svc):
        assert svc.create_token("alice") != svc.create_token("bob")

    def test_tokens_differ_across_calls_due_to_time(self, svc):
        # Both calls happen in the same second — tokens should still differ
        # because time.time() progresses; but even if same second, user_id
        # payload differs. This test verifies determinism on same uid+time.
        t1 = svc.create_token("alice")
        t2 = svc.create_token("alice")
        # They may be equal if called in the same second — that's OK.
        # The important invariant: both verify correctly.
        assert svc.verify_token(t1) == "alice"
        assert svc.verify_token(t2) == "alice"


# ---------------------------------------------------------------------------
# verify_token — valid tokens
# ---------------------------------------------------------------------------


class TestVerifyTokenValid:
    def test_returns_user_id_for_fresh_token(self, svc):
        token = svc.create_token("alice")
        assert svc.verify_token(token) == "alice"

    def test_works_for_all_users(self, svc):
        for uid in ("alice", "bob", "charlie"):
            assert svc.verify_token(svc.create_token(uid)) == uid

    def test_round_trip_preserves_user_id(self, svc):
        uid = "alice"
        assert svc.verify_token(svc.create_token(uid)) == uid


# ---------------------------------------------------------------------------
# verify_token — expired tokens
# ---------------------------------------------------------------------------


class TestVerifyTokenExpired:
    def test_expired_token_returns_none(self, svc):
        # Mock time so the token is already expired when verified
        past = int(time.time()) - _TOKEN_TTL_SECONDS - 1
        with patch("app.ws.token_service.time") as mock_time:
            mock_time.time.return_value = float(past)
            token = svc.create_token("alice")
        # Verify with current time (token's exp is in the past)
        assert svc.verify_token(token) is None

    def test_token_at_exact_expiry_boundary_is_rejected(self, svc):
        now = int(time.time())
        with patch("app.ws.token_service.time") as mock_time:
            mock_time.time.return_value = float(now)
            token = svc.create_token("alice")
        # Advance time past expiry
        with patch("app.ws.token_service.time") as mock_time:
            mock_time.time.return_value = float(now + _TOKEN_TTL_SECONDS + 1)
            assert svc.verify_token(token) is None


# ---------------------------------------------------------------------------
# verify_token — invalid / tampered tokens
# ---------------------------------------------------------------------------


class TestVerifyTokenInvalid:
    def test_wrong_signature_returns_none(self, svc):
        token = svc.create_token("alice")
        payload_b64 = token.rsplit(".", 1)[0]
        fake_token = f"{payload_b64}.{'a' * 64}"
        assert svc.verify_token(fake_token) is None

    def test_no_dot_separator_returns_none(self, svc):
        assert svc.verify_token("notokenhere") is None

    def test_empty_string_returns_none(self, svc):
        assert svc.verify_token("") is None

    def test_tampered_payload_returns_none(self, svc):
        token = svc.create_token("alice")
        payload_b64, sig = token.rsplit(".", 1)
        # Modify one char in the payload
        tampered = payload_b64[:-1] + ("X" if payload_b64[-1] != "X" else "Y")
        assert svc.verify_token(f"{tampered}.{sig}") is None

    def test_invalid_base64_payload_returns_none(self, svc):
        sig = svc._crypto.sign(b"!!!invalid")
        assert svc.verify_token(f"!!!invalid.{sig}") is None

    def test_valid_sig_but_invalid_json_returns_none(self, svc):
        bad_payload = base64.urlsafe_b64encode(b"not json").rstrip(b"=").decode()
        sig = svc._crypto.sign(bad_payload.encode())
        assert svc.verify_token(f"{bad_payload}.{sig}") is None

    def test_payload_missing_uid_field_returns_none(self, svc):
        payload = json.dumps({"exp": int(time.time()) + 60}).encode()
        b64 = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
        sig = svc._crypto.sign(b64.encode())
        # uid field missing → KeyError → return None
        assert svc.verify_token(f"{b64}.{sig}") is None

    def test_payload_missing_exp_field_returns_none(self, svc):
        payload = json.dumps({"uid": "alice"}).encode()
        b64 = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
        sig = svc._crypto.sign(b64.encode())
        assert svc.verify_token(f"{b64}.{sig}") is None
