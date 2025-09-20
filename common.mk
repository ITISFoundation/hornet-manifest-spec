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
