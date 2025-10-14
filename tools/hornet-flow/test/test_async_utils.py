# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# pylint: disable=unused-variable
# pylint: disable=too-many-arguments

import asyncio

import pytest

from hornet_flow.async_utils import AsyncBridge
from hornet_flow.services.workflow_service import EventDispatcher, WorkflowEvent


@pytest.fixture
def app_ready_event() -> asyncio.Event:
    """Fixture providing an asyncio Event for app readiness."""
    return asyncio.Event()


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    """Fixture providing the current event loop."""
    return asyncio.get_event_loop()


@pytest.fixture
def async_bridge(
    app_ready_event: asyncio.Event, event_loop: asyncio.AbstractEventLoop
) -> AsyncBridge:
    """Fixture providing an AsyncBridge instance."""
    return AsyncBridge(app_ready_event, event_loop)


def sync_function_that_uses_event_dispatcher(event_dispatcher: EventDispatcher) -> str:
    """Simulates a sync function that registers callbacks with EventDispatcher."""
    result = "not_ready"

    def on_app_ready(**kwargs):
        nonlocal result
        result = "ready"

    # Register callback for app ready event
    event_dispatcher.register(WorkflowEvent.BEFORE_PROCESS_MANIFEST, on_app_ready)

    # Trigger the event to see if callback fires
    event_dispatcher.trigger(WorkflowEvent.BEFORE_PROCESS_MANIFEST)

    return result


async def test_async_bridge_coordination(
    async_bridge: AsyncBridge, app_ready_event: asyncio.Event
):
    """Test that AsyncBridge properly adapts async events for sync functions."""

    # Create EventDispatcher that will be passed to sync function
    event_dispatcher = EventDispatcher()

    # Register AsyncBridge callback with EventDispatcher
    event_dispatcher.register(
        WorkflowEvent.BEFORE_PROCESS_MANIFEST, async_bridge.wait_for_app_ready_sync
    )

    # Track execution state
    sync_function_completed = False
    sync_function_result = None

    async def run_sync_function():
        """Run the sync function in a thread."""
        nonlocal sync_function_completed, sync_function_result
        sync_function_result = await asyncio.to_thread(
            sync_function_that_uses_event_dispatcher, event_dispatcher
        )
        sync_function_completed = True

    # Start the sync function (it will wait for app ready event)
    task = asyncio.create_task(run_sync_function())

    # Give it a moment to start and register callback
    await asyncio.sleep(0.1)
    assert not sync_function_completed

    # Set the app ready event (simulating app startup completion)
    app_ready_event.set()

    # Wait for sync function to complete
    await asyncio.wait_for(task, timeout=1.0)

    # Verify the sync function completed successfully
    assert sync_function_completed
    assert sync_function_result == "ready"
