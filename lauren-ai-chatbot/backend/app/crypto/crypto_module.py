"""CryptoModule — provides CryptoService and SignatureGuard for import by other modules."""

from lauren import module

from app.crypto.crypto_service import CryptoService
from app.crypto.signature_guard import SignatureGuard


@module(providers=[CryptoService, SignatureGuard], exports=[CryptoService, SignatureGuard])
class CryptoModule:
    pass
