from __future__ import annotations

from datetime import datetime, timezone
import json

import polars as pl
from typer.testing import CliRunner

from sis.cli import app

runner = CliRunner()


def _write_strategy_signals(
    data_dir,
    *,
    strategy_id: str = "equity_index_momentum_v0",
    execution_symbol: str = "XYZ100",
    real_market_symbol: str = "QQQ",
) -> None:
    path = data_dir / "research/strategy_signals.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "schema_version": "strategy_signal.v1",
                "signal_id": "sig-001",
                "generated_at": datetime.now(timezone.utc),
                "strategy_id": strategy_id,
                "strategy_family": "momentum",
                "strategy_version": "v0",
                "trial_id": None,
                "parameter_hash": None,
                "ts_signal": datetime.now(timezone.utc),
                "timeframe": "4h",
                "execution_venue": "trade_xyz",
                "execution_symbol": execution_symbol,
                "real_market_symbol": real_market_symbol,
                "side": "long",
                "raw_score": 1.0,
                "rank_score": 0.9,
                "percentile_rank": 0.9,
                "tail_bucket": "top",
                "confidence": 0.8,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
                "feature_snapshot_ref": "feature-snap-001",
                "quote_ref": "quote-001",
                "tracking_ref": "tracking-001",
                "reason_codes": ["test"],
                "block_reasons": [],
            }
        ]
    ).write_parquet(path)


def test_strategy_lab_cli_artifact_chain(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_strategy_signals(data_dir)

    result = runner.invoke(app, ["evaluate-strategy-lab"])
    assert result.exit_code == 0
    assert (data_dir / "research/trial_ledger.jsonl").exists()

    result = runner.invoke(app, ["build-paper-candidate-pack"])
    assert result.exit_code == 0
    pack_path = data_dir / "research/paper_candidate_pack.json"
    assert pack_path.exists()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert pack["live_order_submitted"] is False

    result = runner.invoke(app, ["promotion-decision", "--decision", "promote"])
    assert result.exit_code == 0
    decision_path = data_dir / "research/promotion_decision.json"
    assert decision_path.exists()

    result = runner.invoke(app, ["build-paper-intent-preview"])
    assert result.exit_code == 0
    intent_path = data_dir / "bot/paper_intent_preview.json"
    assert intent_path.exists()
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    assert intents[0]["paper_only"] is True
    assert intents[0]["live_conversion_allowed"] is False


def test_strategy_lab_cli_preserves_sp500_signal_lineage(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_strategy_signals(
        data_dir,
        strategy_id="sp500_index_momentum_v0",
        execution_symbol="SP500",
        real_market_symbol="SPY",
    )

    result = runner.invoke(app, ["evaluate-strategy-lab"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["build-paper-candidate-pack"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["promotion-decision", "--decision", "promote"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["build-paper-intent-preview"])
    assert result.exit_code == 0

    pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert pack["candidates"][0]["strategy_id"] == "sp500_index_momentum_v0"
    assert pack["candidates"][0]["execution_symbol"] == "SP500"
    assert pack["candidates"][0]["real_market_symbol"] == "SPY"

    intents = json.loads((data_dir / "bot/paper_intent_preview.json").read_text())
    assert intents[0]["execution_symbol"] == "SP500"
    assert intents[0]["real_market_symbol"] == "SPY"
