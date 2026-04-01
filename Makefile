# =============================================================================
# CryptoQuant Makefile
# =============================================================================

.PHONY: install dev build up down logs migrate test lint clean help

DOCKER_COMPOSE := docker compose
BACKEND_DIR    := backend
FRONTEND_DIR   := frontend

## ── Colour helpers ──────────────────────────────────────────────────────────
BOLD  := \033[1m
RESET := \033[0m
GREEN := \033[32m
CYAN  := \033[36m

# Default target
.DEFAULT_GOAL := help

# =============================================================================
# Local Development (no Docker)
# =============================================================================

## install: Install all backend and frontend dependencies
install:
	@echo "$(CYAN)→ Installing backend dependencies...$(RESET)"
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	@echo "$(CYAN)→ Installing frontend dependencies...$(RESET)"
	cd $(FRONTEND_DIR) && npm install
	@echo "$(GREEN)✔ All dependencies installed$(RESET)"

## dev: Start backend and frontend in development mode (without Docker)
dev:
	@echo "$(CYAN)→ Starting development servers...$(RESET)"
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

# =============================================================================
# Docker
# =============================================================================

## build: Build all Docker images
build:
	@echo "$(CYAN)→ Building Docker images...$(RESET)"
	$(DOCKER_COMPOSE) build --parallel
	@echo "$(GREEN)✔ Build complete$(RESET)"

## up: Start all services in detached mode
up:
	@echo "$(CYAN)→ Starting services...$(RESET)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✔ Services running. API → http://localhost:8000 | UI → http://localhost:3000$(RESET)"

## down: Stop and remove all containers
down:
	@echo "$(CYAN)→ Stopping services...$(RESET)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✔ Services stopped$(RESET)"

## down-volumes: Stop containers AND remove persistent volumes (⚠ data loss)
down-volumes:
	@echo "$(CYAN)→ Stopping services and removing volumes...$(RESET)"
	$(DOCKER_COMPOSE) down -v
	@echo "$(GREEN)✔ Services and volumes removed$(RESET)"

## logs: Tail logs for all services (pass s=<service> to filter, e.g. make logs s=backend)
logs:
	$(DOCKER_COMPOSE) logs -f $(s)

## ps: Show status of all services
ps:
	$(DOCKER_COMPOSE) ps

# =============================================================================
# Database
# =============================================================================

## migrate: Run Alembic database migrations inside the backend container
migrate:
	@echo "$(CYAN)→ Running database migrations...$(RESET)"
	$(DOCKER_COMPOSE) exec backend alembic upgrade head
	@echo "$(GREEN)✔ Migrations complete$(RESET)"

## migrate-create: Create a new migration (usage: make migrate-create msg="add users table")
migrate-create:
	$(DOCKER_COMPOSE) exec backend alembic revision --autogenerate -m "$(msg)"

## migrate-downgrade: Roll back one migration
migrate-downgrade:
	$(DOCKER_COMPOSE) exec backend alembic downgrade -1

# =============================================================================
# Testing
# =============================================================================

## test: Run full test suite (backend + frontend)
test:
	@echo "$(CYAN)→ Running backend tests...$(RESET)"
	$(MAKE) test-backend
	@echo "$(CYAN)→ Running frontend tests...$(RESET)"
	$(MAKE) test-frontend
	@echo "$(GREEN)✔ All tests passed$(RESET)"

## test-backend: Run backend unit/integration tests with coverage
test-backend:
	cd $(BACKEND_DIR) && pytest --cov=app --cov-report=term-missing --cov-report=xml -v

## test-frontend: Run frontend tests
test-frontend:
	cd $(FRONTEND_DIR) && npm test -- --run

# =============================================================================
# Linting & Formatting
# =============================================================================

## lint: Lint and type-check backend and frontend
lint:
	@echo "$(CYAN)→ Linting backend...$(RESET)"
	$(MAKE) lint-backend
	@echo "$(CYAN)→ Linting frontend...$(RESET)"
	$(MAKE) lint-frontend
	@echo "$(GREEN)✔ Lint complete$(RESET)"

## lint-backend: Ruff lint + mypy type-check for Python
lint-backend:
	cd $(BACKEND_DIR) && ruff check . && mypy app

## lint-frontend: ESLint + TypeScript type-check for the frontend
lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint && npm run type-check

## format: Auto-format backend (ruff + black) and frontend (prettier)
format:
	@echo "$(CYAN)→ Formatting backend...$(RESET)"
	cd $(BACKEND_DIR) && ruff check --fix . && black .
	@echo "$(CYAN)→ Formatting frontend...$(RESET)"
	cd $(FRONTEND_DIR) && npm run format
	@echo "$(GREEN)✔ Format complete$(RESET)"

# =============================================================================
# Utilities
# =============================================================================

## shell-backend: Open an interactive shell in the backend container
shell-backend:
	$(DOCKER_COMPOSE) exec backend bash

## shell-db: Open a psql session in the postgres container
shell-db:
	$(DOCKER_COMPOSE) exec postgres psql -U cryptoquant -d cryptoquant

## clean: Remove build artefacts, caches, and compiled files
clean:
	@echo "$(CYAN)→ Cleaning artefacts...$(RESET)"
	find . -type d -name __pycache__  -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc"      -delete 2>/dev/null            || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache"   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache"   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov"       -exec rm -rf {} + 2>/dev/null || true
	rm -f $(BACKEND_DIR)/coverage.xml
	rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/node_modules/.cache
	@echo "$(GREEN)✔ Clean complete$(RESET)"

## env: Create .env from .env.example (will not overwrite an existing .env)
env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✔ .env created from .env.example — update the values before use$(RESET)"; \
	else \
		echo ".env already exists — skipped"; \
	fi

# =============================================================================
# Help
# =============================================================================

## help: Show this help message
help:
	@echo "$(BOLD)CryptoQuant — available targets$(RESET)"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) \
		| sed 's/## //' \
		| awk -F': ' '{ printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2 }'
	@echo ""
