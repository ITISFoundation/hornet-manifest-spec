# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

from pathlib import Path

import pytest

from hornet_flow.services.workflow_service import AsyncEventDispatcher, WorkflowEvent


@pytest.fixture
def dispatcher() -> AsyncEventDispatcher:
    """Create an AsyncEventDispatcher instance for testing."""
    return AsyncEventDispatcher()


@pytest.mark.asyncio
async def test_event_dispatcher_creation(dispatcher: AsyncEventDispatcher) -> None:
    """Test creating async event dispatcher from README example."""
    assert dispatcher is not None
    assert hasattr(dispatcher, "register")
    assert hasattr(dispatcher, "trigger")


@pytest.mark.asyncio
async def test_single_event_handler(dispatcher: AsyncEventDispatcher) -> None:
    """Test single async event handler registration and triggering."""
    callback_called = False
    callback_kwargs = {}

    async def check_external_readiness(**kwargs) -> None:
        nonlocal callback_called, callback_kwargs
        callback_called = True
        callback_kwargs = kwargs

    # Register callback
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, check_external_readiness)

    # Trigger event
    test_kwargs = {
        "repo_path": Path("/test/repo"),
        "cad_manifest": Path("/test/cad.json"),
        "sim_manifest": None,
        "release": None,
    }
    await dispatcher.trigger(WorkflowEvent.MANIFESTS_READY, **test_kwargs)

    # Verify
    assert callback_called
    assert callback_kwargs == test_kwargs


@pytest.mark.asyncio
async def test_multiple_event_handlers(dispatcher: AsyncEventDispatcher) -> None:
    """Test multiple async event handlers from README example."""
    # Track which handlers were called
    handlers_called: list[str] = []

    async def check_service_health(**kwargs) -> None:
        handlers_called.append("health_check")

    async def log_workflow_progress(**kwargs) -> None:
        handlers_called.append("log_progress")

    async def send_notification(**kwargs) -> None:
        handlers_called.append("notification")

    # Register all handlers
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, check_service_health)
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, log_workflow_progress)
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, send_notification)

    # Trigger event
    await dispatcher.trigger(WorkflowEvent.MANIFESTS_READY, repo_path=Path("/test"))

    # Verify all handlers were called
    assert len(handlers_called) == 3
    assert "health_check" in handlers_called
    assert "log_progress" in handlers_called
    assert "notification" in handlers_called


@pytest.mark.asyncio
async def test_event_handler_exception_handling(
    dispatcher: AsyncEventDispatcher,
) -> None:
    """Test that exceptions in async event handlers are properly handled."""

    async def failing_handler(**kwargs) -> None:
        raise RuntimeError("Handler failed")

    async def successful_handler(**kwargs) -> None:
        successful_handler.called = True  # type: ignore

    successful_handler.called = False  # type: ignore

    # Register both handlers
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, failing_handler)
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, successful_handler)

    # Trigger event - should not raise exception
    await dispatcher.trigger(WorkflowEvent.MANIFESTS_READY, repo_path=Path("/test"))

    # Verify successful handler was still called despite failing handler
    assert successful_handler.called  # type: ignore
