# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable

from pathlib import Path

import pytest

from hornet_flow.api import EventDispatcher, WorkflowEvent


@pytest.fixture
def dispatcher() -> EventDispatcher:
    """Create an EventDispatcher instance for testing."""
    return EventDispatcher()


def test_event_dispatcher_creation(dispatcher: EventDispatcher) -> None:
    """Test creating event dispatcher from README example."""
    assert dispatcher is not None
    assert hasattr(dispatcher, "register")
    assert hasattr(dispatcher, "trigger")


def test_single_event_handler(dispatcher: EventDispatcher) -> None:
    """Test single event handler registration and triggering."""
    callback_called = False
    callback_kwargs = {}

    def check_external_readiness(**kwargs) -> None:
        nonlocal callback_called, callback_kwargs
        callback_called = True
        callback_kwargs = kwargs

    # Register callback
    dispatcher.register(WorkflowEvent.BEFORE_PROCESS_MANIFEST, check_external_readiness)

    # Trigger event
    test_kwargs = {
        "repo_path": Path("/test/repo"),
        "cad_manifest": Path("/test/cad.json"),
        "sim_manifest": None,
        "release": None,
    }
    dispatcher.trigger(WorkflowEvent.BEFORE_PROCESS_MANIFEST, **test_kwargs)

    # Verify
    assert callback_called
    assert callback_kwargs == test_kwargs


def test_multiple_event_handlers(dispatcher: EventDispatcher) -> None:
    """Test multiple event handlers from README example."""
    # Track which handlers were called
    handlers_called: list[str] = []

    def check_service_health(**kwargs) -> None:
        handlers_called.append("health_check")

    def log_workflow_progress(**kwargs) -> None:
        handlers_called.append("log_progress")

    def send_notification(**kwargs) -> None:
        handlers_called.append("notification")

    # Register all handlers
    dispatcher.register(WorkflowEvent.BEFORE_PROCESS_MANIFEST, check_service_health)
    dispatcher.register(WorkflowEvent.BEFORE_PROCESS_MANIFEST, log_workflow_progress)
    dispatcher.register(WorkflowEvent.BEFORE_PROCESS_MANIFEST, send_notification)

    # Trigger event
    dispatcher.trigger(WorkflowEvent.BEFORE_PROCESS_MANIFEST, repo_path=Path("/test"))

    # Verify all handlers were called
    assert len(handlers_called) == 3
    assert "health_check" in handlers_called
    assert "log_progress" in handlers_called
    assert "notification" in handlers_called


def test_event_handler_exception_handling(dispatcher: EventDispatcher) -> None:
    """Test that exceptions in event handlers are properly handled."""

    def failing_handler(**kwargs) -> None:
        raise RuntimeError("Handler failed")

    def successful_handler(**kwargs) -> None:
        successful_handler.called = True  # type: ignore

    successful_handler.called = False  # type: ignore

    # Register both handlers
    dispatcher.register(WorkflowEvent.BEFORE_PROCESS_MANIFEST, failing_handler)
    dispatcher.register(WorkflowEvent.BEFORE_PROCESS_MANIFEST, successful_handler)

    # Trigger event - should not raise exception
    dispatcher.trigger(WorkflowEvent.BEFORE_PROCESS_MANIFEST, repo_path=Path("/test"))

    # Verify successful handler was still called despite failing handler
    assert successful_handler.called  # type: ignore
