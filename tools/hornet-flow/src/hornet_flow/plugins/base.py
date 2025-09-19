"""Base interface for manifest processing plugins."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class HornetFlowPlugin(ABC):
    """Base interface for manifest processing plugins."""

    @abstractmethod
    def setup(
        self,
        repo_path: Path,
        manifest_path: Path,
        logger: logging.Logger,
        repo_url: Optional[str] = None,
        repo_commit: Optional[str] = None,
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
    def load_component(
        self,
        component_id: str,
        component_type: str,
        component_description: Optional[str],
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
    def teardown(self) -> None:
        """Clean up plugin resources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name for CLI selection."""
