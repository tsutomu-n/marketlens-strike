from __future__ import annotations

from pathlib import Path

__all__ = ["build_artifact_paths", "latest_evidence_card_path", "row_count"]


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def latest_evidence_card_path(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "evidence").glob("evidence_card_*.json"))
    return paths[-1] if paths else None


def build_artifact_paths(data_dir: Path, day: str) -> dict[str, str | None]:
    evidence_path = latest_evidence_card_path(data_dir)
    return {
        "sidecar_metadata": str(data_dir / f"raw/sidecar/gtrade/{day}.jsonl"),
        "sidecar_pricing": str(data_dir / f"raw/sidecar/gtrade-pricing/{day}.jsonl"),
        "raw_quotes": str(data_dir / f"raw/quotes/gtrade/{day}.jsonl"),
        "normalized_quotes": str(data_dir / "normalized/quotes.parquet"),
        "cost_matrix": str(data_dir / "research/venue_cost_matrix.csv"),
        "backtest_metrics": str(data_dir / "research/backtest_metrics.json"),
        "go_no_go_report": str(data_dir / "research/go_no_go_report.md"),
        "evidence_card": str(evidence_path) if evidence_path else None,
    }
