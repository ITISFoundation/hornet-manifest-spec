"""OSparc plugin for loading components into OSparc."""

import logging
from pathlib import Path
from typing import Optional

import XCoreModeling

from .base import HornetFlowPlugin


class OSparcPlugin(HornetFlowPlugin):
    """Plugin for loading components into OSparc."""

    def __init__(self):
        self._name = "osparc"
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._repo_path: Optional[Path] = None
        self._manifest_path: Optional[Path] = None
        self._main_group: Optional[XCoreModeling.EntityGroup] = (
            None  # XCoreModeling.EntityGroup when available
        )
        self._loaded_groups: list[
            XCoreModeling.EntityGroup
        ] = []  # Track loaded groups for cleanup

    @property
    def name(self) -> str:
        """Plugin name for CLI selection."""
        return self._name

    def setup(
        self, repo_path: Path, manifest_path: Path, logger: logging.Logger
    ) -> None:
        """Initialize OSparc plugin."""
        self._logger = logger
        self._repo_path = repo_path
        self._manifest_path = manifest_path

        # Verify s4l model
        _ = XCoreModeling.GetActiveModel()

        # TODO: check if group with same name exists
        # Create a new group for this repository
        self._main_group = XCoreModeling.CreateGroup(repo_path.name)

    def load_component(
        self,
        component_id: str,
        component_type: str,
        component_description: Optional[str],
        component_files: list[Path],  # these are verified paths!!
        parent_id: Optional[str] = None,
    ) -> bool:
        """Load component into OSparc."""
        try:
            # 1. Create a group for the component and set name
            component_group = XCoreModeling.CreateGroup(component_id)
            self._loaded_groups.append(component_group)

            # 2. Save metadata in Group name Properties
            component_group.SetDescription("hornet.description", component_description)
            component_group.SetDescription("hornet.component_id", component_id)
            component_group.SetDescription("hornet.component_type", component_type)

            # 3. Load component trying at least one of the provided files
            is_file_imported = False
            for component_path in component_files:
                try:
                    imported_entities = XCoreModeling.Import(str(component_path))

                except Exception:  # pylint: disable=broad-exception-caught
                    # FIXME: should be exceptionr elated with Import, not path existence etc
                    self._logger.warning(
                        "Cannot import %s, let's check next ...", component_path
                    )

                else:
                    component_group.Add(imported_entities)
                    self._logger.info(
                        "Successfully imported %d entities for component %s using %s",
                        len(imported_entities),
                        component_id,
                        component_path,
                    )
                    is_file_imported = True
                    break

            if not is_file_imported:
                raise FileNotFoundError(
                    f"No valid files could be loaded for component '{component_id}'"
                )

            # 4. Add component_group to main group or parent group
            assert self._main_group  # nosec

            if parent_id is None:
                self._main_group.Add(component_group)
                return True

            # Search for parent group in loaded groups
            # FIXME: parent_id is in realaity a path, not just a name! we need here a name
            parent_group = next(
                (
                    grp
                    for grp in self._loaded_groups
                    if grp.GetDescription("hornet.component_id") == parent_id
                ),
                None,
            )
            if not parent_group:
                parent_group = self._main_group

            parent_group.Add(component_group)
            self._logger.debug(
                "Added group '%s' to parent group '%s'",
                component_group.Name,
                parent_group.Name,
            )

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self._logger.exception("Failed to load component %s: %s", component_id, e)
            return False

    def teardown(self) -> None:
        """Clean up OSparc resources."""
        self._logger.info("🧹 Cleaning up OSparc plugin")

        # Zoom to loaded components
        if self._loaded_groups:
            try:
                from s4l_v1.renderer import ZoomToEntity

                ZoomToEntity(self._loaded_groups, zoom_factor=1.2)
            except Exception as e:  # pylint: disable=broad-exception-caught
                self._logger.warning("Failed to zoom to components: %s", e)

        # Reset state
        self._loaded_groups.clear()
        self._main_group = None
