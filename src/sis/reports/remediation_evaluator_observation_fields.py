from __future__ import annotations

from collections.abc import Mapping, Set

from sis.reports import remediation_signal_evaluator as _signal_evaluator

_coerce_value = _signal_evaluator.coerce_value
_issue_preview_values = _signal_evaluator.issue_preview_values


def _normalized_observation_value(value: object) -> object:
    return value if isinstance(value, (bool, int)) else _coerce_value(str(value))


def collect_mapped_observations(
    summary: Mapping[str, object],
    field_map: Mapping[str, str],
    *,
    observed_fields: dict[str, object] | None = None,
    observed_counts: dict[str, int] | None = None,
    issue_preview_source_keys: Set[str] = frozenset(),
) -> tuple[dict[str, object], dict[str, int]]:
    fields = dict(observed_fields) if observed_fields is not None else {}
    counts = dict(observed_counts) if observed_counts is not None else {}
    for source_key, target_key in field_map.items():
        if target_key in fields or source_key not in summary:
            continue
        value = summary.get(source_key)
        if value is None:
            continue
        if source_key in issue_preview_source_keys:
            previews = _issue_preview_values(value)
            if not previews:
                continue
            if target_key == "phase_gate_issue_previews":
                fields[target_key] = previews
            else:
                fields["phase_gate_issue_previews"] = previews
                fields[target_key] = value
            continue
        normalized = _normalized_observation_value(value)
        fields[target_key] = normalized
        if isinstance(normalized, int) and target_key not in counts:
            counts[target_key] = normalized
    return fields, counts
