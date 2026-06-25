from __future__ import annotations

from enum import Enum

__all__ = ["CollectionGateResult", "evaluate_collection_volume", "expected_metadata_rows"]


class CollectionGateResult(str, Enum):
    PASS = "pass"
    RETRYABLE_LOW_VOLUME = "retryable_low_volume"
    HARD_FAIL = "hard_fail"


def expected_metadata_rows(duration_minutes: int, metadata_interval_seconds: int) -> int:
    snapshots = max(1, (duration_minutes * 60) // metadata_interval_seconds)
    return max(1, (snapshots * 8 + 9) // 10)


def evaluate_collection_volume(
    *,
    metadata_rows_delta: int,
    pricing_rows_delta: int,
    min_metadata_rows: int,
) -> CollectionGateResult:
    if pricing_rows_delta <= 0 or metadata_rows_delta <= 0:
        return CollectionGateResult.HARD_FAIL
    if metadata_rows_delta < min_metadata_rows:
        return CollectionGateResult.RETRYABLE_LOW_VOLUME
    return CollectionGateResult.PASS
