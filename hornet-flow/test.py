# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# pylint: disable=unused-variable
# pylint: disable=too-many-arguments

import pytest
from typing import Any
from pytest_mock import MockerFixture
from pathlib import Path

from hornet_flow.service import load_metadata


def test_load_metadata_portal_device():
    """Test loading metadata from portal-device-metadata.json file."""
    # Get the path to the test JSON file
    metadata_path = Path(__file__).parent / "examples" / "portal-device-metadata.json"

    # Load the metadata
    metadata = load_metadata(metadata_path)

    # Verify release information
    assert "release" in metadata
    release = metadata["release"]
    assert release["origin"] == "GitHub"
    assert release["url"] == "https://github.com/ITISFoundation/hornet-manifest-spec"
    assert release["label"] == "1.0.0"
    assert release["marker"] == "main"
