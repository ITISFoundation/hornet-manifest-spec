"""Metadata operations service.

This module provides functionality for working with metadata.json files.
"""

import json
from pathlib import Path

import jsonschema

from ..model import Release, validate_metadata_and_get_release


def load_metadata_release(metadata_path: Path | str) -> Release:
    """Load and parse the metadata JSON file from local path and returns the release section"""
    metadata_file = Path(metadata_path)
    with metadata_file.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    try:
        return validate_metadata_and_get_release(metadata)
    except jsonschema.ValidationError as e:
        msg = f"Invalid metadata file {metadata_path}: {e.message}"
        raise ValueError(msg) from e
