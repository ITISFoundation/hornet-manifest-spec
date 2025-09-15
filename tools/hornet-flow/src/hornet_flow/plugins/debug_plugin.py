"""Debug plugin for testing manifest processing."""

import logging
from pathlib import Path
from typing import Any, Optional

from .base import HornetFlowPlugin


class DebugPlugin(HornetFlowPlugin):
    """Simple debug plugin that logs component information."""

    def __init__(self):
        self._name = "debug"
        self.logger: Optional[logging.Logger] = None
        self.component_count = 0

    @property
    def name(self) -> str:
        """Plugin name for CLI selection."""
        return self._name

    def setup(
        self, repo_path: Path, manifest_path: Path, logger: logging.Logger
    ) -> None:
        """Initialize debug plugin."""
        self.logger = logger
        self.component_count = 0
        if self.logger:
            self.logger.info("🐛 Setting up Debug plugin")
            self.logger.debug("Repository: %s", repo_path)
            self.logger.debug("Manifest: %s", manifest_path)

    def load_component(
        self,
        component: dict[str, Any],
        component_files: list[Path],
        parent_id: Optional[str] = None,
    ) -> bool:
        """Process component with debug logging."""
        self.component_count += 1

        if self.logger:
            self.logger.info(
                "🔍 Component #%d: %s",
                self.component_count,
                component.get("id", "unknown"),
            )
            self.logger.info("   Type: %s", component.get("type", "unknown"))
            self.logger.info("   Parent: %s", parent_id or "None")
            self.logger.info("   Files: %d", len(component_files))

            for i, file_path in enumerate(component_files, 1):
                self.logger.info("     %d. %s", i, file_path.name)

        # Always succeed
        return True

    def teardown(self) -> None:
        """Clean up debug plugin."""
        if self.logger:
            self.logger.info(
                "🐛 Debug plugin processed %d components", self.component_count
            )
