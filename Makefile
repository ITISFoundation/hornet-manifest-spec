include ./common.mk
.PHONY: clean clean-dry clean-all clean-ignored

clean: ## Clean files based on .gitignore (safe - only removes ignored files)
	@$(MAKE) -f common.mk clean_common

clean-dry: ## Show what would be cleaned (dry run)
	@echo "Files that would be cleaned:"
	@git clean -fXd --dry-run

clean-ignored: ## Clean only ignored files (safer than clean-all)
	@echo "Cleaning ignored files and directories..."
	git clean -fXd
	@echo "✓ Ignored files cleaned"

clean-all: ## Nuclear option - clean everything untracked
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
