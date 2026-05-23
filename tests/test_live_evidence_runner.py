from pathlib import Path

from sis.live_evidence_runner import (
    CollectionGateResult,
    LiveEvidenceManifest,
    RunOutcome,
    default_manifest_path,
    evaluate_collection_volume,
    load_manifest,
    terminal_outcome,
    write_manifest,
)


def test_evaluate_collection_volume_pass() -> None:
    result = evaluate_collection_volume(
        metadata_rows_delta=96,
        pricing_rows_delta=500,
        min_metadata_rows=96,
    )

    assert result == CollectionGateResult.PASS


def test_evaluate_collection_volume_retryable_low_volume() -> None:
    result = evaluate_collection_volume(
        metadata_rows_delta=40,
        pricing_rows_delta=500,
        min_metadata_rows=96,
    )

    assert result == CollectionGateResult.RETRYABLE_LOW_VOLUME


def test_evaluate_collection_volume_hard_fail_when_pricing_missing() -> None:
    result = evaluate_collection_volume(
        metadata_rows_delta=96,
        pricing_rows_delta=0,
        min_metadata_rows=96,
    )

    assert result == CollectionGateResult.HARD_FAIL


def test_manifest_round_trip(tmp_path) -> None:
    path = tmp_path / "manifests/live_evidence_20260522_2308.json"
    manifest = LiveEvidenceManifest(
        run_id="20260522_2308",
        status=RunOutcome.COMPLETED_WITH_RETRIES,
        duration_minutes=120,
        metadata_interval_seconds=120,
        row_counts={"raw_quotes": 192},
        decision="GO",
    )

    write_manifest(path, manifest)
    loaded = load_manifest(path)

    assert loaded.run_id == "20260522_2308"
    assert loaded.status == RunOutcome.COMPLETED_WITH_RETRIES
    assert loaded.row_counts["raw_quotes"] == 192


def test_terminal_outcome_recognizes_manifest_statuses() -> None:
    assert terminal_outcome("completed")
    assert terminal_outcome("completed_with_retries")
    assert terminal_outcome("partial_failed")
    assert terminal_outcome("failed_preflight")
    assert terminal_outcome("failed_collection")
    assert not terminal_outcome("running")


def test_default_manifest_path_uses_run_id() -> None:
    assert default_manifest_path("20260522_2308") == Path(
        "logs/live_evidence/manifests/live_evidence_20260522_2308.json"
    )
