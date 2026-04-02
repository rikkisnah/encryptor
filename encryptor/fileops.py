# #ai-assisted — generated with Claude and Codex LLM with human supervision.
"""File and directory encryption/decryption operations."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Optional

from . import crypto

MAGIC = crypto.MAGIC
HEADER_SALT_SIZE = crypto.SALT_SIZE
ZERO_SALT: bytes = b"\x00" * HEADER_SALT_SIZE
MANIFEST_NAME = ".manifest"


def read_key_file(path: Path) -> bytes:
    return path.read_bytes()


def write_key_file(path: Path, key: bytes) -> None:
    path.write_bytes(key)
    try:
        path.chmod(0o600)
    except (PermissionError, OSError):
        pass


def _directory_output_path(source: Path, *, suffix: str) -> Path:
    return Path(str(source) + suffix)


def _iter_regular_files(base: Path):
    for root, _dirs, files in os.walk(base, topdown=True, followlinks=False):
        for file_name in files:
            source = Path(root) / file_name
            if source.is_symlink():
                continue
            yield source


def encrypt_data(
    data: bytes,
    *,
    key: Optional[bytes] = None,
    passphrase: Optional[str] = None,
    salt: Optional[bytes] = None,
) -> bytes:
    """Encrypt bytes and wrap into the file payload format."""
    if key is not None and passphrase is not None:
        raise ValueError("provide only one of key or passphrase")
    if key is None and passphrase is None:
        raise ValueError("key or passphrase is required")

    if key is not None:
        token = crypto.encrypt_bytes(data, key)
        return MAGIC + ZERO_SALT + token

    assert passphrase is not None
    derived_salt = salt if salt is not None else crypto.generate_salt()
    derived_key = crypto.derive_key_from_passphrase(passphrase, derived_salt)
    token = crypto.encrypt_bytes(data, derived_key)
    return MAGIC + derived_salt + token


def decrypt_data(
    payload: bytes,
    *,
    key: Optional[bytes] = None,
    passphrase: Optional[str] = None,
) -> bytes:
    """Validate header and decrypt payload into plain bytes."""
    min_len = len(MAGIC) + HEADER_SALT_SIZE + 1
    if len(payload) < min_len:
        raise ValueError("corrupt encrypted payload")

    if payload[: len(MAGIC)] != MAGIC:
        raise ValueError("invalid encrypted payload header")

    salt = payload[len(MAGIC) : len(MAGIC) + HEADER_SALT_SIZE]
    token = payload[len(MAGIC) + HEADER_SALT_SIZE :]

    if salt == ZERO_SALT:
        if key is None:
            raise ValueError("key is required when payload was encrypted with a key file")
        return crypto.decrypt_bytes(token, key)

    if passphrase is None:
        raise ValueError("passphrase is required when payload was encrypted with a passphrase")

    derived_key = crypto.derive_key_from_passphrase(passphrase, salt)
    return crypto.decrypt_bytes(token, derived_key)


def encrypt_file(
    source: Path,
    destination: Path,
    *,
    key: Optional[bytes] = None,
    passphrase: Optional[str] = None,
) -> None:
    """Encrypt a single file."""
    data = source.read_bytes()
    payload = encrypt_data(data, key=key, passphrase=passphrase)
    destination.write_bytes(payload)


def decrypt_file(
    source: Path,
    destination: Path,
    *,
    key: Optional[bytes] = None,
    passphrase: Optional[str] = None,
) -> None:
    """Decrypt a single file."""
    payload = source.read_bytes()
    data = decrypt_data(payload, key=key, passphrase=passphrase)
    destination.write_bytes(data)


def _random_hex_name() -> str:
    """Generate a random 16-char hex string for obfuscated filenames."""
    return secrets.token_hex(8)


def encrypt_directory(
    source: Path,
    destination: Optional[Path] = None,
    *,
    key: Optional[bytes] = None,
    passphrase: Optional[str] = None,
) -> Path:
    """Encrypt a directory into a flat structure with obfuscated names.

    All files are encrypted into random hex-named files in a flat output
    directory.  An encrypted manifest (``.manifest``) maps each random
    name back to its original relative path so ``decrypt_directory`` can
    restore the original structure.
    """
    source_path = source.resolve()
    if not source_path.is_dir():
        raise ValueError("source must be a directory")

    destination_dir = destination or _directory_output_path(source_path, suffix=".enc")
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, str] = {}

    for source_file in _iter_regular_files(source_path):
        rel = source_file.relative_to(source_path)
        random_name = _random_hex_name()
        target = destination_dir / random_name
        encrypt_file(source_file, target, key=key, passphrase=passphrase)
        manifest[random_name] = str(rel)

    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_payload = encrypt_data(manifest_bytes, key=key, passphrase=passphrase)
    (destination_dir / MANIFEST_NAME).write_bytes(manifest_payload)

    return destination_dir


def decrypt_directory(
    source: Path,
    destination: Optional[Path] = None,
    *,
    key: Optional[bytes] = None,
    passphrase: Optional[str] = None,
) -> Path:
    """Decrypt a directory previously created by ``encrypt_directory``.

    Reads the encrypted manifest to restore the original directory
    structure and filenames.
    """
    source_path = source.resolve()
    if not source_path.is_dir():
        raise ValueError("source must be a directory")

    manifest_file = source_path / MANIFEST_NAME
    if not manifest_file.exists():
        raise ValueError("missing .manifest — directory was not encrypted by encryptor")

    manifest_payload = manifest_file.read_bytes()
    manifest_bytes = decrypt_data(manifest_payload, key=key, passphrase=passphrase)
    manifest: dict[str, str] = json.loads(manifest_bytes.decode("utf-8"))

    destination_dir = destination or _directory_output_path(source_path, suffix=".dec")
    destination_dir = Path(destination_dir)

    for random_name, original_rel in manifest.items():
        source_file = source_path / random_name
        target = destination_dir / original_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        decrypt_file(source_file, target, key=key, passphrase=passphrase)

    return destination_dir
