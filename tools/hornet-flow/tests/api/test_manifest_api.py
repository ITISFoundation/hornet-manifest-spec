# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from hornet_flow.api import HornetFlowAPI
from hornet_flow.exceptions import ApiFileNotFoundError


@pytest.fixture
def api() -> HornetFlowAPI:
    """Create a HornetFlowAPI instance for testing."""
    return HornetFlowAPI()


def test_manifest_validate_both_valid(
    mocker: MockerFixture, api: HornetFlowAPI
) -> None:
    """Test validating manifests when both are valid."""
    # Setup
    mock_find = mocker.patch(
        "hornet_flow.services.manifest_service.find_hornet_manifests"
    )
    mock_validate = mocker.patch(
        "hornet_flow.services.manifest_service.validate_manifest_schema"
    )

    mock_find.return_value = (Path("/repo/cad.json"), Path("/repo/sim.json"))
    mock_validate.return_value = None  # No exceptions means valid

    # Execute
    cad_valid, sim_valid = api.manifest.validate("/path/to/repo")

    # Verify
    assert cad_valid is True
    assert sim_valid is True
    assert mock_validate.call_count == 2


def test_manifest_validate_no_manifests(
    mocker: MockerFixture, api: HornetFlowAPI
) -> None:
    """Test validating when no manifests are found."""
    # Setup
    mock_find = mocker.patch(
        "hornet_flow.services.manifest_service.find_hornet_manifests"
    )
    mock_find.return_value = (None, None)

    # Execute & Verify
    with pytest.raises(ApiFileNotFoundError):
        api.manifest.validate("/path/to/repo")


def test_manifest_show_both(mocker: MockerFixture, api: HornetFlowAPI) -> None:
    """Test showing both manifest types from README example."""
    # Setup
    mock_find = mocker.patch(
        "hornet_flow.services.manifest_service.find_hornet_manifests"
    )
    mock_read = mocker.patch(
        "hornet_flow.services.manifest_service.read_manifest_contents"
    )

    mock_find.return_value = (Path("/repo/cad.json"), Path("/repo/sim.json"))
    mock_read.side_effect = [{"cad_data": "test"}, {"sim_data": "test"}]

    # Execute
    result = api.manifest.show("/path/to/repo", manifest_type="both")

    # Verify
    assert "cad" in result
    assert "sim" in result
    assert result["cad"] == {"cad_data": "test"}
    assert result["sim"] == {"sim_data": "test"}


def test_manifest_show_cad_only(mocker: MockerFixture, api: HornetFlowAPI) -> None:
    """Test showing only CAD manifest."""
    # Setup
    mock_find = mocker.patch(
        "hornet_flow.services.manifest_service.find_hornet_manifests"
    )
    mock_read = mocker.patch(
        "hornet_flow.services.manifest_service.read_manifest_contents"
    )

    mock_find.return_value = (Path("/repo/cad.json"), None)
    mock_read.return_value = {"cad_data": "test"}

    # Execute
    result = api.manifest.show("/path/to/repo", manifest_type="cad")

    # Verify
    assert "cad" in result
    assert "sim" not in result
    assert result["cad"] == {"cad_data": "test"}
