# ruff: noqa: F401

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from jsonschema import validate
import polars as pl
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.research.strategy_lab.authoring.compiler.artifacts import (
    strategy_signals_to_research_signals,
    write_authoring_signal_artifacts,
)
from sis.research.strategy_lab.authoring.compiler.build import (
    build_authoring_signals,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.io import (
    load_authoring_bundle_spec,
    load_authoring_spec,
    template_yaml,
)
from sis.research.strategy_lab.authoring.validation import validate_authoring_inputs

runner = CliRunner()


def _write_spec(path: Path) -> None:
    path.write_text(template_yaml(), encoding="utf-8")


def test_strategy_authoring_example_specs_and_bundles_parse() -> None:
    examples_dir = Path("docs/strategy_research_lab/examples")
    spec_paths = sorted(examples_dir.glob("*_authoring_spec.yaml"))
    bundle_paths = sorted(examples_dir.glob("*bundle.yaml"))

    assert spec_paths
    assert bundle_paths
    for spec_path in spec_paths:
        assert load_authoring_spec(spec_path).schema_version == "strategy_authoring_spec.v1"
    for bundle_path in bundle_paths:
        bundle = load_authoring_bundle_spec(bundle_path)
        assert bundle.schema_version == "strategy_authoring_bundle.v1"
        for member in bundle.members:
            assert (bundle_path.parent / member.spec_path).exists()


def _feature_rows() -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "ts": start + timedelta(hours=4 * index),
            "canonical_symbol": "QQQ",
            "trade_allowed": True,
            "close_above_sma20": True,
            "vix_level": 20.0,
            "research_return_1d": 0.02,
            "research_return_4h": 0.01,
            "source_confidence": 0.8,
            "venue_quality_score": 0.9,
            "atr_stop_bps": 150.0,
            "atr_take_profit_bps": 300.0,
            "direction": "long",
        }
        for index in range(3)
    ]


def _quote(ts: datetime, price: float) -> dict:
    return {
        "ts_client": ts.isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "XYZ100",
        "venue_symbol": "XYZ100",
        "exec_buy_price": price,
        "exec_sell_price": price - 0.1,
        "mark_price": price,
        "mid_price": price,
        "oracle_price": price,
        "index_price": price,
        "spread_bps": 1.0,
        "min_side_depth_10bps_usd": 10_000.0,
        "oracle_ts_ms": int(ts.timestamp() * 1000),
        "market_status": "open",
        "is_tradable": True,
    }


def _write_data(data_dir: Path) -> None:
    feature_path = data_dir / "research/feature_panel.parquet"
    quote_path = data_dir / "normalized/quotes.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    rows = _feature_rows()
    pl.DataFrame(rows).write_parquet(feature_path)
    quotes = []
    for index in range(5):
        quotes.append(_quote(rows[0]["ts"] + timedelta(hours=index * 4), 100.0 + index))
    pl.DataFrame(quotes).write_parquet(quote_path)


__all__ = [name for name in globals() if not name.startswith("__")]
