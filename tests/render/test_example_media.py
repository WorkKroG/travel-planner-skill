"""The shipped trip keeps every imported photograph reproducible and attributed."""

import hashlib
import re
from pathlib import Path

from travel_planner.cli import main
from travel_planner.state import load_trip

EXAMPLE = Path(__file__).parents[2] / "examples/japan-autumn-2026"


def test_japan_example_retains_the_imported_day_photos_and_exact_html(tmp_path):
    state = load_trip(EXAMPLE)
    expected_counts = [1, 1, 2, 1, 2, 2, 1, 1, 2, 2, 2, 1]
    assert [len(day["media"]) for day in state.itinerary["days"]] == expected_counts
    hashes = dict(re.findall(r"([a-f0-9]{64})  (day-\d+-\d+\.jpg)",
                             (EXAMPLE / "media/README.md").read_text()))
    assert len(hashes) == 18
    for digest, filename in hashes.items():
        assert hashlib.sha256((EXAMPLE / "media" / filename).read_bytes()).hexdigest() == digest
    output = tmp_path / "japan.html"
    assert main(["render", str(EXAMPLE), "--output", str(output), "--at",
                 "2026-09-10T17:24:46+00:00"]) == 0
    assert output.read_bytes() == (EXAMPLE / "outputs/itinerary.html").read_bytes()
    assert list(tmp_path.iterdir()) == [output]
    assert output.read_text().count('<figure class="day-photo"') == 18
    hakone = output.read_text().split('id="day-6" data-day', 1)[1].split('<nav class="day-nav"', 1)[0]
    assert re.findall(r'class="timeline-period">([^<]+)', hakone) == [
        'Утро', 'День', 'Вечер', 'Утро', 'День', 'Вечер', 'Утро', 'День', 'Вечер',
    ]
