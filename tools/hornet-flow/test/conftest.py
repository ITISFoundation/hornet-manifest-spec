# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=unused-variable


import sys
from pathlib import Path

import pytest

_CURRENT_DIR = Path(
    sys.argv[0] if __name__ == "__main__" else __file__
).parent.resolve()


@pytest.fixture
def repo_path() -> Path:
    base_path = _CURRENT_DIR.parent.parent.parent
    assert list(base_path.glob("README.md")), f"{base_path} does not contain README.md"
    assert list(base_path.glob("LICENSE")), f"{base_path} does not contain LICENSE"
    return base_path


@pytest.fixture
def package_dir(repo_path: Path) -> Path:
    dir_path = repo_path / "tools" / "hornet_flow"
    assert dir_path.exists()
    assert dir_path.is_dir()
    return dir_path


@pytest.fixture
def schema_dir(package_dir: Path) -> Path:
    dir_path = package_dir / "schema"
    assert dir_path.exists()
    assert dir_path.is_dir()
    return dir_path
