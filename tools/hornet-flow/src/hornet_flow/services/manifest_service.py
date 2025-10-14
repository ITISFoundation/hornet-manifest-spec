"""Manifest operations service.

This module provides functionality for working with hornet manifest files including
finding, validating, reading, and processing manifest contents.
"""

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import jsonschema

from ..model import Component, File


def _load_manifest_data(manifest_file: Path) -> dict[str, Any]:
    """Load manifest data from file.

    Raises:
        json.JSONDecodeError: If file is not valid JSON
        FileNotFoundError: If file does not exist
    """
    with manifest_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _extract_schema_url(manifest_data: dict[str, Any], manifest_file: Path) -> str:
    """Extract and validate schema URL from manifest data.

    Raises:
        FileNotFoundError: If no $schema field found
    """
    schema_url = manifest_data.get("$schema")
    if not schema_url:
        raise FileNotFoundError(f"No $schema field found in {manifest_file}")
    return schema_url


def _validate_against_schema(
    manifest_data: dict[str, Any], schema: dict[str, Any]
) -> None:
    """Validate manifest data against JSON schema.

    Raises:
        jsonschema.ValidationError: If manifest is invalid
    """
    jsonschema.validate(manifest_data, schema)


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
    """Extract $schema URL from manifest file and validate using jsonschema.

    Raises:
        FileNotFoundError: If no $schema field found
        httpx.HTTPError: If schema download fails
        jsonschema.ValidationError: If manifest is invalid
    """
    manifest_data = _load_manifest_data(manifest_file)
    schema_url = _extract_schema_url(manifest_data, manifest_file)

    # Download schema
    response = httpx.get(schema_url)
    response.raise_for_status()
    schema = response.json()

    # Validate manifest against schema
    _validate_against_schema(manifest_data, schema)


async def validate_manifest_schema_async(manifest_file: Path):
    """Extract $schema URL from manifest file and validate using jsonschema (async version).

    Raises:
        FileNotFoundError: If no $schema field found
        httpx.HTTPError: If schema download fails
        jsonschema.ValidationError: If manifest is invalid
    """
    # Load manifest in thread pool to avoid blocking
    manifest_data = await asyncio.to_thread(_load_manifest_data, manifest_file)
    schema_url = _extract_schema_url(manifest_data, manifest_file)

    # Download schema asynchronously
    async with httpx.AsyncClient() as client:
        response = await client.get(schema_url)
        response.raise_for_status()
        schema = response.json()

    # Validate in thread pool since jsonschema is CPU-bound
    await asyncio.to_thread(_validate_against_schema, manifest_data, schema)


def read_manifest_contents(manifest: Path) -> dict[str, Any]:
    """Read and return the JSON contents of a manifest file."""
    with manifest.open("r", encoding="utf-8") as f:
        return json.load(f)


def walk_manifest_components(
    manifest_data: dict[str, Any], parent_path: list[str] | None = None
) -> Iterator[Component]:
    """Walk through manifest components and yield Component dataclass instances.

    Args:
        manifest_data: The loaded manifest JSON data
        parent_id: List of parent component IDs (path to parent)

    Yields:
        Component: Component dataclass instances with proper parent tracking
    """
    if parent_path is None:
        parent_path = []

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
            parent_path=parent_path.copy(),
        )

        # Yield the current component
        yield component

        # Recursively walk child components if they exist
        if "components" in component_dict and component_dict["components"]:
            # Create new parent path for children
            child_path = parent_path + [component_dict["id"]]

            # Create a temporary manifest structure for recursion
            child_manifest = {"components": component_dict["components"]}

            yield from walk_manifest_components(child_manifest, child_path)


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


def validate_sim_manifest_references(
    sim_manifest: Path, cad_components: Iterator[Component]
):
    """Validate that all references in sim-manifest.json exist in cad-manifest.json."""
    raise NotImplementedError
