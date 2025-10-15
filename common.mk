# Common Makefile for shared targets and documentation
# Usage: include this file at the top of your Makefile

.PHONY: help clean_common
help:  ## Show this help message
	@echo "Available targets in $(MAKEFILE_LIST):"
	@grep -h -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Internal target: do not use directly, not shown in help
clean_common:
	@echo "Cleaning files that git would ignore..."
	@if git status --porcelain --ignored | grep '^!!' > /dev/null; then \
		git clean -fX; \
		echo "✓ Cleanup complete"; \
	else \
		echo "✓ Nothing to clean"; \
	fi

.PHONY: info
info: ## displays tools versions
	@echo ' awk           : $(shell awk -W version 2>&1 | head -n 1)'
	@echo ' make          : $(shell make --version 2>&1 | head -n 1)'
	@echo ' python        : $(shell python3 --version) ($(shell which python3))'
	@echo ' uv            : $(shell uv --version 2> /dev/null || echo ERROR uv missing)'
	@echo ' ubuntu        : $(shell lsb_release --description --short 2> /dev/null | tail || echo ERROR Not an Ubuntu OS )'