.PHONY: help test test-unit test-integration lint clean install run-example

# Default target
help:
	@echo "Available targets:"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration- Run integration tests only"
	@echo "  lint            - Run code linting"
	@echo "  clean           - Clean up temporary files"
	@echo "  install         - Install dependencies"
	@echo "  run-example     - Run loader with example metadata"
	@echo "  run-dry         - Run loader in dry-run mode"

# Test targets
test:
	@echo "Running all tests..."
	python -m pytest test_hornet_manifest_loader.py -v

test-unit:
	@echo "Running unit tests only..."
	python -m pytest test_hornet_manifest_loader.py -v -k "not test_create_sample_manifest_and_validate"

test-integration:
	@echo "Running integration tests only..."
	python -m pytest test_hornet_manifest_loader.py -v -k "test_create_sample_manifest_and_validate"

# Code quality
lint:
	@echo "Running code linting..."
	python -m flake8 hornet_manifest_loader.py test_hornet_manifest_loader.py --max-line-length=100 --ignore=E501
	python -m pylint hornet_manifest_loader.py --disable=C0103,R0903,R0912,R0915

# Dependencies
install:
	@echo "Installing dependencies..."
	pip install jsonschema requests flake8 pylint pytest pytest-mock

# Example runs
run-example:
	@echo "Running loader with example metadata..."
	@if [ -f "../examples/sample_metadata.json" ]; then \
		python hornet_manifest_loader.py ../examples/sample_metadata.json --work-dir /tmp/hornet_test --verbose; \
	else \
		echo "Error: No example metadata file found. Create ../examples/sample_metadata.json first."; \
	fi

run-dry:
	@echo "Running loader in dry-run mode..."
	@if [ -f "../examples/sample_metadata.json" ]; then \
		python hornet_manifest_loader.py ../examples/sample_metadata.json --dry-run --work-dir /tmp/hornet_test --verbose; \
	else \
		echo "Error: No example metadata file found. Create ../examples/sample_metadata.json first."; \
	fi

run-quiet:
	@echo "Running loader in quiet mode..."
	@if [ -f "../examples/sample_metadata.json" ]; then \
		python hornet_manifest_loader.py ../examples/sample_metadata.json --work-dir /tmp/hornet_test --quiet; \
	else \
		echo "Error: No example metadata file found. Create ../examples/sample_metadata.json first."; \
	fi

# Utility targets
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf /tmp/hornet_test_*

# Development helpers
check-deps:
	@echo "Checking dependencies..."
	@python -c "import jsonschema, requests, pytest; print('✓ All dependencies available')" || \
		(echo "✗ Missing dependencies. Run 'make install'"; exit 1)

validate-code:
	@echo "Validating Python syntax..."
	python -m py_compile hornet_manifest_loader.py
	python -m py_compile test_hornet_manifest_loader.py
	@echo "✓ Code syntax is valid"

# Create example metadata for testing
create-example:
	@echo "Creating example metadata file..."
	@mkdir -p ../examples
	@cat > ../examples/sample_metadata.json << 'EOF'
{
    "datePublished": "2025-01-24",
    "pennsieveDatasetId": 422,
    "version": 1,
    "name": "Example/hornet-test",
    "description": "Example repository for testing hornet manifest loader",
    "files": [
        {
            "name": "test.zip",
            "path": "assets/test.zip",
            "size": 1000,
            "fileType": "ZIP",
            "sha256": "abc123def456"
        }
    ],
    "release": {
        "origin": "GitHub",
        "url": "https://github.com/ITISFoundation/hornet-manifest-spec",
        "label": "1.0.0",
        "marker": "main"
    }
}
EOF
	@echo "✓ Created ../examples/sample_metadata.json"

# Test with coverage
test-coverage:
	@echo "Running tests with coverage..."
	python -m pytest test_hornet_manifest_loader.py --cov=hornet_manifest_loader --cov-report=html --cov-report=term

# Full development workflow
dev-setup: install validate-code test
	@echo "✓ Development setup complete"

# CI-like workflow
ci: check-deps validate-code lint test
	@echo "✓ CI checks passed"
