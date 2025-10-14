# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# pylint: disable=unused-variable
# pylint: disable=too-many-arguments

import asyncio
import threading

import pytest

from hornet_flow.async_utils import AsyncBridge


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


async def test_async_bridge_coordination(
    async_bridge: AsyncBridge, app_ready_event: asyncio.Event
):
    # Setup
    bridge, loop = async_bridge, event_loop

    # Track when background task completes
    background_completed = threading.Event()
    background_exception = None

    def background_task():
        """Simulates the workflow watching background task."""
        nonlocal background_exception
        try:
            # This simulates what happens in the workflow setup
            async_bridge.wait_for_app_ready_sync()
            background_completed.set()
        except Exception as e:
            background_exception = e
            background_completed.set()

    # Start background task (simulating asyncio.to_thread behavior)
    background_thread = threading.Thread(target=background_task)
    background_thread.start()

    # Verify background task is waiting
    await asyncio.sleep(0.1)
    assert not background_completed.is_set()

    # Set the app ready event (simulating app startup completion)
    app_ready_event.set()

    # Wait for background task to complete
    background_thread.join(timeout=1.0)

    # Verify coordination worked
    assert background_completed.is_set()
    assert background_exception is None
    assert background_thread.is_alive() is False


async def test_async_bridge_from_async_context(
    async_bridge: AsyncBridge, app_ready_event: asyncio.Event
):
    """Test AsyncBridge when called from within an async context."""
    # Set event immediately
    app_ready_event.set()

    # This should work without blocking since event is already set
    async def async_caller():
        # Simulate calling from async context (though this is unusual)
        await asyncio.to_thread(async_bridge.wait_for_app_ready_sync)

    # Should complete quickly since event is set
    await asyncio.wait_for(async_caller(), timeout=1.0)


async def test_multiple_waiters(
    async_bridge: AsyncBridge, app_ready_event: asyncio.Event
):
    """Test that multiple background tasks can wait for the same event."""
    completed_tasks = []

    def create_background_task(task_id):
        def task():
            async_bridge.wait_for_app_ready_sync()
            completed_tasks.append(task_id)

        return task

    # Start multiple background tasks
    threads = []
    for i in range(3):
        thread = threading.Thread(target=create_background_task(i))
        thread.start()
        threads.append(thread)

    # Verify all are waiting
    await asyncio.sleep(0.1)
    assert len(completed_tasks) == 0

    # Set the event
    app_ready_event.set()

    # Wait for all tasks to complete
    for thread in threads:
        thread.join(timeout=1.0)

    # Verify all completed
    assert len(completed_tasks) == 3
    assert set(completed_tasks) == {0, 1, 2}


def test_sync_context_no_loop():
    """Test AsyncBridge when called from pure sync context (no event loop)."""
    # This test runs without asyncio.run to simulate pure sync context
    app_ready_event = asyncio.Event()
    loop = asyncio.new_event_loop()
    bridge = AsyncBridge(app_ready_event, loop)

    # Set event in the loop
    loop.call_soon_threadsafe(app_ready_event.set)

    # Start the loop in background
    loop_thread = threading.Thread(target=loop.run_forever)
    loop_thread.daemon = True
    loop_thread.start()

    try:
        # This should work from sync context
        bridge.wait_for_app_ready_sync()
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=1.0)
        loop.close()
