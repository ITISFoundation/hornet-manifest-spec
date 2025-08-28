.PHONY: help clean clean-dry clean-all clean-ignored

# Default target
help:
	@echo "Root Makefile - Available targets:"
	@echo "  clean         - Clean files that git would ignore (safe)"
	@echo "  clean-dry     - Show what would be cleaned (dry run)"
	@echo "  clean-ignored - Clean only ignored files (git clean -fX)"
	@echo "  clean-all     - Clean everything untracked (git clean -fdx)"

# Clean files based on .gitignore (safe - only removes ignored files)
clean:
	@echo "Cleaning files that git would ignore..."
	@if git status --porcelain --ignored | grep '^!!' > /dev/null; then \
		git clean -fX; \
		echo "✓ Cleanup complete"; \
	else \
		echo "✓ Nothing to clean"; \
	fi

# Show what would be cleaned (dry run)
clean-dry:
	@echo "Files that would be cleaned:"
	@git clean -fXd --dry-run

# Clean only ignored files (safer than clean-all)
clean-ignored:
	@echo "Cleaning ignored files and directories..."
	git clean -fXd
	@echo "✓ Ignored files cleaned"

# Nuclear option - clean everything untracked
clean-all:
	@echo "WARNING: This will remove ALL untracked files and directories!"
	@echo "Files that would be removed:"
	@git clean -fdx --dry-run
	@echo ""
	@printf "Are you sure? [y/N] "; \
	read REPLY; \
	case "$$REPLY" in \
		[Yy]|[Yy][Ee][Ss]) \
			git clean -fdx; \
			echo "✓ Complete cleanup done" ;; \
		*) \
			echo "Cleanup cancelled" ;; \
	esac