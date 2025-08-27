# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable


import json
import pytest
from pathlib import Path

from hornet_flow.models import HornetCadManifest
from hornet_flow.service import clone_repository, load_metadata, walk_manifest_components


def test_load_metadata_portal_device():
    """Test loading metadata from portal-device-metadata.json file."""
    # Get the path to the test JSON file
    metadata_path = Path(__file__).parent / "examples" / "portal-device-metadata.json"

    # Load the metadata
    metadata = load_metadata(metadata_path)

    # Verify release information
    assert "release" in metadata
    release = metadata["release"]
    assert release["origin"] == "GitHub"
    assert release["url"] == "https://github.com/ITISFoundation/hornet-manifest-spec"
    assert release["label"] == "1.0.0"
    assert release["marker"] == "main"


@pytest.mark.parametrize("commit_hash", ["main", "ceca2ac4abc8055a7aeaa624ab68a460cd03ff1e"])
def test_clone_repository(tmp_path: Path, commit_hash: str):
    repo_url = "https://github.com/ITISFoundation/hornet-manifest-spec"

    # Clone the repository
    repo_path = clone_repository(repo_url, commit_hash, tmp_path / "repo")

    # Verify the repository was cloned successfully
    assert repo_path.exists()
    assert repo_path.is_dir()

    # Verify expected folders exist
    expected_folders = ["vocab", "doc", "scripts", "schema"]
    for folder_name in expected_folders:
        folder_path = repo_path / folder_name
        assert folder_path.exists(), f"Expected folder '{folder_name}' not found"
        assert folder_path.is_dir(), f"'{folder_name}' exists but is not a directory"


def test_walk_cad_manifest_components():
    """Test walking through CAD manifest components and validating with Pydantic model."""
    # Get the path to the test CAD manifest file
    manifest_path = Path(__file__).parent.parent / "examples" / "cad_manifest.json"

    # Load the manifest JSON
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Validate the manifest structure using Pydantic model
    cad_manifest = HornetCadManifest.model_validate(manifest_data)
    assert cad_manifest is not None

    # Walk through all components using the walk_manifest_components function
    component_count = 0
    file_count = 0

    for component in walk_manifest_components(manifest_data):
        component_count += 1

        # Verify component has required fields
        assert "id" in component
        assert "type" in component
        assert "description" in component
        assert "files" in component

        # Count files in this component
        files = component.get("files", [])
        file_count += len(files)

        # Verify each file has required fields
        for file_info in files:
            assert "path" in file_info
            assert "type" in file_info

    # Verify we found components and files
    assert component_count > 0, "Should find at least one component"
    assert file_count > 0, "Should find at least one file"
