<!--
#ai-assisted
Code was generated with Claude and Codex LLM with human supervision.
Tag: #ai-assisted
-->

# Encryptor — Project Plan (Claude)

## Overview

A Python CLI tool that encrypts and decrypts files, directories, and text using symmetric key cryptography.

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.9+ | Already available, matches workspace venv |
| Crypto library | `cryptography` (Fernet / AES-256-CBC-HMAC) | Installed (`41.0.5`), high-level safe API, OWASP-recommended, fast via OpenSSL backend |
| CLI framework | `argparse` (stdlib) | Zero dependencies, sufficient for this scope |
| Testing | `pytest` + `pytest-cov` | De facto standard, easy 100% coverage reporting |
| Linting / formatting | `ruff` | Fast, single tool for lint + format |
| Packaging | `pyproject.toml` (PEP 621) | Modern standard, no `setup.py` needed |

### Why Fernet (AES-256-CBC + HMAC-SHA256)?

- **Secure**: Authenticated encryption — tampered ciphertext is rejected before decryption.
- **Fast**: Backed by OpenSSL's AES implementation (hardware-accelerated on most CPUs).
- **Simple**: Single `encrypt()`/`decrypt()` API eliminates nonce/IV/padding foot-guns.
- **Key derivation**: Use PBKDF2-HMAC-SHA256 (100k+ iterations) to derive a Fernet key from a user-supplied passphrase, with a random salt stored alongside the ciphertext.

## Project Structure

```
encryptor/
├── pyproject.toml          # Project metadata, dependencies, scripts entry point
├── src/
│   └── encryptor/
│       ├── __init__.py     # Package version
│       ├── cli.py          # argparse CLI entry point
│       ├── crypto.py       # Key derivation, encrypt/decrypt primitives
│       └── fileops.py      # File/directory traversal, read/write helpers
├── tests/
│   ├── conftest.py         # Shared fixtures (tmp dirs, sample files)
│   ├── test_crypto.py      # Unit tests for crypto module
│   ├── test_fileops.py     # Unit tests for file operations
│   └── test_cli.py         # Integration tests for CLI
├── instructions.md
├── encryptor-claude.md     # This plan
├── CLAUDE.md
├── AGENTS.md -> CLAUDE.md
├── README.md
└── LICENSE
```

## CLI Interface Design

```
encryptor <command> [options]

Commands:
  encrypt     Encrypt a file, directory, or text
  decrypt     Decrypt a file, directory, or text
  keygen      Generate a new random key file

Common options:
  -k, --key <file>       Path to key file
  -p, --passphrase       Prompt for passphrase (derived into key via PBKDF2)
  -o, --output <path>    Output path (default: <input>.enc / <input>.dec)

Examples:
  encryptor keygen -o my.key
  encryptor encrypt -k my.key secret.txt
  encryptor encrypt -p -o encrypted/ docs/
  encryptor decrypt -k my.key secret.txt.enc
  echo "hello" | encryptor encrypt -p          # stdin/stdout text mode
```

## Encrypted File Format

```
[4 bytes]  magic: "ENC\x01"      — identifies file + format version
[16 bytes] salt                   — random, for PBKDF2 key derivation
[N bytes]  Fernet token           — ciphertext (self-contained: IV + AES-CBC + HMAC)
```

When using a key file directly (no passphrase), the salt field is zeroed and ignored.

## Implementation Phases

### Phase 1 — Core crypto module (`crypto.py`)
- Key generation (random Fernet key)
- Passphrase-to-key derivation (PBKDF2 + salt)
- `encrypt_bytes(data, key) -> ciphertext`
- `decrypt_bytes(ciphertext, key) -> data`
- Tests: round-trip, wrong key rejection, tampered ciphertext rejection

### Phase 2 — File operations (`fileops.py`)
- Single file encrypt/decrypt (read → encrypt → write with format header)
- Directory encrypt/decrypt (recursive walk, preserve structure)
- Stdin/stdout streaming for text mode
- Tests: temp files, nested dirs, symlink handling, large files

### Phase 3 — CLI (`cli.py`)
- Argument parsing and validation
- Passphrase prompt (via `getpass`)
- Error messages and exit codes
- Tests: subprocess-based integration tests covering all commands

### Phase 4 — Polish
- `pyproject.toml` with `[project.scripts]` entry point
- 100% test coverage gate
- README with usage examples
- Ruff lint/format clean

## Security Considerations

- Never log or print keys/passphrases.
- Use `os.urandom()` for all randomness (CSPRNG).
- Overwrite key material in memory where feasible (`del` + gc).
- Reject decryption of tampered data (Fernet does this automatically).
- Key files should be created with `0o600` permissions.

## Dependencies

**Runtime:**
- `cryptography` (already installed)

**Dev:**
- `pytest`
- `pytest-cov`
- `ruff`
