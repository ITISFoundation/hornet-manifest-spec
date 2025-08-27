.PHONY: help test test-unit test-integration lint clean install install-uv run-example

# Default target
help:
	@echo "Available targets:"
	@echo "  install-uv      - Install uv package manager"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration- Run integration tests only"
	@echo "  lint            - Run code linting"
	@echo "  clean           - Clean up temporary files"
	@echo "  install         - Install development dependencies"
	@echo "  run-example     - Run loader with example metadata"
	@echo "  run-dry         - Run loader in dry-run mode"

# Install uv
install-uv:
	@echo "Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "✓ uv installed. You may need to restart your shell or run 'source ~/.bashrc'"

# Test targets
test:
	@echo "Running all tests..."
	uv run --with pytest --with pytest-mock pytest test_hornet_manifest_loader.py -v

test-unit:
	@echo "Running unit tests only..."
	uv run --with pytest --with pytest-mock pytest test_hornet_manifest_loader.py -v -k "not test_create_sample_manifest_and_validate"

test-integration:
	@echo "Running integration tests only..."
	uv run --with pytest --with pytest-mock pytest test_hornet_manifest_loader.py -v -k "test_create_sample_manifest_and_validate"

# Code quality
lint:
	@echo "Running code linting..."
	uv run --with flake8 flake8 hornet_manifest_loader.py test_hornet_manifest_loader.py --max-line-length=100 --ignore=E501
	uv run --with pylint pylint hornet_manifest_loader.py --disable=C0103,R0903,R0912,R0915

# Dependencies
install:
	@echo "Installing development dependencies..."
	@echo "Note: Runtime dependencies are handled by inline script metadata in hornet_manifest_loader.py"
	@echo "Development tools will be installed as needed via uv run --with"

# Example runs
run-example:
	@echo "Running loader with example metadata..."
	uv run hornet_manifest_loader.py ../examples/sample_metadata.json --work-dir /tmp/hornet_test --verbose

run-dry:
	@echo "Running loader in dry-run mode..."
	uv run hornet_manifest_loader.py ../examples/sample_metadata.json --dry-run --work-dir /tmp/hornet_test --verbose

run-quiet:
	@echo "Running loader in quiet mode..."
	uv run hornet_manifest_loader.py ../examples/sample_metadata.json --work-dir /tmp/hornet_test --quiet

# Utility targets
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf /tmp/hornet_test_*

# Development helpers
check-deps:
	@echo "Checking if uv is available..."
	@command -v uv >/dev/null 2>&1 || (echo "✗ uv not found. Run 'make install-uv'"; exit 1)
	@echo "✓ uv is available"

validate-code:
	@echo "Validating Python syntax..."
	uv run -c "import py_compile; py_compile.compile('hornet_manifest_loader.py', doraise=True)"
	uv run -c "import py_compile; py_compile.compile('test_hornet_manifest_loader.py', doraise=True)"
	@echo "✓ Code syntax is valid"


# Test with coverage
test-coverage:
	@echo "Running tests with coverage..."
	uv run --with pytest --with pytest-cov --with pytest-mock pytest test_hornet_manifest_loader.py --cov=hornet_manifest_loader --cov-report=html --cov-report=term

# Full development workflow
dev-setup: check-deps validate-code test
	@echo "✓ Development setup complete"

# CI-like workflow
ci: check-deps validate-code lint test
	@echo "✓ CI checks passed"
