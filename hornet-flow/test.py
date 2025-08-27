# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable


import pytest
from typing import Any
from pytest_mock import MockerFixture
from pathlib import Path
import tempfile

from hornet_flow.service import load_metadata, clone_repository


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
