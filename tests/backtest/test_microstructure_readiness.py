from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate
import polars as pl

from sis.backtest.microstructure_readiness import (
    build_strategy_backtest_microstructure_readiness,
)


def _schema(name: str) -> dict:
    return json.loads(Path("schemas", name).read_text(encoding="utf-8"))


def test_microstructure_readiness_reports_baseline_not_ready(tmp_path: Path) -> None:
    metrics_path = tmp_path / "metrics.json"
    signals_path = tmp_path / "signals.parquet"
    quotes_path = tmp_path / "quotes.parquet"
    metrics_path.write_text('{"summary": {}}\n', encoding="utf-8")
    pl.DataFrame({"ts_signal": ["2026-01-01T00:00:00+00:00"], "side": ["long"]}).write_parquet(
        signals_path
    )
    pl.DataFrame(
        {
            "ts_client": ["2026-01-01T00:00:00+00:00"],
            "canonical_symbol": ["QQQ"],
            "mid_price": [100.0],
            "best_bid": [99.9],
            "best_ask": [100.1],
        }
    ).write_parquet(quotes_path)

    result = build_strategy_backtest_microstructure_readiness(
        metrics_path=metrics_path,
        signals_path=signals_path,
        quotes_path=quotes_path,
        data_availability_path=None,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    validate(
        instance=result.payload,
        schema=_schema("strategy_backtest_microstructure_readiness.v1.schema.json"),
    )
    assert result.payload["decision"] == "NOT_READY_FOR_HFT_REPLAY"
    assert "trade_ticks" in result.payload["missing_requirements"]
    assert result.payload["market_impact_supported"] is False
    assert result.payload["dependency_added"] is False
    assert result.payload["engine_run"] is False
    assert result.payload["permits_live_order"] is False
