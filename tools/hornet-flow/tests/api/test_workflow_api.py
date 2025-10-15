# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

import tempfile
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from hornet_flow.api import EventDispatcher, HornetFlowAPI, WorkflowEvent
from hornet_flow.exceptions import ApiFileNotFoundError, ApiInputValueError


@pytest.fixture
def api() -> HornetFlowAPI:
    """Create a HornetFlowAPI instance for testing."""
    return HornetFlowAPI()


def test_workflow_run_basic(mocker: MockerFixture, api: HornetFlowAPI) -> None:
    """Test basic workflow run from README example."""
    # Setup
    mock_run_workflow = mocker.patch(
        "hornet_flow.services.workflow_service.run_workflow"
    )
    mock_run_workflow.return_value = (5, 10)

    # Execute
    success_count, total_count = api.workflow.run(
        repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        plugin="osparc",
        fail_fast=True,
    )

    # Verify
    assert success_count == 5
    assert total_count == 10
    mock_run_workflow.assert_called_once()

    # Check that the right parameters were passed
    call_args = mock_run_workflow.call_args
    assert (
        call_args.kwargs["repo_url"]
        == "https://github.com/COSMIIC-Inc/Implantables-Electrodes"
    )
    assert call_args.kwargs["plugin"] == "osparc"
    assert call_args.kwargs["fail_fast"] is True


def test_workflow_watch_basic(
    mocker: MockerFixture, api: HornetFlowAPI, tmp_path: Path
) -> None:
    """Test basic watch functionality from README example."""
    mock_watch = mocker.patch("hornet_flow.services.watcher.watch_for_metadata")

    inputs_dir = tmp_path / "inputs"
    work_dir = tmp_path / "work"

    # Create inputs directory
    inputs_dir.mkdir()

    # Execute
    api.workflow.watch(
        inputs_dir=str(inputs_dir), work_dir=str(work_dir), plugin="osparc", once=True
    )

    # Verify
    mock_watch.assert_called_once()
    call_args = mock_watch.call_args
    assert call_args.kwargs["plugin"] == "osparc"
    assert call_args.kwargs["once"] is True


def test_workflow_watch_nonexistent_directory(api: HornetFlowAPI) -> None:
    """Test watch with non-existent directory raises proper exception."""
    with pytest.raises(ApiFileNotFoundError):
        api.workflow.watch(inputs_dir="/nonexistent/directory", work_dir="/tmp/work")


def test_workflow_watch_file_instead_of_directory(api: HornetFlowAPI) -> None:
    """Test watch with file path instead of directory raises proper exception."""
    with tempfile.NamedTemporaryFile() as temp_file:
        with pytest.raises(ApiInputValueError):
            api.workflow.watch(
                inputs_dir=temp_file.name,  # File, not directory
                work_dir="/tmp/work",
            )


def test_workflow_run_with_event_dispatcher(
    mocker: MockerFixture, api: HornetFlowAPI
) -> None:
    """Test workflow run with event dispatcher from README example."""
    mock_run_workflow = mocker.patch(
        "hornet_flow.services.workflow_service.run_workflow"
    )
    mock_run_workflow.return_value = (3, 5)

    dispatcher = EventDispatcher()
    callback_called = False

    def check_external_readiness(**kwargs) -> None:
        nonlocal callback_called
        callback_called = True

    dispatcher.register(WorkflowEvent.MANIFESTS_READY, check_external_readiness)

    # Execute
    success_count, total_count = api.workflow.run(
        repo_url="https://github.com/COSMIIC-Inc/Implantables-Electrodes",
        plugin="osparc",
        event_dispatcher=dispatcher,
    )

    # Verify workflow ran
    assert success_count == 3
    assert total_count == 5
    mock_run_workflow.assert_called_once()

    # Verify event dispatcher was passed
    call_args = mock_run_workflow.call_args
    assert call_args.kwargs["event_dispatcher"] == dispatcher


def test_watch_with_event_dispatcher(
    mocker: MockerFixture, api: HornetFlowAPI, tmp_path: Path
) -> None:
    """Test watcher with event dispatcher integration."""
    mock_watch = mocker.patch("hornet_flow.services.watcher.watch_for_metadata")

    dispatcher = EventDispatcher()
    callback_called = False

    def check_readiness(**kwargs) -> None:
        nonlocal callback_called
        callback_called = True

    dispatcher.register(WorkflowEvent.MANIFESTS_READY, check_readiness)

    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()

    api.workflow.watch(
        inputs_dir=str(inputs_dir), work_dir="/tmp/work", event_dispatcher=dispatcher
    )

    # Verify event dispatcher was passed to watcher
    mock_watch.assert_called_once()
    call_args = mock_watch.call_args
    assert call_args.kwargs["event_dispatcher"] == dispatcher
