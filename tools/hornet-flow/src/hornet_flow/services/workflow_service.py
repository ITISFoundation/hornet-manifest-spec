"""Workflow orchestration service for hornet-flow operations.

This module provides workflow orchestration functionality that can be used
by both the API layer and other services like the watcher.
"""

import logging
import shutil
import tempfile
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ..model import Release
from . import git_service, manifest_service, metadata_service
from .processor import ManifestProcessor

_logger = logging.getLogger(__name__)


class WorkflowEvent(Enum):
    """Workflow event types."""

    BEFORE_PROCESS_MANIFEST = "before_process_manifest"


class EventDispatcher:
    """Simple event dispatcher for workflow events."""

    def __init__(self):
        self._callbacks: Dict[WorkflowEvent, List[Callable]] = {}

    def register(self, event: WorkflowEvent, callback: Callable) -> None:
        """Register a callback for a specific event."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def trigger(self, event: WorkflowEvent, **kwargs) -> None:
        """Trigger all callbacks for a specific event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    _logger.error(f"Error in event callback for {event.value}: {e}")


def run_workflow(
    metadata_file_path: Optional[Path] = None,
    repo_url: Optional[str] = None,
    repo_commit: str = "main",
    repo_path: Optional[Path] = None,
    work_dir: Optional[Path] = None,
    fail_fast: bool = False,
    plugin: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    event_dispatcher: Optional[EventDispatcher] = None,
) -> Tuple[int, int]:
    """Run a complete workflow to process hornet manifests.

    Args:
        metadata_file_path: Path to metadata.json file
        repo_url: Repository URL to clone
        repo_commit: Git commit/branch to checkout
        repo_path: Local repository path
        work_dir: Working directory for clones
        fail_fast: Stop on first error
        plugin: Plugin to use for processing
        type_filter: Filter components by type
        name_filter: Filter components by name
        event_dispatcher: Optional event dispatcher for workflow events

    Returns:
        Tuple of (success_count, total_count)

    Raises:
        ValueError: If input validation fails
        FileNotFoundError: If required files/directories not found
        RuntimeError: If processing fails
        subprocess.CalledProcessError: If git operations fail
    """
    # Input validation
    if metadata_file_path and (repo_url or repo_commit != "main"):
        raise ValueError("metadata_file cannot be combined with repo_url or commit")

    if not metadata_file_path and not repo_url and not repo_path:
        raise ValueError("Must specify either metadata_file, repo_url, or repo_path")

    release = None
    if metadata_file_path:
        # Extract release info
        release = metadata_service.load_metadata_release(str(metadata_file_path))
        repo_url = release.url
        repo_commit = release.marker

    if repo_path:
        # Repo in place
        return _process_manifests(
            repo_path,
            fail_fast,
            plugin,
            type_filter,
            name_filter,
            release,
            event_dispatcher,
        )

    else:
        assert repo_url  # Already validated above

        # Clone repository
        work_path = work_dir or Path(tempfile.gettempdir())

        # Create persistent directory for manual cleanup
        temp_dir = tempfile.mkdtemp(prefix="hornet_", suffix="_repo", dir=work_path)
        temp_path = Path(temp_dir)
        # Deduce repository name from repo_url
        repo_name = Path(repo_url.rstrip("/").split("/")[-1]).stem
        target_repo_path = temp_path / repo_name

        try:
            # Clone repo
            git_service.clone_repository(repo_url, repo_commit, target_repo_path)

            # Process manifests
            return _process_manifests(
                target_repo_path,
                fail_fast,
                plugin,
                type_filter,
                name_filter,
                release,
                event_dispatcher,
            )

        except Exception:
            # Clean up on error
            if temp_path.exists():
                shutil.rmtree(temp_path)
            raise


def _process_manifests(
    repo_path: Path,
    fail_fast: bool = False,
    plugin_name: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    release: Optional[Release] = None,
    event_dispatcher: Optional[EventDispatcher] = None,
) -> Tuple[int, int]:
    """Process manifests found in repository."""
    # 1. Find hornet manifests
    cad_manifest, sim_manifest = manifest_service.find_hornet_manifests(repo_path)

    if not cad_manifest and not sim_manifest:
        raise FileNotFoundError(
            f"No hornet manifest files found in repository at {repo_path}"
        )

    # 2. Validate manifests
    validation_errors = []

    if cad_manifest:
        try:
            manifest_service.validate_manifest_schema(cad_manifest)
        except Exception as e:  # pylint: disable=broad-exception-caught
            if fail_fast:
                raise
            validation_errors.append(f"CAD manifest validation failed: {e}")

    if sim_manifest:
        try:
            manifest_service.validate_manifest_schema(sim_manifest)
        except Exception as e:  # pylint: disable=broad-exception-caught
            if fail_fast:
                raise
            validation_errors.append(f"SIM manifest validation failed: {e}")

    # Log validation errors if any
    if validation_errors:
        for error in validation_errors:
            _logger.error(error)

    # 3. Trigger before_process_manifest event
    if event_dispatcher:
        event_dispatcher.trigger(
            WorkflowEvent.BEFORE_PROCESS_MANIFEST,
            repo_path=repo_path,
            cad_manifest=cad_manifest,
            sim_manifest=sim_manifest,
            release=release,
        )

    # 4. Process CAD manifest with plugin
    if cad_manifest:
        return _process_manifest_with_plugin(
            cad_manifest,
            repo_path,
            plugin_name,
            type_filter,
            name_filter,
            release,
        )

    return 0, 0


def _process_manifest_with_plugin(
    cad_manifest: Path,
    repo_path: Path,
    plugin_name: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    repo_release: Optional[Release] = None,
) -> Tuple[int, int]:
    """Process CAD manifest using specified plugin."""
    processor = ManifestProcessor(plugin_name, _logger)

    success_count, total_count = processor.process_manifest(
        cad_manifest, repo_path, True, type_filter, name_filter, repo_release
    )
    return success_count, total_count
