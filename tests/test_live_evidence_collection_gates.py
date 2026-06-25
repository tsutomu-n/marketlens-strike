from sis.live_evidence_collection_gates import (
    CollectionGateResult,
    evaluate_collection_volume,
    expected_metadata_rows,
)
from sis.live_evidence_runner import evaluate_collection_volume as runner_evaluate_collection_volume


def test_expected_metadata_rows_preserves_minimum_and_rounds_up() -> None:
    assert expected_metadata_rows(duration_minutes=1, metadata_interval_seconds=120) == 1
    assert expected_metadata_rows(duration_minutes=120, metadata_interval_seconds=60) == 96
    assert expected_metadata_rows(duration_minutes=125, metadata_interval_seconds=60) == 100


def test_evaluate_collection_volume_hard_fails_when_any_required_stream_missing() -> None:
    assert (
        evaluate_collection_volume(
            metadata_rows_delta=0,
            pricing_rows_delta=500,
            min_metadata_rows=96,
        )
        == CollectionGateResult.HARD_FAIL
    )
    assert (
        evaluate_collection_volume(
            metadata_rows_delta=96,
            pricing_rows_delta=0,
            min_metadata_rows=96,
        )
        == CollectionGateResult.HARD_FAIL
    )


def test_evaluate_collection_volume_retries_low_metadata_before_passing() -> None:
    assert (
        evaluate_collection_volume(
            metadata_rows_delta=95,
            pricing_rows_delta=500,
            min_metadata_rows=96,
        )
        == CollectionGateResult.RETRYABLE_LOW_VOLUME
    )
    assert (
        evaluate_collection_volume(
            metadata_rows_delta=96,
            pricing_rows_delta=500,
            min_metadata_rows=96,
        )
        == CollectionGateResult.PASS
    )


def test_runner_collection_gate_wrapper_preserves_compatibility() -> None:
    assert runner_evaluate_collection_volume(
        metadata_rows_delta=96,
        pricing_rows_delta=500,
        min_metadata_rows=96,
    ) == evaluate_collection_volume(
        metadata_rows_delta=96,
        pricing_rows_delta=500,
        min_metadata_rows=96,
    )
