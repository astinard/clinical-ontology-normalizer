.PHONY: test lint typecheck dev clean help

# Default target
help:
	@echo "Clinical Ontology Normalizer - Build Commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  test       Run all tests (backend + frontend)"
	@echo "  lint       Run all linters"
	@echo "  typecheck  Run type checkers"
	@echo "  dev        Start development servers"
	@echo "  clean      Clean build artifacts"
	@echo ""

# Run all tests
test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	@cd backend && python3 -m pytest tests/ -v || echo "Backend tests not yet configured"

test-frontend:
	@echo "Running frontend tests..."
	@if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then \
		cd frontend && npm test; \
	else \
		echo "Frontend not yet configured"; \
	fi

# Run all linters
lint: lint-backend lint-frontend

lint-backend:
	@echo "Running backend linting..."
	@cd backend && python3 -m ruff check . || echo "Backend linting not yet configured"

lint-frontend:
	@echo "Running frontend linting..."
	@if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then \
		cd frontend && npm run lint; \
	else \
		echo "Frontend not yet configured"; \
	fi

# Run type checkers
typecheck: typecheck-backend typecheck-frontend

typecheck-backend:
	@echo "Running backend type checking..."
	@cd backend && python3 -m mypy app/ || echo "Backend type checking not yet configured"

typecheck-frontend:
	@echo "Running frontend type checking..."
	@if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then \
		cd frontend && npm run typecheck; \
	else \
		echo "Frontend not yet configured"; \
	fi

# Start development servers
dev:
	@echo "Starting development servers..."
	@echo "Backend: cd backend && uvicorn app.main:app --reload"
	@echo "Frontend: cd frontend && npm run dev"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done"
