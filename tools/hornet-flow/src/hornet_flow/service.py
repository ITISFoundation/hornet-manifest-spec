import json
import subprocess
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
    """Clone repository and checkout specific commit."""
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

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


# TODO: validate that references in sim-manifest.json exist in cad-manifest.json
