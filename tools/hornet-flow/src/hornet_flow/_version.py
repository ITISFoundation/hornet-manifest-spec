"""Version information for hornet-flow package

## Versioning Scheme
    Uses a custom versioning scheme in which 
        - the minor version number is bumped for breaking changes, and 
        - the patch version number is bumped for bug fixes, enhancements, and other non-breaking changes.

    Once v1.0.0 is released, the versioning scheme will adhere to [Semantic Versioning](https://semver.org/).
"""

import importlib.metadata
from typing import Final

try:
    _version = importlib.metadata.version("hornet-flow")
except importlib.metadata.PackageNotFoundError:
    # Fallback for development/editable installs where package might not be "installed"
    _version = "0.0.0-dev"

__version__: Final[str] = _version
