"""Base interface for manifest processing plugins."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path


class HornetFlowPlugin(ABC):
    """Base interface for manifest processing plugins.

    All plugin methods are async to support non-blocking I/O operations.
    """

    @abstractmethod
    async def setup(
        self,
        repo_path: Path,
        manifest_path: Path,
        logger: logging.Logger,
        repo_url: str | None = None,
        repo_commit: str | None = None,
    ) -> None:
        """Initialize plugin with repository and manifest context.

        Args:
            repo_path: Path to the repository root
            manifest_path: Path to the manifest file being processed
            logger: Logger instance for plugin to use
            repo_url: Repository URL from release info (if available)
            repo_commit: Repository commit hash from release info (if available)
        """

    @abstractmethod
    async def load_component(
        self,
        component_id: str,
        component_type: str,
        component_description: str | None,
        component_files: list[Path],
        component_parent_path: list[str],
    ) -> bool:
        """
        Process a single component from the manifest.

        Args:
            component_id: ID of the component
            component_type: Type of the component
            component_description: Description of the component, if any
            component_files: List of resolved file paths for this component
            component_parent_id: Path to parent components as list of IDs

        Returns:
            True if successful, False if failed
        """

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up plugin resources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name for CLI selection."""
