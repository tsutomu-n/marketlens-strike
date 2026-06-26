from __future__ import annotations

from pathlib import Path

from sis.reports.live_evidence_report_artifacts import (
    build_live_evidence_artifacts,
)


def test_build_live_evidence_artifacts_uses_manifest_overrides() -> None:
    data_dir = Path("data")
    artifacts = build_live_evidence_artifacts(
        data_dir=data_dir,
        artifact_paths={
            "sidecar_metadata": "override/sidecar.jsonl",
            "sidecar_pricing": "override/pricing.jsonl",
            "raw_quotes": "override/raw.jsonl",
            "normalized_quotes": "override/quotes.parquet",
            "cost_matrix": "override/cost.csv",
            "backtest_metrics": "override/metrics.json",
            "go_no_go_report": "override/go_no_go.md",
            "evidence_card": "override/evidence_card.json",
        },
        today_utc="2026-05-22",
        fallback_evidence_card=Path("data/evidence/latest.json"),
    )

    assert artifacts.sidecar_metadata == Path("override/sidecar.jsonl")
    assert artifacts.sidecar_pricing == Path("override/pricing.jsonl")
    assert artifacts.raw_quotes == Path("override/raw.jsonl")
    assert artifacts.normalized_quotes == Path("override/quotes.parquet")
    assert artifacts.cost_matrix == Path("override/cost.csv")
    assert artifacts.backtest_metrics == Path("override/metrics.json")
    assert artifacts.go_no_go_report == Path("override/go_no_go.md")
    assert artifacts.evidence_card == Path("override/evidence_card.json")


def test_build_live_evidence_artifacts_uses_default_paths_and_fallback_card() -> None:
    data_dir = Path("data")
    artifacts = build_live_evidence_artifacts(
        data_dir=data_dir,
        artifact_paths={},
        today_utc="2026-05-22",
        fallback_evidence_card=Path("data/evidence/latest.json"),
    )

    assert artifacts.sidecar_metadata == Path("data/raw/sidecar/gtrade/2026-05-22.jsonl")
    assert artifacts.sidecar_pricing == Path("data/raw/sidecar/gtrade-pricing/2026-05-22.jsonl")
    assert artifacts.raw_quotes == Path("data/raw/quotes/gtrade/2026-05-22.jsonl")
    assert artifacts.normalized_quotes == Path("data/normalized/quotes.parquet")
    assert artifacts.cost_matrix == Path("data/research/venue_cost_matrix.csv")
    assert artifacts.backtest_metrics == Path("data/research/backtest_metrics.json")
    assert artifacts.go_no_go_report == Path("data/research/go_no_go_report.md")
    assert artifacts.evidence_card == Path("data/evidence/latest.json")


def test_build_live_evidence_artifacts_ignores_empty_evidence_card_override() -> None:
    artifacts = build_live_evidence_artifacts(
        data_dir=Path("data"),
        artifact_paths={"evidence_card": ""},
        today_utc="2026-05-22",
        fallback_evidence_card=None,
    )

    assert artifacts.evidence_card is None
