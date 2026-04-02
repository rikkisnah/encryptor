<!--
#ai-assisted
Code was generated with Claude and Codex LLM with human supervision.
Tag: #ai-assisted
-->

# encryptor

Encryptor is a small Python CLI for encrypting and decrypting files, directories, and text payloads using Fernet.

## Install

### Option 1 — Project-local development (preferred)

```bash
cd /Users/rkisnah/src/rikkisnah/encryptor
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

See `INSTALL.md` for the full setup guide.

> **Note:** Examples below use `uv run encryptor`.
> If you used Option 2, drop the `uv run` prefix and use `encryptor` directly.

## Quick start

```bash
uv run encryptor keygen -o my.key
uv run encryptor encrypt -k my.key secret.txt
uv run encryptor decrypt -k my.key secret.txt.enc
```

## Commands

| Command | Description |
|---------|-------------|
| `keygen` | Generate a Fernet key file (`-o` required) |
| `encrypt` | Encrypt a file, directory, or stdin data |
| `decrypt` | Decrypt a file, directory, or stdin data |

## Usage

### Generate a key

```bash
uv run encryptor keygen -o my.key
```

### Encrypt / decrypt a single file

```bash
# Encrypt (creates secret.txt.enc)
uv run encryptor encrypt -k my.key secret.txt

# Encrypt to a specific output path
uv run encryptor encrypt -k my.key secret.txt -o /tmp/secret.encrypted

# Decrypt (creates secret.txt.enc.dec)
uv run encryptor decrypt -k my.key secret.txt.enc

# Decrypt to a specific output path
uv run encryptor decrypt -k my.key secret.txt.enc -o restored.txt
```

### Encrypt / decrypt an entire directory

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

Encrypt it recursively:

```bash
# Default output: rik.enc/
uv run encryptor encrypt -k my.key rik/

# Custom output directory
uv run encryptor encrypt -k my.key rik/ -o rik-encrypted/
```

Encrypted output is **fully obfuscated** — filenames are random hex, directory
structure is flattened, and an encrypted `.manifest` maps names back for
decryption:

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

Restored result matches the original:

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

### Passphrase mode (no key file)

```bash
# Encrypt with a passphrase
uv run encryptor encrypt -p rik/ -o rik-encrypted/
# Passphrase: ********

# Decrypt with the same passphrase
uv run encryptor decrypt -p rik-encrypted/ -o rik-restored/
# Passphrase: ********
```

### Stdin / stdout (text mode)

```bash
# Encrypt from stdin to stdout
echo "secret message" | uv run encryptor encrypt -k my.key > encrypted.bin

# Decrypt from stdin to stdout
cat encrypted.bin | uv run encryptor decrypt -k my.key
# Output: secret message

# Encrypt stdin to a file
echo "secret" | uv run encryptor encrypt -k my.key -o secret.enc

# Decrypt to a file
cat secret.enc | uv run encryptor decrypt -k my.key -o secret.txt
```

### Full round-trip example

```bash
uv run encryptor keygen -o /tmp/rik.key
uv run encryptor encrypt -k /tmp/rik.key /tmp/rik/ -o /tmp/rik-encrypted/
uv run encryptor decrypt -k /tmp/rik.key /tmp/rik-encrypted/ -o /tmp/rik-restored/
diff -r /tmp/rik/ /tmp/rik-restored/
# No output = files are identical
```

## File format

Encrypted files use a binary format with a 20-byte header:

```
Offset  Size     Field
0       4 bytes  Magic: ENC\x01 (format version 1)
4       16 bytes Salt (random for passphrase mode, zeroed for key file mode)
20      N bytes  Fernet token (IV + AES-CBC ciphertext + HMAC-SHA256)
```

Symlinks are skipped during directory encryption.

### Directory encryption

When encrypting a directory, all files are flattened into a single directory
with random hex filenames. An encrypted `.manifest` file stores the mapping
from random names back to original relative paths. The manifest is encrypted
with the same key/passphrase, so without the key no one can see the original
filenames, directory names, or structure.

## Documentation

- `docs/user-guide.md` — full user guide with all options, auth modes, and examples
- `INSTALL.md` — setup guide for agents and humans
- `CREATE-PR.md` — PR workflow
- `CLAUDE.md` / `AGENTS.md` — coding rules and quality bar
