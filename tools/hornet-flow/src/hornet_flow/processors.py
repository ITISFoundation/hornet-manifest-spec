"""Manifest processing orchestration."""

import logging
from pathlib import Path
from typing import Optional

from hornet_flow import service
from hornet_flow.plugins import get_plugin
from hornet_flow.plugins.base import HornetFlowPlugin

from .model import Component


class ManifestProcessor:
    """Orchestrates the processing of manifest components through plugins."""

    def __init__(self, plugin_name: str, logger: logging.Logger):
        self.plugin_name = plugin_name
        self.logger = logger
        self.plugin_instance: Optional[HornetFlowPlugin] = None

    def process_manifest(
        self,
        manifest_path: Path,
        repo_path: Path,
        fail_fast: bool = False,
        type_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
    ) -> tuple[int, int]:
        """
        Process a manifest file using the configured plugin.

        Returns:
            Tuple of (successful_components, total_components)

        Raises:
            ValueError: If plugin cannot be found or loaded
            FileNotFoundError: If required files are missing (when fail_fast=True)
            RuntimeError: If component processing fails (when fail_fast=True)
        """
        try:
            # 1. Setup plugin
            plugin_class = get_plugin(self.plugin_name)
            self.plugin_instance: HornetFlowPlugin = plugin_class()
            self.plugin_instance.setup(repo_path, manifest_path, self.logger)

            # 2. Load and process manifest
            manifest_data = service.read_manifest_contents(manifest_path)
            return self._process_components(
                manifest_data,
                manifest_path,
                repo_path,
                fail_fast,
                type_filter,
                name_filter,
            )

        finally:
            # 3. Cleanup
            if self.plugin_instance:
                self.plugin_instance.teardown()
                self.plugin_instance = None

    def _process_components(
        self,
        manifest_data: dict,
        manifest_path: Path,
        repo_path: Path,
        fail_fast: bool,
        type_filter: Optional[str],
        name_filter: Optional[str],
    ) -> tuple[int, int]:
        """Process individual components from manifest data."""
        success_count = 0
        total_count = 0

        for component in service.walk_manifest_components(manifest_data):
            total_count += 1

            # Apply filters
            if not self._should_process_component(component, type_filter, name_filter):
                continue

            # Resolve and validate files
            component_files = self._resolve_component_files(
                component, manifest_path, repo_path, fail_fast
            )

            # Process with plugin
            if self._process_single_component(component, component_files, fail_fast):
                success_count += 1

        return success_count, total_count

    def _should_process_component(
        self,
        component: Component,
        type_filter: Optional[str],
        name_filter: Optional[str],
    ) -> bool:
        """Check if component should be processed based on filters."""
        if type_filter and component.type != type_filter:
            self.logger.debug("Skipping component %s due to type filter", component.id)
            return False
        if name_filter and name_filter.lower() not in component.id.lower():
            self.logger.debug("Skipping component %s due to name filter", component.id)
            return False
        return True

    def _resolve_component_files(
        self,
        component: Component,
        manifest_path: Path,
        repo_path: Path,
        fail_fast: bool,
    ) -> list[Path]:
        """Resolve component file paths and validate existence."""
        component_files = []
        for file_obj in component.files:
            file_path = service.resolve_component_file_path(
                manifest_path, file_obj.path, repo_path
            )
            if file_path.exists():
                component_files.append(file_path)
            else:
                self.logger.error("Missing file: %s", file_path)
                if fail_fast:
                    raise FileNotFoundError(f"Missing file: {file_path}")
        return component_files

    def _process_single_component(
        self, component: Component, component_files: list[Path], fail_fast: bool
    ) -> bool:
        """Process a single component with the plugin."""
        assert self.plugin_instance is not None  # nosec Should be set by process_manifest

        try:
            parent_id = "/".join(component.parent_id) if component.parent_id else None
            success = self.plugin_instance.load_component(
                component_id=component.id,
                component_type=component.type,
                component_description=component.description,
                component_files=component_files,
                parent_id=parent_id,
            )

            if success:
                self.logger.debug("Processed component: %s", component.id)
                return True
            else:
                self.logger.error("Failed to process component: %s", component.id)
                if fail_fast:
                    raise RuntimeError(f"Failed to process component: {component.id}")
                return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Plugin error processing %s: %s", component.id, e)
            if fail_fast:
                raise
            return False
