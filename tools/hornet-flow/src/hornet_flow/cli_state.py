"""CLI state management and shared utilities.

This module contains global state, console, logger, and utility functions
that are shared between CLI modules without creating circular imports.
"""

import logging
from dataclasses import dataclass

from rich.console import Console

from .logging_utils import setup_logging

# Global console instance
app_console = Console()

# Global logger
app_logger = logging.getLogger(__name__)


# Global state for CLI options
@dataclass
class AppState:
    verbose: bool = False
    quiet: bool = False
    plain: bool = False


# Global app state instance
app_state = AppState()


def merge_global_options(
    main_verbose: bool = False,
    main_quiet: bool = False,
    main_plain: bool = False,
    cmd_verbose: bool = False,
    cmd_quiet: bool = False,
    cmd_plain: bool = False,
) -> None:
    """Merge global options from main callback and command, giving precedence to command-level options."""
    # Command-level options take precedence
    verbose = cmd_verbose or main_verbose
    quiet = cmd_quiet or main_quiet
    plain = cmd_plain or main_plain

    # Update global state
    app_state.verbose = verbose
    app_state.quiet = quiet
    app_state.plain = plain

    # Reconfigure logging if options changed
    setup_logging(verbose, quiet, plain, console=app_console)
