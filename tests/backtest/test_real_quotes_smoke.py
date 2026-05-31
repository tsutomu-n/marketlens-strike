from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest


def test_real_normalized_quotes_smoke_script_when_available(tmp_path) -> None:
    input_path = Path("data/normalized/quotes.parquet")
    if not input_path.exists():
        pytest.skip("data/normalized/quotes.parquet is not available")

    raw = pl.read_parquet(input_path)
    if "canonical_symbol" not in raw.columns:
        pytest.skip("normalized quotes do not include canonical_symbol")
    if raw.filter(pl.col("canonical_symbol") == "SP500").is_empty():
        pytest.skip("SP500 rows are not available in normalized quotes")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_trade_xyz_backtest_smoke.py",
            "--input",
            str(input_path),
            "--symbol",
            "SP500",
            "--timeframe",
            "1h",
            "--close-source",
            "mid_price",
            "--event-time-source",
            "ts_client",
            "--out",
            str(tmp_path),
            "--auto-small-lookback",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    run_dir = Path(completed.stdout.strip().splitlines()[-1])

    assert run_dir.exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "backtest_report.html").exists()
    assert (run_dir / "data_manifest.json").exists()

    candidate = json.loads((run_dir / "candidate_result.json").read_text(encoding="utf-8"))
    assert candidate["smoke_only"] is True
    assert candidate["usable_for_strategy_selection"] is False

    manifest = json.loads((run_dir / "data_manifest.json").read_text(encoding="utf-8"))
    assert manifest["input_data_ref"] == str(input_path)
    assert manifest["input_file_sha256"]
    assert manifest["close_source"] == "mid_price"
    assert manifest["bar_builder"] == "quote_bar_v1"
