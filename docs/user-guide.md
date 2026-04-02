<!--
#ai-assisted
Code was generated with Claude and Codex LLM with human supervision.
Tag: #ai-assisted
-->

# Encryptor User Guide

Encryptor is a command-line tool for encrypting and decrypting files,
directories, and text using Fernet (AES-256-CBC + HMAC-SHA256).

## Installation

### Option 1 — Project-local development (preferred)

```bash
git clone <repo-url> && cd encryptor
make install        # uses uv sync, creates .venv/
uv run encryptor --help
```

Uses `uv run encryptor` from the project directory.

### Option 2 — Install into shared venv (optional)

Install once, use `encryptor` from any directory:

```bash
cd /Users/rkisnah/src/rikkisnah/encryptor
source ~/.venvs/rikkisnah/bin/activate
pip install -e .
```

Run it directly without activating the venv:

```bash
~/.venvs/rikkisnah/bin/encryptor --help
~/.venvs/rikkisnah/bin/encryptor keygen -o my.key
```

Optional alias for shorter commands:

```bash
alias encryptor='~/.venvs/rikkisnah/bin/encryptor'
encryptor --help
```

Then from anywhere:

```bash
encryptor keygen -o my.key
encryptor encrypt -k my.key secret.txt
```

See `INSTALL.md` for detailed setup instructions.

> **Note:** Examples below use `uv run encryptor`.
> If you used Option 2, drop the `uv run` prefix and use `encryptor` directly.

## Getting Started

### 1. Generate a key

```bash
uv run encryptor keygen -o my.key
```

This creates a random Fernet key file with restricted permissions (`0600`).
Keep this file safe — anyone with the key can decrypt your data.

### 2. Encrypt a file

```bash
uv run encryptor encrypt -k my.key secret.txt
```

This creates `secret.txt.enc` in the same directory.

### 3. Decrypt a file

```bash
uv run encryptor decrypt -k my.key secret.txt.enc
```

This creates `secret.txt.enc.dec`. Use `-o` to specify a custom output path:

```bash
uv run encryptor decrypt -k my.key secret.txt.enc -o restored.txt
```

## Commands

### `keygen` — Generate a key file

```bash
uv run encryptor keygen -o <path>
```

| Option | Required | Description |
|--------|----------|-------------|
| `-o, --output` | Yes | Path for the new key file |

The key file contains a 44-byte URL-safe base64 Fernet key.
File permissions are set to `0600` (owner read/write only).

### `encrypt` — Encrypt data

```bash
uv run encryptor encrypt (-k <keyfile> | -p) [options] [path]
```

| Option | Description |
|--------|-------------|
| `-k, --key` | Path to key file |
| `-p, --passphrase` | Prompt for passphrase instead of key file |
| `-o, --output` | Output path (default: `<input>.enc`) |
| `path` | File or directory to encrypt (omit for stdin) |

### `decrypt` — Decrypt data

```bash
uv run encryptor decrypt (-k <keyfile> | -p) [options] [path]
```

| Option | Description |
|--------|-------------|
| `-k, --key` | Path to key file |
| `-p, --passphrase` | Prompt for passphrase instead of key file |
| `-o, --output` | Output path (default: `<input>.dec`) |
| `path` | File or directory to decrypt (omit for stdin) |

## Authentication Modes

Encryptor supports two authentication modes. You must use exactly one per
operation — they cannot be combined.

### Key file mode (`-k`)

Uses a random Fernet key stored in a file. Best for automation and scripting.

```bash
uv run encryptor keygen -o my.key
uv run encryptor encrypt -k my.key data.txt
uv run encryptor decrypt -k my.key data.txt.enc
```

### Passphrase mode (`-p`)

Derives an encryption key from a passphrase using PBKDF2-HMAC-SHA256 with
200,000 iterations and a random 16-byte salt. Best for interactive use.

```bash
uv run encryptor encrypt -p secret.txt
# Passphrase: ********

uv run encryptor decrypt -p secret.txt.enc
# Passphrase: ********
```

The salt is stored in the encrypted file header, so decryption only needs the
same passphrase.

## Working with Files

### Single file

```bash
# Encrypt (creates notes.txt.enc)
uv run encryptor encrypt -k my.key notes.txt

# Encrypt to specific output
uv run encryptor encrypt -k my.key notes.txt -o encrypted/notes.bin

# Decrypt (creates notes.txt.enc.dec)
uv run encryptor decrypt -k my.key notes.txt.enc

# Decrypt to specific output
uv run encryptor decrypt -k my.key notes.txt.enc -o restored/notes.txt
```

### Directories

Encryptor recursively encrypts all regular files in a directory.
Symlinks are skipped for security.

**Filename and structure obfuscation:** All files are flattened into a single
output directory with random hex filenames. An encrypted `.manifest` file
stores the mapping from random names back to the original relative paths.
Without the key, no one can see the original filenames, directory names, or
directory structure.

Given a directory tree:

```
rik/
├── rik.txt
├── rik2/
│   └── rik2.txt
└── rik3/
    ├── rik3.txt
    └── rik31/
        └── rik31.txt
```

Encrypt it:

```bash
# Default output: rik.enc/
uv run encryptor encrypt -k my.key rik/

# Custom output directory
uv run encryptor encrypt -k my.key rik/ -o rik-encrypted/
```

Encrypted output is fully obfuscated — flat structure, random names:

```
rik-encrypted/
├── .manifest          # encrypted mapping (random name → original path)
├── 3a1f8c2e9b4d7012   # was rik.txt
├── 7e0d4a9c1b3f5628   # was rik2/rik2.txt
├── b2c8e1a04f6d3971   # was rik3/rik3.txt
└── d5f2a8e7c0194b36   # was rik3/rik31/rik31.txt
```

No one can tell what the original files or directories were.

Decrypt it back:

```bash
# Default output: rik-encrypted.dec/
uv run encryptor decrypt -k my.key rik-encrypted/

# Custom output directory
uv run encryptor decrypt -k my.key rik-encrypted/ -o rik-restored/
```

Decryption reads the encrypted manifest and restores the original structure:

```
rik-restored/
├── rik.txt
├── rik2/
│   └── rik2.txt
└── rik3/
    ├── rik3.txt
    └── rik31/
        └── rik31.txt
```

Verify the round-trip:

```bash
diff -r rik/ rik-restored/
# No output = files are identical
```

#### Passphrase mode for directories

```bash
uv run encryptor encrypt -p rik/ -o rik-encrypted/
# Passphrase: ********

uv run encryptor decrypt -p rik-encrypted/ -o rik-restored/
# Passphrase: ********
```

### Stdin / Stdout (text mode)

When no file path is given, Encryptor reads from stdin and writes to stdout.
This works well with pipes.

```bash
# Encrypt text
echo "secret message" | uv run encryptor encrypt -k my.key > encrypted.bin

# Decrypt text
cat encrypted.bin | uv run encryptor decrypt -k my.key
# Output: secret message

# Encrypt stdin to file
echo "secret" | uv run encryptor encrypt -k my.key -o secret.enc

# Decrypt to file
cat secret.enc | uv run encryptor decrypt -k my.key -o secret.txt
```

## Encrypted File Format

All encrypted files use a binary format with a 20-byte header:

```
Offset  Size     Field
0       4 bytes  Magic: ENC\x01 (identifies file + format version 1)
4       16 bytes Salt (random for passphrase mode, zeroed for key file mode)
20      N bytes  Fernet token (contains IV + AES-CBC ciphertext + HMAC-SHA256)
```

- The Fernet token is self-contained: it includes the IV, ciphertext, and HMAC.
- Tampered files are rejected during decryption (HMAC verification fails).
- The salt field distinguishes key file mode (zeroed) from passphrase mode
  (random), so the tool knows how to derive the decryption key.

## Security Notes

- **Key files** are created with `0600` permissions (owner-only access).
- **Passphrase derivation** uses PBKDF2-HMAC-SHA256 with 200,000 iterations.
- **Authenticated encryption**: Fernet guarantees that tampered ciphertext is
  rejected before any plaintext is returned.
- **Randomness**: All salts and IVs use `os.urandom()` (CSPRNG).
- **Symlinks are skipped** during directory encryption to prevent symlink
  attacks or accidentally encrypting files outside the target directory.
- **Never share key files** or commit them to version control. Add `*.key` to
  your `.gitignore`.

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `path not found` | Input file or directory does not exist | Check the path |
| `invalid encrypted payload header` | File was not encrypted by Encryptor | Verify you are decrypting the right file |
| `corrupt encrypted payload` | File is too small to be valid | File may be truncated |
| `InvalidToken` | Wrong key or passphrase, or data was tampered with | Use the correct key/passphrase |
| `key is required` | Trying to decrypt a key-file-encrypted payload with `-p` | Use `-k` with the original key file |
| `passphrase is required` | Trying to decrypt a passphrase-encrypted payload with `-k` | Use `-p` and enter the original passphrase |

## Examples

### Full round-trip (file)

```bash
uv run encryptor keygen -o /tmp/rik.key
uv run encryptor encrypt -k /tmp/rik.key /tmp/rik/rik.txt
uv run encryptor decrypt -k /tmp/rik.key /tmp/rik/rik.txt.enc -o /tmp/rik_restored.txt
diff /tmp/rik/rik.txt /tmp/rik_restored.txt
# No output = identical
```

### Full round-trip (directory)

```bash
uv run encryptor keygen -o /tmp/rik.key
uv run encryptor encrypt -k /tmp/rik.key /tmp/rik/ -o /tmp/rik-encrypted/
uv run encryptor decrypt -k /tmp/rik.key /tmp/rik-encrypted/ -o /tmp/rik-restored/
diff -r /tmp/rik/ /tmp/rik-restored/
# No output = identical
```

### Encrypt a project directory before sharing

```bash
uv run encryptor keygen -o project.key
uv run encryptor encrypt -k project.key my-project/ -o my-project-encrypted/
# Share my-project-encrypted/ and project.key via separate channels
```

### Encrypt with a passphrase for quick sharing

```bash
uv run encryptor encrypt -p report.pdf -o report.pdf.enc
# Share report.pdf.enc and tell the recipient the passphrase
```

### Pipe encryption in a script

```bash
# Encrypt a database dump
pg_dump mydb | uv run encryptor encrypt -k backup.key -o db-backup.enc

# Restore later
uv run encryptor decrypt -k backup.key db-backup.enc -o db-dump.sql
psql mydb < db-dump.sql
```
