# #ai-assisted — generated with Claude and Codex LLM with human supervision.
"""CLI entrypoint for encryptor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from cryptography.fernet import InvalidToken

from . import crypto, fileops


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="encryptor",
        description="Encrypt and decrypt files and directories",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    keygen = subparsers.add_parser("keygen", help="generate a new key file")
    keygen.add_argument("-o", "--output", required=True, help="output key file")

    encrypt = subparsers.add_parser("encrypt", help="encrypt file, directory, or stdin data")
    _add_crypto_options(encrypt)
    _add_target_argument(encrypt)

    decrypt = subparsers.add_parser("decrypt", help="decrypt file, directory, or stdin data")
    _add_crypto_options(decrypt)
    _add_target_argument(decrypt)

    return parser


def _add_crypto_options(parser: argparse.ArgumentParser) -> None:
    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument("-k", "--key", help="path to key file")
    auth.add_argument("-p", "--passphrase", action="store_true", help="prompt for passphrase")
    parser.add_argument("-o", "--output", help="output path")


def _add_target_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "path",
        nargs="?",
        help="input file/directory, omitted for stdin/stdout mode",
    )


def _read_credentials(args: argparse.Namespace):
    if args.key is not None:
        return fileops.read_key_file(Path(args.key)), None

    import getpass

    return None, getpass.getpass("Passphrase: ")


def _output_for_file(path: Path, mode: str) -> Path:
    suffix = ".enc" if mode == "encrypt" else ".dec"
    return path.with_suffix(path.suffix + suffix)


def _output_directory(path: Path, destination: Optional[str], mode: str) -> Path:
    if destination:
        return Path(destination)
    return Path(str(path) + (".enc" if mode == "encrypt" else ".dec"))


def _ensure_path_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"path not found: {path}")


def do_encrypt(args: argparse.Namespace) -> None:
    key, passphrase = _read_credentials(args)

    if args.path is None:
        data = sys.stdin.buffer.read()
        encrypted = fileops.encrypt_data(data, key=key, passphrase=passphrase)
        if args.output is None:
            sys.stdout.buffer.write(encrypted)
        else:
            Path(args.output).write_bytes(encrypted)
        return

    source = Path(args.path)
    _ensure_path_exists(source)

    if source.is_dir():
        dest = _output_directory(source, args.output, "encrypt")
        fileops.encrypt_directory(
            source,
            destination=dest,
            key=key,
            passphrase=passphrase,
        )
        return

    output = Path(args.output) if args.output else _output_for_file(source, "encrypt")
    fileops.encrypt_file(source, output, key=key, passphrase=passphrase)


def do_decrypt(args: argparse.Namespace) -> None:
    key, passphrase = _read_credentials(args)

    if args.path is None:
        encrypted = sys.stdin.buffer.read()
        data = fileops.decrypt_data(encrypted, key=key, passphrase=passphrase)
        if args.output is None:
            sys.stdout.buffer.write(data)
        else:
            Path(args.output).write_bytes(data)
        return

    source = Path(args.path)
    _ensure_path_exists(source)

    if source.is_dir():
        dest = _output_directory(source, args.output, "decrypt")
        fileops.decrypt_directory(
            source,
            destination=dest,
            key=key,
            passphrase=passphrase,
        )
        return

    output = Path(args.output) if args.output else _output_for_file(source, "decrypt")
    fileops.decrypt_file(source, output, key=key, passphrase=passphrase)


def do_keygen(args: argparse.Namespace) -> None:
    key = crypto.generate_key()
    fileops.write_key_file(Path(args.output), key)


def run(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "encrypt":
            do_encrypt(args)
        elif args.command == "decrypt":
            do_decrypt(args)
        elif args.command == "keygen":
            do_keygen(args)
    except (FileNotFoundError, ValueError, InvalidToken, OSError) as exc:
        print(f"encryptor: {exc}", file=sys.stderr)
        return 1

    return 0


def main(argv: Optional[list[str]] = None) -> None:
    raise SystemExit(run(argv))


if __name__ == "__main__":  # pragma: no cover
    main()
