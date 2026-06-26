from __future__ import annotations

from typing import cast

from sis.reports.summary_normalizers import source_confidence_for_observed_sources


def flatten_observed_sources(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(flatten_observed_sources(nested))
        return flattened
    if isinstance(value, list):
        flattened: list[str] = []
        for nested in value:
            flattened.extend(flatten_observed_sources(nested))
        return flattened
    return []


def verification_confidence(signal_observed_sources: object, verification: list[str]) -> str:
    if not isinstance(signal_observed_sources, dict) or not verification:
        return "unknown"
    signal_sources = cast(dict[str, object], signal_observed_sources)
    flattened: list[str] = []
    for signal in verification:
        if not isinstance(signal, str):
            continue
        flattened.extend(flatten_observed_sources(signal_sources.get(signal)))
    values = [str(source) for source in flattened if isinstance(source, str)]
    if not values:
        return "unknown"
    rank_map = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    reverse_rank_map = {0: "high", 1: "medium", 2: "low", 3: "unknown"}
    normalized = [
        source_confidence_for_observed_sources([source]) or "unknown" for source in values
    ]
    return reverse_rank_map[max(rank_map.get(value, 3) for value in normalized)]


def ordered_verification(signal_observed_sources: object, verification: list[str]) -> list[str]:
    if not isinstance(signal_observed_sources, dict):
        return verification
    rank_map = {"unknown": 0, "low": 1, "medium": 2, "high": 3}

    def sort_key(signal: str) -> tuple[int, str]:
        confidence = verification_confidence(signal_observed_sources, [signal])
        return (rank_map.get(confidence, 0), signal)

    return sorted([value for value in verification if isinstance(value, str)], key=sort_key)
