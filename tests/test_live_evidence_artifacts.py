from sis.live_evidence_artifacts import (
    build_artifact_paths,
    latest_evidence_card_path,
    row_count,
)
from sis.live_evidence_runner import build_artifact_paths as runner_build_artifact_paths


def test_row_count_counts_nonblank_lines_and_missing_files(tmp_path) -> None:
    path = tmp_path / "raw/quotes/gtrade/2026-06-26.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text('{"n":1}\n\n{"n":2}\n   \n', encoding="utf-8")

    assert row_count(path) == 2
    assert row_count(tmp_path / "missing.jsonl") == 0


def test_latest_evidence_card_path_returns_sorted_latest_or_none(tmp_path) -> None:
    data_dir = tmp_path / "data"

    assert latest_evidence_card_path(data_dir) is None

    evidence_dir = data_dir / "evidence"
    evidence_dir.mkdir(parents=True)
    older = evidence_dir / "evidence_card_20260626_060000.json"
    newer = evidence_dir / "evidence_card_20260626_061500.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")

    assert latest_evidence_card_path(data_dir) == newer


def test_build_artifact_paths_preserves_keys_and_optional_evidence_card(tmp_path) -> None:
    data_dir = tmp_path / "data"

    assert build_artifact_paths(data_dir, "2026-06-26") == {
        "sidecar_metadata": str(data_dir / "raw/sidecar/gtrade/2026-06-26.jsonl"),
        "sidecar_pricing": str(data_dir / "raw/sidecar/gtrade-pricing/2026-06-26.jsonl"),
        "raw_quotes": str(data_dir / "raw/quotes/gtrade/2026-06-26.jsonl"),
        "normalized_quotes": str(data_dir / "normalized/quotes.parquet"),
        "cost_matrix": str(data_dir / "research/venue_cost_matrix.csv"),
        "backtest_metrics": str(data_dir / "research/backtest_metrics.json"),
        "go_no_go_report": str(data_dir / "research/go_no_go_report.md"),
        "evidence_card": None,
    }

    evidence_dir = data_dir / "evidence"
    evidence_dir.mkdir(parents=True)
    card_path = evidence_dir / "evidence_card_20260626_061500.json"
    card_path.write_text("{}", encoding="utf-8")

    paths = build_artifact_paths(data_dir, "2026-06-26")

    assert paths["evidence_card"] == str(card_path)
    assert runner_build_artifact_paths(data_dir, "2026-06-26") == paths
