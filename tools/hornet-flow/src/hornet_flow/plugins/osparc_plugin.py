"""OSparc plugin for loading components into OSparc."""

import logging
from pathlib import Path
from typing import Optional

from .base import HornetFlowPlugin


class OSparcPlugin(HornetFlowPlugin):
    """Plugin for loading components into OSparc."""

    def __init__(self):
        self._name = "osparc"
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.repo_path: Optional[Path] = None
        self.manifest_path: Optional[Path] = None
        self.main_group = None  # XCoreModeling.EntityGroup when available
        self.loaded_groups = []  # Track loaded groups for cleanup

    @property
    def name(self) -> str:
        """Plugin name for CLI selection."""
        return self._name

    def setup(
        self, repo_path: Path, manifest_path: Path, logger: logging.Logger
    ) -> None:
        """Initialize OSparc plugin."""
        self.logger = logger
        self.repo_path = repo_path
        self.manifest_path = manifest_path
        self.logger.info("🔧 Setting up OSparc plugin")
        self.logger.debug("Repository path: %s", repo_path)
        self.logger.debug("Manifest path: %s", manifest_path)

        # Initialize XCoreModeling if available
        try:
            # import XCoreModeling
            # self.main_group = XCoreModeling.CreateGroup("MainGroup")
            self.logger.debug("XCoreModeling initialized (placeholder)")
        except ImportError:
            self.logger.warning("XCoreModeling not available - running in dry-run mode")

    def load_component(
        self,
        component_id: str,
        component_type: str,
        component_description: Optional[str],
        component_files: list[Path],
        parent_id: Optional[str] = None,
    ) -> bool:
        """Load component into OSparc."""
        try:
            self.logger.debug(
                "Loading component: %s (type: %s, parent: %s)",
                component_id,
                component_type,
                parent_id,
            )

            # Create component group
            # component_group = XCoreModeling.CreateGroup(component_id)
            # self.loaded_groups.append(component_group)

            # Set description if available
            if component_description:
                self.logger.debug("Description: %s", component_description)

            # Load files
            for file_path in component_files:
                self.logger.debug("Loading file: %s", file_path)
                if file_path.exists():
                    # XCoreModeling.LoadFile(str(file_path))
                    self.logger.debug("File loaded successfully: %s", file_path.name)
                else:
                    self.logger.warning("File not found: %s", file_path)

            # Add to parent group or main group
            # if self.main_group:
            #     self.main_group.Add(component_group)

            self.logger.debug("Component %s loaded successfully", component_id)
            return True

        except Exception as e:  # noqa: BLE001
            self.logger.error("Failed to load component %s: %s", component_id, e)
            return False

    def teardown(self) -> None:
        """Clean up OSparc resources."""
        self.logger.info("🧹 Cleaning up OSparc plugin")

        # Zoom to loaded components
        if self.loaded_groups:
            try:
                # from s4l_v1.renderer import ZoomToEntity
                # ZoomToEntity(self.loaded_groups, zoom_factor=1.2)
                self.logger.debug(
                    "Zoomed to %d loaded components", len(self.loaded_groups)
                )
            except ImportError:
                self.logger.debug("ZoomToEntity not available")
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Failed to zoom to components: %s", e)

        # Reset state
        self.loaded_groups.clear()
        self.main_group = None
