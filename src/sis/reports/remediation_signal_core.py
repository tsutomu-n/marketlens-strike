from __future__ import annotations

import re
from typing import Any, cast

from sis.reports.remediation_signal_observations import coerce_value

_IN_SET_RE = re.compile(r"^(?P<field>[A-Za-z0-9_]+)\s+in\s+\{(?P<values>.+)\}$")
_EQ_RE = re.compile(r"^(?P<field>[A-Za-z0-9_]+)\s*==\s*(?P<value>.+)$")
_EMPTY_RE = re.compile(r"^(?P<field>[A-Za-z0-9_ ]+)\s+is\s+empty$")
_NON_NULL_RE = re.compile(r"^(?P<field>[A-Za-z0-9_ ]+)\s+are\s+non-null$")


def issue_preview_values(value: object) -> list[str]:
    previews: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                item = cast(dict[str, Any], item)
                path = item.get("path")
                message = item.get("message")
                if path is not None and message is not None:
                    previews.append(f"{path}: {message}")
                elif path is not None:
                    previews.append(str(path))
                elif message is not None:
                    previews.append(str(message))
            elif isinstance(item, str):
                previews.append(item)
    return previews


def evaluate_signal(signal: str, summary: dict) -> dict[str, object]:
    stripped = signal.strip()
    match = _EQ_RE.match(stripped)
    if match:
        field = match.group("field")
        expected = coerce_value(match.group("value"))
        observed = summary.get(field)
        return {
            "signal": signal,
            "status": "pass" if observed == expected else "fail",
            "field": field,
            "expected": expected,
            "observed": observed,
        }
    match = _IN_SET_RE.match(stripped)
    if match:
        field = match.group("field")
        values = [coerce_value(item) for item in match.group("values").split(",")]
        observed = summary.get(field)
        return {
            "signal": signal,
            "status": "pass" if observed in values else "fail",
            "field": field,
            "expected": values,
            "observed": observed,
        }
    match = _EMPTY_RE.match(stripped)
    if match:
        field = match.group("field").replace(" ", "_")
        observed = summary.get(field)
        return {
            "signal": signal,
            "status": "pass" if observed in ([], {}, None, "") else "fail",
            "field": field,
            "expected": "empty",
            "observed": observed,
        }
    match = _NON_NULL_RE.match(stripped)
    if match:
        field = match.group("field").replace(" ", "_")
        observed = summary.get(field)
        status = (
            "pass"
            if isinstance(observed, dict) and all(value is not None for value in observed.values())
            else "unsupported"
        )
        return {
            "signal": signal,
            "status": status,
            "field": field,
            "expected": "non-null",
            "observed": observed,
        }
    return {
        "signal": signal,
        "status": "unsupported",
        "field": None,
        "expected": None,
        "observed": None,
    }


def action_result(evaluations: list[dict[str, object]]) -> str:
    statuses = [str(item.get("status")) for item in evaluations]
    if not evaluations:
        return "manual_review"
    if any(status == "fail" for status in statuses):
        return "fail"
    if all(status == "pass" for status in statuses):
        return "pass"
    if any(status == "pass" for status in statuses):
        return "partial"
    return "manual_review"


def evaluator_status(action_results: list[str]) -> str:
    if not action_results:
        return "no_actions"
    if any(result == "fail" for result in action_results):
        return "needs_retry"
    if all(result == "pass" for result in action_results):
        return "auto_passed"
    if any(result == "partial" for result in action_results):
        return "partial"
    return "manual_review"
