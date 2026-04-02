# #ai-assisted — generated with Claude and Codex LLM with human supervision.
"""Crypto unit tests."""

from __future__ import annotations

import pytest
from cryptography.fernet import InvalidToken

from encryptor import crypto


def test_roundtrip_encrypt_decrypt_bytes() -> None:
    key = crypto.generate_key()
    data = b"hello, encryptor"

    token = crypto.encrypt_bytes(data, key)
    decrypted = crypto.decrypt_bytes(token, key)

    assert decrypted == data


def test_wrong_key_rejection() -> None:
    key = crypto.generate_key()
    wrong = crypto.generate_key()
    data = b"bad key test"

    token = crypto.encrypt_bytes(data, key)
    with pytest.raises(InvalidToken):
        crypto.decrypt_bytes(token, wrong)


def test_tampered_token_rejection() -> None:
    key = crypto.generate_key()
    token = bytearray(crypto.encrypt_bytes(b"secret", key))
    token[0] ^= 0xFF

    with pytest.raises(InvalidToken):
        crypto.decrypt_bytes(bytes(token), key)


def test_passphrase_derivation_roundtrip() -> None:
    passphrase = "correct horse battery staple"
    salt = crypto.generate_salt()
    data = b"derived-secret"

    key = crypto.derive_key_from_passphrase(passphrase, salt)
    token = crypto.encrypt_bytes(data, key)
    out = crypto.decrypt_bytes(token, key)

    assert out == data
