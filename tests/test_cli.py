# #ai-assisted — generated with Claude and Codex LLM with human supervision.
"""CLI tests — in-process calls to run() for coverage."""

from __future__ import annotations

import io
from pathlib import Path
from unittest import mock

import pytest

from encryptor import crypto
from encryptor.cli import main, run

# -- keygen ----------------------------------------------------------------


def test_keygen_creates_key_file(tmp_path: Path) -> None:
    key_file = tmp_path / "my.key"
    rc = run(["keygen", "-o", str(key_file)])
    assert rc == 0
    assert len(key_file.read_bytes()) == 44
    assert key_file.stat().st_mode & 0o777 == 0o600


# -- encrypt / decrypt file with key --------------------------------------


def test_encrypt_decrypt_file_with_key(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())

    source = tmp_path / "in.txt"
    source.write_text("hello")
    enc = tmp_path / "in.txt.enc"
    dec = tmp_path / "in.txt.dec"

    assert run(["encrypt", "-k", str(key_file), "-o", str(enc), str(source)]) == 0
    assert run(["decrypt", "-k", str(key_file), "-o", str(dec), str(enc)]) == 0
    assert dec.read_text() == "hello"


def test_encrypt_decrypt_file_default_output(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())

    source = tmp_path / "doc.txt"
    source.write_text("auto-output")

    assert run(["encrypt", "-k", str(key_file), str(source)]) == 0
    enc = tmp_path / "doc.txt.enc"
    assert enc.exists()

    assert run(["decrypt", "-k", str(key_file), str(enc)]) == 0
    dec = tmp_path / "doc.txt.enc.dec"
    assert dec.read_text() == "auto-output"


# -- encrypt / decrypt stdin/stdout with key -------------------------------


def test_encrypt_decrypt_stdin_stdout_with_key(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())

    stdin_data = b"stdin payload"
    enc_buf = io.BytesIO()

    with mock.patch("sys.stdin", new=mock.Mock(buffer=io.BytesIO(stdin_data))):
        with mock.patch("sys.stdout", new=mock.Mock(buffer=enc_buf)):
            assert run(["encrypt", "-k", str(key_file)]) == 0

    encrypted = enc_buf.getvalue()
    assert encrypted.startswith(crypto.MAGIC)

    dec_buf = io.BytesIO()
    with mock.patch("sys.stdin", new=mock.Mock(buffer=io.BytesIO(encrypted))):
        with mock.patch("sys.stdout", new=mock.Mock(buffer=dec_buf)):
            assert run(["decrypt", "-k", str(key_file)]) == 0

    assert dec_buf.getvalue() == stdin_data


def test_encrypt_stdin_to_file(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())
    out = tmp_path / "enc.bin"

    with mock.patch("sys.stdin", new=mock.Mock(buffer=io.BytesIO(b"file-out"))):
        assert run(["encrypt", "-k", str(key_file), "-o", str(out)]) == 0

    assert out.exists()

    dec_out = tmp_path / "dec.bin"
    with mock.patch("sys.stdin", new=mock.Mock(buffer=io.BytesIO(out.read_bytes()))):
        assert run(["decrypt", "-k", str(key_file), "-o", str(dec_out)]) == 0

    assert dec_out.read_bytes() == b"file-out"


# -- encrypt / decrypt with passphrase ------------------------------------


def test_encrypt_decrypt_file_with_passphrase(tmp_path: Path) -> None:
    source = tmp_path / "secret.txt"
    source.write_text("classified")
    enc = tmp_path / "secret.txt.enc"
    dec = tmp_path / "secret.txt.dec"

    with mock.patch("getpass.getpass", return_value="mypass"):
        assert run(["encrypt", "-p", "-o", str(enc), str(source)]) == 0
    with mock.patch("getpass.getpass", return_value="mypass"):
        assert run(["decrypt", "-p", "-o", str(dec), str(enc)]) == 0

    assert dec.read_text() == "classified"


# -- directory encrypt / decrypt -------------------------------------------


def test_directory_encrypt_decrypt_with_key(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())

    src = tmp_path / "input"
    (src / "a").mkdir(parents=True)
    (src / "a" / "b.txt").write_text("one")
    (src / "c.txt").write_text("two")

    enc_dir = tmp_path / "enc_dir"
    dec_dir = tmp_path / "dec_dir"

    assert run(["encrypt", "-k", str(key_file), "-o", str(enc_dir), str(src)]) == 0
    assert run(["decrypt", "-k", str(key_file), "-o", str(dec_dir), str(enc_dir)]) == 0

    assert (dec_dir / "a" / "b.txt").read_text() == "one"
    assert (dec_dir / "c.txt").read_text() == "two"


def test_directory_default_output(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())

    src = tmp_path / "mydir"
    src.mkdir()
    (src / "f.txt").write_text("data")

    assert run(["encrypt", "-k", str(key_file), str(src)]) == 0
    enc_dir = Path(str(src) + ".enc")
    assert enc_dir.is_dir()

    assert run(["decrypt", "-k", str(key_file), str(enc_dir)]) == 0
    dec_dir = Path(str(enc_dir) + ".dec")
    assert (dec_dir / "f.txt").read_text() == "data"


# -- error paths -----------------------------------------------------------


def test_wrong_key_fails(tmp_path: Path) -> None:
    key_file = tmp_path / "good.key"
    bad_key = tmp_path / "bad.key"
    key_file.write_bytes(crypto.generate_key())
    bad_key.write_bytes(crypto.generate_key())

    source = tmp_path / "in.bin"
    source.write_bytes(b"z")
    enc = tmp_path / "in.bin.enc"

    assert run(["encrypt", "-k", str(key_file), "-o", str(enc), str(source)]) == 0
    rc = run(["decrypt", "-k", str(bad_key), "-o", str(tmp_path / "out.bin"), str(enc)])
    assert rc == 1


def test_encrypt_missing_file(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())
    rc = run(["encrypt", "-k", str(key_file), str(tmp_path / "nope.txt")])
    assert rc == 1


def test_decrypt_missing_file(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    key_file.write_bytes(crypto.generate_key())
    rc = run(["decrypt", "-k", str(key_file), str(tmp_path / "nope.txt")])
    assert rc == 1


def test_no_command_exits_error() -> None:
    with pytest.raises(SystemExit):
        run([])


def test_mutually_exclusive_key_passphrase() -> None:
    with pytest.raises(SystemExit):
        run(["encrypt", "-k", "x", "-p", "file.txt"])


# -- main() wrapper --------------------------------------------------------


def test_main_success(tmp_path: Path) -> None:
    key_file = tmp_path / "k.key"
    with pytest.raises(SystemExit) as exc_info:
        main(["keygen", "-o", str(key_file)])
    assert exc_info.value.code == 0


def test_main_failure() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["encrypt", "-k", "/nonexistent.key", "/nonexistent.txt"])
    assert exc_info.value.code == 1
