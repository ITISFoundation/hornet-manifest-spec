"""Workflow orchestration service for hornet-flow operations.

This module provides workflow orchestration functionality that can be used
by both the API layer and other services like the watcher.
"""

import logging
import shutil
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path

from ..model import Release
from . import git_service, manifest_service, metadata_service
from .processor import ManifestProcessor

_logger = logging.getLogger(__name__)


@contextmanager
def _local_repository_dir(
    repo_url: str, work_dir: Path | None = None
) -> Generator[Path, None, None]:
    """Create persistent directory for the cloned repo that is cleaned up only on failure

    The name of the folder is derived from the repository name.

    Args:
        repo_url: Repository URL to extract name from
        work_dir: Working directory for temporary files

    Yields:
        Path to the target repository directory
    """
    work_path = work_dir or Path(tempfile.gettempdir())

    # Create persistent directory that is cleaned up only on failure
    temp_dir = tempfile.mkdtemp(prefix="hornet_", suffix="_repo", dir=work_path)
    temp_path = Path(temp_dir)

    # Deduce repository name from repo_url
    repo_name = Path(repo_url.rstrip("/").split("/")[-1]).stem
    target_repo_path = temp_path / repo_name

    try:
        yield target_repo_path
    except Exception:
        # Clean up temporary directory only on failure
        if temp_path.exists():
            shutil.rmtree(temp_path)
        raise


class WorkflowEvent(Enum):
    WORKFLOW_STARTED = (
        "workflow_started"  # Triggered at workflow start after validation
    )
    REPOSITORY_READY = (
        "repository_ready"  # Triggered when repository is available locally
    )
    MANIFESTS_READY = (
        "manifests_ready"  # Triggered when manifests are validated and ready to process
    )
    WORKFLOW_COMPLETED = (
        "workflow_completed"  # Triggered at workflow end with success/failure status
    )


class EventDispatcher:
    """Simple event dispatcher for workflow events."""

    def __init__(self):
        self._callbacks: dict[WorkflowEvent, list[Callable]] = {}

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
                except Exception:  # pylint: disable=broad-exception-caught
                    _logger.exception("Error in event callback for %s", event.value)


def run_workflow(
    metadata_file_path: Path | None = None,
    repo_url: str | None = None,
    repo_commit: str = "main",
    repo_path: Path | None = None,
    work_dir: Path | None = None,
    fail_fast: bool = False,
    plugin: str | None = None,
    type_filter: str | None = None,
    name_filter: str | None = None,
    event_dispatcher: EventDispatcher | None = None,
) -> tuple[int, int]:
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

    # Trigger workflow started event
    if event_dispatcher:
        event_dispatcher.trigger(
            WorkflowEvent.WORKFLOW_STARTED,
            metadata_file_path=metadata_file_path,
            repo_url=repo_url,
            repo_commit=repo_commit,
            repo_path=repo_path,
            plugin=plugin,
            type_filter=type_filter,
            name_filter=name_filter,
        )

    success_count = 0
    total_count = 0
    workflow_succeeded = False
    workflow_exception = None

    try:
        release = None
        # 1. Extract release info if needed
        if metadata_file_path:
            release = metadata_service.load_metadata_release(str(metadata_file_path))
            repo_url = release.url
            repo_commit = release.marker

        # 2. Clone repository if needed
        if not repo_path:
            assert repo_url  # Already validated above

            with _local_repository_dir(repo_url, work_dir) as target_repo_path:
                git_service.clone_repository(repo_url, repo_commit, target_repo_path)

                repo_path = target_repo_path

        if event_dispatcher:
            event_dispatcher.trigger(
                WorkflowEvent.REPOSITORY_READY,
                repo_path=repo_path,
                repo_url=repo_url,
                repo_commit=repo_commit,
            )

        # 3. Process manifests
        success_count, total_count = _process_manifests(
            repo_path,
            fail_fast,
            plugin,
            type_filter,
            name_filter,
            release,
            event_dispatcher,
        )

        workflow_succeeded = True

    except Exception as e:
        workflow_exception = e
        raise

    finally:
        # Trigger workflow completed event
        if event_dispatcher:
            event_dispatcher.trigger(
                WorkflowEvent.WORKFLOW_COMPLETED,
                success_count=success_count,
                total_count=total_count,
                workflow_succeeded=workflow_succeeded,
                workflow_exception=workflow_exception,
                repo_path=repo_path,
            )

    return success_count, total_count


def _process_manifests(
    repo_path: Path,
    fail_fast: bool = False,
    plugin_name: str | None = None,
    type_filter: str | None = None,
    name_filter: str | None = None,
    release: Release | None = None,
    event_dispatcher: EventDispatcher | None = None,
) -> tuple[int, int]:
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

    # 3. Trigger manifests ready event
    if event_dispatcher:
        event_dispatcher.trigger(
            WorkflowEvent.MANIFESTS_READY,
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
    plugin_name: str | None = None,
    type_filter: str | None = None,
    name_filter: str | None = None,
    repo_release: Release | None = None,
) -> tuple[int, int]:
    """Process CAD manifest using specified plugin."""
    processor = ManifestProcessor(plugin_name, _logger)

    success_count, total_count = processor.process_manifest(
        cad_manifest, repo_path, True, type_filter, name_filter, repo_release
    )
    return success_count, total_count
