from __future__ import annotations

from sis.crypto_perp.event_card import EventCard


def _escape_cell(value: str) -> str:
    return value.replace("|", "/")


def render_event_card_markdown(card: EventCard) -> str:
    lines = [
        f"# {card.title}",
        "",
        f"- event_id: `{card.event_id}`",
        f"- status: `{card.status}`",
        "",
        "| field | value |",
        "| --- | --- |",
    ]
    for item in card.lines:
        lines.append(f"| `{_escape_cell(item.label)}` | `{_escape_cell(item.value)}` |")
    if card.warnings:
        lines.extend(["", "## Data Quality", ""])
        lines.extend(f"- `{_escape_cell(item)}`" for item in card.warnings)
    return "\n".join(lines)
