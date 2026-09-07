from travel_planner.evidence import iter_claims, render_sources_markdown, source_index
from travel_planner.state import TripState


def test_source_and_claim_helpers_preserve_metadata_without_scoring(
    state: TripState,
) -> None:
    state.candidates["claims"] = [
        {
            "id": "claim-entry",
            "topic": "entry",
            "status": "not_released_yet",
            "source_ids": ["official-1"],
            "value": None,
        }
    ]

    sources = source_index(state)
    claims = tuple(iter_claims(state))

    assert sources["official-1"]["source_type"] == "official"
    assert claims[0]["status"] == "not_released_yet"
    assert claims[0]["value"] is None
    assert all("confidence" not in claim for claim in claims)


def test_sources_projection_includes_readiness_claims(state: TripState) -> None:
    state.candidates["claims"] = [
        {
            "id": "claim-visa",
            "topic": "entry",
            "status": "verified",
            "source_ids": ["official-1"],
        }
    ]
    state.readiness["items"] = [
        {
            "id": "ready-entry",
            "category": "entry",
            "status": "recheck",
            "source_ids": ["official-1"],
            "claim_ids": ["claim-visa"],
        }
    ]

    markdown = render_sources_markdown(state)

    assert "claim-visa" in markdown
    assert "ready-entry" in markdown
    assert "last checked" in markdown.lower()


def test_sources_projection_preserves_photo_credits(state: TripState) -> None:
    state.itinerary["days"] = [{"id": "day-1", "media": [{
        "path": "media/garden.jpg", "source_id": "official-1", "caption": "Garden",
        "attribution": "Recorded Author", "license": "CC BY-SA 4.0",
    }]}]
    markdown = render_sources_markdown(state)
    assert "Garden" in markdown and "media/garden.jpg" in markdown
    assert "Recorded Author" in markdown and "CC BY-SA 4.0" in markdown
    assert source_index(state)["official-1"]["url"] in markdown
