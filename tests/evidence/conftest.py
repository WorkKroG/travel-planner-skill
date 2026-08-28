import shutil
from pathlib import Path

import pytest
from travel_planner.state import TripState, load_trip


@pytest.fixture
def state(tmp_path: Path) -> TripState:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return load_trip(target)

