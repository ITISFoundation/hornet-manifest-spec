import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

from . import service

_logger = logging.getLogger(__name__)


class HornetManifestProcessor:
    """CLI processor for loading and processing hornet manifests with logging and error handling."""

    def __init__(self, fail_fast: bool = False, dry_run: bool = False) -> None:
        self.fail_fast = fail_fast
        self.dry_run = dry_run
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def load_metadata(self, metadata_path: Path | str) -> dict[str, Any]:
        """Load and parse the metadata JSON file from local path."""
        try:
            metadata = service.load_metadata(metadata_path)
            self._logger.info("Loaded metadata from %s", metadata_path)
            return metadata
        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            error_msg = f"Failed to load metadata from {metadata_path}: {e}"
            self._handle_error(error_msg)
            return {}

    def clone_repository(
        self, repo_url: str, commit_hash: str, target_dir: Path | str
    ) -> str:
        """Clone repository with depth 1 and checkout specific commit."""
        try:
            target_path = Path(target_dir)
            repo_path = target_path / "repo"

            if self.dry_run:
                self._logger.info(
                    "[DRY RUN] Would clone %s at commit %s to %s",
                    repo_url,
                    commit_hash,
                    repo_path,
                )
                return str(repo_path)

            service.clone_repository(repo_url, commit_hash, repo_path)

            self._logger.info(
                "Cloned repository %s at commit %s", repo_url, commit_hash
            )
            return str(repo_path)

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to clone repository {repo_url}: {e}"
            self._handle_error(error_msg)
            return ""

    def find_hornet_manifests(
        self, repo_path: Path | str
    ) -> tuple[Path | None, Path | None]:
        """Look for .hornet/cad_manifest.json and .hornet/sim_manifest.json."""

        cad_manifest, sim_manifest = service.find_hornet_manifests(repo_path)

        if cad_manifest:
            self._logger.info("Found CAD manifest: %s", cad_manifest)
        if sim_manifest:
            self._logger.info("Found SIM manifest: %s", sim_manifest)

        if not cad_manifest and not sim_manifest:
            self._handle_error("No hornet manifest files found in repository")

        return cad_manifest, sim_manifest

    def validate_manifest_schema(self, manifest_path: Path | str) -> bool:
        """Extract $schema URL from manifest file and validate using jsonschema."""
        try:
            service.validate_manifest_schema(Path(manifest_path))
            self._logger.info("Schema validation successful for %s", manifest_path)
            return True

        except jsonschema.ValidationError as e:
            error_msg = f"Schema validation failed for {manifest_path}: {e.message}"
            self._handle_error(error_msg)
            return False
        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            error_msg = f"Failed to validate schema for {manifest_path}: {e}"
            self._handle_error(error_msg)
            return False

    def validate_cad_files_exist(
        self, cad_manifest_path: Path | str, repo_path: Path | str
    ) -> list[Path]:
        """Parse CAD manifest JSON tree and verify referenced files exist."""
        try:
            manifest_file = Path(cad_manifest_path)
            repo_dir = Path(repo_path)

            with manifest_file.open("r", encoding="utf-8") as f:
                manifest = json.load(f)

            valid_files: list[Path] = []

            for component in service.walk_manifest_components(manifest):
                files = component.get("files", [])
                for file_info in files:
                    file_path = file_info.get("path", "")

                    full_path = service.resolve_component_file_path(
                        manifest_file, file_path, repo_dir
                    )

                    if full_path.exists():
                        valid_files.append(full_path)
                        self._logger.debug("Found file: %s", file_path)
                    else:
                        error_msg = f"Missing file referenced in manifest: {full_path}"
                        self._handle_error(error_msg)

            self._logger.info("Validated %d CAD files", len(valid_files))
            return valid_files

        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            error_msg = f"Failed to validate CAD files from {cad_manifest_path}: {e}"
            self._handle_error(error_msg)
            return []

    def load_cad_file(self, file_path: Path) -> None:
        """Mock function that prints file path for now."""
        if self.dry_run:
            self._logger.info("[DRY RUN] Would load CAD file: %s", file_path)
        else:
            self._logger.info("Loading CAD file: %s", file_path)
            # TODO: Implement actual CAD file loading logic here

    def cleanup_repository(self, repo_path: Path | str) -> None:
        """Explicitly remove cloned repository directory."""
        try:
            repo_dir = Path(repo_path)
            if repo_dir.exists():
                if self.dry_run:
                    self._logger.info(
                        "[DRY RUN] Would cleanup repository at %s", repo_dir
                    )
                else:
                    shutil.rmtree(repo_dir)
                    self._logger.info("Cleaned up repository at %s", repo_dir)
        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            self._handle_error(f"Failed to cleanup repository {repo_path}: {e}")

    def process_hornet_manifest(
        self, metadata_path: Path | str, work_dir: Path | str, cleanup: bool = False
    ) -> dict[str, Any]:
        """Main orchestration function that calls all steps in sequence."""
        results: dict[str, Any] = {
            "success": False,
            "errors": [],
            "warnings": [],
            "processed_files": [],
        }

        try:
            # Step 1: Load metadata
            metadata = self.load_metadata(metadata_path)
            if not metadata:
                return results

            # Step 2: Extract release info
            release = metadata.get("release", {})
            repo_url = release.get("url", "")
            commit_hash = release.get("marker", "")

            if not repo_url or not commit_hash:
                self._handle_error("Missing repository URL or commit hash in metadata")
                return results

            # Create working directory
            work_path = Path(work_dir)
            with tempfile.TemporaryDirectory(dir=work_path) as temp_dir:
                temp_path = Path(temp_dir)

                # Step 1: Clone repository
                repo_path = self.clone_repository(repo_url, commit_hash, temp_path)
                if not repo_path:
                    return results

                # Step 2: Find hornet manifests (check both repo and extracted content)
                cad_manifest, sim_manifest = self.find_hornet_manifests(repo_path)

                # Step 3: Validate manifests against schemas
                if cad_manifest and not self.validate_manifest_schema(cad_manifest):
                    if self.fail_fast:
                        return results

                if sim_manifest and not self.validate_manifest_schema(sim_manifest):
                    if self.fail_fast:
                        return results

                # Step 4: Validate and load CAD files
                if cad_manifest:
                    valid_files = self.validate_cad_files_exist(cad_manifest, repo_path)
                    for file_path in valid_files:
                        self.load_cad_file(file_path)
                        results["processed_files"].append(file_path)

                # Step 5: Cleanup if requested
                if cleanup:
                    self.cleanup_repository(repo_path)

            results["success"] = len(self.errors) == 0 or not self.fail_fast
            results["errors"] = self.errors
            results["warnings"] = self.warnings

            return results

        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            self._logger.exception("Unexpected error during processing")
            self._handle_error(f"Unexpected error during processing: {e}")
            results["errors"] = self.errors
            return results

    def _handle_error(self, error_msg: str) -> None:
        """Handle errors based on fail_fast mode."""
        self._logger.error(error_msg)
        self.errors.append(error_msg)
        if self.fail_fast:
            sys.exit(1)


def main() -> None:
    """
    Hornet Manifest Flow

    Loads metadata from a JSON file, clones a git repository,
    verifies ZIP files, extracts them, finds and validates hornet manifests,
    and loads CAD files according to the manifest specifications.

    Usage
        hornet-flow --help
        hornet-flow ./examples/sample_metadata.json --work-dir /tmp/hornet_test --verbose
    """

    parser = argparse.ArgumentParser(description="Load and process hornet manifests")
    parser.add_argument("metadata_path", help="Path to metadata JSON file")
    parser.add_argument(
        "--work-dir", default="/tmp", help="Working directory for clones"
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first error")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually load files"
    )
    parser.add_argument("--cleanup", action="store_true", help="Clean up cloned repo")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show errors")

    args = parser.parse_args()

    # Configure logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    loader = HornetManifestProcessor(fail_fast=args.fail_fast, dry_run=args.dry_run)
    results = loader.process_hornet_manifest(
        args.metadata_path, args.work_dir, cleanup=args.cleanup
    )

    _logger.info(
        "Processing %s\n Files processed: %d\n Errors: %d\n Warnings: %d",
        "completed" if results["success"] else "failed",
        len(results["processed_files"]),
        len(results["errors"]),
        len(results["warnings"]),
    )

    if results["errors"]:
        _logger.error("Errors: %d", len(results["errors"]))
        for error in results["errors"]:
            _logger.error(" %s", error)

    if results["warnings"]:
        _logger.warning("Warnings: %d", len(results["warnings"]))
        for warning in results["warnings"]:
            _logger.warning(" %s", warning)

    sys.exit(os.EX_OK if results["success"] else os.EX_SOFTWARE)
