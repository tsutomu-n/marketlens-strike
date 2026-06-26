from __future__ import annotations

import re

_KV_INT_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>-?\d+)")
_KV_ANY_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>[A-Za-z0-9_.-]+)")


def coerce_value(raw: str) -> object:
    value = raw.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    if value == "True":
        return True
    if value == "False":
        return False
    if value == "None":
        return None
    try:
        return int(value)
    except ValueError:
        return value


def observed_counts(stdout_summary: str | None, stderr_summary: str | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    combined = " ".join(
        value for value in (stdout_summary, stderr_summary) if isinstance(value, str) and value
    )
    for match in _KV_INT_RE.finditer(combined):
        counts[match.group("key")] = int(match.group("value"))
    return counts


def observed_fields(stdout_summary: str | None, stderr_summary: str | None) -> dict[str, object]:
    fields: dict[str, object] = {}
    combined = " ".join(
        value for value in (stdout_summary, stderr_summary) if isinstance(value, str) and value
    )
    for match in _KV_ANY_RE.finditer(combined):
        fields[match.group("key")] = coerce_value(match.group("value"))
    return fields


def diagnostics_row_presence(
    stdout_summary: str | None, stderr_summary: str | None
) -> dict[str, object]:
    combined = " ".join(
        value for value in (stdout_summary, stderr_summary) if isinstance(value, str) and value
    )
    return {
        "venue_present": "venue=" in combined,
        "symbol_present": "symbol=" in combined,
        "rows_present": "rows=" in combined,
        "tradable_rate_present": "tradable_rate=" in combined,
        "stale_rate_present": "stale_rate=" in combined,
    }
