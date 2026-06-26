from __future__ import annotations

from pathlib import Path


def cost_matrix_rows(path: Path) -> list[dict[str, str | None]]:
    if not path.exists():
        return []
    import csv

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def threshold_result(
    rows: list[dict[str, str | None]],
    column: str,
    *,
    maximum: float | None = None,
    minimum: float | None = None,
) -> str:
    values: list[float] = []
    for row in rows:
        value = row.get(column)
        if value in {None, ""}:
            return "MISSING"
        if value is None:
            return "MISSING"
        values.append(float(value))
    if not values:
        return "MISSING"
    if maximum is not None and any(value > maximum for value in values):
        return "NO_GO"
    if minimum is not None and any(value < minimum for value in values):
        return "NO_GO"
    return "PASS"


def holding_cost_result(rows: list[dict[str, str | None]]) -> str:
    if not rows:
        return "MISSING"
    required = ("holding_cost_4h_bps", "holding_cost_24h_bps", "holding_cost_72h_bps")
    completed = [all(row.get(column) not in {None, ""} for column in required) for row in rows]
    if all(completed):
        return "PASS"
    if any(completed):
        return "PARTIAL"
    return "MISSING"


def venue_cost_rows(rows: list[dict[str, str | None]], venue: str) -> list[dict[str, str | None]]:
    return [row for row in rows if row.get("venue") == venue]
