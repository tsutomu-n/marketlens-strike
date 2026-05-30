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
    signal_id: str = "sig-001",
    strategy_id: str = "equity_index_momentum_v0",
    execution_symbol: str = "XYZ100",
    real_market_symbol: str = "QQQ",
) -> None:
    path = data_dir / "research/strategy_signals.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            _strategy_signal_row(
                signal_id=signal_id,
                strategy_id=strategy_id,
                execution_symbol=execution_symbol,
                real_market_symbol=real_market_symbol,
            )
        ]
    ).write_parquet(path)


def _strategy_signal_row(
    *,
    signal_id: str,
    strategy_id: str,
    execution_symbol: str,
    real_market_symbol: str,
) -> dict:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": signal_id,
        "generated_at": now,
        "strategy_id": strategy_id,
        "strategy_family": "momentum",
        "strategy_version": "v0",
        "trial_id": None,
        "parameter_hash": None,
        "ts_signal": now,
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


def test_strategy_lab_cli_artifact_chain(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_strategy_signals(data_dir)

    result = runner.invoke(app, ["evaluate-strategy-lab"])
    assert result.exit_code == 0
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    assert ledger_path.exists()
    ledger_record = json.loads(ledger_path.read_text(encoding="utf-8").strip())
    assert ledger_record["trial_id"].startswith("trial-")
    assert ledger_record["trial_id"] != "trial-001"
    run_id = ledger_record["trial_id"].removeprefix("trial-")
    assert ledger_record["trial_group_id"] == f"trial-group-{run_id}"
    assert ledger_record["metrics"]["signal_artifact_run_id"] == run_id

    result = runner.invoke(app, ["build-paper-candidate-pack"])
    assert result.exit_code == 0
    pack_path = data_dir / "research/paper_candidate_pack.json"
    assert pack_path.exists()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert pack["live_order_submitted"] is False
    assert pack["pack_id"] == f"paper-pack-{run_id}"
    assert pack["candidates"][0]["candidate_id"] == f"candidate-trial-{run_id}"

    result = runner.invoke(app, ["promotion-decision", "--decision", "promote"])
    assert result.exit_code == 0
    decision_path = data_dir / "research/promotion_decision.json"
    assert decision_path.exists()
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["promotion_id"] == f"promotion-{run_id}"
    assert decision["source_pack_id"] == pack["pack_id"]

    result = runner.invoke(app, ["build-paper-intent-preview"])
    assert result.exit_code == 0
    intent_path = data_dir / "bot/paper_intent_preview.json"
    assert intent_path.exists()
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    assert intents[0]["paper_only"] is True
    assert intents[0]["live_conversion_allowed"] is False
    assert intents[0]["source_pack_id"] == pack["pack_id"]


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


def test_evaluate_strategy_lab_rejects_mixed_signal_artifact(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    path = data_dir / "research/strategy_signals.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            _strategy_signal_row(
                signal_id="sig-001",
                strategy_id="equity_index_momentum_v0",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
            ),
            _strategy_signal_row(
                signal_id="sig-002",
                strategy_id="sp500_index_momentum_v0",
                execution_symbol="SP500",
                real_market_symbol="SPY",
            ),
        ]
    ).write_parquet(path)

    result = runner.invoke(app, ["evaluate-strategy-lab"])

    assert result.exit_code == 2
    assert "mixed strategy/symbol identities" in result.stdout
    assert not (data_dir / "research/trial_ledger.jsonl").exists()


def test_build_signals_unknown_generator_exits_with_registered_ids(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    pl.DataFrame(
        [
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "is_event_blackout": False,
                "close_above_sma20": True,
                "research_return_1d": 0.01,
                "t10y2y": 1.0,
                "vix_level": 20.0,
            }
        ]
    ).write_parquet(feature_panel_path)

    result = runner.invoke(app, ["build-signals", "--generator-id", "unknown_generator"])

    assert result.exit_code == 2
    assert "unknown_generator" in result.stdout
    assert "qqq_trend_rates_vix" in result.stdout
    assert "sp500_trend_rates_vix" in result.stdout
