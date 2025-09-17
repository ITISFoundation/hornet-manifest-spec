.PHONY: help test test-unit test-integration lint clean clean-venv install install-dev install-lint install-all install-uv venv run-example run-dry check-deps validate-code test-coverage dev-setup ci

# Default target
help:
	@echo "Available targets:"
	@echo "  install-uv      - Install uv package manager"
	@echo "  venv            - Create virtual environment"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration- Run integration tests only"
	@echo "  lint            - Run code linting"
	@echo "  clean           - Clean up temporary files"
	@echo "  clean-venv      - Remove virtual environment"
	@echo "  install         - Install package in editable mode"
	@echo "  install-dev     - Install dev dependency group"
	@echo "  install-lint    - Install lint dependency group"
	@echo "  install-all     - Install all dependency groups"
	@echo "  run-example     - Run workflow with example metadata"
	@echo "  run-clone-example - Run repo clone example"
	@echo "  run-validate-example - Run manifest validation example"
	@echo "  run-show-example - Run manifest show example"

# Install uv
install-uv:
	@echo "Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "✓ uv installed. You may need to restart your shell or run 'source ~/.bashrc'"

# Virtual environment
venv: check-deps
	@echo "Creating virtual environment..."
	@if [ ! -d ".venv" ]; then \
		uv venv; \
		echo "✓ Virtual environment created at .venv"; \
	else \
		echo "✓ Virtual environment already exists"; \
	fi

# Test targets
test:
	@echo "Running all tests..."
	uv run pytest test.py -v

test-unit:
	@echo "Running unit tests..."
	uv run pytest test.py -v -k "not integration"

test-integration:
	@echo "Running integration tests..."
	uv run pytest test.py -v -k "integration"

lint:
	@echo "Running code linting..."
	uv run ruff check src/ test.py
	uv run ruff format --check src/ test.py


# Dependencies
install: venv
	@echo "Installing package in editable mode with dependencies..."
	uv sync
	@echo "✓ Package installed in editable mode"

install-dev: venv
	@echo "Installing dev dependency group..."
	uv sync --group dev

install-lint: venv
	@echo "Installing lint dependency group..."
	uv sync --group lint

install-all: venv
	@echo "Installing all dependency groups..."
	uv sync --all-groups

# Example runs
run-example:
	@echo "Running workflow with example metadata..."
	uv run hornet-flow workflow run --metadata-file examples/portal-device-metadata.json --work-dir /tmp/hornet-flow --verbose


run-clone-example:
	@echo "Running repo clone example..."
	mkdir -p /tmp/hornet-electrodes
	uv run hornet-flow repo clone --repo-url https://github.com/COSMIIC-Inc/Implantables-Electrodes --dest /tmp/hornet-electrodes --verbose

run-validate-example:
	@echo "Running manifest validation example..."
	uv run hornet-flow manifest validate --repo-path /tmp/hornet-electrodes --verbose

run-show-example:
	@echo "Running manifest show example..."
	uv run hornet-flow manifest show --repo-path /tmp/hornet-electrodes --type cad --verbose


# Utility targets
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf /tmp/hornet*

clean-venv:
	@echo "Removing virtual environment..."
	rm -rf .venv
	@echo "✓ Virtual environment removed"

# Development helpers
check-deps:
	@echo "Checking if uv is available..."
	@command -v uv >/dev/null 2>&1 || (echo "✗ uv not found. Run 'make install-uv'"; exit 1)
	@echo "✓ uv is available"

validate-code:
	@echo "Validating code with ruff..."
	uv run ruff check src/ test.py
	@echo "✓ Code validation passed"

# Test with coverage
test-coverage:
	@echo "Running tests with coverage..."
	uv run --with pytest-cov --with pytest-mock pytest test.py --cov=src/hornet_flow --cov-report=html --cov-report=term

# Full development workflow
dev-setup: check-deps venv install-all validate-code test
	@echo "✓ Development setup complete"

# CI-like workflow
ci: check-deps venv install-lint validate-code lint test
	@echo "✓ CI checks passed"
