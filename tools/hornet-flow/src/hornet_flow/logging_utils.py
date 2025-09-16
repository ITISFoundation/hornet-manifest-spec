import contextlib
import logging


class log_action(contextlib.ContextDecorator):  # pylint: disable=invalid-name
    """Context manager/decorator for logging action start/completion.

    Args:
        logger: Logger instance to use
        action: Action description (e.g., "Reading manifest", "Loading component X")
        level: Log level to use (default: INFO)

    Usage as context manager:
        with log_action(logger, "Loading component", level=logging.DEBUG):
            # your code here
            pass

    Usage as decorator:
        @log_action(logger, "Processing data")
        def my_function():
            # your code here
            pass
    """

    def __init__(
        self,
        logger: logging.Logger,
        action: str,
        *,
        level: int = logging.INFO,
    ):
        self.logger = logger
        self.action = action
        self.level = level

    def __enter__(self):
        self.logger.log(self.level, "%s ...", self.action, stacklevel=2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.log(self.level, "%s [success]", self.action, stacklevel=2)

        return False  # do not suppress exceptions


class log_and_suppress(contextlib.ContextDecorator):  # pylint: disable=invalid-name
    """Context manager/decorator that suppresses exceptions while logging them.

    Args:
        logger: Logger instance to use
        action: Action description for logging (optional)
        exceptions: Exception types to suppress (default: Exception)

    Usage as context manager:
        with log_and_suppress(logger, "Optional operation"):
            # might fail but won't crash
            risky_operation()

    Usage as decorator:
        @log_and_suppress(logger, "Cleanup task")
        def cleanup():
            # errors will be logged but not raised
            pass
    """

    def __init__(
        self,
        logger: logging.Logger,
        *exceptions,
        action: str = "Operation",
    ):
        self.logger = logger
        self.action = action
        self.exceptions = exceptions or (Exception,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, self.exceptions):
            self.logger.exception(
                "%s failed but continuing: %s", self.action, str(exc_val), stacklevel=2
            )
            return True  # Suppress the exception
        return False
