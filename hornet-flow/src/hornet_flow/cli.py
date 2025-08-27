import argparse
import logging
import os
import sys

from .service import HornetManifestLoader

_logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Load and process hornet manifests")
    parser.add_argument("metadata_path", help="Path to metadata JSON file")
    parser.add_argument(
        "--work-dir", default="/tmp", help="Working directory for clones"
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first error")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually load files"
    )
    parser.add_argument("--cleanup", action="store_true", help="Clean up cloned repo")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show errors")

    args = parser.parse_args()

    # Configure logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    loader = HornetManifestLoader(fail_fast=args.fail_fast, dry_run=args.dry_run)
    results = loader.process_hornet_manifest(
        args.metadata_path, args.work_dir, cleanup=args.cleanup
    )

    _logger.info(
        "Processing %s\n Files processed: %d\n Errors: %d\n Warnings: %d",
        "completed" if results["success"] else "failed",
        len(results["processed_files"]),
        len(results["errors"]),
        len(results["warnings"]),
    )

    if results["errors"]:
        _logger.error("Errors: %d", len(results["errors"]))
        for error in results["errors"]:
            _logger.error(" %s", error)

    if results["warnings"]:
        _logger.warning("Warnings: %d", len(results["warnings"]))
        for warning in results["warnings"]:
            _logger.warning(" %s", warning)

    sys.exit(os.EX_OK if results["success"] else os.EX_SOFTWARE)
