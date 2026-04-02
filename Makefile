.DEFAULT_GOAL := help
.PHONY: help install install-cli setup sync test test-v lint format format-check check score score-v score-json run validate clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install project with dev dependencies
	uv sync

install-cli: install ## Install encryptor into shared venv (~/.venvs/rikkisnah)
	~/.venvs/rikkisnah/bin/pip install -e .

setup: install-cli validate ## Full setup: install + venv + validate

sync: install ## Alias for install

test: ## Run tests with coverage
	uv run pytest

test-v: ## Run tests verbose with coverage
	uv run pytest -v --cov-report=term-missing

lint: ## Lint with ruff
	uv run ruff check .

format: ## Format with ruff
	uv run ruff format .

format-check: ## Check formatting without modifying
	uv run ruff format --check .

check: lint test ## Lint then test

score: ## Run architecture scorecard
	uv run python scripts/score_architecture.py

score-v: ## Run scorecard with verbose violations
	uv run python scripts/score_architecture.py --verbose

score-json: ## Run scorecard as JSON
	uv run python scripts/score_architecture.py --json

run: check score ## Full quality bar: lint + test + scorecard

validate: ## All guardrails: lint + format-check + test + scorecard (min 8)
	@echo "===> Lint"
	uv run ruff check .
	@echo ""
	@echo "===> Format check"
	uv run ruff format --check .
	@echo ""
	@echo "===> Tests (100% coverage)"
	uv run pytest
	@echo ""
	@echo "===> Architecture scorecard (min-score 8)"
	uv run python scripts/score_architecture.py --verbose --min-score 8

clean: ## Remove build artifacts and caches
	rm -rf .venv .pytest_cache .ruff_cache __pycache__ encryptor/__pycache__ tests/__pycache__
	rm -rf dist build *.egg-info .coverage htmlcov
