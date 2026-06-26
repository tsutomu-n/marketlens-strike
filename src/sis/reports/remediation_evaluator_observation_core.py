from __future__ import annotations


def apply_aliases(
    observed_fields: dict[str, object], observed_counts: dict[str, int]
) -> tuple[dict[str, object], dict[str, int]]:
    alias_map = {
        "phase_gate_checked_files": "checked_files",
        "phase_gate_strict_validation_issue_count": "issues",
        "phase_gate_decision": "decision",
        "phase_gate_reason": "phase2_entry_reason",
    }
    for source_key, target_key in alias_map.items():
        if source_key in observed_fields and target_key not in observed_fields:
            observed_fields[target_key] = observed_fields[source_key]
        if source_key in observed_counts and target_key not in observed_counts:
            observed_counts[target_key] = observed_counts[source_key]
    return observed_fields, observed_counts


def merge_observation_sources(
    sources: list[tuple[str, dict[str, object], dict[str, int]]],
) -> tuple[dict[str, object], dict[str, int], dict[str, str], dict[str, str]]:
    merged_fields: dict[str, object] = {}
    merged_counts: dict[str, int] = {}
    field_sources: dict[str, str] = {}
    count_sources: dict[str, str] = {}
    for source_name, fields, counts in sources:
        for key, value in fields.items():
            if key in merged_fields:
                continue
            merged_fields[key] = value
            field_sources[key] = source_name
        for key, value in counts.items():
            if key in merged_counts:
                continue
            merged_counts[key] = value
            count_sources[key] = source_name
    return merged_fields, merged_counts, field_sources, count_sources
