"""CryptoService — HMAC-SHA256 payload signing and verification.

Every AI chat request must carry an ``X-Signature`` header whose value is
the hex-encoded HMAC-SHA256 of the raw request body, keyed with the shared
``PAYLOAD_SECRET`` environment variable.

The service is registered as a SINGLETON so the secret is read from the
environment exactly once at startup.
"""

import hashlib
import hmac
import os

from lauren import Scope, injectable


@injectable(scope=Scope.SINGLETON)
class CryptoService:
    """Signs and verifies request payloads using HMAC-SHA256."""

    def __init__(self) -> None:
        secret = os.environ.get("PAYLOAD_SECRET")
        if not secret:
            raise ValueError("Environment variable 'PAYLOAD_SECRET' is not set")
        self._secret: bytes = secret.encode("utf-8")

    def sign(self, data: bytes) -> str:
        """Return the hex HMAC-SHA256 digest of *data*."""
        return hmac.new(self._secret, data, hashlib.sha256).hexdigest()

    def verify(self, data: bytes, signature: str) -> bool:
        """Return ``True`` if *signature* matches the HMAC of *data*.

        Uses :func:`hmac.compare_digest` to prevent timing attacks.
        """
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)
