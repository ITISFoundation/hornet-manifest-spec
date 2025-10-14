# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable


import contextlib
import json
import logging
from pathlib import Path

import pytest

from hornet_flow import logging_utils, model
from hornet_flow.services import git_service, manifest_service, metadata_service


def test_load_metadata_portal_device(tools_hornet_flow_examples_dir: Path):
    """Test loading metadata from portal-device-metadata.json file."""
    # Get the path to the test JSON file
    metadata_path = tools_hornet_flow_examples_dir / "portal-device-metadata.json"
    assert metadata_path.exists(), f"Test file {metadata_path} should exist"

    # Load the metadata
    release = metadata_service.load_metadata_release(metadata_path)

    # Verify release information
    assert release == model.Release(
        **{
            "origin": "GitHub",
            "url": "https://github.com/COSMIIC-Inc/Implantables-Electrodes",
            "label": "main",
            "marker": "c04576f1a83803dec3192d8c03c731638e377fcb",
        }
    )


@pytest.mark.parametrize(
    "commit_hash", ["main", "ceca2ac4abc8055a7aeaa624ab68a460cd03ff1e"]
)
def test_clone_repository(tmp_path: Path, commit_hash: str):
    repo_url = "https://github.com/ITISFoundation/hornet-manifest-spec"

    # Clone the repository
    repo_path = git_service.clone_repository(repo_url, commit_hash, tmp_path / "repo")

    # Verify the repository was cloned successfully
    assert repo_path.exists()
    assert repo_path.is_dir()

    # Verify expected folders exist
    expected_folders = ["vocab", "doc", "scripts", "schema"]
    for folder_name in expected_folders:
        folder_path = repo_path / folder_name
        assert folder_path.exists(), f"Expected folder '{folder_name}' not found"
        assert folder_path.is_dir(), f"'{folder_name}' exists but is not a directory"

    repo_release = git_service.extract_git_repo_info(repo_path)
    assert repo_release.url == repo_url
    if commit_hash != "main":
        assert repo_release.marker == commit_hash


def test_walk_cad_manifest_components(examples_dir: Path, tmp_path: Path):
    """Test walking through CAD manifest components and validating with Pydantic model."""
    # Get the path to the test CAD manifest file
    manifest_path = examples_dir / "cad_manifest.json"

    # Load the manifest JSON
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Walk through all components using the walk_manifest_components function
    component_count = 0
    file_count = 0

    for component in manifest_service.walk_manifest_components(manifest_data):
        assert isinstance(component, model.Component)
        component_count += 1

        # Verify component has required fields (now it's a dataclass)
        assert component.id
        assert component.type
        assert component.description
        assert component.files

        # Count files in this component
        file_count += len(component.files)

        # Create a directory for each component using its id
        folder_parts = component.parent_path + [component.id]
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


def _validate_manifest_files(
    manifest_path: Path, repo_path: Path
) -> tuple[list[str], list[str]]:
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    missing_files = []
    existing_files = []

    for component in manifest_service.walk_manifest_components(manifest_data):
        # Now component is a Component dataclass instance
        for file_obj in component.files:
            file_path = file_obj.path
            if file_path:  # Only check non-empty paths
                full_path = manifest_service.resolve_component_file_path(
                    manifest_path, file_path, repo_path
                )
                if full_path.exists():
                    existing_files.append(file_path)
                else:
                    missing_files.append(file_path)

    return existing_files, missing_files


@pytest.mark.slow
@pytest.mark.integration
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

    repo_path = git_service.clone_repository(repo_url, commit_hash, tmp_path / "repo")
    assert repo_path.exists(), "Repository directory should exist"

    # Step 2: Find CAD manifest files
    cad_manifest, sim_manifest = manifest_service.find_hornet_manifests(repo_path)

    # Both manifests should exist in this repository
    assert cad_manifest is not None, (
        f"CAD manifest should exist in {repo_id} repository"
    )
    assert sim_manifest is not None, (
        f"SIM manifest should exist in {repo_id} repository"
    )

    # Step 3: Validate CAD files exist
    manifest_service.validate_manifest_schema(cad_manifest)

    cad_existing_files, cad_missing_files = _validate_manifest_files(
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

    # Step 4: Validate SIM manifest if it exists
    manifest_service.validate_manifest_schema(sim_manifest)


def test_lifespan_in_contextmanager(caplog: pytest.LogCaptureFixture):
    """Test that log_lifespan logs start and end of context, including when exceptions are raised."""

    # Create a real logger for testing
    logger = logging.getLogger("test_logger")

    @contextlib.contextmanager
    def some_lifespan_ctx():
        with logging_utils.log_lifespan(logger, "Action"):
            try:
                yield
            finally:
                pass

    # Test normal execution (no exception)
    with caplog.at_level(logging.INFO):
        with some_lifespan_ctx():
            pass

    # Verify start and end logs were captured
    assert len(caplog.records) == 2
    assert "Action ..." in caplog.records[0].message
    assert "Action [done]" in caplog.records[1].message

    # Clear captured logs for exception test
    caplog.clear()

    # Test with exception
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError):
            with some_lifespan_ctx():
                raise ValueError("test exception")

    # Verify start, exception, and end logs were captured
    assert len(caplog.records) == 3
    assert "Action ..." in caplog.records[0].message
    assert "Action [raised]" in caplog.records[1].message
    assert "test exception" in caplog.records[1].message
    assert "Action [done]" in caplog.records[2].message
