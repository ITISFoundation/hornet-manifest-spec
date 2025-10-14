# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

import pytest
from pytest_mock import MockerFixture

from hornet_flow.api import HornetFlowAPI


@pytest.fixture
def api() -> HornetFlowAPI:
    """Create a HornetFlowAPI instance for testing."""
    return HornetFlowAPI()


def test_cad_load_basic(mocker: MockerFixture, api: HornetFlowAPI) -> None:
    """Test basic CAD loading from README example."""
    # Setup
    mock_run_workflow = mocker.patch(
        "hornet_flow.services.workflow_service.run_workflow"
    )
    mock_run_workflow.return_value = (2, 4)

    # Execute
    success_count, total_count = api.cad.load(
        repo_path="/path/to/repo", plugin="debug", type_filter="assembly"
    )

    # Verify
    assert success_count == 2
    assert total_count == 4
    mock_run_workflow.assert_called_once()

    call_args = mock_run_workflow.call_args
    assert call_args.kwargs["plugin"] == "debug"
    assert call_args.kwargs["type_filter"] == "assembly"
