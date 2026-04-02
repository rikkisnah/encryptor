<!--
#ai-assisted
Code was generated with Claude and Codex LLM with human supervision.
Tag: #ai-assisted
-->

# Encryptor Setup

This file is the agent-facing onboarding guide for installing Encryptor.
It is designed to be followed by Claude Code or Codex with minimal user
decision-making.

Primary source of truth for setup behavior:

1. `INSTALL.md` (this file)
2. `CLAUDE.md` / `AGENTS.md`
3. `Makefile`
4. `README.md`
5. `docs/user-guide.md`

## Intent

The default goal is:

1. Install all dependencies and dev tools
2. Install `encryptor` CLI into the shared venv so it works from any directory
3. Run all quality gates (`make validate`)
4. Confirm `encryptor --help` works

Do not turn setup into a checklist for the user unless a real blocker requires
their input.

## Copy/Paste Prompt

Paste this into Claude Code or Codex:

```text
Set up this Encryptor repository for local development by following
INSTALL.md, CLAUDE.md, Makefile, and README.md.

Goal:
- Get this repo installed, validated, and ready to run locally.
- Prefer doing the work over giving me a checklist.
- Keep going until setup is complete or there is a real blocker that requires
  my input.

Required workflow:
1. Confirm you are in the repo root.
2. Detect platform and current toolchain state.
3. Check whether git, Python 3.9+, uv, and make are installed.
4. If prerequisites are missing, install them:
   - macOS: brew install git python@3.11 uv make
   - Ubuntu: sudo apt-get update && sudo apt-get install -y git make curl python3.11 python3.11-venv
   - Ubuntu: install uv from https://astral.sh/uv/install.sh
5. Do not ask me to create or activate a virtual environment manually.
   This repo uses uv-managed environments.
6. Run `make setup` which does all of the following:
   - `make install` — uv sync (creates .venv/ with all deps)
   - `make install-cli` — pip install -e . into ~/.venvs/rikkisnah
   - `make validate` — lint + format-check + test + scorecard
7. Verify the install with:
   - encryptor --help (should work from any directory with shared venv active)
8. Report what passed, what failed, and any remaining manual step.

Ask me only when you actually need:
- approval for an escalated command
- a secret or credential
Otherwise, continue without asking.
```

## Prerequisites

| Tool | Minimum | Check |
|------|---------|-------|
| git | any | `git --version` |
| Python | 3.9+ | `python3 --version` |
| uv | 0.4+ | `uv --version` |
| make | any | `make --version` |

## Setup

One command does everything:

```bash
make setup
```

This runs:
1. `make install` — `uv sync` (creates `.venv/`, installs all dependencies)
2. `make install-cli` — `pip install -e .` into `~/.venvs/rikkisnah` (so `encryptor` works from any directory)
3. `make validate` — lint + format-check + tests (100% coverage) + architecture scorecard

## What `make validate` Checks

| Gate | What it verifies | Failure means |
|------|-----------------|---------------|
| `ruff check` | Zero lint errors | Fix lint issues |
| `ruff format --check` | Code is formatted | Run `make format` |
| `pytest` | All tests pass, 100% coverage | Fix tests or add missing coverage |
| `score_architecture.py` | All 8 dimensions >= 8/10 | Fix architectural violations |

## CLI Entrypoints

After `make setup`, these work from any directory:

Direct path execution, no shell activation required:

```bash
~/.venvs/rikkisnah/bin/encryptor --help
~/.venvs/rikkisnah/bin/encryptor keygen -o my.key
~/.venvs/rikkisnah/bin/encryptor encrypt -k my.key <file>
~/.venvs/rikkisnah/bin/encryptor decrypt -k my.key <file>.enc
```

If the shared venv is active, the plain `encryptor` command also works:

```bash
encryptor --help
encryptor keygen -o my.key
encryptor encrypt -k my.key <file>
encryptor decrypt -k my.key <file>.enc
```

Optional shell alias for direct use without activating the venv:

```bash
alias encryptor='~/.venvs/rikkisnah/bin/encryptor'
encryptor --help
```

From the project directory, `uv run encryptor` also works without the venv:

```bash
uv run encryptor --help
```

## Sandboxed Environments

If running in a sandbox with restricted permissions:

```bash
UV_CACHE_DIR=.uv-cache make install
UV_CACHE_DIR=.uv-cache make validate
UV_CACHE_DIR=.uv-cache uv run encryptor --help
```

## Next Steps

Setup is complete. Follow the workflow docs in order:

| Step | File | Purpose |
|------|------|---------|
| 2 | `CLAUDE.md` / `AGENTS.md` | Daily coding rules and quality bar |
| 3 | `CREATE-PR.md` | Commit, review, push, create PR |
