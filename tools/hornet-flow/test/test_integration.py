# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from hornet_flow.api import HornetFlowAPI
from hornet_flow.exceptions import ApiProcessingError, ApiValidationError


@pytest.fixture
def api() -> HornetFlowAPI:
    """Create a HornetFlowAPI instance for testing."""
    return HornetFlowAPI()


def test_complete_workflow_with_error_handling(
    mocker: MockerFixture, api: HornetFlowAPI
) -> None:
    """Test complete workflow with error handling from README example."""
    # Setup successful responses
    mock_clone = mocker.patch("hornet_flow.services.git_service.clone_repository")
    mock_find = mocker.patch(
        "hornet_flow.services.manifest_service.find_hornet_manifests"
    )
    mock_run_workflow = mocker.patch(
        "hornet_flow.services.workflow_service.run_workflow"
    )

    mock_clone.return_value = Path("/tmp/electrodes")
    mock_find.return_value = (Path("/repo/cad.json"), Path("/repo/sim.json"))
    mock_run_workflow.return_value = (3, 5)

    try:
        # Clone repository
        repo_path = api.repo.clone(
            repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
            dest="/tmp/electrodes",
        )

        # Validate manifests
        cad_valid, sim_valid = api.manifest.validate(str(repo_path))

        # Run workflow
        success_count, total_count = api.workflow.run(
            repo_path=str(repo_path), plugin="osparc", fail_fast=True
        )

        # Verify successful execution
        assert repo_path == Path("/tmp/electrodes")
        assert success_count == 3
        assert total_count == 5

    except (ApiValidationError, ApiProcessingError) as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_batch_processing_multiple_repositories(
    mocker: MockerFixture, api: HornetFlowAPI
) -> None:
    """Test batch processing multiple repositories from README example."""
    # Setup
    mock_run_workflow = mocker.patch(
        "hornet_flow.services.workflow_service.run_workflow"
    )
    mock_run_workflow.side_effect = [(2, 3), (4, 5)]

    repositories = [
        "https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        "https://github.com/CARSSCenter/Sub-mm-Parylene-Cuff-Electrode",
    ]

    results: list[tuple[str, int | None, int | str]] = []
    for repo_url in repositories:
        try:
            success_count, total_count = api.workflow.run(
                repo_url=repo_url, plugin="debug", work_dir="/tmp/batch-processing"
            )
            results.append((repo_url, success_count, total_count))
        except Exception as e:
            results.append((repo_url, None, str(e)))

    # Verify
    assert len(results) == 2
    assert results[0] == (repositories[0], 2, 3)
    assert results[1] == (repositories[1], 4, 5)
    assert mock_run_workflow.call_count == 2
