import asyncio
import logging

_logger = logging.getLogger(__name__)


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
            RuntimeError: If the event loop is closed or shutting down
            Exception: If waiting for the event fails
        """
        waiter_coro = self._app_ready_event.wait()
        future = asyncio.run_coroutine_threadsafe(waiter_coro, self._loop)
        result = future.result()  # Block until the asyncio event is set
        _logger.debug("App is ready: %s", result)
