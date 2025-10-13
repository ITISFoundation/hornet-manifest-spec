"""File watcher functionality for monitoring metadata.json files.

This module provides functionality to watch for metadata.json files and trigger
hornet-flow workflow processing when files are detected and stable.
"""

import logging
import time
from pathlib import Path
from typing import Optional

from watchfiles import watch

from . import workflow_service

_logger = logging.getLogger(__name__)


def _check_file_stability(file_path: Path, stability_seconds: float = 2.0) -> bool:
    """Check if a file is stable (not being written to).

    Args:
        file_path: Path to the file to check
        stability_seconds: How long to wait for file stability

    Returns:
        True if file is stable, False otherwise
    """
    if not file_path.exists():
        return False

    try:
        initial_size = file_path.stat().st_size
        time.sleep(stability_seconds)

        if not file_path.exists():
            return False

        final_size = file_path.stat().st_size
        return initial_size == final_size and initial_size > 0
    except (OSError, IOError) as e:
        _logger.error("Error checking file stability for %s: %s", file_path, e)
        return False


def _process_metadata_file(
    metadata_path: Path,
    work_dir: Path,
    plugin: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    fail_fast: bool = False,
    event_dispatcher: Optional[workflow_service.EventDispatcher] = None,
) -> tuple[int, int]:
    """Process a metadata file using the workflow service.

    Args:
        metadata_path: Path to the metadata.json file
        work_dir: Working directory for clones
        plugin: Plugin to use for processing
        type_filter: Filter components by type
        name_filter: Filter components by name
        fail_fast: Stop on first error
        event_dispatcher: Optional event dispatcher for workflow events

    Returns:
        Tuple of (success_count, total_count)

    Raises:
        Exception: If workflow processing fails
    """
    _logger.info("🚀 Processing metadata file: %s", metadata_path)

    # Ensure work directory exists
    work_dir.mkdir(parents=True, exist_ok=True)

    # Call the workflow service
    return workflow_service.run_workflow(
        metadata_file_path=metadata_path,
        work_dir=work_dir,
        plugin=plugin,
        type_filter=type_filter,
        name_filter=name_filter,
        fail_fast=fail_fast,
        event_dispatcher=event_dispatcher,
    )


def watch_for_metadata(
    inputs_dir: Path,
    work_dir: Path,
    once: bool = True,
    plugin: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    fail_fast: bool = False,
    stability_seconds: float = 2.0,
    event_dispatcher: Optional[workflow_service.EventDispatcher] = None,
) -> None:
    """Watch for metadata.json files and process them.

    Args:
        inputs_dir: Directory to watch for metadata.json files
        work_dir: Working directory for workflow processing
        once: If True, exit after processing one file
        plugin: Plugin to use for processing
        type_filter: Filter components by type
        name_filter: Filter components by name
        fail_fast: Stop on first error
        stability_seconds: How long to wait for file stability
        event_dispatcher: Optional event dispatcher for workflow events

    Raises:
        FileNotFoundError: If inputs_dir doesn't exist
        PermissionError: If directories can't be accessed
    """
    # Validate inputs directory
    if not inputs_dir.exists():
        raise FileNotFoundError(f"Inputs directory does not exist: {inputs_dir}")

    if not inputs_dir.is_dir():
        raise NotADirectoryError(f"Inputs path is not a directory: {inputs_dir}")

    # Ensure work directory exists
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise PermissionError(f"Cannot create work directory {work_dir}: {e}") from e

    _logger.info("👀 Watching for metadata.json in: %s", inputs_dir)
    _logger.info("📁 Work directory: %s", work_dir)
    _logger.info("🔄 Mode: %s", "single file" if once else "continuous")

    metadata_filename = "metadata.json"

    try:
        for changes in watch(inputs_dir, recursive=False):
            for change_type, file_path in changes:
                file_path = Path(file_path)

                # Only process metadata.json files
                if file_path.name != metadata_filename:
                    continue

                # Only process file creation/modification events
                if change_type not in (1, 2):  # Created or Modified
                    continue

                _logger.info("📄 Detected %s: %s", metadata_filename, file_path)

                # Check file stability
                _logger.info("⏳ Checking file stability...")
                if not _check_file_stability(file_path, stability_seconds):
                    _logger.warning(
                        "❌ File not stable or empty, skipping: %s", file_path
                    )
                    continue

                _logger.info("✅ File is stable, processing...")

                try:
                    success_count, total_count = _process_metadata_file(
                        file_path,
                        work_dir,
                        plugin=plugin,
                        type_filter=type_filter,
                        name_filter=name_filter,
                        fail_fast=fail_fast,
                        event_dispatcher=event_dispatcher,
                    )

                    _logger.info(
                        "✅ Successfully processed %d/%d components",
                        success_count,
                        total_count,
                    )

                except Exception as e:  # pylint: disable=broad-exception-caught
                    _logger.error("❌ Failed to process metadata file: %s", e)
                    if fail_fast:
                        raise

                if once:
                    _logger.info("🏁 Single file mode - exiting after processing")
                    return
                else:
                    _logger.info("👀 Continuing to watch for more files...")

    except KeyboardInterrupt:
        _logger.info("⛔ Stopping watcher (Ctrl+C received)")
    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.error("❌ Watcher error: %s", e)
        raise
