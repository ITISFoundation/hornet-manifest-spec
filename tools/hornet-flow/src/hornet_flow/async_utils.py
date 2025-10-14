import asyncio


class AsyncBridge:
    """Bridge to handle sync/async communication for workflow events."""

    def __init__(
        self, app_ready_event: asyncio.Event, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._app_ready_event = app_ready_event
        self._loop = loop

    def wait_for_app_ready_sync(self, **kwargs) -> None:
        """Sync wrapper that waits for async event.

        Raises:
            RuntimeError: If called from incompatible event loop context
            Exception: If waiting for the event fails
        """
        # Check if we're running in an event loop thread
        try:
            asyncio.get_running_loop()
            # We're in an event loop thread - use run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(
                self._app_ready_event.wait(), self._loop
            )
            future.result()  # Block until the event is set
        except RuntimeError:
            # No running loop - we can safely use asyncio.run
            asyncio.run(self._app_ready_event.wait())
