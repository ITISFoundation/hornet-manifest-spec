"""Metadata operations service.

This module provides functionality for working with metadata.json files.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import jsonschema

from ..model import Release, validate_metadata_and_get_release


def _load_metadata_data(metadata_file: Path) -> dict[str, Any]:
    """Load metadata data from file.

    Raises:
        json.JSONDecodeError: If file is not valid JSON
        FileNotFoundError: If file does not exist
    """
    with metadata_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_and_extract_release(
    metadata: dict[str, Any], metadata_path: Path
) -> Release:
    """Validate metadata and extract release information.

    Raises:
        ValueError: If metadata validation fails
        jsonschema.ValidationError: If metadata schema is invalid
    """
    try:
        return validate_metadata_and_get_release(metadata)
    except jsonschema.ValidationError as e:
        msg = f"Invalid metadata file {metadata_path}: {e.message}"
        raise ValueError(msg) from e


def load_metadata_release(metadata_path: Path | str) -> Release:
    """Load and parse the metadata JSON file from local path and returns the release section.

    Raises:
        ValueError: If metadata validation fails
        json.JSONDecodeError: If file is not valid JSON
        FileNotFoundError: If file does not exist
    """
    metadata_file = Path(metadata_path)
    metadata = _load_metadata_data(metadata_file)
    return _validate_and_extract_release(metadata, metadata_file)


async def load_metadata_release_async(metadata_path: Path | str) -> Release:
    """Load and parse the metadata JSON file from local path and returns the release section (async version).

    Raises:
        ValueError: If metadata validation fails
        json.JSONDecodeError: If file is not valid JSON
        FileNotFoundError: If file does not exist
    """
    metadata_file = Path(metadata_path)
    # Load metadata in thread pool to avoid blocking
    metadata = await asyncio.to_thread(_load_metadata_data, metadata_file)
    # Validate in thread pool since validation is CPU-bound
    return await asyncio.to_thread(
        _validate_and_extract_release, metadata, metadata_file
    )
