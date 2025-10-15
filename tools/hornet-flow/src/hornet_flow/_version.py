"""Version information for hornet-flow package."""

import importlib.metadata
from typing import Final

try:
    _version = importlib.metadata.version("hornet-flow")
except importlib.metadata.PackageNotFoundError:
    # Fallback for development/editable installs where package might not be "installed"
    _version = "0.0.0-dev"

__version__: Final[str] = _version
