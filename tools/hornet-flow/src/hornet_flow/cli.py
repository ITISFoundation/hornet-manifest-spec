import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
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

console = Console()

__version__ = "0.1.0"


# Global state for CLI options
class AppState:
    def __init__(self):
        self.verbose = False
        self.quiet = False
        self.plain = False


app_state = AppState()


def version_callback(value: bool):
    if value:
        console.print(f"hornet-flow version {__version__}")
        raise typer.Exit()


app = typer.Typer(help="Hornet Manifest Flow - Load and process hornet manifests")

_logger = logging.getLogger(__name__)

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


def _handle_subprocess_error(e: subprocess.CalledProcessError, operation: str) -> None:
    """Handle subprocess errors with detailed logging."""
    _logger.error("❌ Failed to %s", operation)
    _logger.error("Command: %s", " ".join(e.cmd) if e.cmd else "Unknown command")
    _logger.error("Exit code: %s", e.returncode)
    if e.stdout:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout
        _logger.error("stdout: %s", stdout)
    if e.stderr:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr
        _logger.error("stderr: %s", stderr)


# Global version option
@app.callback()
def main(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Only show errors")
    ] = False,
    plain: Annotated[
        bool,
        typer.Option("--plain", help="Use plain logging output (no rich formatting)"),
    ] = False,
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

    # Setup logging with global options
    _setup_logging(verbose, quiet, plain)


@app.command("info")
def show_info() -> None:
    """Show current configuration and system information."""

    console.print()
    console.print(Panel.fit("🔧 Hornet Flow Configuration", style="bold blue"))

    # Version information
    version_table = Table(show_header=False, box=None, padding=(0, 1))
    version_table.add_column("Property", style="cyan", min_width=20)
    version_table.add_column("Value", style="white")

    version_table.add_row("Version", f"v{__version__}")
    version_table.add_row("Python", f"{sys.version.split()[0]}")
    version_table.add_row("Platform", platform.platform())

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
    if app_state.verbose:
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
def workflow_run(
    metadata_file: Annotated[
        Optional[str],
        typer.Option("--metadata-file", help="Path to metadata JSON file"),
    ] = None,
    repo_url: Annotated[
        Optional[str], typer.Option("--repo-url", help="Repository URL")
    ] = None,
    commit: Annotated[str, typer.Option("--commit", help="Commit hash")] = "main",
    repo_path: Annotated[
        Optional[str], typer.Option("--repo-path", help="Path to already-cloned repo")
    ] = None,
    work_dir: Annotated[
        Optional[str], typer.Option("--work-dir", help="Working directory for clones")
    ] = None,
    fail_fast: Annotated[
        bool, typer.Option("--fail-fast", help="Stop on first error")
    ] = False,
    cleanup: Annotated[
        bool, typer.Option("--cleanup", help="Clean up cloned repo")
    ] = False,
    plugin: Annotated[
        Optional[str],
        typer.Option("--plugin", help="Plugin to use for processing components"),
    ] = None,
    type_filter: Annotated[
        Optional[str], typer.Option("--type-filter", help="Filter components by type")
    ] = None,
    name_filter: Annotated[
        Optional[str], typer.Option("--name-filter", help="Filter components by name")
    ] = None,
) -> None:
    """
    Run a complete workflow to process hornet manifests.

    Can be run using a metadata file, inline repo parameters, or an existing repo path.
    """
    # Use global logging options - no need to call _setup_logging again
    # as it was already called in the main callback

    # Validation: metadata_file cannot be combined with repo_url/commit
    if metadata_file and (repo_url or commit != "main"):
        _logger.error("--metadata-file cannot be combined with --repo-url or --commit")
        raise typer.Exit(os.EX_USAGE)

    # At least one input method must be specified
    if not metadata_file and not repo_url and not repo_path:
        _logger.error("Must specify either --metadata-file, --repo-url, or --repo-path")
        raise typer.Exit(os.EX_USAGE)

    _logger.info("🚀 Running Hornet Workflow")

    try:
        if metadata_file:
            _logger.info("📄 Loading metadata from: %s", metadata_file)
            metadata = service.load_metadata(metadata_file)

            # Extract release info
            release = metadata.get("release", {})
            repo_url = release.get("url", "")
            commit = release.get("marker", "")

            if not repo_url or not commit:
                _logger.error("Missing repository URL or commit hash in metadata")
                raise typer.Exit(os.EX_USAGE)

        if repo_path:
            _logger.info("📁 Using existing repo: %s", repo_path)
            target_repo_path = Path(repo_path)
            _process_manifests(
                target_repo_path, fail_fast, plugin, type_filter, name_filter
            )
        else:
            assert repo_url  # nosec
            _logger.info("🔗 Repository URL: %s", repo_url)
            _logger.info("📌 Commit: %s", commit)

            # Clone repository
            work_path = Path(work_dir or tempfile.gettempdir())
            if cleanup:
                # Use temporary directory for automatic cleanup
                with tempfile.TemporaryDirectory(dir=work_path) as temp_dir:
                    temp_path = Path(temp_dir)
                    target_repo_path = temp_path / "repo"

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                        transient=True,
                    ) as progress:
                        task = progress.add_task("Cloning repository...", total=None)
                        try:
                            service.clone_repository(repo_url, commit, target_repo_path)
                        except subprocess.CalledProcessError as e:
                            _handle_subprocess_error(e, "clone repository")
                            raise typer.Exit(1)
                        progress.update(
                            task, description="Repository cloned successfully"
                        )

                    _logger.info("Successfully cloned repository")

                    # Process manifests within the temporary directory context
                    _process_manifests(
                        target_repo_path, fail_fast, plugin, type_filter, name_filter
                    )
                    # Automatic cleanup happens when exiting the context
                    _logger.info("🧹 Automatically cleaning up temporary repository")
            else:
                # Create persistent directory for manual cleanup
                temp_dir = tempfile.mkdtemp(dir=work_path)
                temp_path = Path(temp_dir)
                target_repo_path = temp_path / "repo"

                try:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                        transient=True,
                    ) as progress:
                        task = progress.add_task("Cloning repository...", total=None)
                        try:
                            service.clone_repository(repo_url, commit, target_repo_path)
                        except subprocess.CalledProcessError as e:
                            _handle_subprocess_error(e, "clone repository")
                            raise typer.Exit(1)
                        progress.update(
                            task, description="Repository cloned successfully"
                        )

                    _logger.info("Successfully cloned repository")

                    # Process manifests
                    _process_manifests(
                        target_repo_path, fail_fast, plugin, type_filter, name_filter
                    )

                    _logger.info("Repository kept at: %s", target_repo_path)
                except Exception:
                    # Clean up on error even if cleanup=False
                    if temp_path.exists():
                        shutil.rmtree(temp_path)
                        _logger.info("🧹 Cleaned up repository after error")
                    raise

    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.exception("Workflow failed: %s [%s]", e, type(e))
        if fail_fast:
            raise typer.Exit(1)


def _process_manifest_with_plugin(
    cad_manifest: Path,
    repo_path: Path,
    fail_fast: bool,
    plugin_name: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
) -> None:
    """Process CAD manifest using specified plugin."""

    processor = ManifestProcessor(plugin_name, _logger)
    try:
        success_count, total_count = processor.process_manifest(
            cad_manifest, repo_path, fail_fast, type_filter, name_filter
        )
        _logger.info(
            "✅ Processed %d/%d components successfully", success_count, total_count
        )
    except (FileNotFoundError, RuntimeError) as e:
        _logger.exception("Processing failed: %s", e)
        raise typer.Exit(1)
    except ValueError as e:
        _logger.exception("Plugin error: %s", e)
        raise typer.Exit(1)


def _process_manifests(
    repo_path: Path,
    fail_fast: bool,
    plugin_name: Optional[str] = None,
    type_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
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
        _logger.error("No hornet manifest files found in repository")
        if fail_fast:
            raise typer.Exit(os.EX_NOINPUT)
        return

    # 2. Validate manifests
    _logger.info("✅ Validating manifest schemas...")
    if cad_manifest:
        try:
            service.validate_manifest_schema(cad_manifest)
            _logger.info("CAD manifest schema validation successful")
        except jsonschema.ValidationError as e:
            _logger.error("CAD manifest schema validation failed: %s", e.message)
            if fail_fast:
                raise typer.Exit(os.EX_DATAERR)

    if sim_manifest:
        try:
            service.validate_manifest_schema(sim_manifest)
            _logger.info("SIM manifest schema validation successful")
        except jsonschema.ValidationError as e:
            _logger.error("SIM manifest schema validation failed: %s", e.message)
            if fail_fast:
                raise typer.Exit(os.EX_DATAERR)

    # 3. Process CAD manifest with plugin
    if cad_manifest:
        _process_manifest_with_plugin(
            cad_manifest, repo_path, fail_fast, plugin_name, type_filter, name_filter
        )


# Repository commands
@repo_app.command("clone")
def repo_clone(
    repo_url: Annotated[str, typer.Option("--repo-url", help="Repository URL")],
    dest: Annotated[Optional[str], typer.Option("--dest", help="Destination path")],
    commit: Annotated[str, typer.Option("--commit", help="Commit hash")] = "main",
) -> None:
    """Clone a repository and checkout a specific commit."""

    _logger.info("📥 Cloning repository")
    _logger.info("🔗 Repository: %s", repo_url)
    _logger.info("📌 Commit: %s", commit)
    _logger.info("📁 Destination: %s", dest)

    try:
        dest_path = Path(dest or tempfile.gettempdir())
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Cloning repository...", total=None)
            repo_path = service.clone_repository(repo_url, commit, dest_path)
            progress.update(task, description="Repository cloned successfully")

        _logger.info("✅ Repository cloned successfully to %s", repo_path)
    except subprocess.CalledProcessError as e:
        _handle_subprocess_error(e, "clone repository")
        raise typer.Exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.error("❌ Failed to clone repository: %s", e)
        raise typer.Exit(1)


# Manifest commands
@manifest_app.command("validate")
def manifest_validate(
    repo_path: Annotated[str, typer.Option("--repo-path", help="Repository path")],
) -> None:
    """Validate hornet manifests against their schemas."""

    _logger.info("✅ Validating manifests")
    _logger.info("📁 Repository: %s", repo_path)

    try:
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
                _logger.error("❌ No hornet manifest files found")
                raise typer.Exit(os.EX_NOINPUT)

            if cad_manifest:
                validate_task = progress.add_task(
                    "Validating CAD manifest...", total=None
                )
                service.validate_manifest_schema(cad_manifest)
                progress.update(
                    validate_task, description="CAD manifest validation successful"
                )
                _logger.info("✅ CAD manifest validation successful")

            if sim_manifest:
                validate_task = progress.add_task(
                    "Validating SIM manifest...", total=None
                )
                service.validate_manifest_schema(sim_manifest)
                progress.update(
                    validate_task, description="SIM manifest validation successful"
                )
                _logger.info("✅ SIM manifest validation successful")

    except jsonschema.ValidationError as e:
        _logger.error("❌ Schema validation failed: %s", e.message)
        raise typer.Exit(os.EX_DATAERR)
    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.error("❌ Validation failed: %s", e)
        raise typer.Exit(os.EX_DATAERR)


@manifest_app.command("show")
def manifest_show(
    repo_path: Annotated[str, typer.Option("--repo-path", help="Repository path")],
    manifest_type: Annotated[
        str,
        typer.Option(
            "--type",
            help="Manifest type to show",
            click_type=Choice(["cad", "sim", "both"], case_sensitive=False),
        ),
    ] = "both",
) -> None:
    """Display hornet manifest contents."""

    _logger.info("📋 Showing manifests")
    _logger.info("📁 Repository: %s", repo_path)
    _logger.info("🔍 Type: %s", manifest_type)

    try:
        repo_dir = Path(repo_path)
        cad_manifest, sim_manifest = service.find_hornet_manifests(repo_dir)

        # Check if requested manifests exist
        if manifest_type.lower() in ["cad", "both"] and not cad_manifest:
            if manifest_type.lower() == "cad":
                _logger.error("❌ No CAD manifest found")
                raise typer.Exit(os.EX_NOINPUT)
            else:
                _logger.warning("⚠️  No CAD manifest found")

        if manifest_type.lower() in ["sim", "both"] and not sim_manifest:
            if manifest_type.lower() == "sim":
                _logger.error("❌ No SIM manifest found")
                raise typer.Exit(os.EX_NOINPUT)
            else:
                _logger.warning("⚠️  No SIM manifest found")

        # If both requested but neither found
        if manifest_type.lower() == "both" and not cad_manifest and not sim_manifest:
            _logger.error("❌ No hornet manifest files found")
            raise typer.Exit(os.EX_NOINPUT)

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

    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.error("❌ Failed to show manifests: %s", e)
        raise typer.Exit(os.EX_DATAERR)


# CAD commands
@cad_app.command("load")
def cad_load(
    repo_path: Annotated[str, typer.Option("--repo-path", help="Repository path")],
    plugin: Annotated[
        Optional[str],
        typer.Option("--plugin", help="Plugin to use for processing components"),
    ] = None,
    type_filter: Annotated[
        Optional[str], typer.Option("--type-filter", help="Filter components by type")
    ] = None,
    name_filter: Annotated[
        Optional[str], typer.Option("--name-filter", help="Filter components by name")
    ] = None,
    fail_fast: Annotated[
        bool, typer.Option("--fail-fast", help="Stop on first error")
    ] = True,
) -> None:
    """Load CAD files referenced in the manifest using plugins."""

    _logger.info("🔧 Loading CAD files")
    _logger.info("📁 Repository: %s", repo_path)

    try:
        repo_dir = Path(repo_path)
        cad_manifest, _ = service.find_hornet_manifests(repo_dir)

        if not cad_manifest:
            _logger.error("❌ No CAD manifest found")
            raise typer.Exit(os.EX_NOINPUT)

        # 1. Validate manifest schema first
        _logger.info("✅ Validating manifest schema...")
        try:
            service.validate_manifest_schema(cad_manifest)
            _logger.info("CAD manifest schema validation successful")
        except jsonschema.ValidationError as e:
            _logger.error("CAD manifest schema validation failed: %s", e.message)
            if fail_fast:
                raise typer.Exit(os.EX_DATAERR)

        # 2. Process with plugin
        _process_manifest_with_plugin(
            cad_manifest, repo_dir, fail_fast, plugin, type_filter, name_filter
        )

    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.error("❌ Failed to load CAD files: %s", e)
        raise typer.Exit(os.EX_DATAERR)


if __name__ == "__main__":
    app()
