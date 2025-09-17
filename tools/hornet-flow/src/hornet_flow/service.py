import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import httpx
import jsonschema

from .model import Component, File, Release, validate_metadata_and_get_release


def load_metadata_release(metadata_path: Path | str) -> Release:
    """Load and parse the metadata JSON file from local path and returns the release section"""
    metadata_file = Path(metadata_path)
    with metadata_file.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    try:
        return validate_metadata_and_get_release(metadata)
    except jsonschema.ValidationError as e:
        msg = f"Invalid metadata file {metadata_path}: {e.message}"
        raise ValueError(msg) from e


def check_git_version() -> Optional[str]:
    """
    Check if git is installed and return its version string.

    Returns:
        Git version string if available, None if git is not found or fails
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return None
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def clone_repository(repo_url: str, commit_hash: str, target_dir: Path | str) -> Path:
    """Clone repository and checkout specific commit."""
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    if not repo_url.startswith("http://") and not repo_url.startswith("https://"):
        raise ValueError(f"Repository URL must be HTTP(S): {repo_url}")

    # Clone with depth 1 first
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

    # Try to checkout the commit, if it fails, fetch it specifically
    try:
        subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=str(target_path),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # Commit not in shallow clone, fetch it specifically
        subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", commit_hash],
            cwd=str(target_path),
            check=True,
            capture_output=True,
        )
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

    cad_manifest: Path | None = None
    sim_manifest: Path | None = None

    def _check(target: Path):
        if target.exists() and target.is_file():
            return target
        return None

    # First check .hornet/ directory otherwise then look in repo root
    hornet_dir = repo_dir / ".hornet"
    if hornet_dir.exists():
        cad_manifest = _check(hornet_dir / "cad_manifest.json")
        sim_manifest = _check(hornet_dir / "sim_manifest.json")
    else:
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


def walk_manifest_components(
    manifest_data: Dict[str, Any], parent_id: Optional[list[str]] = None
) -> Iterator[Component]:
    """Walk through manifest components and yield Component dataclass instances.

    Args:
        manifest_data: The loaded manifest JSON data
        parent_id: List of parent component IDs (path to parent)

    Yields:
        Component: Component dataclass instances with proper parent tracking
    """
    if parent_id is None:
        parent_id = []

    # Get components from manifest
    components = manifest_data.get("components", [])

    for component_dict in components:
        # Convert file dictionaries to File dataclass instances
        files = [
            File(path=file_dict["path"], type=file_dict["type"])
            for file_dict in component_dict.get("files", [])
        ]

        # Create Component instance
        component = Component(
            id=component_dict["id"],
            type=component_dict["type"],
            description=component_dict["description"],
            files=files,
            parent_id=parent_id.copy(),
        )

        # Yield the current component
        yield component

        # Recursively walk child components if they exist
        if "components" in component_dict and component_dict["components"]:
            # Create new parent path for children
            child_parent_id = parent_id + [component_dict["id"]]

            # Create a temporary manifest structure for recursion
            child_manifest = {"components": component_dict["components"]}

            yield from walk_manifest_components(child_manifest, child_parent_id)


def resolve_component_file_path(
    manifest_file: Path, file_path: str, repo_dir: Path
) -> Path:
    """Get the full path of a file based on the manifest file location."""
    # NOTE: how path is interpreted
    if file_path.startswith("./"):
        base_dir = manifest_file.resolve().parent
        file_path = file_path[2:]
    else:
        base_dir = repo_dir
    return base_dir / file_path


def read_manifest_contents(manifest: Path) -> dict[str, Any]:
    """Read and return the JSON contents of a manifest file."""
    with manifest.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_sim_manifest_references(
    sim_manifest: Path, cad_components: Iterator[Component]
):
    """Validate that all references in sim-manifest.json exist in cad-manifest.json."""
    raise NotImplementedError


def extract_git_repo_info(repo_path: Path | str) -> Release:
    """
    Extract git repository information from a cloned repository.

    Returns:
        Release object with repository URL and current commit

    Raises:
        subprocess.CalledProcessError: If git commands fail
        ValueError: If repository information cannot be extracted
    """
    repo_dir = Path(repo_path)

    if not repo_dir.exists():
        raise ValueError(f"Repository path does not exist: {repo_dir}")

    try:
        # Get the remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        repo_url = result.stdout.strip()

        # Get current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        commit_hash = result.stdout.strip()

        # Get a human-readable label (try tag first, then branch, then short hash)
        label = commit_hash[:8]  # Default to short hash

        # Try to get tag
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--exact-match", "HEAD"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            label = result.stdout.strip()
        except subprocess.CalledProcessError:
            # Try to get branch name
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                branch = result.stdout.strip()
                if branch != "HEAD":  # Not in detached HEAD state
                    label = branch
            except subprocess.CalledProcessError:
                pass  # Keep short hash as label

        return Release(
            origin="git",
            url=repo_url,
            label=label,
            marker=commit_hash,
        )

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to extract git repository information: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise ValueError(f"Git command timed out: {e}") from e
