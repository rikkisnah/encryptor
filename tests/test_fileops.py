# #ai-assisted — generated with Claude and Codex LLM with human supervision.
"""File and directory operation tests."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from cryptography.fernet import InvalidToken

from encryptor import crypto, fileops

# -- key file I/O ----------------------------------------------------------


def test_write_and_read_key_file(tmp_path: Path) -> None:
    key = crypto.generate_key()
    key_path = tmp_path / "test.key"
    fileops.write_key_file(key_path, key)
    assert key_path.stat().st_mode & 0o777 == 0o600
    assert fileops.read_key_file(key_path) == key


def test_write_key_file_chmod_failure(tmp_path: Path) -> None:
    key = crypto.generate_key()
    key_path = tmp_path / "test.key"
    with mock.patch.object(Path, "chmod", side_effect=OSError("no chmod")):
        fileops.write_key_file(key_path, key)
    assert key_path.read_bytes() == key


# -- encrypt_data / decrypt_data ------------------------------------------


def test_encrypt_data_with_key_roundtrip() -> None:
    key = crypto.generate_key()
    payload = fileops.encrypt_data(b"hello", key=key)
    assert payload.startswith(crypto.MAGIC)
    assert payload[4:20] == b"\x00" * 16  # zero salt for key mode
    assert fileops.decrypt_data(payload, key=key) == b"hello"


def test_encrypt_data_with_passphrase_roundtrip() -> None:
    payload = fileops.encrypt_data(b"secret", passphrase="pw")
    assert payload.startswith(crypto.MAGIC)
    assert payload[4:20] != b"\x00" * 16  # real salt
    assert fileops.decrypt_data(payload, passphrase="pw") == b"secret"


def test_encrypt_data_both_key_and_passphrase_raises() -> None:
    with pytest.raises(ValueError, match="only one"):
        fileops.encrypt_data(b"x", key=b"k", passphrase="p")


def test_encrypt_data_neither_key_nor_passphrase_raises() -> None:
    with pytest.raises(ValueError, match="required"):
        fileops.encrypt_data(b"x")


def test_decrypt_data_corrupt_payload() -> None:
    with pytest.raises(ValueError, match="corrupt"):
        fileops.decrypt_data(b"short")


def test_decrypt_data_invalid_header() -> None:
    with pytest.raises(ValueError, match="invalid"):
        fileops.decrypt_data(b"BAAD" + b"\x00" * 20)


def test_decrypt_data_zero_salt_requires_key() -> None:
    key = crypto.generate_key()
    payload = fileops.encrypt_data(b"x", key=key)
    with pytest.raises(ValueError, match="key is required"):
        fileops.decrypt_data(payload, passphrase="nope")


def test_decrypt_data_real_salt_requires_passphrase() -> None:
    payload = fileops.encrypt_data(b"x", passphrase="pw")
    key = crypto.generate_key()
    with pytest.raises(ValueError, match="passphrase is required"):
        fileops.decrypt_data(payload, key=key)


# -- single file encrypt / decrypt ----------------------------------------


def test_encrypt_decrypt_file_with_key(tmp_path: Path) -> None:
    data = b"plaintext"
    in_path = tmp_path / "plain.txt"
    in_path.write_bytes(data)

    out_path = tmp_path / "plain.txt.enc"
    dec_path = tmp_path / "plain.txt.dec"

    key = crypto.generate_key()
    fileops.encrypt_file(in_path, out_path, key=key)
    fileops.decrypt_file(out_path, dec_path, key=key)
    assert dec_path.read_bytes() == data


def test_encrypt_decrypt_file_with_passphrase(tmp_path: Path) -> None:
    data = b"important secrets"
    in_path = tmp_path / "in.bin"
    in_path.write_bytes(data)

    out_path = tmp_path / "in.bin.enc"
    dec_path = tmp_path / "in.bin.dec"

    fileops.encrypt_file(in_path, out_path, passphrase="test-passphrase")
    fileops.decrypt_file(out_path, dec_path, passphrase="test-passphrase")
    assert dec_path.read_bytes() == data


def test_wrong_passphrase_rejected(tmp_path: Path) -> None:
    in_path = tmp_path / "in.bin"
    in_path.write_bytes(b"abc")
    enc = tmp_path / "in.bin.enc"
    out = tmp_path / "in.bin.dec"

    fileops.encrypt_file(in_path, enc, passphrase="right")
    with pytest.raises(InvalidToken):
        fileops.decrypt_file(enc, out, passphrase="wrong")


# -- directory encrypt / decrypt -------------------------------------------


def test_directory_roundtrip_and_symlink_is_skipped(tmp_path: Path) -> None:
    root = tmp_path / "src"
    nested = root / "nested"
    nested.mkdir(parents=True)

    (root / "a.txt").write_text("A")
    (nested / "b.txt").write_text("B")
    target = tmp_path / "real.txt"
    target.write_text("secret")
    (root / "link.txt").symlink_to(target)

    key = crypto.generate_key()
    enc_root = tmp_path / "enc"
    dec_root = tmp_path / "dec"

    encrypted_root = fileops.encrypt_directory(root, enc_root, key=key)
    assert encrypted_root == enc_root

    # Output is flat with random hex names — no original names visible
    enc_files = [f.name for f in enc_root.iterdir() if f.name != ".manifest"]
    assert len(enc_files) == 2  # a.txt + nested/b.txt, symlink skipped
    for name in enc_files:
        assert len(name) == 16  # hex names
        assert "a.txt" not in name
        assert "b.txt" not in name
    assert not any("nested" in str(f) for f in enc_root.rglob("*"))

    # Manifest exists
    assert (enc_root / ".manifest").exists()

    # Round-trip restores original structure
    fileops.decrypt_directory(encrypted_root, dec_root, key=key)
    assert (dec_root / "a.txt").read_text() == "A"
    assert (dec_root / "nested" / "b.txt").read_text() == "B"
    # Symlink was not encrypted so it is not restored
    assert not (dec_root / "link.txt").exists()


def test_directory_names_are_obfuscated(tmp_path: Path) -> None:
    """Encrypted output must not contain any original filenames or dir names."""
    root = tmp_path / "confidential_project"
    (root / "secret_docs").mkdir(parents=True)
    (root / "passwords.txt").write_text("admin:hunter2")
    (root / "secret_docs" / "keys.pem").write_text("PRIVATE KEY")

    key = crypto.generate_key()
    enc_root = fileops.encrypt_directory(root, key=key)

    # No original names anywhere in the encrypted directory
    all_names = [f.name for f in enc_root.rglob("*")]
    for name in all_names:
        if name == ".manifest":
            continue
        assert "confidential" not in name
        assert "secret" not in name
        assert "passwords" not in name
        assert "keys" not in name
        assert "pem" not in name

    # Structure is flat (no subdirectories)
    assert not any(f.is_dir() for f in enc_root.iterdir())


def test_directory_default_output_paths(tmp_path: Path) -> None:
    src = tmp_path / "mydir"
    src.mkdir()
    (src / "f.txt").write_text("data")

    key = crypto.generate_key()
    enc_dir = fileops.encrypt_directory(src, key=key)
    assert enc_dir == Path(str(src.resolve()) + ".enc")

    dec_dir = fileops.decrypt_directory(enc_dir, key=key)
    assert dec_dir == Path(str(enc_dir.resolve()) + ".dec")
    assert (dec_dir / "f.txt").read_text() == "data"


def test_encrypt_directory_not_a_dir_raises(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(ValueError, match="directory"):
        fileops.encrypt_directory(f, key=crypto.generate_key())


def test_decrypt_directory_not_a_dir_raises(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(ValueError, match="directory"):
        fileops.decrypt_directory(f, key=crypto.generate_key())


def test_decrypt_directory_missing_manifest_raises(tmp_path: Path) -> None:
    """Decrypting a dir without .manifest must fail clearly."""
    src = tmp_path / "no_manifest"
    src.mkdir()
    (src / "somefile").write_bytes(b"data")
    with pytest.raises(ValueError, match="missing .manifest"):
        fileops.decrypt_directory(src, key=crypto.generate_key())


def test_directory_roundtrip_with_passphrase(tmp_path: Path) -> None:
    root = tmp_path / "src"
    root.mkdir()
    (root / "doc.txt").write_text("hello")

    enc = tmp_path / "enc"
    dec = tmp_path / "dec"

    fileops.encrypt_directory(root, enc, passphrase="mypass")
    fileops.decrypt_directory(enc, dec, passphrase="mypass")
    assert (dec / "doc.txt").read_text() == "hello"


def test_large_file_roundtrip(tmp_path: Path) -> None:
    payload = b"x" * (1024 * 1024)
    source = tmp_path / "big.bin"
    source.write_bytes(payload)

    encrypted = tmp_path / "big.bin.enc"
    decrypted = tmp_path / "big.bin.dec"
    key = crypto.generate_key()

    fileops.encrypt_file(source, encrypted, key=key)
    fileops.decrypt_file(encrypted, decrypted, key=key)
    assert decrypted.read_bytes() == payload
