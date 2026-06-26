from __future__ import annotations

from typing import cast


def note_value(notes: list[object], prefix: str) -> str | None:
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return None


def note_counts(items: list[dict[str, object]], prefix: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        notes = item.get("notes", [])
        if not isinstance(notes, list):
            continue
        value = note_value(cast(list[object], notes), prefix)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts
