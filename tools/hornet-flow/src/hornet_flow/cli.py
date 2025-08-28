import json
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Annotated

import jsonschema
import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import service

console = Console()
app = typer.Typer(help="Hornet Manifest Flow - Load and process hornet manifests")

_logger = logging.getLogger(__name__)


class HornetManifestProcessor:
    """CLI processor for loading and processing hornet manifests with logging and error handling."""

    def __init__(self, fail_fast: bool = False) -> None:
        self.fail_fast = fail_fast
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def load_metadata(self, metadata_path: Path | str) -> dict[str, Any]:
        """Load and parse the metadata JSON file from local path."""
        try:
            metadata = service.load_metadata(metadata_path)
            console.print(f"[green]✓[/green] Loaded metadata from {metadata_path}")
            return metadata
        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            error_msg = f"Failed to load metadata from {metadata_path}: {e}"
            self._handle_error(error_msg)
            return {}

    def clone_repository(
        self, repo_url: str, commit_hash: str, target_dir: Path | str
    ) -> str:
        """Clone repository with depth 1 and checkout specific commit."""
        try:
            target_path = Path(target_dir)
            repo_path = target_path / "repo"

            console.print(f"[blue]Cloning repository:[/blue] {repo_url}")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Cloning repository...", total=None)
                service.clone_repository(repo_url, commit_hash, repo_path)
                progress.update(task, description="Repository cloned successfully")

            console.print(
                f"[green]✓[/green] Successfully cloned repository at commit {commit_hash[:8]}"
            )
            return str(repo_path)

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to clone repository {repo_url}: {e}"
            console.print(f"[red]✗ {error_msg}[/red]")
            self._handle_error(error_msg)
            return ""

    def find_hornet_manifests(
        self, repo_path: Path | str
    ) -> tuple[Path | None, Path | None]:
        """Look for .hornet/cad_manifest.json and .hornet/sim_manifest.json."""

        cad_manifest, sim_manifest = service.find_hornet_manifests(repo_path)

        if cad_manifest:
            console.print(f"[green]✓[/green] Found CAD manifest: {cad_manifest}")
        if sim_manifest:
            console.print(f"[green]✓[/green] Found SIM manifest: {sim_manifest}")

        if not cad_manifest and not sim_manifest:
            console.print("[red]✗ No hornet manifest files found in repository[/red]")
            self._handle_error("No hornet manifest files found in repository")

        return cad_manifest, sim_manifest

    def validate_manifest_schema(self, manifest_path: Path | str) -> bool:
        """Extract $schema URL from manifest file and validate using jsonschema."""
        try:
            service.validate_manifest_schema(Path(manifest_path))
            console.print(
                f"[green]✓[/green] Schema validation successful for {manifest_path}"
            )
            return True

        except jsonschema.ValidationError as e:
            error_msg = f"Schema validation failed for {manifest_path}: {e.message}"
            self._handle_error(error_msg)
            return False
        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            error_msg = f"Failed to validate schema for {manifest_path}: {e}"
            self._handle_error(error_msg)
            return False

    def validate_cad_files_exist(
        self, cad_manifest_path: Path | str, repo_path: Path | str
    ) -> list[Path]:
        """Parse CAD manifest JSON tree and verify referenced files exist."""
        try:
            manifest_file = Path(cad_manifest_path)
            repo_dir = Path(repo_path)

            with manifest_file.open("r", encoding="utf-8") as f:
                manifest = json.load(f)

            valid_files: list[Path] = []

            for component in service.walk_manifest_components(manifest):
                files = component.get("files", [])
                for file_info in files:
                    file_path = file_info.get("path", "")

                    full_path = service.resolve_component_file_path(
                        manifest_file, file_path, repo_dir
                    )

                    if full_path.exists():
                        valid_files.append(full_path)
                        console.print(
                            f"[dim]  Found file: {file_path}[/dim]", style="dim"
                        )
                    else:
                        error_msg = f"Missing file referenced in manifest: {full_path}"
                        self._handle_error(error_msg)

            console.print(f"[green]✓[/green] Validated {len(valid_files)} CAD files")
            return valid_files

        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            error_msg = f"Failed to validate CAD files from {cad_manifest_path}: {e}"
            self._handle_error(error_msg)
            return []

    def load_cad_file(self, file_path: Path) -> None:
        """Mock function that prints file path for now."""
        console.print(f"[blue]Loading CAD file:[/blue] {file_path}")
        # TODO: Implement actual CAD file loading logic here

    def cleanup_repository(self, repo_path: Path | str) -> None:
        """Explicitly remove cloned repository directory."""
        try:
            repo_dir = Path(repo_path)
            if repo_dir.exists():
                shutil.rmtree(repo_dir)
                console.print(f"[green]✓[/green] Cleaned up repository at {repo_dir}")
        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            self._handle_error(f"Failed to cleanup repository {repo_path}: {e}")

    def process_hornet_manifest(
        self, metadata_path: Path | str, work_dir: Path | str, cleanup: bool = False
    ) -> dict[str, Any]:
        """Main orchestration function that calls all steps in sequence."""
        results: dict[str, Any] = {
            "success": False,
            "errors": [],
            "warnings": [],
            "processed_files": [],
        }

        try:
            # Step 1: Load metadata
            metadata = self.load_metadata(metadata_path)
            if not metadata:
                return results

            # Step 2: Extract release info
            release = metadata.get("release", {})
            repo_url = release.get("url", "")
            commit_hash = release.get("marker", "")

            if not repo_url or not commit_hash:
                self._handle_error("Missing repository URL or commit hash in metadata")
                return results

            # Create working directory
            work_path = Path(work_dir)
            with tempfile.TemporaryDirectory(dir=work_path) as temp_dir:
                temp_path = Path(temp_dir)

                # Step 1: Clone repository
                repo_path = self.clone_repository(repo_url, commit_hash, temp_path)
                if not repo_path:
                    return results

                # Step 2: Find hornet manifests (check both repo and extracted content)
                cad_manifest, sim_manifest = self.find_hornet_manifests(repo_path)

                # Step 3: Validate manifests against schemas
                if cad_manifest and not self.validate_manifest_schema(cad_manifest):
                    if self.fail_fast:
                        return results

                if sim_manifest and not self.validate_manifest_schema(sim_manifest):
                    if self.fail_fast:
                        return results

                # Step 4: Validate and load CAD files
                if cad_manifest:
                    valid_files = self.validate_cad_files_exist(cad_manifest, repo_path)
                    for file_path in valid_files:
                        self.load_cad_file(file_path)
                        results["processed_files"].append(file_path)

                # Step 5: Cleanup if requested
                if cleanup:
                    self.cleanup_repository(repo_path)

            results["success"] = len(self.errors) == 0 or not self.fail_fast
            results["errors"] = self.errors
            results["warnings"] = self.warnings

            return results

        except Exception as e:  # pylint: disable=W0718:broad-exception-caught
            console.print(f"[red]✗ Unexpected error during processing: {e}[/red]")
            self._handle_error(f"Unexpected error during processing: {e}")
            results["errors"] = self.errors
            return results

    def _handle_error(self, error_msg: str) -> None:
        """Handle errors based on fail_fast mode."""
        console.print(f"[red]✗ {error_msg}[/red]")
        self.errors.append(error_msg)
        if self.fail_fast:
            sys.exit(1)


@app.command()
def main(
    metadata_path: Annotated[str, typer.Argument(help="Path to metadata JSON file")],
    work_dir: Annotated[
        str, typer.Option("/tmp", "--work-dir", help="Working directory for clones")
    ],
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
    Hornet Manifest Flow

    Loads metadata from a JSON file, clones a git repository,
    and loads CAD files according to the manifest specifications.
    """
    # Configure logging
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

    console.print("[bold blue]🚀 Hornet Manifest Flow[/bold blue]")
    console.print(f"Processing metadata: [cyan]{metadata_path}[/cyan]")

    processor = HornetManifestProcessor(fail_fast=fail_fast)
    results = processor.process_hornet_manifest(
        Path(metadata_path), Path(work_dir), cleanup=cleanup
    )

    # Print summary
    status = (
        "[green]✓ completed[/green]" if results["success"] else "[red]✗ failed[/red]"
    )
    console.print(f"\n[bold]Processing {status}[/bold]")
    console.print(f"📁 Files processed: [cyan]{len(results['processed_files'])}[/cyan]")
    console.print(f"❌ Errors: [red]{len(results['errors'])}[/red]")
    console.print(f"⚠️  Warnings: [yellow]{len(results['warnings'])}[/yellow]")

    if results["errors"]:
        console.print(f"\n[bold red]Errors ({len(results['errors'])}):[/bold red]")
        for error in results["errors"]:
            console.print(f"  [red]•[/red] {error}")

    if results["warnings"]:
        console.print(
            f"\n[bold yellow]Warnings ({len(results['warnings'])}):[/bold yellow]"
        )
        for warning in results["warnings"]:
            console.print(f"  [yellow]•[/yellow] {warning}")

    raise typer.Exit(0 if results["success"] else 1)
