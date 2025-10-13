"""Pure API functions for hornet-flow operations.

This module provides a clean programmatic interface to hornet-flow functionality
without CLI dependencies. Functions raise core domain exceptions only.
"""

import contextlib
import logging
import subprocess
import tempfile
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, TypeAlias

import jsonschema

from .exceptions import (
    ApiFileNotFoundError,
    ApiInputValueError,
    ApiProcessingError,
    ApiValidationError,
)
from .model import Release
from .services import git_service, manifest_service, watcher, workflow_service
from .services.processor import ManifestProcessor
from .services.workflow_service import EventDispatcher, WorkflowEvent

_logger = logging.getLogger(__name__)

assert WorkflowEvent  # nosec

__all__: tuple[str, ...] = (
    "EventDispatcher",
    "WorkflowEvent",
)

SuccessCountInt: TypeAlias = int
TotalCountInt: TypeAlias = int


def _create_processing_error(
    e: subprocess.CalledProcessError, operation: str
) -> ApiProcessingError:
    """Convert subprocess errors to ProcessingError with detailed information."""
    error_details = [f"Failed to {operation}"]
    if e.cmd:
        error_details.append(f"Command: {' '.join(e.cmd)}")
    error_details.append(f"Exit code: {e.returncode}")

    if e.stdout:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout
        error_details.append(f"stdout: {stdout}")
    if e.stderr:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr
        error_details.append(f"stderr: {stderr}")

    return ApiProcessingError(". ".join(error_details))


def handle_service_exceptions(operation_name: str = "operation"):
    """Decorator to handle common service layer exceptions and convert them to API exceptions."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                raise ApiInputValueError(str(e)) from e
            except FileNotFoundError as e:
                raise ApiFileNotFoundError(str(e)) from e
            except RuntimeError as e:
                raise ApiProcessingError(str(e)) from e
            except subprocess.CalledProcessError as e:
                raise _create_processing_error(e, operation_name) from e
            except jsonschema.ValidationError as e:
                raise ApiValidationError(
                    f"Schema validation failed: {e.message}"
                ) from e

        return wrapper

    return decorator


class WorkflowAPI:
    """API for workflow operations."""

    @handle_service_exceptions("workflow operation")
    def run(
        self,
        metadata_file: Optional[str] = None,
        repo_url: Optional[str] = None,
        repo_commit: str = "main",
        repo_path: Optional[str] = None,
        work_dir: Optional[str] = None,
        fail_fast: bool = False,
        plugin: Optional[str] = None,
        type_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
    ) -> Tuple[SuccessCountInt, TotalCountInt]:
        """Run a complete workflow to process hornet manifests."""
        return workflow_service.run_workflow(
            metadata_file_path=Path(metadata_file) if metadata_file else None,
            repo_url=repo_url,
            repo_commit=repo_commit,
            repo_path=Path(repo_path) if repo_path else None,
            work_dir=Path(work_dir) if work_dir else None,
            fail_fast=fail_fast,
            plugin=plugin,
            type_filter=type_filter,
            name_filter=name_filter,
            event_dispatcher=event_dispatcher,
        )

    @handle_service_exceptions("watch operation")
    def watch(
        self,
        inputs_dir: str,
        work_dir: str,
        once: bool = False,
        plugin: Optional[str] = None,
        type_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        fail_fast: bool = False,
        stability_seconds: float = 2.0,
    ) -> None:
        """Watch for metadata.json files and automatically process them."""
        inputs_path = Path(inputs_dir).resolve()
        work_path = Path(work_dir).resolve()

        # Validate inputs directory exists
        if not inputs_path.exists():
            raise ApiFileNotFoundError(
                f"Inputs directory does not exist: {inputs_path}"
            )

        if not inputs_path.is_dir():
            raise ApiInputValueError(f"Inputs path is not a directory: {inputs_path}")

        watcher.watch_for_metadata(
            inputs_dir=inputs_path,
            work_dir=work_path,
            once=once,
            plugin=plugin,
            type_filter=type_filter,
            name_filter=name_filter,
            fail_fast=fail_fast,
            stability_seconds=stability_seconds,
        )


class RepoAPI:
    """API for repository operations."""

    @handle_service_exceptions("clone repository")
    def clone(
        self, repo_url: str, dest: Optional[str] = None, commit: str = "main"
    ) -> Path:
        """Clone a repository and checkout a specific commit."""
        dest_path = Path(dest or tempfile.gettempdir()).resolve()
        repo_path = git_service.clone_repository(repo_url, commit, dest_path)
        return repo_path


class ManifestAPI:
    """API for manifest operations."""

    def validate_schema(self, manifest_path: Path, manifest_type: str) -> None:
        """Validate a manifest schema."""
        try:
            manifest_service.validate_manifest_schema(manifest_path)
        except jsonschema.ValidationError as e:
            msg = f"{manifest_type} manifest schema validation failed: {e.message}"
            raise ApiValidationError(msg) from e

    @handle_service_exceptions("manifest validation")
    def validate(self, repo_path: str) -> Tuple[bool, bool]:
        """Validate hornet manifests against their schemas."""
        repo_dir = Path(repo_path)
        cad_manifest, sim_manifest = manifest_service.find_hornet_manifests(repo_dir)

        if not cad_manifest and not sim_manifest:
            raise ApiFileNotFoundError("No hornet manifest files found")

        cad_valid = False
        sim_valid = False

        if cad_manifest:
            with contextlib.suppress(ApiValidationError):
                self.validate_schema(cad_manifest, "CAD")
                cad_valid = True

        if sim_manifest:
            with contextlib.suppress(ApiValidationError):
                self.validate_schema(sim_manifest, "SIM")
                sim_valid = True

        return cad_valid, sim_valid

    @handle_service_exceptions("manifest show")
    def show(self, repo_path: str, manifest_type: str = "both") -> Dict[str, Any]:
        """Get manifest contents."""
        repo_dir = Path(repo_path)
        cad_manifest, sim_manifest = manifest_service.find_hornet_manifests(repo_dir)

        result = {}

        # Check if requested manifests exist
        if manifest_type.lower() in ["cad", "both"] and not cad_manifest:
            if manifest_type.lower() == "cad":
                raise ApiFileNotFoundError("No CAD manifest found")

        if manifest_type.lower() in ["sim", "both"] and not sim_manifest:
            if manifest_type.lower() == "sim":
                raise ApiFileNotFoundError("No SIM manifest found")

        # If both requested but neither found
        if manifest_type.lower() == "both" and not cad_manifest and not sim_manifest:
            raise ApiFileNotFoundError("No hornet manifest files found")

        # Get CAD manifest if requested and exists
        if manifest_type.lower() in ["cad", "both"] and cad_manifest:
            result["cad"] = manifest_service.read_manifest_contents(cad_manifest)

        # Get SIM manifest if requested and exists
        if manifest_type.lower() in ["sim", "both"] and sim_manifest:
            result["sim"] = manifest_service.read_manifest_contents(sim_manifest)

        return result

    @handle_service_exceptions("manifest processing")
    def process_with_plugin(
        self,
        cad_manifest: Path,
        repo_path: Path,
        plugin_name: Optional[str] = None,
        type_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        repo_release: Optional[Release] = None,
    ) -> Tuple[SuccessCountInt, TotalCountInt]:
        """Process CAD manifest using specified plugin."""
        processor = ManifestProcessor(plugin_name, _logger)
        success_count, total_count = processor.process_manifest(
            cad_manifest, repo_path, True, type_filter, name_filter, repo_release
        )
        return success_count, total_count

    @handle_service_exceptions("manifest processing")
    def process(
        self,
        repo_path: Path,
        fail_fast: bool = False,
        plugin_name: Optional[str] = None,
        type_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        release: Optional[Release] = None,
    ) -> Tuple[SuccessCountInt, TotalCountInt]:
        """Process manifests found in repository."""
        # 1. Find hornet manifests
        cad_manifest, sim_manifest = manifest_service.find_hornet_manifests(repo_path)

        if not cad_manifest and not sim_manifest:
            msg = f"No hornet manifest files found in repository at {repo_path}"
            raise ApiFileNotFoundError(msg)

        # 2. Validate manifests
        validation_errors = []

        if cad_manifest:
            try:
                self.validate_schema(cad_manifest, "CAD")
            except ApiValidationError as e:
                if fail_fast:
                    raise
                validation_errors.append(str(e))

        if sim_manifest:
            try:
                self.validate_schema(sim_manifest, "SIM")
            except ApiValidationError as e:
                if fail_fast:
                    raise
                validation_errors.append(str(e))

        # If we had validation errors and fail_fast is False, log them
        if validation_errors:
            for error in validation_errors:
                _logger.error(error)

        # 3. Process CAD manifest with plugin
        if cad_manifest:
            return self.process_with_plugin(
                cad_manifest,
                repo_path,
                plugin_name,
                type_filter,
                name_filter,
                release,
            )

        return 0, 0


class CadAPI:
    """API for CAD operations."""

    @handle_service_exceptions("CAD loading")
    def load(
        self,
        repo_path: str,
        plugin: Optional[str] = None,
        type_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        fail_fast: bool = True,
    ) -> Tuple[int, int]:
        """Load CAD files referenced in the manifest using plugins."""
        return workflow_service.run_workflow(
            repo_path=Path(repo_path),
            plugin=plugin,
            type_filter=type_filter,
            name_filter=name_filter,
            fail_fast=fail_fast,
        )


class HornetFlowAPI:
    """Main API class containing all hornet-flow functionality."""

    def __init__(self):
        self.workflow = WorkflowAPI()
        self.repo = RepoAPI()
        self.manifest = ManifestAPI()
        self.cad = CadAPI()
