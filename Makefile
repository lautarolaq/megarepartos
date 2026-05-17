.PHONY: help dev dev-db dev-backend dev-frontend stop \
	install install-backend install-frontend \
	test test-fast test-unit test-integration test-e2e \
	lint lint-backend lint-frontend lint-fix \
	migrate migration-new \
	health integrity security-check seed-demo \
	check-arquitectura check-test-coverage behavior-coverage \
	build clean

# ---- Configuración ----
BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTHON := python3.12
VENV := $(BACKEND_DIR)/.venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
ALEMBIC := $(VENV)/bin/alembic
UVICORN := $(VENV)/bin/uvicorn

help: ## Lista los comandos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ---- Instalación ----

install: install-backend install-frontend ## Instala dependencias backend + frontend

install-backend: ## Crea venv backend e instala dependencias
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e "$(BACKEND_DIR)[dev]"

install-frontend: ## Instala dependencias frontend
	cd $(FRONTEND_DIR) && npm install

# ---- Desarrollo ----

dev: dev-db ## Arranca DB + backend + frontend en paralelo (Ctrl+C corta todo)
	@echo ">> Arrancando backend (:8000) y frontend (:5173)..."
	@trap 'kill 0' INT TERM EXIT; \
	  ( $(MAKE) --no-print-directory dev-backend ) & \
	  ( $(MAKE) --no-print-directory dev-frontend ) & \
	  wait

dev-db: ## Levanta Postgres local con docker-compose
	docker compose up -d db
	@echo ">> Postgres listo en localhost:5432"

dev-backend: ## Arranca solo el backend (uvicorn con reload)
	cd $(BACKEND_DIR) && ../$(UVICORN) megarepartos.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src

dev-frontend: ## Arranca solo el frontend (Vite)
	cd $(FRONTEND_DIR) && npm run dev

stop: ## Detiene servicios de docker-compose
	docker compose down

# ---- Migraciones ----

migrate: ## alembic upgrade head
	cd $(BACKEND_DIR) && ../$(ALEMBIC) upgrade head

migration-new: ## Crea nueva migración autogenerada. Uso: make migration-new m="descripcion"
	cd $(BACKEND_DIR) && ../$(ALEMBIC) revision --autogenerate -m "$(m)"

# ---- Testing ----

# `|| [ $$? -eq 5 ]` tolera la suite vacía mientras no haya tests todavía
# (pytest sale con 5 cuando no encuentra tests). Se quita cuando aterricen los
# primeros tests en TASKs siguientes.
test: ## Corre toda la suite (unit + integration + e2e)
	cd $(BACKEND_DIR) && ../$(PYTEST) || [ $$? -eq 5 ]

test-fast: ## Corre unit + integration, saltea e2e
	cd $(BACKEND_DIR) && ../$(PYTEST) -m "not e2e" || [ $$? -eq 5 ]

test-unit: ## Solo tests unit
	cd $(BACKEND_DIR) && ../$(PYTEST) tests/unit || [ $$? -eq 5 ]

test-integration: ## Solo tests integration
	cd $(BACKEND_DIR) && ../$(PYTEST) tests/integration || [ $$? -eq 5 ]

test-e2e: ## Solo tests e2e (Playwright)
	cd $(BACKEND_DIR) && ../$(PYTEST) tests/e2e || [ $$? -eq 5 ]

# ---- Lint ----

lint: lint-backend lint-frontend ## ruff + mypy + biome

lint-backend: ## ruff check + mypy en backend
	$(RUFF) check $(BACKEND_DIR)
	$(RUFF) format --check $(BACKEND_DIR)
	$(MYPY) $(BACKEND_DIR)/src

lint-frontend: ## biome check en frontend
	cd $(FRONTEND_DIR) && npm run lint

lint-fix: ## Aplica fixes automáticos
	$(RUFF) check --fix $(BACKEND_DIR)
	$(RUFF) format $(BACKEND_DIR)
	cd $(FRONTEND_DIR) && npm run lint:fix

# ---- Smoke checks locales ----

health: ## Smoke test completo del backend
	@echo "TODO: implementar en TASK siguiente"

integrity: ## Validaciones de integridad sobre DB local
	@echo "TODO: implementar en TASK siguiente"

security-check: ## Suite de aislamiento multi-tenant
	cd $(BACKEND_DIR) && ../$(PYTEST) -m "isolation"

seed-demo: ## Carga data demo en DB local
	@echo "TODO: implementar en TASK siguiente"

# ---- Checks de arquitectura / coverage ----

check-arquitectura: ## AST parsing de reglas no negociables
	$(PY) scripts/check_arquitectura.py

check-test-coverage: ## Verifica que cambios en domain/api tienen cambios en tests
	$(PY) scripts/check_test_coverage_changes.py

behavior-coverage: ## REQ-IDs sin test asociado
	$(PY) scripts/behavior_coverage.py

# ---- Build / clean ----

build: ## Build de prod (backend + frontend)
	cd $(FRONTEND_DIR) && npm run build

clean: ## Limpia artifacts
	rm -rf $(VENV) $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
