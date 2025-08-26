#!/usr/bin/env python3
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# pylint: disable=unused-variable
# pylint: disable=too-many-arguments
"""
Test suite for the Hornet Manifest Loader

This module contains comprehensive tests for all functionality of the
hornet_manifest_loader module using pytest.
"""

import json
import logging
import tempfile
import subprocess
import hashlib
from pathlib import Path
import pytest
from typing import Any
from pytest_mock import MockerFixture

from hornet_manifest_loader import HornetManifestLoader

# Configure test logger
_logger = logging.getLogger(__name__)


# Test fixtures
@pytest.fixture
def sample_metadata() -> dict[str, Any]:
    """Sample metadata for testing."""
    return {
        "datePublished": "2025-01-24",
        "pennsieveDatasetId": 422,
        "version": 1,
        "name": "Test/test-repo",
        "description": "Test repository for hornet manifest loader",
        "files": [
            {
                "name": "test.zip",
                "path": "assets/test.zip",
                "size": 1000,
                "fileType": "ZIP",
                "sha256": "abc123def456"
            },
            {
                "name": "readme.md",
                "path": "readme.md",
                "size": 500,
                "fileType": "Markdown",
                "sha256": "def456abc123"
            }
        ],
        "release": {
            "origin": "GitHub",
            "url": "https://github.com/Test/test-repo",
            "label": "1.0.0",
            "marker": "abc123def456789"
        }
    }


@pytest.fixture
def sample_cad_manifest() -> dict[str, Any]:
    """Sample CAD manifest for testing."""
    return {
        "$schema": "https://example.com/cad_manifest.schema.json",
        "repository": "https://github.com/Test/test-repo",
        "components": [
            {
                "id": "TestAssembly",
                "type": "assembly",
                "description": "Test assembly",
                "files": [
                    {"path": "assemblies/test.sldasm", "type": "solidworks_assembly"}
                ],
                "components": [
                    {
                        "id": "TestPart",
                        "type": "part",
                        "description": "Test part",
                        "files": [
                            {"path": "parts/test.sldprt", "type": "solidworks_part"},
                            {"path": "exports/test.step", "type": "step_export"}
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def loader() -> HornetManifestLoader:
    """Basic loader instance."""
    return HornetManifestLoader(fail_fast=False, dry_run=False)


@pytest.fixture
def loader_dry_run() -> HornetManifestLoader:
    """Dry run loader instance."""
    return HornetManifestLoader(fail_fast=False, dry_run=True)


@pytest.fixture
def loader_fail_fast() -> HornetManifestLoader:
    """Fail fast loader instance."""
    return HornetManifestLoader(fail_fast=True, dry_run=False)


@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(name)s - %(levelname)s - %(message)s'
    )


# Initialization tests
def test_init() -> None:
    """Test HornetManifestLoader initialization."""
    loader = HornetManifestLoader(fail_fast=True, dry_run=True)
    assert loader.fail_fast is True
    assert loader.dry_run is True
    assert not loader.errors
    assert not loader.warnings


# Metadata loading tests
def test_load_metadata_success(mocker: MockerFixture, loader: HornetManifestLoader, sample_metadata: dict[str, Any]) -> None:
    """Test successful metadata loading."""
    mock_open = mocker.mock_open(read_data=json.dumps(sample_metadata))
    mocker.patch('pathlib.Path.open', mock_open)
    
    result = loader.load_metadata("/fake/path/metadata.json")
    
    assert result == sample_metadata
    mock_open.assert_called_once()


def test_load_metadata_file_not_found(loader: HornetManifestLoader) -> None:
    """Test metadata loading with missing file."""
    result = loader.load_metadata("/fake/path/nonexistent.json")
    
    assert result == {}
    assert len(loader.errors) == 1
    assert "Failed to load metadata" in loader.errors[0]


# Repository cloning tests
def test_clone_repository_success(mocker: MockerFixture, loader: HornetManifestLoader) -> None:
    """Test successful repository cloning."""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = loader.clone_repository(
            "https://github.com/test/repo", 
            "abc123", 
            temp_dir
        )
        
        expected_path = str(Path(temp_dir) / "repo")
        assert result == expected_path
        assert mock_subprocess.call_count == 2  # clone + checkout


def test_clone_repository_dry_run(loader_dry_run: HornetManifestLoader) -> None:
    """Test repository cloning in dry run mode."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = loader_dry_run.clone_repository(
            "https://github.com/test/repo", 
            "abc123", 
            temp_dir
        )
        
        expected_path = str(Path(temp_dir) / "repo")
        assert result == expected_path


def test_clone_repository_failure(mocker: MockerFixture, loader: HornetManifestLoader) -> None:
    """Test repository cloning failure."""
    mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git'))
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = loader.clone_repository(
            "https://github.com/test/repo", 
            "abc123", 
            temp_dir
        )
        
        assert result == ""
        assert len(loader.errors) == 1
        assert "Failed to clone repository" in loader.errors[0]


# ZIP file verification tests
def test_verify_zip_file_success(loader: HornetManifestLoader) -> None:
    """Test successful ZIP file verification."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        test_content = b"test zip content"
        temp_path.write_bytes(test_content)
        
        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        result = loader.verify_zip_file(temp_path, expected_hash)
        
        assert result is True
        temp_path.unlink()


def test_verify_zip_file_mismatch(loader: HornetManifestLoader) -> None:
    """Test ZIP file verification with hash mismatch."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_path.write_bytes(b"test content")
        
        result = loader.verify_zip_file(temp_path, "wrong_hash")
        
        assert result is False
        assert len(loader.errors) == 1
        assert "SHA256 mismatch" in loader.errors[0]
        temp_path.unlink()


def test_verify_zip_file_dry_run(loader_dry_run: HornetManifestLoader) -> None:
    """Test ZIP file verification in dry run mode."""
    result = loader_dry_run.verify_zip_file("/fake/path", "fake_hash")
    assert result is True


# ZIP file extraction tests
def test_extract_zip_file_success(mocker: MockerFixture, loader: HornetManifestLoader) -> None:
    """Test successful ZIP file extraction."""
    mock_zipfile = mocker.patch('zipfile.ZipFile')
    mock_zip = mocker.MagicMock()
    mock_zipfile.return_value.__enter__.return_value = mock_zip
    
    with tempfile.TemporaryDirectory() as extract_dir:
        result = loader.extract_zip_file("/fake/zip", extract_dir)
        
        assert result == extract_dir
        mock_zip.extractall.assert_called_once_with(Path(extract_dir))


def test_extract_zip_file_dry_run(loader_dry_run: HornetManifestLoader) -> None:
    """Test ZIP file extraction in dry run mode."""
    result = loader_dry_run.extract_zip_file("/fake/zip", "/fake/dir")
    assert result == "/fake/dir"


# Manifest discovery tests
def test_find_hornet_manifests_in_hornet_dir(loader: HornetManifestLoader, sample_cad_manifest: dict[str, Any]) -> None:
    """Test finding manifests in .hornet directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create .hornet directory with manifests
        hornet_dir = temp_path / ".hornet"
        hornet_dir.mkdir()
        
        cad_path = hornet_dir / "cad_manifest.json"
        sim_path = hornet_dir / "sim_manifest.json"
        
        cad_path.write_text(json.dumps(sample_cad_manifest))
        sim_path.write_text(json.dumps({"$schema": "test"}))
        
        cad_manifest, sim_manifest = loader.find_hornet_manifests(temp_path)
        
        assert cad_manifest == str(cad_path)
        assert sim_manifest == str(sim_path)


def test_find_hornet_manifests_in_root(loader: HornetManifestLoader, sample_cad_manifest: dict[str, Any]) -> None:
    """Test finding manifests in root directory fallback."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create manifests in root
        cad_path = temp_path / "cad_manifest.json"
        cad_path.write_text(json.dumps(sample_cad_manifest))
        
        cad_manifest, sim_manifest = loader.find_hornet_manifests(temp_path)
        
        assert cad_manifest == str(cad_path)
        assert sim_manifest is None


def test_find_hornet_manifests_none_found(loader: HornetManifestLoader) -> None:
    """Test when no manifests are found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cad_manifest, sim_manifest = loader.find_hornet_manifests(temp_dir)
        
        assert cad_manifest is None
        assert sim_manifest is None
        assert len(loader.errors) == 1
        assert "No hornet manifest files found" in loader.errors[0]


# Schema validation tests
def test_validate_manifest_schema_success(mocker: MockerFixture, loader: HornetManifestLoader, sample_cad_manifest: dict[str, Any]) -> None:
    """Test successful manifest schema validation."""
    mock_open = mocker.mock_open(read_data=json.dumps(sample_cad_manifest))
    mocker.patch('pathlib.Path.open', mock_open)
    
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"type": "object"}
    mock_response.raise_for_status.return_value = None
    mocker.patch('requests.get', return_value=mock_response)
    
    mock_validate = mocker.patch('jsonschema.validate')
    
    result = loader.validate_manifest_schema("/fake/manifest.json")
    
    assert result is True
    mock_validate.assert_called_once()


def test_validate_manifest_schema_no_schema_field(mocker: MockerFixture, loader: HornetManifestLoader) -> None:
    """Test manifest validation with missing $schema field."""
    mock_open = mocker.mock_open(read_data=json.dumps({"components": []}))
    mocker.patch('pathlib.Path.open', mock_open)
    
    result = loader.validate_manifest_schema("/fake/manifest.json")
    
    assert result is False
    assert len(loader.errors) == 1
    assert "No $schema field found" in loader.errors[0]


def test_validate_manifest_schema_dry_run(loader_dry_run: HornetManifestLoader, sample_cad_manifest: dict[str, Any]) -> None:
    """Test manifest schema validation in dry run mode."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_path.write_text(json.dumps(sample_cad_manifest))
        
        result = loader_dry_run.validate_manifest_schema(temp_path)
        
        assert result is True
        temp_path.unlink()


# CAD file validation tests
def test_validate_cad_files_exist_success(loader: HornetManifestLoader, sample_cad_manifest: dict[str, Any]) -> None:
    """Test successful CAD file validation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create manifest file
        manifest_path = temp_path / "cad_manifest.json"
        manifest_path.write_text(json.dumps(sample_cad_manifest))
        
        # Create referenced files
        (temp_path / "assemblies").mkdir()
        (temp_path / "parts").mkdir()
        (temp_path / "exports").mkdir()
        
        (temp_path / "assemblies" / "test.sldasm").write_text("dummy assembly")
        (temp_path / "parts" / "test.sldprt").write_text("dummy part")
        (temp_path / "exports" / "test.step").write_text("dummy step")
        
        valid_files = loader.validate_cad_files_exist(manifest_path, temp_path)
        
        assert len(valid_files) == 3
        assert all(Path(f).exists() for f in valid_files)


def test_validate_cad_files_exist_missing_files(loader: HornetManifestLoader, sample_cad_manifest: dict[str, Any]) -> None:
    """Test CAD file validation with missing files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create manifest file
        manifest_path = temp_path / "cad_manifest.json"
        manifest_path.write_text(json.dumps(sample_cad_manifest))
        
        # Don't create the referenced files
        valid_files = loader.validate_cad_files_exist(manifest_path, temp_path)
        
        assert len(valid_files) == 0
        assert len(loader.errors) == 3  # 3 missing files


# CAD file loading tests
def test_load_cad_file(loader: HornetManifestLoader) -> None:
    """Test CAD file loading (mock implementation)."""
    # This should not raise an exception
    loader.load_cad_file("/fake/path/file.step")


def test_load_cad_file_dry_run(loader_dry_run: HornetManifestLoader) -> None:
    """Test CAD file loading in dry run mode."""
    loader_dry_run.load_cad_file("/fake/path/file.step")


# Cleanup tests
def test_cleanup_repository(loader: HornetManifestLoader) -> None:
    """Test repository cleanup."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_repo = temp_path / "test_repo"
        test_repo.mkdir()
        
        # Create a test file
        test_file = test_repo / "test.txt"
        test_file.write_text("test")
        
        # Cleanup should remove the directory
        loader.cleanup_repository(test_repo)
        
        assert not test_repo.exists()


def test_cleanup_repository_dry_run(loader_dry_run: HornetManifestLoader) -> None:
    """Test repository cleanup in dry run mode."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_repo = temp_path / "test_repo"
        test_repo.mkdir()
        
        # Cleanup in dry run should not remove the directory
        loader_dry_run.cleanup_repository(test_repo)
        
        assert test_repo.exists()


# Error handling tests
def test_handle_error_fail_fast(loader_fail_fast: HornetManifestLoader) -> None:
    """Test error handling in fail-fast mode."""
    with pytest.raises(SystemExit):
        loader_fail_fast._handle_error("Test error")


def test_handle_error_continue(loader: HornetManifestLoader) -> None:
    """Test error handling in continue mode."""
    loader._handle_error("Test error")
    
    assert len(loader.errors) == 1
    assert loader.errors[0] == "Test error"


# End-to-end workflow tests
def test_process_hornet_manifest_success(mocker: MockerFixture, loader: HornetManifestLoader, sample_metadata: dict[str, Any]) -> None:
    """Test successful end-to-end manifest processing."""
    # Setup mocks
    mocker.patch.object(loader, 'load_metadata', return_value=sample_metadata)
    mocker.patch.object(loader, 'clone_repository', return_value="/fake/repo")
    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch.object(loader, 'verify_zip_file', return_value=True)
    mocker.patch.object(loader, 'extract_zip_file', return_value="/fake/extracted")
    mocker.patch.object(loader, 'find_hornet_manifests', return_value=("/fake/cad.json", "/fake/sim.json"))
    mocker.patch.object(loader, 'validate_manifest_schema', return_value=True)
    mocker.patch.object(loader, 'validate_cad_files_exist', return_value=["/fake/file1.step", "/fake/file2.step"])
    mocker.patch.object(loader, 'load_cad_file')
    
    result = loader.process_hornet_manifest("/fake/metadata.json", "/tmp")
    
    assert result['success'] is True
    assert len(result['processed_files']) == 2
    assert len(result['errors']) == 0


def test_process_hornet_manifest_no_metadata(mocker: MockerFixture, loader: HornetManifestLoader) -> None:
    """Test manifest processing with no metadata."""
    mocker.patch.object(loader, 'load_metadata', return_value={})
    
    result = loader.process_hornet_manifest("/fake/metadata.json", "/tmp")
    
    assert result['success'] is False
    assert len(result['processed_files']) == 0


def test_process_hornet_manifest_missing_release_info(mocker: MockerFixture, loader: HornetManifestLoader, sample_metadata: dict[str, Any]) -> None:
    """Test manifest processing with missing release info."""
    incomplete_metadata = sample_metadata.copy()
    del incomplete_metadata['release']['url']
    mocker.patch.object(loader, 'load_metadata', return_value=incomplete_metadata)
    
    result = loader.process_hornet_manifest("/fake/metadata.json", "/tmp")
    
    assert result['success'] is False
    assert len(loader.errors) == 1
    assert "Missing repository URL" in loader.errors[0]


# Integration tests
def test_create_sample_manifest_and_validate() -> None:
    """Integration test: create sample manifest and validate it."""
    with tempfile.TemporaryDirectory() as test_data_dir:
        test_path = Path(test_data_dir)
        
        # Create a sample CAD manifest
        sample_manifest = {
            "$schema": "https://raw.githubusercontent.com/ITISFoundation/hornet-manifest-spec/refs/heads/main/schema/cad_manifest.schema.json",
            "repository": "https://github.com/test/integration-test",
            "components": [
                {
                    "id": "IntegrationTest",
                    "type": "part",
                    "description": "Integration test component",
                    "files": [
                        {"path": "test.step", "type": "step_export"}
                    ]
                }
            ]
        }
        
        # Write manifest to file
        manifest_path = test_path / "cad_manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest, indent=2))
        
        # Create the referenced file
        test_file = test_path / "test.step"
        test_file.write_text("STEP file content")
        
        # Test file validation
        loader = HornetManifestLoader()
        valid_files = loader.validate_cad_files_exist(manifest_path, test_path)
        
        assert len(valid_files) == 1
        assert valid_files[0].endswith("test.step")


# Pytest markers for test categories
pytestmark = pytest.mark.unit
