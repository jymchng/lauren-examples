"""Unit tests for CryptoService — HMAC-SHA256 payload signing and verification."""

import hashlib
import hmac
import os

import pytest

from app.crypto.crypto_service import CryptoService

SECRET = "test-secret-abc123"


@pytest.fixture()
def svc() -> CryptoService:
    os.environ["PAYLOAD_SECRET"] = SECRET
    return CryptoService()


class TestSign:
    def test_returns_hex_string(self, svc: CryptoService):
        sig = svc.sign(b"hello")
        assert isinstance(sig, str)
        assert all(c in "0123456789abcdef" for c in sig)

    def test_length_is_64_hex_chars(self, svc: CryptoService):
        # SHA-256 produces 32 bytes = 64 hex chars
        assert len(svc.sign(b"hello")) == 64

    def test_deterministic_for_same_input(self, svc: CryptoService):
        assert svc.sign(b"data") == svc.sign(b"data")

    def test_different_for_different_input(self, svc: CryptoService):
        assert svc.sign(b"data-a") != svc.sign(b"data-b")

    def test_empty_bytes_produces_valid_hmac(self, svc: CryptoService):
        sig = svc.sign(b"")
        expected = hmac.new(SECRET.encode(), b"", hashlib.sha256).hexdigest()
        assert sig == expected

    def test_matches_stdlib_hmac(self, svc: CryptoService):
        data = b'{"messages":[{"role":"user","content":"hi"}]}'
        expected = hmac.new(SECRET.encode(), data, hashlib.sha256).hexdigest()
        assert svc.sign(data) == expected

    def test_large_payload(self, svc: CryptoService):
        data = b"x" * 100_000
        sig = svc.sign(data)
        assert len(sig) == 64


class TestVerify:
    def test_valid_signature_returns_true(self, svc: CryptoService):
        data = b"payload"
        sig = svc.sign(data)
        assert svc.verify(data, sig) is True

    def test_wrong_signature_returns_false(self, svc: CryptoService):
        assert svc.verify(b"payload", "deadbeef" * 8) is False

    def test_tampered_data_returns_false(self, svc: CryptoService):
        data = b"original"
        sig = svc.sign(data)
        assert svc.verify(b"tampered", sig) is False

    def test_empty_signature_returns_false(self, svc: CryptoService):
        assert svc.verify(b"data", "") is False

    def test_partial_signature_returns_false(self, svc: CryptoService):
        data = b"hello"
        full_sig = svc.sign(data)
        assert svc.verify(data, full_sig[:32]) is False

    def test_signature_case_sensitive(self, svc: CryptoService):
        data = b"hello"
        sig = svc.sign(data)
        # Flip one hex char's case — hmac.compare_digest is byte-level
        flipped = sig[:-1] + ("A" if sig[-1].islower() else "a")
        # The flipped version should NOT match (different hex string)
        assert svc.verify(data, flipped) is not svc.verify(data, sig)

    def test_different_secrets_produce_different_sigs(self):
        svc_a = CryptoService.__new__(CryptoService)
        svc_a._secret = b"secret-a"
        svc_b = CryptoService.__new__(CryptoService)
        svc_b._secret = b"secret-b"
        data = b"same data"
        assert svc_a.sign(data) != svc_b.sign(data)
        assert svc_a.verify(data, svc_b.sign(data)) is False

    def test_unicode_secret_encoded_utf8(self):
        os.environ["PAYLOAD_SECRET"] = "café-secret"
        svc = CryptoService()
        data = b"test"
        sig = svc.sign(data)
        assert svc.verify(data, sig) is True

    def test_verify_uses_compare_digest_timing_safe(self, svc: CryptoService):
        """Verify calls hmac.compare_digest (not ==) to resist timing attacks."""
        import unittest.mock as mock
        data = b"hello"
        correct_sig = svc.sign(data)
        with mock.patch("hmac.compare_digest", wraps=hmac.compare_digest) as mocked:
            result = svc.verify(data, correct_sig)
            mocked.assert_called_once()
        assert result is True

    def test_json_payload_roundtrip(self, svc: CryptoService):
        import json
        payload = json.dumps(
            {"messages": [{"role": "user", "content": "hello"}], "model": "gpt-4o-mini"}
        ).encode()
        sig = svc.sign(payload)
        assert svc.verify(payload, sig) is True
        assert svc.verify(payload + b" ", sig) is False
