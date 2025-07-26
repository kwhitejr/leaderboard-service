# Leaderboard Service Development Makefile

.PHONY: help install test coverage check-coverage lint format clean setup-dev

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
	@echo "  test          Run all tests"
	@echo "  coverage      Run tests with coverage report"
	@echo "  check-coverage Run dynamic coverage threshold check"
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
	pip install --upgrade pip
	pip install -r requirements.txt -r requirements-dev.txt

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

# Run tests with coverage
coverage:
	@echo "📊 Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html
	@echo "📈 Coverage report generated in htmlcov/"

# Run dynamic coverage check (same as CI)
check-coverage:
	@echo "🎯 Running dynamic coverage threshold check..."
	python scripts/check-coverage.py

# Run linting
lint:
	@echo "🔍 Running linting checks..."
	black --check src/ tests/
	ruff check src/ tests/
	mypy src/

# Format code
format:
	@echo "✨ Formatting code..."
	black src/ tests/
	ruff check --fix src/ tests/

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

# Variables for colors
RESET=\033[0m
BOLD=\033[1m
GREEN=\033[32m
YELLOW=\033[33m
BLUE=\033[34m