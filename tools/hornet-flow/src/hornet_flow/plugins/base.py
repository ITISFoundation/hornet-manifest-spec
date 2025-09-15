"""Base interface for manifest processing plugins."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class HornetFlowPlugin(ABC):
    """Base interface for manifest processing plugins."""

    @abstractmethod
    def setup(
        self, repo_path: Path, manifest_path: Path, logger: logging.Logger
    ) -> None:
        """Initialize plugin with repository and manifest context.

        Args:
            repo_path: Path to the repository root
            manifest_path: Path to the manifest file being processed
            logger: Logger instance for plugin to use
        """

    @abstractmethod
    def load_component(
        self,
        component: dict[str, Any],
        component_files: list[Path],
        parent_id: Optional[str] = None,
    ) -> bool:
        """
        Process a single component from the manifest.

        Args:
            component: Component data from manifest (id, type, description, etc.)
            component_files: List of resolved file paths for this component
            parent_id: ID of parent component if this is nested

        Returns:
            True if successful, False if failed
        """

    @abstractmethod
    def teardown(self) -> None:
        """Clean up plugin resources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name for CLI selection."""
