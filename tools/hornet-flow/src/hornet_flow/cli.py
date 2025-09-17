"""CLI application setup and entry point for hornet-flow.

This module contains the Typer app setup, global options, sub-app registration,
and the main entry point. All command implementations are in cli_commands.py.
"""

import os
import platform
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.panel import Panel
from rich.table import Table

import hornet_flow
from hornet_flow import service
from hornet_flow.plugins import discover_plugins, get_default_plugin

from .cli_commands import (
    PlainOption,
    QuietOption,
    VerboseOption,
    cad_load_cmd,
    manifest_show_cmd,
    manifest_validate_cmd,
    repo_clone_cmd,
    workflow_run_cmd,
)
from .cli_state import app_logger, app_state, console, merge_global_options

__version__ = "0.2.0"


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

    merge_global_options(app_state.verbose, False, False, verbose, False, False)

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
        app_logger.exception("Error loading plugins")
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


# Add sub-apps to main app
app.add_typer(workflow_app, name="workflow")
app.add_typer(repo_app, name="repo")
app.add_typer(manifest_app, name="manifest")
app.add_typer(cad_app, name="cad")

# Register commands with their respective sub-apps
workflow_app.command("run")(workflow_run_cmd)
repo_app.command("clone")(repo_clone_cmd)
manifest_app.command("validate")(manifest_validate_cmd)
manifest_app.command("show")(manifest_show_cmd)
cad_app.command("load")(cad_load_cmd)


if __name__ == "__main__":
    app()
