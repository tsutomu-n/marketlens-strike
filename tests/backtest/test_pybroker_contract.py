from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate
import polars as pl

from sis.backtest.pybroker_contract import build_strategy_backtest_pybroker_contract


def _schema(name: str) -> dict:
    return json.loads(Path("schemas", name).read_text(encoding="utf-8"))


def test_pybroker_contract_blocks_external_data_and_requires_provenance(tmp_path: Path) -> None:
    signals_path = tmp_path / "signals.parquet"
    quotes_path = tmp_path / "quotes.parquet"
    pl.DataFrame(
        {
            "ts_signal": ["2026-01-01T00:00:00+00:00"],
            "canonical_symbol": ["QQQ"],
            "side": ["long"],
        }
    ).write_parquet(signals_path)
    pl.DataFrame(
        {
            "ts_client": ["2026-01-01T00:00:00+00:00"],
            "canonical_symbol": ["QQQ"],
            "mid_price": [100.0],
        }
    ).write_parquet(quotes_path)

    result = build_strategy_backtest_pybroker_contract(
        signals_path=signals_path,
        quotes_path=quotes_path,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    validate(
        instance=result.payload,
        schema=_schema("strategy_backtest_pybroker_contract.v1.schema.json"),
    )
    assert result.payload["decision"] == "NOT_READY_FOR_PYBROKER_REFERENCE_RUN"
    assert result.payload["external_data_source_allowed"] is False
    assert result.payload["dependency_added"] is False
    assert result.payload["engine_run"] is False
    assert any("Commons Clause" in note for note in result.payload["risk_notes"])
