<!--
#ai-assisted
Code was generated with Claude and Codex LLM with human supervision.
Tag: #ai-assisted
-->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Disclaimer

This project was created with #ai-assisted (with Claude and Codex LLM).
All code, tests, and documentation were generated with human supervision.
All new code and documentation must include the `#ai-assisted` tag.

## Project

Encryptor — a Python CLI tool that encrypts and decrypts files, directories, and text using Fernet (AES-256-CBC + HMAC-SHA256).

## Quality Requirements

All code changes **must**:

1. **Pass `make validate`** before committing — this is the quality gate:
   - `ruff check` — zero lint errors
   - `ruff format --check` — zero formatting issues
   - `pytest` — all tests pass with **100% code coverage**
   - `score_architecture.py --min-score 8` — all 8 dimensions >= 8/10
2. **Maintain 100% test coverage** — every new function, branch, and error path must have tests.
3. **Update documentation** — any user-facing change must update:
   - `README.md` — usage examples, command reference, file format docs
   - `docs/user-guide.md` — detailed how-to for end users
   - Module/function docstrings as needed
4. **Follow the PR workflow** in `CREATE-PR.md` when committing and pushing.

## Development

Uses **uv** for dependency and virtual environment management.

```bash
uv sync              # Install all deps (creates .venv/)
uv run pytest        # Run tests (100% coverage required)
uv run ruff check .  # Lint
uv run ruff format . # Format
```

Or via Makefile:

```bash
make help      # Show all targets
make install   # uv sync
make test      # pytest with coverage
make test-v    # verbose with missing-line report
make lint      # ruff check
make format    # ruff format
make check     # lint + test
make score     # architecture scorecard
make score-v   # scorecard with violations
make validate  # ALL guardrails (lint + format + test + scorecard)
make run       # lint + test + scorecard
make clean     # remove caches and build artifacts
```

## Project Layout

```
encryptor/              # Package (flat layout)
  __init__.py           # Version
  crypto.py             # Key generation, PBKDF2 derivation, encrypt/decrypt primitives
  fileops.py            # File format (ENC\x01 header), file/directory operations
  cli.py                # argparse CLI: keygen, encrypt, decrypt
tests/                  # pytest tests (100% coverage gate)
  conftest.py           # Shared fixtures
  test_crypto.py        # Crypto module tests
  test_fileops.py       # File operations tests
  test_cli.py           # CLI integration tests (in-process)
scripts/
  score_architecture.py # 8-dimension architecture scorecard
docs/
  user-guide.md         # End-user documentation
pyproject.toml          # uv/hatchling config
Makefile                # Build, test, lint, validate targets
INSTALL.md              # Setup guide for agents and humans
CREATE-PR.md            # PR workflow for agents and humans
```

## Workflow Documents

| Step | File | Purpose |
|------|------|---------|
| 1 | `INSTALL.md` | Set up the repo for local development |
| 2 | This file (`CLAUDE.md`) | Daily coding rules and quality bar |
| 3 | `CREATE-PR.md` | Commit, review, push, create PR |
