"""Manifest processing orchestration."""

import asyncio
import logging
from pathlib import Path

from hornet_flow.logging_utils import log_lifespan
from hornet_flow.plugins import get_default_plugin, get_plugin
from hornet_flow.plugins.base import HornetFlowPlugin

from ..model import Component, Release
from . import git_service, manifest_service


class PluginProcessingError(Exception):
    """Exception raised for errors in plugin processing."""

    def __init__(self, msg: str, *args):
        super().__init__(msg % args)


class ManifestProcessor:
    """Orchestrates the processing of manifest components through plugins."""

    def __init__(
        self,
        plugin_name: str | None,
        logger: logging.Logger,
        concurrent_components: bool = False,
    ):
        self.logger = logger
        # plugin
        self.plugin_name = plugin_name or get_default_plugin()
        self.plugin_class = get_plugin(self.plugin_name)
        self.plugin_instance: HornetFlowPlugin | None = None
        self.concurrent_components = concurrent_components

    async def _prepare_release_data(
        self, repo_path: Path, repo_release: Release | None
    ) -> Release | None:
        """Get or extract release information."""
        if repo_release:
            return repo_release
        try:
            return await git_service.extract_git_repo_info(repo_path)
        except ValueError as e:
            self.logger.warning("Could not extract git repository information: %s", e)
            return None

    async def process_manifest(
        self,
        manifest_path: Path,
        repo_path: Path,
        fail_fast: bool = False,
        type_filter: str | None = None,
        name_filter: str | None = None,
        repo_release: Release | None = None,
    ) -> tuple[int, int]:
        """
        Process a manifest file using the configured plugin.

        Args:
            manifest_path: Path to the manifest file
            repo_path: Path to the repository
            fail_fast: Whether to stop on first error
            type_filter: Filter components by type
            name_filter: Filter components by name pattern
            release: Release information (will be extracted from git if not provided)

        Returns:
            Tuple of (successful_components, total_components)

        Raises:
            ValueError: If plugin cannot be found or loaded
            FileNotFoundError: If required files are missing (when fail_fast=True)
            RuntimeError: If component processing fails (when fail_fast=True)
        """
        # 0. Preprocessing
        repo_release = await self._prepare_release_data(repo_path, repo_release)
        self.logger.debug("Repo %s release data: %s", repo_path, repo_release)

        try:
            # 1. Setup plugin
            with log_lifespan(
                self.logger,
                f"Setting up plugin '{self.plugin_name}'",
                level=logging.DEBUG,
            ):
                # refresh instance for each run
                self.plugin_instance = self.plugin_class()

                assert self.plugin_instance is not None  # nosec

                # Extract repo_url and repo_commit from release if available
                await self.plugin_instance.setup(
                    repo_path,
                    manifest_path,
                    self.logger,
                    repo_url=repo_release.url if repo_release else None,
                    repo_commit=repo_release.marker if repo_release else None,
                )

            # 2. Load and process manifest
            with log_lifespan(
                self.logger,
                f"Processing manifest '{manifest_path.name}' with plugin '{self.plugin_name}'",
                level=logging.DEBUG,
            ):
                manifest_data = await manifest_service.read_manifest_contents(
                    manifest_path
                )
                return await self._process_components(
                    manifest_data,
                    manifest_path,
                    repo_path,
                    fail_fast,
                    type_filter,
                    name_filter,
                )

        finally:
            # 3. Cleanup
            with log_lifespan(
                self.logger,
                f"Tearing down plugin '{self.plugin_name}'",
                level=logging.DEBUG,
            ):
                if self.plugin_instance:
                    await self.plugin_instance.teardown()
                    self.plugin_instance = None

    async def _process_components(
        self,
        manifest_data: dict,
        manifest_path: Path,
        repo_path: Path,
        fail_fast: bool,
        type_filter: str | None,
        name_filter: str | None,
    ) -> tuple[int, int]:
        """Process individual components from manifest data.

        Components are grouped by parent path. If concurrent_components is enabled,
        sibling components are processed in parallel while maintaining parent-child
        ordering. Otherwise, components are processed sequentially.
        """
        success_count = 0
        total_count = 0

        # Group components by parent path for concurrent processing
        components_by_parent: dict[tuple[str, ...], list[Component]] = {}
        all_components = []

        for component in manifest_service.walk_manifest_components(manifest_data):
            total_count += 1
            all_components.append(component)

            # Apply filters
            if not self._should_process_component(component, type_filter, name_filter):
                continue

            # Group by parent path
            parent_key = tuple(component.parent_path) if component.parent_path else ()
            if parent_key not in components_by_parent:
                components_by_parent[parent_key] = []
            components_by_parent[parent_key].append(component)

        # Process components level by level (by parent depth)
        # Sort by parent path depth to ensure parents are processed before children
        sorted_groups = sorted(components_by_parent.items(), key=lambda x: len(x[0]))

        for parent_key, components in sorted_groups:
            if self.concurrent_components:
                # Process all components with the same parent concurrently
                tasks = []
                for component in components:
                    # Resolve and validate files
                    component_files = self._resolve_component_files(
                        component, manifest_path, repo_path, fail_fast
                    )
                    # Create task for concurrent processing
                    tasks.append(
                        self._process_single_component(
                            component, component_files, fail_fast
                        )
                    )

                # Process sibling components concurrently
                if tasks:
                    results = await asyncio.gather(
                        *tasks, return_exceptions=not fail_fast
                    )

                    # Count successes
                    for result in results:
                        if isinstance(result, Exception):
                            if fail_fast:
                                raise result
                            self.logger.error("Component processing failed: %s", result)
                        elif result is True:
                            success_count += 1
            else:
                # Process components sequentially
                for component in components:
                    # Apply filters
                    component_files = self._resolve_component_files(
                        component, manifest_path, repo_path, fail_fast
                    )
                    # Process component
                    result = await self._process_single_component(
                        component, component_files, fail_fast
                    )
                    if result is True:
                        success_count += 1

        return success_count, total_count

    def _should_process_component(
        self,
        component: Component,
        type_filter: str | None,
        name_filter: str | None,
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
            file_path = manifest_service.resolve_component_file_path(
                manifest_path, file_obj.path, repo_path
            )
            if file_path.exists():
                component_files.append(file_path)
            else:
                self.logger.error("Missing file: %s", file_path)
                if fail_fast:
                    raise FileNotFoundError(f"Missing file: {file_path}")
        return component_files

    async def _process_single_component(
        self, component: Component, component_files: list[Path], fail_fast: bool
    ) -> bool:
        """Process a single component with the plugin."""
        assert self.plugin_instance is not None  # nosec Should be set by process_manifest

        try:
            success = await self.plugin_instance.load_component(
                component_id=component.id,
                component_type=component.type,
                component_description=component.description,
                component_files=component_files,
                component_parent_path=component.parent_path,
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
            error = PluginProcessingError(
                "Plugin error processing %s: %s", component.id, str(e)
            )
            if fail_fast:
                raise error from e

            return False
