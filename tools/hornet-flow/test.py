# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable


import json
import sys
from pathlib import Path

import pytest

from hornet_flow import service
from hornet_flow.model import Component

_CURRENT_DIR = Path(
    sys.argv[0] if __name__ == "__main__" else __file__
).parent.resolve()


@pytest.fixture
def repo_path() -> Path:
    return _CURRENT_DIR.parent.parent


@pytest.fixture
def package_dir(repo_path: Path) -> Path:
    return repo_path / "tools" / "hornet_flow"


def test_load_metadata_portal_device():
    """Test loading metadata from portal-device-metadata.json file."""
    # Get the path to the test JSON file
    metadata_path = Path(__file__).parent / "examples" / "portal-device-metadata.json"

    # Load the metadata
    metadata = service.load_metadata(metadata_path)

    # Verify release information
    assert "release" in metadata
    release = metadata["release"]
    assert release == {
        "origin": "GitHub",
        "url": "https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        "label": "main",
        "marker": "c04576f1a83803dec3192d8c03c731638e377fcb",
    }


@pytest.mark.parametrize(
    "commit_hash", ["main", "ceca2ac4abc8055a7aeaa624ab68a460cd03ff1e"]
)
def test_clone_repository(tmp_path: Path, commit_hash: str):
    repo_url = "https://github.com/ITISFoundation/hornet-manifest-spec"

    # Clone the repository
    repo_path = service.clone_repository(repo_url, commit_hash, tmp_path / "repo")

    # Verify the repository was cloned successfully
    assert repo_path.exists()
    assert repo_path.is_dir()

    # Verify expected folders exist
    expected_folders = ["vocab", "doc", "scripts", "schema"]
    for folder_name in expected_folders:
        folder_path = repo_path / folder_name
        assert folder_path.exists(), f"Expected folder '{folder_name}' not found"
        assert folder_path.is_dir(), f"'{folder_name}' exists but is not a directory"


def test_walk_cad_manifest_components(repo_path: Path, tmp_path: Path):
    """Test walking through CAD manifest components and validating with Pydantic model."""
    # Get the path to the test CAD manifest file
    manifest_path = repo_path / "examples" / "cad_manifest.json"

    # Load the manifest JSON
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Walk through all components using the walk_manifest_components function
    component_count = 0
    file_count = 0

    for component in service.walk_manifest_components(manifest_data):
        assert isinstance(component, Component)
        component_count += 1

        # Verify component has required fields (now it's a dataclass)
        assert component.id
        assert component.type
        assert component.description
        assert component.files

        # Count files in this component
        file_count += len(component.files)

        # Create a directory for each component using its id
        folder_parts = component.parent_id + [component.id]
        component_dir = Path.joinpath(tmp_path, *folder_parts)
        component_dir.mkdir(exist_ok=True)
        assert component_dir.exists() and component_dir.is_dir()

        # Verify each file has required fields (now File dataclass instances)
        for file_obj in component.files:
            assert file_obj.path
            assert file_obj.type
            (component_dir / Path(file_obj.path).name).touch()

    # Verify we found components and files
    assert component_count > 0, "Should find at least one component"
    assert file_count > 0, "Should find at least one file"


def validate_manifest_files(
    manifest_path: Path, repo_path: Path
) -> tuple[list[str], list[str]]:
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    missing_files = []
    existing_files = []

    for component in service.walk_manifest_components(manifest_data):
        # Now component is a Component dataclass instance
        for file_obj in component.files:
            file_path = file_obj.path
            if file_path:  # Only check non-empty paths
                full_path = service.resolve_component_file_path(
                    manifest_path, file_path, repo_path
                )
                if full_path.exists():
                    existing_files.append(file_path)
                else:
                    missing_files.append(file_path)

    return existing_files, missing_files


@pytest.mark.parametrize(
    "repo_id,metadata",
    [
        pytest.param(
            "cosmiic",
            {
                "release": {
                    "origin": "GitHub",
                    "url": "https://github.com/COSMIIC-Inc/Implantables-Electrodes",
                    "label": "main",
                    "marker": "c04576f1a83803dec3192d8c03c731638e377fcb",
                }
            },
            id="cosmiic",
        ),
        pytest.param(
            "carsscenter",
            {
                "release": {
                    "origin": "GitHub",
                    "url": "https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode",
                    "label": "main",
                    "marker": "main",
                }
            },
            marks=pytest.mark.xfail(
                reason="Expected to fail - repository under development"
            ),
            id="carsscenter",
        ),
    ],
)
def test_repository_manifest_validation(tmp_path: Path, repo_id: str, metadata: dict):
    """Test complete workflow with different repositories: clone, find manifests, validate files."""

    # Step 1: Clone repository
    release = metadata["release"]
    repo_url = release["url"]
    commit_hash = release["marker"]

    repo_path = service.clone_repository(repo_url, commit_hash, tmp_path / "repo")
    assert repo_path.exists(), "Repository directory should exist"

    # Step 2: Find CAD manifest files
    cad_manifest, sim_manifest = service.find_hornet_manifests(repo_path)

    # Both manifests should exist in this repository
    assert cad_manifest is not None, (
        f"CAD manifest should exist in {repo_id} repository"
    )
    service.validate_manifest_schema(cad_manifest)

    assert sim_manifest is not None, (
        f"SIM manifest should exist in {repo_id} repository"
    )
    service.validate_manifest_schema(sim_manifest)

    # Step 3: Validate CAD files exist
    cad_existing_files, cad_missing_files = validate_manifest_files(
        cad_manifest, repo_path
    )

    # Report results
    print(
        f"CAD manifest: Found {len(cad_existing_files)} existing files, {len(cad_missing_files)} missing files"
    )

    # Assert no missing files - all referenced files should exist
    assert len(cad_missing_files) == 0, (
        f"CAD manifest has missing files: {cad_missing_files}"
    )

    # Assert we found files in both manifests
    assert len(cad_existing_files) > 0, (
        "CAD manifest should reference at least some files"
    )
