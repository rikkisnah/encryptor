# #ai-assisted — generated with Claude and Codex LLM with human supervision.
"""Cryptographic primitives used by the Encryptor CLI."""

from __future__ import annotations

import base64
import os
from typing import Final

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC: Final = b"ENC\x01"
SALT_SIZE: Final = 16
PBKDF2_ITERATIONS: Final = 200_000


def generate_key() -> bytes:
    """Generate a fresh Fernet-compatible key."""
    return Fernet.generate_key()


def derive_key_from_passphrase(
    passphrase: str | bytes,
    salt: bytes,
    *,
    iterations: int = PBKDF2_ITERATIONS,
) -> bytes:
    """Derive a Fernet key from a passphrase and salt using PBKDF2-HMAC-SHA256."""
    passphrase_bytes = passphrase if isinstance(passphrase, bytes) else passphrase.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=None,
    )
    raw_key = kdf.derive(passphrase_bytes)
    return base64.urlsafe_b64encode(raw_key)


def generate_salt() -> bytes:
    """Generate cryptographically random salt."""
    return os.urandom(SALT_SIZE)


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    """Encrypt bytes with a Fernet key."""
    return Fernet(key).encrypt(data)


def decrypt_bytes(token: bytes, key: bytes) -> bytes:
    """Decrypt bytes previously returned by :func:`encrypt_bytes`."""
    return Fernet(key).decrypt(token)
