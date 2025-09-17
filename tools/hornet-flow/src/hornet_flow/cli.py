import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Annotated, Optional

import jsonschema
import typer
from click import Choice
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

import hornet_flow
from hornet_flow import service
from hornet_flow.plugins import discover_plugins, get_default_plugin
from hornet_flow.processors import ManifestProcessor

__version__ = "0.2.0"


#
# ERRORS: Custom exceptions and helpers for CLI operations
#
class HornetFlowError(Exception):
    """Base exception for hornet-flow CLI operations."""

    def __init__(self, message: str, exit_code: int = os.EX_SOFTWARE):
        super().__init__(message)
        self.exit_code = exit_code


class DataValidationError(HornetFlowError):
    """Raised when validation fails."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_DATAERR)


class ProcessingError(HornetFlowError):
    """Raised when processing operations fail."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_SOFTWARE)


class InputError(HornetFlowError):
    """Raised when input parameters are invalid."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_USAGE)


class InputFileNotFoundError(HornetFlowError):
    """Raised when required files are not found."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=os.EX_NOINPUT)


def handle_command_errors(func):
    """Decorator to handle exceptions in CLI commands and convert them to typer.Exit."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HornetFlowError as e:
            _logger.exception("❌ Command failed: %s", e)
            raise typer.Exit(e.exit_code) from e
        except Exception as e:
            _logger.exception("❌ Unexpected error: %s [%s]", e, type(e).__name__)
            raise typer.Exit(os.EX_SOFTWARE) from e

    return wrapper


def _create_processing_error(
    e: subprocess.CalledProcessError, operation: str
) -> ProcessingError:
    """Handle subprocess errors with detailed logging and return a ProcessingError."""
    error_details = [f"Failed to {operation}"]
    if e.cmd:
        error_details.append(f"Command: {' '.join(e.cmd)}")
    error_details.append(f"Exit code: {e.returncode}")

    if e.stdout:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout
        error_details.append(f"stdout: {stdout}")
    if e.stderr:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr
        error_details.append(f"stderr: {stderr}")

    return ProcessingError(". ".join(error_details))


## Console and logging setup
console = Console()


# Global state for CLI options
@dataclass
class AppState:
    verbose: bool = False
    quiet: bool = False
    plain: bool = False


app_state = AppState()

_logger = logging.getLogger(__name__)


def _setup_logging(
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


def _merge_global_options(
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
    _setup_logging(verbose, quiet, plain)


def _validate_manifest_schema(
    manifest_path: Path, manifest_type: str, fail_fast: bool = True
) -> None:
    """Validate a manifest schema with consistent error handling."""
    try:
        service.validate_manifest_schema(manifest_path)
        _logger.info("%s manifest schema validation successful", manifest_type)
    except jsonschema.ValidationError as e:
        msg = f"{manifest_type} manifest schema validation failed: {e.message}"
        if fail_fast:
            raise DataValidationError(msg) from e
        _logger.error(msg)


def version_callback(value: bool):
    if value:
        console.print(f"hornet-flow version {__version__}")
        raise typer.Exit(os.EX_OK)


#
# CLI APPLICATION
#

app = typer.Typer(help="Hornet Manifest Flow - Load and process hornet manifests")


# Create sub-apps for each resource
workflow_app = typer.Typer(help="Workflow operations")
repo_app = typer.Typer(help="Repository operations")
manifest_app = typer.Typer(help="Manifest operations")
cad_app = typer.Typer(help="CAD operations")

# Add sub-apps to main app
app.add_typer(workflow_app, name="workflow")
app.add_typer(repo_app, name="repo")
app.add_typer(manifest_app, name="manifest")
app.add_typer(cad_app, name="cad")


#
# CLI COMMANDS
#

# Type aliases for options repeated more than once
VerboseOption = Annotated[
    bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
]
QuietOption = Annotated[bool, typer.Option("--quiet", "-q", help="Only show errors")]
PlainOption = Annotated[
    bool, typer.Option("--plain", help="Use plain logging output (no rich formatting)")
]
RepoPathOption = Annotated[str, typer.Option("--repo-path", help="Repository path")]
PluginOption = Annotated[
    Optional[str],
    typer.Option("--plugin", help="Plugin to use for processing components"),
]
TypeFilterOption = Annotated[
    Optional[str], typer.Option("--type-filter", help="Filter components by type")
]
NameFilterOption = Annotated[
    Optional[str], typer.Option("--name-filter", help="Filter components by name")
]
FailFastOption = Annotated[
    bool, typer.Option("--fail-fast", help="Stop on first error")
]


# Global version option
@app.callback()
def main(
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, help="Show version and exit"
        ),
    ] = None,
):
    """Hornet Manifest Flow - Load and process hornet manifests"""
    _ = version
    # Store global options in app state
    app_state.verbose = verbose
    app_state.quiet = quiet
    app_state.plain = plain


@app.command("info")
def show_info(
    verbose: VerboseOption = False,
) -> None:
    """Show current configuration and system information."""

    _merge_global_options(app_state.verbose, False, False, verbose, False, False)

    console.print()
    console.print(Panel.fit("🔧 Hornet Flow Configuration", style="bold blue"))

    # Version information
    version_table = Table(show_header=False, box=None, padding=(0, 1))
    version_table.add_column("Property", style="cyan", min_width=20)
    version_table.add_column("Value", style="white")

    version_table.add_row("Version", f"v{__version__}")
    version_table.add_row("Python", f"{sys.version.split()[0]}")
    version_table.add_row("Platform", platform.platform())

    # Check git version
    git_version = service.check_git_version()
    if git_version:
        version_table.add_row("Git", git_version)
    else:
        version_table.add_row("Git", "[red]Not found or not working[/red]")

    console.print()
    console.print("📋 Version Information")
    console.print(version_table)

    # Plugin information
    try:
        plugins = discover_plugins()
        default_plugin = get_default_plugin()

        console.print()
        console.print("🔌 Available Plugins")

        if plugins:
            plugin_table = Table(show_header=True, box=None, padding=(0, 1))
            plugin_table.add_column("Name", style="cyan", min_width=15)
            plugin_table.add_column("Status", style="white", min_width=10)
            plugin_table.add_column("Description", style="dim")

            for plugin_name, plugin_class in plugins.items():
                status = "✅ Default" if plugin_name == default_plugin else "Available"

                # Try to get plugin description
                try:
                    description = plugin_class.__doc__ or "No description available"
                    if description:
                        description = description.split("\n")[0].strip()
                except Exception:  # pylint: disable=broad-exception-caught
                    description = "No description available"

                plugin_table.add_row(plugin_name, status, description)

            console.print(plugin_table)
        else:
            console.print("  [red]No plugins found[/red]")

    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.exception("Error loading plugins")
        console.print(f"  [red]Error loading plugins: {e}[/red]")

    # Configuration details (verbose mode) - use global verbose option
    if verbose:
        console.print()
        console.print("⚙️  Configuration Details")

        config_table = Table(show_header=False, box=None, padding=(0, 1))
        config_table.add_column("Setting", style="cyan", min_width=25)
        config_table.add_column("Value", style="white")

        # Show Python path info
        package_path = Path(hornet_flow.__file__).parent
        config_table.add_row("Package Location", str(package_path))

        # Show plugin directory
        plugin_dir = package_path / "plugins"
        config_table.add_row("Plugin Directory", str(plugin_dir))
        config_table.add_row("Plugin Directory Exists", str(plugin_dir.exists()))

        # Show temp directory
        temp_dir = tempfile.gettempdir()
        config_table.add_row("Temp Directory", temp_dir)

        console.print(config_table)

        # Show environment variables if relevant
        console.print()
        console.print("🌍 Environment")
        env_table = Table(show_header=False, box=None, padding=(0, 1))
        env_table.add_column("Variable", style="cyan", min_width=25)
        env_table.add_column("Value", style="dim")

        # Check for relevant environment variables
        env_vars = ["HOME", "TMPDIR", "PATH"]
        for var in env_vars:
            value = os.environ.get(var, "Not set")
            # Truncate long PATH values
            if var == "PATH" and len(value) > 60:
                value = value[:57] + "..."
            env_table.add_row(var, value)

        console.print(env_table)

    console.print()
    console.print("💡 Use [cyan]--verbose[/cyan] for more details")
    console.print("💡 Use [cyan]hornet-flow --help[/cyan] to see all commands")
    console.print()


# Workflow commands
@workflow_app.command("run")
@handle_command_errors
def workflow_run(
    metadata_file: Annotated[
        Optional[str],
        typer.Option("--metadata-file", help="Path to metadata JSON file"),
    ] = None,
    repo_url: Annotated[
        Optional[str], typer.Option("--repo-url", help="Repository URL")
    ] = None,
    repo_commit: Annotated[str, typer.Option("--commit", help="Commit hash")] = "main",
    repo_path: Annotated[
        Optional[str], typer.Option("--repo-path", help="Path to already-cloned repo")
    ] = None,
    work_dir: Annotated[
        Optional[str], typer.Option("--work-dir", help="Working directory for clones")
    ] = None,
    fail_fast: FailFastOption = False,
    plugin: PluginOption = None,
    type_filter: TypeFilterOption = None,
    name_filter: NameFilterOption = None,
    # Add global options to this command
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """
    Run a complete workflow to process hornet manifests.

    Can be run using a metadata file, inline repo parameters, or an existing repo path.
    """
    # Merge global options (command-level takes precedence)
    _merge_global_options(
        app_state.verbose, app_state.quiet, app_state.plain, verbose, quiet, plain
    )

    # Validation: metadata_file cannot be combined with repo_url/commit
    if metadata_file and (repo_url or repo_commit != "main"):
        raise InputError(
            "--metadata-file cannot be combined with --repo-url or --commit"
        )

    # At least one input method must be specified
    if not metadata_file and not repo_url and not repo_path:
        raise InputError(
            "Must specify either --metadata-file, --repo-url, or --repo-path"
        )

    _logger.info("🚀 Running Hornet Workflow")

    release = None
    if metadata_file:
        _logger.info("📄 Loading metadata from: %s", metadata_file)

        # Extract release info
        release = service.load_metadata_release(metadata_file)
        repo_url = release.url
        repo_commit = release.marker

    if repo_path:
        _logger.info("📁 Using existing repo: %s", repo_path)
        target_repo_path = Path(repo_path)

        _process_manifests(
            target_repo_path, fail_fast, plugin, type_filter, name_filter, release
        )
    else:
        assert repo_url  # nosec
        _logger.info("🔗 Repository URL: %s", repo_url)
        _logger.info("📌 Commit: %s", repo_commit)

        # Clone repository
        work_path = Path(work_dir or tempfile.gettempdir())

        # Create persistent directory for manual cleanup
        temp_dir = tempfile.mkdtemp(prefix="hornet_", dir=work_path)
        temp_path = Path(temp_dir)
        target_repo_path = temp_path / "repo"
        try:
            # Clone repo
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(
                    f"Cloning repository to {target_repo_path}...", total=None
                )
                try:
                    service.clone_repository(repo_url, repo_commit, target_repo_path)
                except subprocess.CalledProcessError as e:
                    new_error = _create_processing_error(e, "clone repository")
                    raise new_error from e
                progress.update(task, description="Repository cloned successfully")

            # Process manifests
            _process_manifests(
                target_repo_path,
                fail_fast,
                plugin,
                type_filter,
                name_filter,
                release,
            )

            _logger.info("Repository kept at: %s", target_repo_path)

        except Exception:
            # Clean up on error
            if temp_path.exists():
                shutil.rmtree(temp_path)
                _logger.info("🧹 Cleaned up repository after error")
            raise


def _process_manifest_with_plugin(
    cad_manifest: Path,
    repo_path: Path,
    fail_fast: bool,
    plugin_name: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    repo_release: Optional[service.Release] = None,
) -> None:
    """Process CAD manifest using specified plugin."""

    processor = ManifestProcessor(plugin_name, _logger)
    try:
        success_count, total_count = processor.process_manifest(
            cad_manifest, repo_path, fail_fast, type_filter, name_filter, repo_release
        )
        _logger.info(
            "✅ Processed %d/%d components successfully", success_count, total_count
        )
    except FileNotFoundError as e:
        raise InputFileNotFoundError(f"Processing failed: {e}") from e
    except RuntimeError as e:
        raise ProcessingError(f"Processing failed: {e}") from e
    except ValueError as e:
        raise DataValidationError(f"Plugin error: {e}") from e


def _process_manifests(
    repo_path: Path,
    fail_fast: bool,
    plugin_name: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    release: Optional[service.Release] = None,
) -> None:
    """Process manifests found in repository using specified plugin."""
    # 1. Find hornet manifests
    _logger.info("🔍 Finding hornet manifests...")
    cad_manifest, sim_manifest = service.find_hornet_manifests(repo_path)

    if cad_manifest:
        _logger.info("Found CAD manifest: %s", cad_manifest)
    if sim_manifest:
        _logger.info("Found SIM manifest: %s", sim_manifest)

    if not cad_manifest and not sim_manifest:
        msg = f"No hornet manifest files found in repository at {repo_path}"
        if fail_fast:
            raise InputFileNotFoundError(msg)
        _logger.error(msg)
        return

    # 2. Validate manifests
    _logger.info("✅ Validating manifest schemas...")
    if cad_manifest:
        _validate_manifest_schema(cad_manifest, "CAD", fail_fast)

    if sim_manifest:
        _validate_manifest_schema(sim_manifest, "SIM", fail_fast)

    # 3. Process CAD manifest with plugin
    if cad_manifest:
        _process_manifest_with_plugin(
            cad_manifest,
            repo_path,
            fail_fast,
            plugin_name,
            type_filter,
            name_filter,
            release,
        )


# Repository commands
@repo_app.command("clone")
@handle_command_errors
def repo_clone(
    repo_url: Annotated[str, typer.Option("--repo-url", help="Repository URL")],
    dest: Annotated[Optional[str], typer.Option("--dest", help="Destination path")],
    commit: Annotated[str, typer.Option("--commit", help="Commit hash")] = "main",
    # Add global options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Clone a repository and checkout a specific commit."""

    # Merge global options
    _merge_global_options(
        app_state.verbose, app_state.quiet, app_state.plain, verbose, quiet, plain
    )

    _logger.info("📥 Cloning repository")
    _logger.info(" 🔗 Repository: %s", repo_url)
    _logger.info(" 📌 Commit: %s", commit)

    dest_path = Path(dest or tempfile.gettempdir()).resolve()
    _logger.info("📁 Destination: %s", dest_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"Cloning repository to {dest_path}...", total=None)
        try:
            repo_path = service.clone_repository(repo_url, commit, dest_path)
        except subprocess.CalledProcessError as e:
            error = _create_processing_error(e, "clone repository")
            raise error from e
        progress.update(task, description="Repository cloned successfully")

    _logger.info("✅ Repository cloned successfully to %s", repo_path)


# Manifest commands
@manifest_app.command("validate")
@handle_command_errors
def manifest_validate(
    repo_path: RepoPathOption,
    # Add global options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Validate hornet manifests against their schemas."""

    # Merge global options
    _merge_global_options(
        app_state.verbose, app_state.quiet, app_state.plain, verbose, quiet, plain
    )

    _logger.info("✅ Validating manifests")
    _logger.info(" 📁 Repository: %s", repo_path)

    repo_dir = Path(repo_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        find_task = progress.add_task("Finding manifest files...", total=None)
        cad_manifest, sim_manifest = service.find_hornet_manifests(repo_dir)
        progress.update(find_task, description="Manifest files found")

        if not cad_manifest and not sim_manifest:
            raise InputFileNotFoundError("No hornet manifest files found")

        if cad_manifest:
            validate_task = progress.add_task("Validating CAD manifest...", total=None)
            _validate_manifest_schema(cad_manifest, "CAD", fail_fast=True)
            progress.update(
                validate_task, description="CAD manifest validation successful"
            )
            _logger.info("✅ CAD manifest validation successful")

        if sim_manifest:
            validate_task = progress.add_task("Validating SIM manifest...", total=None)
            _validate_manifest_schema(sim_manifest, "SIM", fail_fast=True)
            progress.update(
                validate_task, description="SIM manifest validation successful"
            )
            _logger.info("✅ SIM manifest validation successful")


@manifest_app.command("show")
@handle_command_errors
def manifest_show(
    repo_path: RepoPathOption,
    manifest_type: Annotated[
        str,
        typer.Option(
            "--type",
            help="Manifest type to show",
            click_type=Choice(["cad", "sim", "both"], case_sensitive=False),
        ),
    ] = "both",
    # Add global options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Display hornet manifest contents."""

    # Merge global options
    _merge_global_options(
        app_state.verbose, app_state.quiet, app_state.plain, verbose, quiet, plain
    )

    _logger.info("📋 Showing manifests")
    _logger.info("📁 Repository: %s", repo_path)
    _logger.info("🔍 Type: %s", manifest_type)

    repo_dir = Path(repo_path)
    cad_manifest, sim_manifest = service.find_hornet_manifests(repo_dir)

    # Check if requested manifests exist
    if manifest_type.lower() in ["cad", "both"] and not cad_manifest:
        if manifest_type.lower() == "cad":
            raise InputFileNotFoundError("No CAD manifest found")
        else:
            _logger.warning("⚠️  No CAD manifest found")

    if manifest_type.lower() in ["sim", "both"] and not sim_manifest:
        if manifest_type.lower() == "sim":
            raise InputFileNotFoundError("No SIM manifest found")
        else:
            _logger.warning("⚠️  No SIM manifest found")

    # If both requested but neither found
    if manifest_type.lower() == "both" and not cad_manifest and not sim_manifest:
        raise InputFileNotFoundError("No hornet manifest files found")

    # Show CAD manifest if requested and exists
    if manifest_type.lower() in ["cad", "both"] and cad_manifest:
        _logger.info("📄 CAD Manifest: %s", cad_manifest)
        cad_contents = service.read_manifest_contents(cad_manifest)
        console.print_json(data=cad_contents)
        if manifest_type.lower() == "both" and sim_manifest:
            console.print()  # Add blank line between manifests

    # Show SIM manifest if requested and exists
    if manifest_type.lower() in ["sim", "both"] and sim_manifest:
        _logger.info("📄 SIM Manifest: %s", sim_manifest)
        sim_contents = service.read_manifest_contents(sim_manifest)
        console.print_json(data=sim_contents)


# CAD commands
@cad_app.command("load")
@handle_command_errors
def cad_load(
    repo_path: RepoPathOption,
    plugin: PluginOption = None,
    type_filter: TypeFilterOption = None,
    name_filter: NameFilterOption = None,
    fail_fast: FailFastOption = True,
    # Add global options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Load CAD files referenced in the manifest using plugins."""

    # Merge global options
    _merge_global_options(
        app_state.verbose, app_state.quiet, app_state.plain, verbose, quiet, plain
    )

    _logger.info("🔧 Loading CAD files")
    _logger.info(" 📁 Repository: %s", repo_path)

    repo_dir = Path(repo_path)
    cad_manifest, _ = service.find_hornet_manifests(repo_dir)

    if not cad_manifest:
        raise InputFileNotFoundError("No CAD manifest found")

    # 1. Validate manifest schema first
    _logger.info("✅ Validating manifest schema...")
    _validate_manifest_schema(cad_manifest, "CAD", fail_fast)

    # 2. Process with plugin
    _process_manifest_with_plugin(
        cad_manifest, repo_dir, fail_fast, plugin, type_filter, name_filter
    )


if __name__ == "__main__":
    app()
