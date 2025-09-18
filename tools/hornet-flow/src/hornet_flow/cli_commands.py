"""CLI command functions that wrap API functions with CLI-specific behavior.

This module contains the actual command implementations that handle CLI concerns
like progress bars, logging, and option merging while delegating business logic
to the API layer.
"""

import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer
from click import Choice
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api import (
    clone_repository_api,
    load_cad_api,
    run_workflow_api,
    show_manifest_api,
    validate_manifests_api,
)
from .cli_exceptions import handle_command_errors
from .cli_state import app_console, app_logger, merge_global_options
from .services.watcher import watch_for_metadata

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


# Workflow commands
@handle_command_errors
def workflow_run_cmd(
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
    # CLI-specific options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Run a complete workflow to process hornet manifests.

    Can be run using a metadata file, inline repo parameters, or an existing repo path.
    """
    # Merge global options (CLI-specific)
    merge_global_options(
        main_verbose=False,
        main_quiet=False,
        main_plain=False,
        cmd_verbose=verbose,
        cmd_quiet=quiet,
        cmd_plain=plain,
    )

    app_logger.info("🚀 Running Hornet Workflow")

    if metadata_file:
        app_logger.info("📄 Loading metadata from: %s", metadata_file)
    if repo_url:
        app_logger.info("🔗 Repository URL: %s", repo_url)
        app_logger.info("📌 Commit: %s", repo_commit)
    if repo_path:
        app_logger.info("📁 Using existing repo: %s", repo_path)

    work_path = Path(work_dir or tempfile.gettempdir())
    if work_dir and not work_path.exists():
        raise typer.BadParameter(f"Working directory does not exist: {work_path}")

    # Progress bar for cloning (CLI-specific)
    if repo_url and not repo_path:
        app_logger.info("📁 Working directory: %s", work_path)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=app_console,
            transient=True,
        ) as progress:
            task = progress.add_task("Processing workflow...", total=None)

            # Call pure API function
            success_count, total_count = run_workflow_api(
                metadata_file=metadata_file,
                repo_url=repo_url,
                repo_commit=repo_commit,
                repo_path=repo_path,
                work_dir=work_dir,
                fail_fast=fail_fast,
                plugin=plugin,
                type_filter=type_filter,
                name_filter=name_filter,
            )

            progress.update(task, description="Workflow completed successfully")
    else:
        # Call pure API function directly
        success_count, total_count = run_workflow_api(
            metadata_file=metadata_file,
            repo_url=repo_url,
            repo_commit=repo_commit,
            repo_path=repo_path,
            work_dir=work_dir,
            fail_fast=fail_fast,
            plugin=plugin,
            type_filter=type_filter,
            name_filter=name_filter,
        )

    app_logger.info(
        "✅ Processed %d/%d components successfully", success_count, total_count
    )


@handle_command_errors
def repo_clone_cmd(
    repo_url: Annotated[str, typer.Option("--repo-url", help="Repository URL")],
    dest: Annotated[
        Optional[str], typer.Option("--dest", help="Destination path")
    ] = None,
    commit: Annotated[str, typer.Option("--commit", help="Commit hash")] = "main",
    # CLI-specific options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Clone a repository and checkout a specific commit."""
    # Merge global options (CLI-specific)
    merge_global_options(
        main_verbose=False,
        main_quiet=False,
        main_plain=False,
        cmd_verbose=verbose,
        cmd_quiet=quiet,
        cmd_plain=plain,
    )

    app_logger.info("📥 Cloning repository")
    app_logger.info(" 🔗 Repository: %s", repo_url)
    app_logger.info(" 📌 Commit: %s", commit)

    dest_path = Path(dest or tempfile.gettempdir()).resolve()
    app_logger.info("📁 Destination: %s", dest_path)

    # Progress bar (CLI-specific)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=app_console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"Cloning repository to {dest_path}...", total=None)

        # Call pure API function
        repo_path = clone_repository_api(repo_url, str(dest_path), commit)

        progress.update(task, description="Repository cloned successfully")

    app_logger.info("✅ Repository cloned successfully to %s", repo_path)


@handle_command_errors
def manifest_validate_cmd(
    repo_path: RepoPathOption,
    # CLI-specific options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Validate hornet manifests against their schemas."""
    # Merge global options (CLI-specific)
    merge_global_options(
        main_verbose=False,
        main_quiet=False,
        main_plain=False,
        cmd_verbose=verbose,
        cmd_quiet=quiet,
        cmd_plain=plain,
    )

    app_logger.info("✅ Validating manifests")
    app_logger.info(" 📁 Repository: %s", repo_path)

    # Progress bar (CLI-specific)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=app_console,
        transient=True,
    ) as progress:
        find_task = progress.add_task("Finding manifest files...", total=None)

        # Call pure API function
        cad_valid, sim_valid = validate_manifests_api(repo_path)

        progress.update(find_task, description="Validation completed")

    # CLI-specific success logging
    if cad_valid:
        app_logger.info("✅ CAD manifest validation successful")
    if sim_valid:
        app_logger.info("✅ SIM manifest validation successful")


@handle_command_errors
def manifest_show_cmd(
    repo_path: RepoPathOption,
    manifest_type: Annotated[
        str,
        typer.Option(
            "--type",
            help="Manifest type to show",
            click_type=Choice(["cad", "sim", "both"], case_sensitive=False),
        ),
    ] = "both",
    # CLI-specific options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Display hornet manifest contents."""
    # Merge global options (CLI-specific)
    merge_global_options(
        main_verbose=False,
        main_quiet=False,
        main_plain=False,
        cmd_verbose=verbose,
        cmd_quiet=quiet,
        cmd_plain=plain,
    )

    app_logger.info("📋 Showing manifests")
    app_logger.info("📁 Repository: %s", repo_path)
    app_logger.info("🔍 Type: %s", manifest_type)

    # Call pure API function
    manifest_data = show_manifest_api(repo_path, manifest_type)

    # CLI-specific output formatting
    if "cad" in manifest_data:
        app_logger.info("📄 CAD Manifest found")
        app_console.print_json(data=manifest_data["cad"])
        if "sim" in manifest_data:
            app_console.print()  # Add blank line between manifests

    if "sim" in manifest_data:
        app_logger.info("📄 SIM Manifest found")
        app_console.print_json(data=manifest_data["sim"])


@handle_command_errors
def cad_load_cmd(
    repo_path: RepoPathOption,
    plugin: PluginOption = None,
    type_filter: TypeFilterOption = None,
    name_filter: NameFilterOption = None,
    fail_fast: FailFastOption = True,
    # CLI-specific options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Load CAD files referenced in the manifest using plugins."""
    # Merge global options (CLI-specific)
    merge_global_options(
        main_verbose=False,
        main_quiet=False,
        main_plain=False,
        cmd_verbose=verbose,
        cmd_quiet=quiet,
        cmd_plain=plain,
    )

    app_logger.info("🔧 Loading CAD files")
    app_logger.info(" 📁 Repository: %s", repo_path)

    # Call pure API function
    success_count, total_count = load_cad_api(
        repo_path, plugin, type_filter, name_filter, fail_fast
    )

    app_logger.info(
        "✅ Processed %d/%d components successfully", success_count, total_count
    )


@handle_command_errors
def workflow_watch_cmd(
    inputs_dir: Annotated[
        str,
        typer.Option(
            "--inputs-dir",
            help="Directory to watch for metadata.json files",
            envvar="INPUTS_DIR",
        ),
    ],
    work_dir: Annotated[
        str,
        typer.Option(
            "--work-dir",
            help="Working directory for workflow processing",
            envvar="WORK_DIR",
        ),
    ],
    once: Annotated[
        bool,
        typer.Option(
            "--once",
            help="Exit after processing one file (default: continuous watching)",
        ),
    ] = False,
    plugin: PluginOption = None,
    type_filter: TypeFilterOption = None,
    name_filter: NameFilterOption = None,
    fail_fast: FailFastOption = False,
    stability_seconds: Annotated[
        float,
        typer.Option(
            "--stability-seconds",
            help="Seconds to wait for file stability",
            min=0.1,
            max=30.0,
        ),
    ] = 2.0,
    # CLI-specific options
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    plain: PlainOption = False,
) -> None:
    """Watch for metadata.json files and automatically process them.

    Monitors INPUTS_DIR for metadata.json files. When a file appears and becomes
    stable, automatically runs the hornet-flow workflow with the detected metadata.
    Creates WORK_DIR/hornet-flows if it doesn't exist.

    Environment variables:
    - INPUTS_DIR: Directory to watch (can be overridden with --inputs-dir)
    - WORK_DIR: Base work directory (can be overridden with --work-dir)
    """
    # Merge global options (CLI-specific)
    merge_global_options(
        main_verbose=False,
        main_quiet=False,
        main_plain=False,
        cmd_verbose=verbose,
        cmd_quiet=quiet,
        cmd_plain=plain,
    )

    app_logger.info("👀 Starting metadata file watcher")

    # Validate and prepare directories
    inputs_path = Path(inputs_dir).resolve()

    # Create work_dir/hornet-flows structure
    work_base = Path(work_dir).resolve()
    work_path = work_base / "hornet-flows"

    app_logger.info("📁 Inputs directory: %s", inputs_path)
    app_logger.info("📁 Work directory: %s", work_path)

    # Validate inputs directory exists
    if not inputs_path.exists():
        raise typer.BadParameter(f"Inputs directory does not exist: {inputs_path}")

    if not inputs_path.is_dir():
        raise typer.BadParameter(f"Inputs path is not a directory: {inputs_path}")

    # Call the watcher function
    try:
        watch_for_metadata(
            inputs_dir=inputs_path,
            work_dir=work_path,
            once=once,
            plugin=plugin,
            type_filter=type_filter,
            name_filter=name_filter,
            fail_fast=fail_fast,
            stability_seconds=stability_seconds,
        )
    except KeyboardInterrupt:
        app_logger.info("⛔ Watcher stopped by user")
    except Exception as e:
        app_logger.error("❌ Watcher failed: %s", e)
        raise typer.Exit(1) from e
