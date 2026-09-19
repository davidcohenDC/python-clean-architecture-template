# Every target is a thin alias for a command you can also type by hand (see README).
.DEFAULT_GOAL := help
.PHONY: help install run run-memory test test-fast lint format typecheck check migrate migration docs docs-build clean new-feature

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and enable the git hooks (conventional commits + checks)
	uv sync --all-extras
	git config core.hooksPath .githooks

run: migrate ## Run the API with auto-reload (SQLite by default)
	uv run uvicorn cleanarch.main:app --reload

run-memory: ## Run the API with in-memory adapters (no database at all)
	DATABASE_URL=memory:// uv run uvicorn cleanarch.main:app --reload

test: ## Run the whole test suite with coverage
	uv run pytest --cov --cov-report=term-missing

test-fast: ## Run only domain + application + architecture tests (no I/O)
	uv run pytest tests/domain tests/application tests/architecture

lint: ## Ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-fix lint issues and format
	uv run ruff check . --fix
	uv run ruff format .

typecheck: ## mypy --strict
	uv run mypy

check: lint typecheck test ## Everything CI runs

migrate: ## Apply database migrations
	uv run alembic upgrade head

migration: ## Autogenerate a migration: make migration m="add players"
	uv run alembic revision --autogenerate -m "$(m)"

new-feature: ## Scaffold a feature: make new-feature name=orders
	uv run python scripts/new_feature.py $(name)

docs: ## Serve the documentation site locally
	cd docs && npm install && npm run start

docs-build: ## Build the documentation site
	cd docs && npm install && npm run build

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build dev.db
