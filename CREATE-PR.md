<!--
#ai-assisted
Code was generated with Claude and Codex LLM with human supervision.
Tag: #ai-assisted
-->

# CREATE-PR Workflow

When invoked, follow these steps exactly. Display each command and its output.
Do NOT execute destructive commands without user confirmation.

---

## Step 1: Show what changed vs remote main

Run and display output:

```bash
git fetch origin main
git diff --stat origin/main...HEAD
git diff --stat
git status -s
```

Show the user a summary table:

| Type | Count |
|------|-------|
| Files changed (committed vs remote main) | N |
| Files changed (uncommitted staged) | N |
| Files changed (uncommitted unstaged) | N |
| Untracked files | N |

---

## Step 2: Show detailed diff for review

Run and display output:

```bash
git diff origin/main...HEAD --name-status
git diff --name-status
git diff --cached --name-status
```

Present a single merged file list with status indicators:

```
A  encryptor/new_module.py     (new file)
M  encryptor/cli.py            (modified)
M  tests/test_cli.py           (modified)
?? scripts/new-script.py       (untracked)
```

---

## Step 2b: Ask about version bump

Before drafting the commit, ask the user:

```
Current version: X.Y.Z (from pyproject.toml)

Do you want to bump the version for this change?
  1. No — keep X.Y.Z
  2. Patch — X.Y.(Z+1)  (bug fixes, small changes)
  3. Minor — X.(Y+1).0  (new features, backward compatible)
  4. Major — (X+1).0.0  (breaking changes)
  5. Custom — enter version manually

Choice? (1/2/3/4/5)
```

**STOP and wait for user response.**

If the user picks 2-5, update the version in both `pyproject.toml` and
`encryptor/__init__.py`, and include both files in the commit.

---

## Step 3: Verify documentation is updated

Before drafting the commit message, check that documentation matches the code changes:

- If any **CLI commands, options, or behavior** changed:
  - `README.md` must reflect the new usage
  - `docs/user-guide.md` must be updated
- If any **file format, encryption, or key handling** changed:
  - `README.md` file format section must be updated
  - `docs/user-guide.md` security notes must be updated
- If any **new module or function** was added:
  - Module docstring must be present
  - `CLAUDE.md` project layout must be updated if structure changed

If documentation is missing or stale, **fix it before proceeding** to Step 4.

---

## Step 4: Run quality gates

Run all gates before committing:

```bash
make validate
```

This runs:
- `ruff check` — lint
- `ruff format --check` — formatting
- `pytest` — tests with 100% coverage
- `score_architecture.py --min-score 8` — architecture scorecard

If any gate fails, **stop and fix before proceeding**.

---

## Step 5: Draft commit message

Analyze ALL changes (committed + uncommitted + untracked) and draft:

**One-line summary** (for `git commit -m`):
- Use conventional commit format: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`
- Max 72 characters
- Describe the "what" concisely

**Detailed body** (for PR description):
- Group changes by area (crypto, fileops, CLI, tests, docs, config)
- List key additions, modifications, deletions
- Note any breaking changes

Display the draft to the user:

```
Proposed commit message:

  feat: add directory encryption with recursive traversal

  - Add encrypt_directory/decrypt_directory to fileops.py
  - Add CLI support for directory paths in encrypt/decrypt commands
  - Add 8 tests for directory operations including symlink skipping
  - Update README.md and docs/user-guide.md with directory examples
  - Update CLAUDE.md project layout

  #ai-assisted
```

---

## Step 6: Ask for confirmation

Display the exact commands that will be executed:

```
The following commands will be run:

  git add <specific files listed>
  git commit -m "<the one-line message>

  <the detailed body>

  #ai-assisted"

Proceed? (yes/no)
```

**STOP and wait for user to say "yes" before executing.**

Do NOT use `git add -A` or `git add .` — list specific files.
Do NOT push unless the user explicitly asks.

---

## Step 7: Execute (only after confirmation)

Run the staged commands and display output:

```bash
git add <files>
git commit -m "<message>"
git status
```

Show the resulting commit hash and summary.

---

## Step 8: Ask about push

```
Commit created: <hash>

Push to origin? (yes/no)
If yes, which branch? (current / new branch name)
```

Wait for user response before pushing.

---

## Rules

- NEVER push without explicit permission
- NEVER use `git add -A` or `git add .`
- NEVER amend existing commits unless asked
- NEVER skip hooks (`--no-verify`)
- Always show the full file list before staging
- Always show the commit message before committing
- Always include `#ai-assisted` in the commit message body
- Exclude `.env`, `credentials.json`, `*.key`, `*.db` from staging
- If uncommitted changes exist alongside committed changes, ask whether to include them in one commit or separate commits
- Documentation must be updated for any user-facing change — do not commit code without corresponding doc updates
