# Leaderboard Service Development Makefile

.PHONY: help install test coverage check-coverage lint format clean setup-dev mutate mutate-html mutate-browse mutate-results mutate-clean test-integration test-integration-only test-all

# Default target
help:
	@echo "Leaderboard Service Development Commands"
	@echo "======================================="
	@echo ""
	@echo "Setup:"
	@echo "  setup-dev     Set up development environment"
	@echo "  install       Install dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test          Run unit tests only"
	@echo "  test-integration Run integration tests (requires Docker)"
	@echo "  test-all      Run both unit and integration tests"
	@echo "  coverage      Run tests with coverage report"
	@echo "  check-coverage Run dynamic coverage threshold check"
	@echo ""
	@echo "Mutation Testing:"
	@echo "  mutate        Run mutation tests"
	@echo "  mutate-html   Run mutation tests with HTML report"
	@echo "  mutate-browse Interactive mutation test browser"
	@echo "  mutate-results Show mutation test results"
	@echo "  mutate-clean  Clean mutation test artifacts"
	@echo ""
	@echo "Quick Start Scripts:"
	@echo "  ./scripts/mutate-local.sh        One-command mutation testing"
	@echo "  ./scripts/mutate-local.sh --quick  Quick test (models.py only)"
	@echo "  ./scripts/mutation-report.py    Enhanced result analysis"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          Run linting (black, ruff, mypy)"
	@echo "  format        Format code with black"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean         Remove temporary files and caches"

# Setup development environment
setup-dev:
	@echo "🔧 Setting up development environment..."
	python -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt -r requirements-dev.txt
	@echo "✅ Development environment ready!"
	@echo "💡 Activate with: source venv/bin/activate"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Run unit tests only
test:
	@echo "🧪 Running unit tests..."
	PYTHONPATH=$(PWD) ./venv/bin/pytest tests/unit/ -v

# Run tests with coverage
coverage:
	@echo "📊 Running unit tests with coverage..."
	PYTHONPATH=$(PWD) ./venv/bin/pytest tests/unit/ --cov=src --cov-report=term-missing --cov-report=html
	@echo "📈 Coverage report generated in htmlcov/"

# Run dynamic coverage check (same as CI)
check-coverage:
	@echo "🎯 Running dynamic coverage threshold check..."
	./venv/bin/python scripts/check-coverage.py

# Run linting
lint:
	@echo "🔍 Running linting checks..."
	./venv/bin/black --check src/ tests/
	./venv/bin/ruff check src/ tests/
	./venv/bin/mypy src/

# Format code
format:
	@echo "✨ Formatting code..."
	./venv/bin/black src/ tests/
	./venv/bin/ruff check --fix src/ tests/

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

# Run mutation tests
mutate:
	@echo "🦠 Running mutation tests..."
	./venv/bin/mutmut run

# Run mutation tests with HTML report
mutate-html:
	@echo "🦠 Running mutation tests with HTML report..."
	./venv/bin/mutmut run
	./venv/bin/mutmut html
	@echo "📊 HTML report generated in html/"

# Interactive mutation test browser
mutate-browse:
	@echo "🔍 Opening interactive mutation test browser..."
	./venv/bin/mutmut browse

# Show mutation test results
mutate-results:
	@echo "📋 Mutation test results:"
	./venv/bin/mutmut results

# Clean mutation test artifacts
mutate-clean:
	@echo "🧹 Cleaning mutation test artifacts..."
	rm -rf .mutmut-cache/
	rm -rf html/
	rm -f mutmut.log

# Run integration tests
test-integration:
	@echo "🐳 Running integration tests (requires Docker)..."
	@echo "⚠️  This will start LocalStack containers"
	PYTHONPATH=$(PWD) ./venv/bin/pytest tests/integration/ -v --tb=short

# Run all tests (unit + integration)
test-all:
	@echo "🧪 Running all tests..."
	PYTHONPATH=$(PWD) ./venv/bin/pytest tests/ -v --tb=short

# Variables for colors
RESET=\033[0m
BOLD=\033[1m
GREEN=\033[32m
YELLOW=\033[33m
BLUE=\033[34m