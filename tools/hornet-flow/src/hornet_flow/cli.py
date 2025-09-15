import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import jsonschema
import typer
from click import Choice
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from hornet_flow import service

console = Console()

__version__ = "0.1.0"


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


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging with RichHandler."""
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[RichHandler(console=console, markup=True)],
    )


def handle_subprocess_error(e: subprocess.CalledProcessError, operation: str) -> None:
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
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, help="Show version and exit"
        ),
    ] = None,
):
    """Hornet Manifest Flow - Load and process hornet manifests"""
    _ = version


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
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Only show errors")
    ] = False,
) -> None:
    """
    Run a complete workflow to process hornet manifests.

    Can be run using a metadata file, inline repo parameters, or an existing repo path.
    """
    setup_logging(verbose, quiet)

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
            _process_manifests(target_repo_path, fail_fast)
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
                            handle_subprocess_error(e, "clone repository")
                            raise typer.Exit(1)
                        progress.update(
                            task, description="Repository cloned successfully"
                        )

                    _logger.info("Successfully cloned repository")

                    # Process manifests within the temporary directory context
                    _process_manifests(target_repo_path, fail_fast)
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
                            handle_subprocess_error(e, "clone repository")
                            raise typer.Exit(1)
                        progress.update(
                            task, description="Repository cloned successfully"
                        )

                    _logger.info("Successfully cloned repository")

                    # Process manifests
                    _process_manifests(target_repo_path, fail_fast)

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


def _process_manifests(repo_path: Path, fail_fast: bool) -> None:
    """Process manifests found in repository."""
    # Find hornet manifests
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

    # Validate manifests
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

    # Validate and load CAD files
    if cad_manifest:
        _logger.info("📋 Validating CAD files...")
        valid_files = _validate_cad_files(cad_manifest, repo_path, fail_fast)

        if valid_files:
            _logger.info("🔧 Loading CAD files...")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                load_task = progress.add_task(
                    f"Loading {len(valid_files)} CAD files...", total=None
                )
                for file_path in valid_files:
                    service.load_cad_file(file_path)
                    _logger.debug("Loaded CAD file: %s", file_path)
                progress.update(
                    load_task,
                    description=f"Successfully loaded {len(valid_files)} CAD files",
                )


def _validate_cad_files(
    cad_manifest_path: Path, repo_path: Path, fail_fast: bool
) -> list[Path]:
    """Validate CAD files exist and return list of valid files."""
    try:
        with cad_manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)

        valid_files: list[Path] = []

        for component in service.walk_manifest_components(manifest):
            for file_obj in component.files:
                file_path = file_obj.path

                full_path = service.resolve_component_file_path(
                    cad_manifest_path, file_path, repo_path
                )

                if full_path.exists():
                    valid_files.append(full_path)
                    _logger.debug("Found file: %s", file_path)
                else:
                    _logger.error("Missing file referenced in manifest: %s", full_path)
                    if fail_fast:
                        raise typer.Exit(os.EX_DATAERR)

        _logger.info("Validated %d CAD files", len(valid_files))
        return valid_files

    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.error("Failed to validate CAD files: %s", e)
        if fail_fast:
            raise typer.Exit(1)
        return []


# Repository commands
@repo_app.command("clone")
def repo_clone(
    repo_url: Annotated[str, typer.Option("--repo-url", help="Repository URL")],
    dest: Annotated[Optional[str], typer.Option("--dest", help="Destination path")],
    commit: Annotated[str, typer.Option("--commit", help="Commit hash")] = "main",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Only show errors")
    ] = False,
) -> None:
    """Clone a repository and checkout a specific commit."""
    setup_logging(verbose, quiet)

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
        handle_subprocess_error(e, "clone repository")
        raise typer.Exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        _logger.error("❌ Failed to clone repository: %s", e)
        raise typer.Exit(1)


# Manifest commands
@manifest_app.command("validate")
def manifest_validate(
    repo_path: Annotated[str, typer.Option("--repo-path", help="Repository path")],
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Only show errors")
    ] = False,
) -> None:
    """Validate hornet manifests against their schemas."""
    setup_logging(verbose, quiet)

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
    except Exception as e:
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
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Only show errors")
    ] = False,
) -> None:
    """Display hornet manifest contents."""
    setup_logging(verbose, quiet)

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

    except Exception as e:
        _logger.error("❌ Failed to show manifests: %s", e)
        raise typer.Exit(os.EX_DATAERR)


# CAD commands
@cad_app.command("load")
def cad_load(
    repo_path: Annotated[str, typer.Option("--repo-path", help="Repository path")],
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Only show errors")
    ] = False,
) -> None:
    """Load CAD files referenced in the manifest."""
    setup_logging(verbose, quiet)

    _logger.info("🔧 Loading CAD files")
    _logger.info("📁 Repository: %s", repo_path)

    try:
        repo_dir = Path(repo_path)
        cad_manifest, _ = service.find_hornet_manifests(repo_dir)

        if not cad_manifest:
            _logger.error("❌ No CAD manifest found")
            raise typer.Exit(os.EX_NOINPUT)

        _logger.info("📋 Processing CAD manifest...")
        valid_files = _validate_cad_files(cad_manifest, repo_dir, fail_fast=True)

        _logger.info("🔧 Loading %d CAD files...", len(valid_files))
        for file_path in valid_files:
            service.load_cad_file(file_path)
            _logger.debug("Loaded: %s", file_path)

        _logger.info("✅ Successfully loaded %d CAD files", len(valid_files))

    except Exception as e:
        _logger.error("❌ Failed to load CAD files: %s", e)
        raise typer.Exit(os.EX_DATAERR)


if __name__ == "__main__":
    app()
