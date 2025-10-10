include ../../common.mk

# Directory variables
TYPINGS_DIR := typings
DIST_STUBS_DIR := dist/type-stubs

.PHONY: test test-unit test-integration lint clean clean-venv install-uv venv run-example run-dry check-deps validate-code test-coverage dev-setup ci

install-uv:
	@echo "Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "✓ uv installed. You may need to restart your shell or run 'source ~/.bashrc'"


# Virtual environment
venv: check-deps ## Creates virtual env in .venv
	@echo "Creating virtual environment..."
	@if [ ! -d ".venv" ]; then \
		uv venv; \
		echo "✓ Virtual environment created at .venv"; \
	else \
		echo "✓ Virtual environment already exists"; \
	fi

# Install and build
.PHONY: install install-dev install-from-git install-lint install-all

install: venv
	@echo "Installing package in editable mode with dependencies..."
	uv sync
	@echo "✓ Package installed in editable mode"

install-dev: venv ## Install from local repository
	@echo "Installing dev dependency group..."
	uv sync --group dev


install-from-git:  ## Install from remote gh repository
	uv pip install "git+https://github.com/ITISFoundation/hornet-manifest-spec.git@main#subdirectory=tools/hornet-flow"

install-lint: venv
	@echo "Installing lint dependency group..."
	uv sync --group lint

install-all: venv
	@echo "Installing all dependency groups..."
	uv sync --all-groups

install-types: venv
	@echo "Installing typing dependencies..."
	uv add --group dev pyright


.PHONY: build
build:  ## Build the package
	uv build

.PHONY: type-stubs type-stubs-package
type-stubs: install-types ## Generate type stubs (.pyi files)
	@echo "Generating type stubs with pyright..."
	uv run pyright --createstub hornet_flow
	@echo "✓ Type stubs generated in $(TYPINGS_DIR)/ directory"

type-stubs-package: type-stubs ## Package type stubs for distribution
	@echo "Creating type stubs package..."
	@mkdir -p $(DIST_STUBS_DIR)
	@cp -r $(TYPINGS_DIR)/hornet_flow $(DIST_STUBS_DIR)/
	@echo "Creating py.typed marker file..."
	@touch $(DIST_STUBS_DIR)/hornet_flow/py.typed
	@echo "Creating __init__.py for stubs package..."
	@echo "# Type stubs for hornet-flow" > $(DIST_STUBS_DIR)/hornet_flow/__init__.pyi
	@echo "✓ Type stubs packaged in $(DIST_STUBS_DIR)/"

# Test targets
test:  ## Run tests
	@echo "Running all tests..."
	uv run pytest -v test.py

test-unit:
	@echo "Running unit tests..."
	uv run pytest test.py -v -k "not integration" .

test-integration:  ## Run integration tests
	@echo "Running integration tests..."
	uv run pytest -v -k "integration"

lint:  ## Run linting
	@echo "Running code linting..."
	uv run ruff check .
	uv run ruff format --check .

# Example runs for manual testing
run-example:
	@echo "Running workflow with example metadata..."
	hornet-flow workflow run --metadata-file examples/portal-device-metadata.json --work-dir /tmp/hornet-flow --verbose

run-clone-example:
	@echo "Running repo clone example..."
	mkdir -p /tmp/hornet-electrodes
	hornet-flow repo clone --repo-url https://github.com/COSMIIC-Inc/Implantables-Electrodes --dest /tmp/hornet-electrodes --verbose

run-validate-example:
	@echo "Running manifest validation example..."
	hornet-flow manifest validate --repo-path /tmp/hornet-electrodes --verbose

run-show-example:
	@echo "Running manifest show example..."
	hornet-flow manifest show --repo-path /tmp/hornet-electrodes --type cad --verbose --quiet


# Utility targets
# Clean files based on .gitignore (safe - only removes ignored files)
# Removes files and directories ignored by git, but leaves untracked files
clean: ## Clean files based on .gitignore (safe - only removes ignored files)
	@$(MAKE) -f ../common.mk clean_common
	@echo "Cleaning type stubs..."
	@rm -rf $(TYPINGS_DIR)/ $(DIST_STUBS_DIR)/
	@echo "✓ Type stubs cleaned"

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

dev-flow: check-deps venv install-all validate-code test ## runs full development workflow
	@echo "✓ Development workflow complete"

# CI-like workflow
ci: check-deps venv install-lint validate-code lint test
	@echo "✓ CI checks passed"

# Demo and testing targets
.PHONY: demo-watch
demo-watch:  ## Demo the workflow watch command (creates temp dirs and runs watcher)
	@echo "🚀 Setting up demo environment for workflow watch..."
	@mkdir -p /tmp/hornet-demo/{inputs,work}
	@echo "📁 Created directories:"
	@echo "   - Inputs: /tmp/hornet-demo/inputs"
	@echo "   - Work:   /tmp/hornet-demo/work"
	@echo ""
	@echo "🔧 Starting workflow watcher in single-file mode..."
	@echo "💡 In another terminal, copy a metadata.json file to /tmp/hornet-demo/inputs/"
	@echo "   Example: cp examples/portal-device-metadata.json /tmp/hornet-demo/inputs/metadata.json"
	@echo ""
	@echo "⚡ Starting watcher (Ctrl+C to stop)..."
	INPUTS_DIR=/tmp/hornet-demo/inputs WORK_DIR=/tmp/hornet-demo/work \
		uv run hornet-flow workflow watch --once --verbose

.PHONY: demo-watch-continuous
demo-watch-continuous:  ## Demo continuous workflow watching (runs until stopped)
	@echo "🚀 Setting up demo environment for continuous workflow watch..."
	@mkdir -p /tmp/hornet-demo/{inputs,work}
	@echo "📁 Created directories:"
	@echo "   - Inputs: /tmp/hornet-demo/inputs"
	@echo "   - Work:   /tmp/hornet-demo/work"
	@echo ""
	@echo "🔧 Starting continuous workflow watcher..."
	@echo "💡 In another terminal, copy metadata.json files to /tmp/hornet-demo/inputs/"
	@echo "   Each file will be processed automatically"
	@echo ""
	@echo "⚡ Starting watcher (Ctrl+C to stop)..."
	INPUTS_DIR=/tmp/hornet-demo/inputs WORK_DIR=/tmp/hornet-demo/work \
		uv run hornet-flow workflow watch --verbose

.PHONY: test-metadata
test-metadata:  ## Create test metadata file for demo
	@echo "📄 Creating test metadata.json file..."
	@mkdir -p /tmp/hornet-demo/inputs
	@cp examples/portal-device-metadata.json /tmp/hornet-demo/inputs/metadata.json
	@echo "✅ Created /tmp/hornet-demo/inputs/metadata.json"
	@echo "💡 Run 'make demo-watch' to process it"

.PHONY: clean-demo
clean-demo:  ## Clean up demo directories
	@echo "🧹 Cleaning up demo directories..."
	@rm -rf /tmp/hornet-demo
	@echo "✅ Demo directories cleaned"
