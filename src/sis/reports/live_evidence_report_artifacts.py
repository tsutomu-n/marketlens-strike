from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LiveEvidenceArtifacts:
    sidecar_metadata: Path
    sidecar_pricing: Path
    raw_quotes: Path
    normalized_quotes: Path
    cost_matrix: Path
    backtest_metrics: Path
    go_no_go_report: Path
    evidence_card: Path | None


def build_live_evidence_artifacts(
    *,
    data_dir: Path,
    artifact_paths: dict[str, Any],
    today_utc: str,
    fallback_evidence_card: Path | None,
) -> LiveEvidenceArtifacts:
    evidence_card_path = artifact_paths.get("evidence_card")
    evidence_card = (
        Path(evidence_card_path)
        if isinstance(evidence_card_path, str) and evidence_card_path
        else fallback_evidence_card
    )
    return LiveEvidenceArtifacts(
        sidecar_metadata=Path(
            artifact_paths.get(
                "sidecar_metadata", data_dir / f"raw/sidecar/gtrade/{today_utc}.jsonl"
            )
        ),
        sidecar_pricing=Path(
            artifact_paths.get(
                "sidecar_pricing", data_dir / f"raw/sidecar/gtrade-pricing/{today_utc}.jsonl"
            )
        ),
        raw_quotes=Path(
            artifact_paths.get("raw_quotes", data_dir / f"raw/quotes/gtrade/{today_utc}.jsonl")
        ),
        normalized_quotes=Path(
            artifact_paths.get("normalized_quotes", data_dir / "normalized/quotes.parquet")
        ),
        cost_matrix=Path(
            artifact_paths.get("cost_matrix", data_dir / "research/venue_cost_matrix.csv")
        ),
        backtest_metrics=Path(
            artifact_paths.get("backtest_metrics", data_dir / "research/backtest_metrics.json")
        ),
        go_no_go_report=Path(
            artifact_paths.get("go_no_go_report", data_dir / "research/go_no_go_report.md")
        ),
        evidence_card=evidence_card,
    )
