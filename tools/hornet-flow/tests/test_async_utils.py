# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# pylint: disable=unused-variable
# pylint: disable=too-many-arguments

import asyncio
import logging

import pytest

from hornet_flow.services.workflow_service import AsyncEventDispatcher, WorkflowEvent


async def test_async_event_dispatcher_basic():
    """Test basic async event dispatcher functionality."""
    dispatcher = AsyncEventDispatcher()
    results = []

    async def callback1(**kwargs):
        results.append(("callback1", kwargs))

    async def callback2(**kwargs):
        results.append(("callback2", kwargs))

    # Register callbacks
    dispatcher.register(WorkflowEvent.WORKFLOW_STARTED, callback1)
    dispatcher.register(WorkflowEvent.WORKFLOW_STARTED, callback2)

    # Trigger event
    await dispatcher.trigger(WorkflowEvent.WORKFLOW_STARTED, data="test", value=123)

    # Verify both callbacks were called with correct data
    assert len(results) == 2
    assert results[0] == ("callback1", {"data": "test", "value": 123})
    assert results[1] == ("callback2", {"data": "test", "value": 123})


async def test_async_event_dispatcher_sequential_execution():
    """Test that callbacks execute sequentially, not concurrently."""
    dispatcher = AsyncEventDispatcher()
    execution_log = []

    async def slow_callback(**kwargs):
        execution_log.append("slow_start")
        await asyncio.sleep(0.1)
        execution_log.append("slow_end")

    async def fast_callback(**kwargs):
        execution_log.append("fast_start")
        await asyncio.sleep(0.01)
        execution_log.append("fast_end")

    # Register callbacks
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, slow_callback)
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, fast_callback)

    # Trigger event
    await dispatcher.trigger(WorkflowEvent.MANIFESTS_READY)

    # Verify sequential execution (slow completes before fast starts)
    assert execution_log == ["slow_start", "slow_end", "fast_start", "fast_end"]


async def test_async_event_dispatcher_error_handling(
    caplog: pytest.LogCaptureFixture,
):
    """Test that errors in one callback don't prevent others from running."""
    dispatcher = AsyncEventDispatcher()
    results = []

    async def failing_callback(**kwargs):
        raise ValueError("Intentional error")

    async def successful_callback(**kwargs):
        results.append("success")

    # Register callbacks
    dispatcher.register(WorkflowEvent.REPOSITORY_READY, failing_callback)
    dispatcher.register(WorkflowEvent.REPOSITORY_READY, successful_callback)

    # Trigger event - should not raise despite failing callback
    with caplog.at_level(logging.ERROR):
        await dispatcher.trigger(WorkflowEvent.REPOSITORY_READY)

    # Verify successful callback still ran
    assert "success" in results

    # Verify error was logged (check both message and exc_info)
    assert any(
        "Error in event callback" in record.getMessage() and record.exc_info is not None
        for record in caplog.records
    )


async def test_async_event_dispatcher_rejects_sync_callbacks():
    """Test that registering a sync callback raises TypeError."""
    dispatcher = AsyncEventDispatcher()

    def sync_callback(**kwargs):
        pass

    # Should raise TypeError when registering sync callback
    with pytest.raises(TypeError, match="must be an async function"):
        dispatcher.register(WorkflowEvent.WORKFLOW_STARTED, sync_callback)


async def test_async_event_dispatcher_multiple_events():
    """Test dispatcher with multiple different events."""
    dispatcher = AsyncEventDispatcher()
    results = {}

    async def workflow_started_callback(**kwargs):
        results["started"] = kwargs

    async def workflow_completed_callback(**kwargs):
        results["completed"] = kwargs

    # Register callbacks for different events
    dispatcher.register(WorkflowEvent.WORKFLOW_STARTED, workflow_started_callback)
    dispatcher.register(WorkflowEvent.WORKFLOW_COMPLETED, workflow_completed_callback)

    # Trigger different events
    await dispatcher.trigger(WorkflowEvent.WORKFLOW_STARTED, stage="begin")
    await dispatcher.trigger(WorkflowEvent.WORKFLOW_COMPLETED, stage="end")

    # Verify each callback received its event data
    assert results["started"] == {"stage": "begin"}
    assert results["completed"] == {"stage": "end"}


async def test_async_event_dispatcher_no_callbacks():
    """Test triggering an event with no registered callbacks."""
    dispatcher = AsyncEventDispatcher()

    # Should not raise when no callbacks registered
    await dispatcher.trigger(WorkflowEvent.WORKFLOW_STARTED, data="test")


async def test_async_event_dispatcher_async_coordination():
    """Test async event coordination between components."""
    dispatcher = AsyncEventDispatcher()
    external_system_ready = asyncio.Event()
    processing_started = False

    async def wait_for_external_system(**kwargs):
        """Callback that waits for external async event."""
        await external_system_ready.wait()

    async def start_processing(**kwargs):
        """Callback that runs after external system is ready."""
        nonlocal processing_started
        processing_started = True

    # Register callbacks
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, wait_for_external_system)
    dispatcher.register(WorkflowEvent.MANIFESTS_READY, start_processing)

    # Create task to trigger event
    trigger_task = asyncio.create_task(
        dispatcher.trigger(WorkflowEvent.MANIFESTS_READY)
    )

    # Give it a moment - should be waiting
    await asyncio.sleep(0.05)
    assert not processing_started

    # Signal external system ready
    external_system_ready.set()

    # Wait for trigger to complete
    await trigger_task

    # Verify processing started after external system was ready
    assert processing_started
