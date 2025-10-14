"""CLI-specific exceptions and decorators for hornet-flow.

These exceptions contain CLI-specific concerns like exit codes and are used
to convert core domain exceptions into proper CLI behavior.
"""

import logging
import os
from collections.abc import Callable
from functools import wraps
from typing import Any

import typer

# Map core exceptions to appropriate exit codes
from .exceptions import (
    ApiFileNotFoundError,
    ApiInputValueError,
    ApiProcessingError,
    ApiValidationError,
    HornetFlowError,
)

_logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Base exception for CLI-specific operations."""

    def __init__(self, message: str, exit_code: int = os.EX_SOFTWARE):
        super().__init__(message)
        self.exit_code = exit_code


class CLIValidationError(CLIError):
    """CLI-specific validation error with exit code."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_DATAERR)


class CLIProcessingError(CLIError):
    """CLI-specific processing error with exit code."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_SOFTWARE)


class CLIInputError(CLIError):
    """CLI-specific input error with exit code."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_USAGE)


class CLIFileNotFoundError(CLIError):
    """CLI-specific file not found error with exit code."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_NOINPUT)


def handle_command_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle exceptions in CLI commands and convert them to typer.Exit."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except CLIError as e:
            _logger.exception("❌ Command failed: %s", e)
            raise typer.Exit(e.exit_code) from e
        except HornetFlowError as e:
            # Convert core exceptions to CLI exceptions with appropriate exit codes
            _logger.exception("❌ Operation failed: %s", e)

            if isinstance(e, ApiValidationError):
                raise typer.Exit(os.EX_DATAERR) from e
            elif isinstance(e, ApiInputValueError):
                raise typer.Exit(os.EX_USAGE) from e
            elif isinstance(e, ApiFileNotFoundError):
                raise typer.Exit(os.EX_NOINPUT) from e
            elif isinstance(e, ApiProcessingError):
                raise typer.Exit(os.EX_SOFTWARE) from e
            else:
                raise typer.Exit(os.EX_SOFTWARE) from e
        except Exception as e:
            _logger.exception("❌ Unexpected error: %s [%s]", e, type(e).__name__)
            raise typer.Exit(os.EX_SOFTWARE) from e

    return wrapper
