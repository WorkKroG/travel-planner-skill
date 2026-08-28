import shutil
from pathlib import Path

import pytest


@pytest.fixture
def minimal_trip(tmp_path: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return target
