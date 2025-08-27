import json
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema
import httpx


from .models import Metadata


def load_metadata(metadata_path: Path | str) -> dict[str, Any]:
    """Load and parse the metadata JSON file from local path."""
    metadata_file = Path(metadata_path)
    with metadata_file.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    return Metadata.model_validate(metadata).model_dump(mode="json")


def clone_repository(repo_url: str, commit_hash: str, target_dir: Path | str) -> Path:
    """Clone repository with depth 1 and checkout specific commit."""
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    # Clone with depth 1
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--no-single-branch",
            repo_url,
            str(target_path),
        ],
        check=True,
        capture_output=True,
    )

    # Checkout specific commit
    subprocess.run(
        ["git", "checkout", commit_hash],
        cwd=str(target_path),
        check=True,
        capture_output=True,
    )

    return target_path


def find_hornet_manifests(repo_path: Path | str) -> tuple[Path | None, Path | None]:
    """Look for .hornet/cad_manifest.json and .hornet/sim_manifest.json."""
    repo_dir = Path(repo_path)
    assert repo_dir.is_dir()

    cad_manifest: Path | None = None
    sim_manifest: Path | None = None

    def _check(target: Path):
        if target.exists() and target.is_file():
            return target
        return None

    # First check .hornet/ directory
    hornet_dir = repo_dir / ".hornet"
    if hornet_dir.exists():
        cad_manifest = _check(hornet_dir / "cad_manifest.json")
        sim_manifest = _check(hornet_dir / "sim_manifest.json")

    # Fallback to root directory
    if not cad_manifest:
        cad_manifest = _check(repo_dir / "cad_manifest.json")
        sim_manifest = _check(repo_dir / "sim_manifest.json")

    return cad_manifest, sim_manifest


def validate_manifest_schema(manifest_file: Path):
    """Extract $schema URL from manifest file and validate using jsonschema."""
    with manifest_file.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    schema_url = manifest.get("$schema")
    if not schema_url:
        error_msg = f"No $schema field found in {manifest_file}"
        raise FileNotFoundError(error_msg)

    # Download schema
    response = httpx.get(schema_url)
    response.raise_for_status()
    schema = response.json()

    # Validate manifest against schema. Raises if not valid
    jsonschema.validate(manifest, schema)

def walk_manifest_components(manifest: dict[str, Any]):
    """Recursively walk through manifest components and yield each component."""
    components = manifest.get("components", [])

    def _walk_component(component: dict[str, Any]):
        """Recursively yield component and its sub-components."""
        yield component

        # Recursively process sub-components
        sub_components = component.get("components", [])
        for sub_component in sub_components:
            yield from _walk_component(sub_component)

    for component in components:
        yield from _walk_component(component)



class HornetManifestLoader:
    """Main class for loading and processing hornet manifests."""

    def __init__(self, fail_fast: bool = False, dry_run: bool = False) -> None:
        self.fail_fast = fail_fast
        self.dry_run = dry_run
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def load_metadata(self, metadata_path: Path | str) -> dict[str, Any]:
        """Load and parse the metadata JSON file from local path."""
        try:
            metadata = load_metadata(metadata_path)
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

            clone_repository(repo_url, commit_hash, repo_path)

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

        cad_manifest, sim_manifest = find_hornet_manifests(repo_path)

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
            validate_manifest_schema(Path(manifest_path))
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
    ) -> list[str]:
        """Parse CAD manifest JSON tree and verify referenced files exist."""
        try:
            manifest_file = Path(cad_manifest_path)
            repo_dir = Path(repo_path)

            with manifest_file.open("r", encoding="utf-8") as f:
                manifest = json.load(f)

            valid_files: list[str] = []

            for component in walk_manifest_components(manifest):
                files = component.get("files", [])
                for file_info in files:
                    file_path = file_info.get("path", "")
                    full_path = repo_dir / file_path

                    if full_path.exists():
                        valid_files.append(str(full_path))
                        self._logger.debug("Found file: %s", file_path)
                    else:
                        error_msg = f"Missing file referenced in manifest: {file_path}"
                        self._handle_error(error_msg)

            self._logger.info("Validated %d CAD files", len(valid_files))
            return valid_files

        except Exception as e:
            error_msg = f"Failed to validate CAD files from {cad_manifest_path}: {e}"
            self._handle_error(error_msg)
            return []

    def load_cad_file(self, file_path: Path | str) -> None:
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
        except Exception as e:
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
            self._handle_error(f"Unexpected error during processing: {e}")
            results["errors"] = self.errors
            return results

    def _handle_error(self, error_msg: str) -> None:
        """Handle errors based on fail_fast mode."""
        self._logger.error(error_msg)
        self.errors.append(error_msg)
        if self.fail_fast:
            sys.exit(1)
