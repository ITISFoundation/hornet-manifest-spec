# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from hornet_flow.api import HornetFlowAPI


@pytest.fixture
def api() -> HornetFlowAPI:
    """Create a HornetFlowAPI instance for testing."""
    return HornetFlowAPI()


def test_repo_clone_basic(mocker: MockerFixture, api: HornetFlowAPI) -> None:
    """Test basic repository cloning from README example."""
    # Setup
    mock_clone = mocker.patch('hornet_flow.services.git_service.clone_repository')
    mock_clone.return_value = Path("/tmp/my-repo")

    # Execute
    repo_path = api.repo.clone(
        repo_url="https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode",
        dest="/tmp/my-repo",
        commit="main"
    )

    # Verify
    assert repo_path == Path("/tmp/my-repo")
    mock_clone.assert_called_once()


def test_repo_clone_with_defaults(mocker: MockerFixture, api: HornetFlowAPI) -> None:
    """Test repository cloning with default parameters."""
    # Setup
    mock_clone = mocker.patch('hornet_flow.services.git_service.clone_repository')
    mock_clone.return_value = Path("/tmp/default-repo")

    # Execute
    repo_path = api.repo.clone(
        repo_url="https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode"
    )

    # Verify
    assert repo_path == Path("/tmp/default-repo")
    mock_clone.assert_called_once()
