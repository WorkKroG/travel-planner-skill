"""Deterministic Markdown projection of the canonical itinerary view."""

from __future__ import annotations

from decimal import Decimal

from .viewmodel import ItineraryView


def _label(value: str) -> str:
    return value.replace("_", " ").capitalize()


def _money(value: Decimal | None, currency: str) -> str:
    if value is None:
        return "Unknown"
    return f"{value:,.0f} {currency}"


def render_markdown(view: ItineraryView) -> str:
    """Render the approved reading order without reading clocks or canonical files."""
    lines = [
        f"# {view.title}",
        "",
        f"**Status: {_label(view.status)}**",
        "",
        f"Generated: {view.generated_at.isoformat()}",
        "",
        "## Trip summary",
        "",
        f"{view.summary.date_range} · {view.summary.traveler_count} travellers",
        "",
        view.summary.thesis,
        "",
        f"**Route:** {view.summary.route_text}",
        "",
        (
            f"**Readiness:** {view.summary.readiness_confirmed} confirmed "
            f"of {view.summary.readiness_total}"
        ),
        "",
        "### Priority blockers",
        "",
    ]
    if view.summary.blockers:
        lines.extend(
            f"- **{finding.rule_id} — Blocking:** {finding.message}"
            for finding in view.summary.blockers[:3]
        )
    else:
        lines.append("No blocking findings.")

    lines.extend(["", "## Route overview", ""])
    if view.route:
        for stop in view.route:
            nights = f" · {stop.nights} nights" if stop.nights is not None else ""
            transfer = f" · {stop.transfer_label}" if stop.transfer_label else ""
            lines.append(f"- **{stop.name}** · {stop.dates}{nights}{transfer}")
    else:
        lines.append("Route not selected.")

    lines.extend(["", "## Open decisions", ""])
    if view.open_decisions:
        for decision in view.open_decisions:
            lines.extend(
                [
                    f"### {decision.question}",
                    "",
                    f"- Status: {_label(decision.severity)}",
                    f"- Why it matters: {decision.why}",
                    f"- Affects: {', '.join(decision.affected_ids) or 'Unknown'}",
                    f"- Deadline: {decision.deadline}",
                    f"- Next action: {decision.next_action}",
                    "",
                ]
            )
    else:
        lines.extend(["No open decisions.", ""])

    lines.extend(["## Detailed days", ""])
    if not view.days:
        lines.extend(["No detailed days recorded.", ""])
    for day in view.days:
        lines.extend(
            [
                f"### Day {day.number}: {day.date} · {day.weekday} · {day.region}",
                "",
                day.thesis,
                "",
                (
                    f"**Overnight:** {day.overnight} · **Load:** {_label(day.load)} · "
                    f"**Travel:** {day.travel} · **Booking:** {_label(day.booking_state)}"
                ),
                "",
                "#### Critical constraints",
                "",
            ]
        )
        lines.extend(f"- {constraint}" for constraint in day.critical_constraints)
        if not day.critical_constraints:
            lines.append("No critical constraints recorded.")
        lines.extend(["", "#### Timeline", ""])
        for event in day.timeline:
            lines.append(f"- **{event.time} — {event.title}:** {event.detail}")
        if not day.timeline:
            lines.append("No timeline recorded.")
        lines.extend(["", "#### Primary and backup", ""])
        for scenario in day.scenarios:
            lines.append(
                f"- **{_label(scenario.kind)} — {scenario.title}:** {scenario.description}"
            )
        if not day.scenarios:
            lines.append("No scenarios recorded.")
        if day.food:
            lines.extend(["", "#### Food", ""])
            for food in day.food:
                lines.append(f"- **{food.name}** · {_label(food.status)} — {food.note}")
        if day.links:
            lines.extend(["", "#### Links", ""])
            for link in day.links:
                network = " · Internet required" if link.requires_internet else ""
                lines.append(f"- [{link.label}]({link.url}){network}")
        lines.extend(["", f"Last checked: {day.last_checked}", ""])

    lines.extend(["## Preparation", ""])
    if view.readiness:
        for item in view.readiness:
            lines.append(
                f"- **{item.title}** · {_label(item.status)} · {item.category} · "
                f"Owner: {item.owner_id} · Next check: {item.next_check_at}"
            )
    else:
        lines.append("No readiness items recorded.")

    lines.extend(
        [
            "",
            "## Budget",
            "",
            (
                f"Expected known range: {_money(view.budget.minimum, view.budget.currency)} — "
                f"{_money(view.budget.maximum, view.budget.currency)}"
            ),
            "",
            f"Confidence: {_label(view.budget.confidence)}",
            "",
            f"Unknown amounts: {view.budget.unknown_count}",
            "",
        ]
    )
    for category in view.budget.categories:
        lines.append(
            f"- **{category.category}:** {_money(category.minimum, category.currency)} — "
            f"{_money(category.maximum, category.currency)} · {_label(category.amount_type)} · "
            f"{_label(category.confidence)} confidence"
        )

    lines.extend(["", "## Risks and warnings", ""])
    if view.risks:
        for finding in view.risks:
            lines.append(
                f"- **{finding.rule_id} — {_label(finding.severity)}:** {finding.message}"
            )
    else:
        lines.append("No open findings.")

    lines.extend(["", "## Sources", ""])
    if view.sources:
        for source in view.sources:
            lines.extend(
                [
                    f"- **{source.source_id} — {source.title}** ({source.source_type})",
                    f"  - Claim status: {_label(source.claim_status)}",
                    f"  - Freshness: {_label(source.freshness_status)}",
                    f"  - Last checked: {source.last_checked}",
                    f"  - URL: {source.url}",
                ]
            )
    else:
        lines.append("No sources recorded.")
    return "\n".join(lines).rstrip() + "\n"
