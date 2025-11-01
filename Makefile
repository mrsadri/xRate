.PHONY: help install install-dev run test lint fmt typecheck clean docker-build docker-run

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

run: ## Run the bot
	python -m xrate

test: ## Run tests
	pytest

lint: ## Run linter (ruff)
	ruff check src/ tests/

fmt: ## Format code (black + isort)
	black src/ tests/
	isort src/ tests/

typecheck: ## Run type checker (mypy)
	mypy src/

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

docker-build: ## Build Docker image
	docker build -f deploy/docker/Dockerfile -t xrate:latest .

docker-run: ## Run Docker container
	docker-compose -f deploy/docker/docker-compose.yml up

