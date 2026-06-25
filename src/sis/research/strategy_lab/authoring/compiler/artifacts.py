from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from sis.research.strategy_lab.authoring.compiler.research_signal_adapter import (
    strategy_signals_to_research_signals as strategy_signals_to_research_signals,
)
from sis.research.signal_builder import _legacy_export
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    strategy_signal_manifest_path,
    write_strategy_signal_manifest,
)


def write_authoring_signal_artifacts(
    frame: pl.DataFrame, manifest: StrategySignalManifest, *, data_dir: Path
) -> dict[str, Path]:
    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    legacy_out = data_dir / "research/signals.csv"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(parquet_out)
    with jsonl_out.open("w", encoding="utf-8") as handle:
        for row in frame.to_dicts():
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    _legacy_export(frame).write_csv(legacy_out)
    write_strategy_signal_manifest(manifest, strategy_signal_manifest_path(data_dir))
    return {
        "signals_parquet": parquet_out,
        "signals_jsonl": jsonl_out,
        "legacy_csv": legacy_out,
        "manifest": strategy_signal_manifest_path(data_dir),
    }
