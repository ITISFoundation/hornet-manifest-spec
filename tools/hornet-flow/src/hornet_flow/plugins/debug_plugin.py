"""Debug plugin for testing manifest processing."""

import logging
from pathlib import Path

from .base import HornetFlowPlugin


class DebugPlugin(HornetFlowPlugin):
    """Simple debug plugin that logs component information."""

    def __init__(self):
        self._name = "debug"
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.component_count = 0

    @property
    def name(self) -> str:
        """Plugin name for CLI selection."""
        return self._name

    async def setup(
        self,
        repo_path: Path,
        manifest_path: Path,
        logger: logging.Logger,
        repo_url: str | None = None,
        repo_commit: str | None = None,
    ) -> None:
        """Initialize debug plugin."""
        self.logger = logger
        self.component_count = 0

        self.logger.info("🐛 Setting up Debug plugin")
        self.logger.info("-Repository: %s", repo_path)
        self.logger.info("-Manifest: %s", manifest_path)
        self.logger.info("-Logger: %s", logger.name)
        self.logger.info("-Repository URL: %s", repo_url)
        self.logger.info("-Repository commit: %s", repo_commit)

    async def load_component(
        self,
        component_id: str,
        component_type: str,
        component_description: str | None,
        component_files: list[Path],
        component_parent_path: list[str],
    ) -> bool:
        """Process component with debug logging."""
        self.component_count += 1

        self.logger.info("🔍 Component #%d: %s", self.component_count, component_id)
        self.logger.info("   Type: %s", component_type)
        self.logger.info(
            "   Parent: '%s'",
            "/".join(component_parent_path) if component_parent_path else "None",
        )
        self.logger.info(
            "   Description: %s",
            component_description if component_description else "No description",
        )
        self.logger.info("   Files: %d", len(component_files))

        for i, file_path in enumerate(component_files, 1):
            self.logger.info("     %d. %s", i, file_path.name)

        # Always succeed
        return True

    async def teardown(self) -> None:
        """Clean up debug plugin."""
        self.logger.info(
            "🐛 Debug plugin processed %d components", self.component_count
        )
