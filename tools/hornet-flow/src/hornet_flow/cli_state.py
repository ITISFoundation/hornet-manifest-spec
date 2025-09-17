"""CLI state management and shared utilities.

This module contains global state, console, logger, and utility functions
that are shared between CLI modules without creating circular imports.
"""

import logging
from dataclasses import dataclass

from rich.console import Console
from rich.logging import RichHandler

# Global console instance
console = Console()

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


def setup_logging(
    verbose: bool = False, quiet: bool = False, plain: bool = False
) -> None:
    """Configure logging with RichHandler or plain logging."""
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    if plain:
        # Use plain logging for better console compatibility
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s: %(message)s [%(filename)s:%(funcName)s:%(lineno)d]",
            handlers=[logging.StreamHandler()],
        )
    else:
        # Use rich formatting
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            handlers=[RichHandler(console=console, markup=True, show_path=True)],
        )


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
    setup_logging(verbose, quiet, plain)
