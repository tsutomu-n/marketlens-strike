from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.research.signal_builder import build_signals

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
    ts_signal: datetime | None = None,
    source_confidence: float = 0.9,
) -> dict:
    now = ts_signal or datetime(2026, 1, 1, tzinfo=timezone.utc)
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
        "source_confidence": source_confidence,
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
    ledger_record["metrics"]["strategy_scorecard"] = {
        "schema_version": "strategy_authoring_scorecard.v1",
        "signal_count": 1,
        "failed_thresholds": [],
        "backtest_passed": True,
        "paper_only": True,
        "live_order_submitted": False,
    }
    ledger_path.write_text(json.dumps(ledger_record) + "\n", encoding="utf-8")

    result = runner.invoke(app, ["build-paper-candidate-pack"])
    assert result.exit_code == 0
    pack_path = data_dir / "research/paper_candidate_pack.json"
    assert pack_path.exists()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert pack["live_order_submitted"] is False
    assert pack["pack_id"] == f"paper-pack-{run_id}"
    assert pack["candidates"][0]["candidate_id"] == f"candidate-trial-{run_id}-sig-001"
    assert pack["candidates"][0]["signal_id"] == "sig-001"
    assert pack["candidates"][0]["status"] == "blocked"
    assert pack["selected_candidate_ids"] == []
    assert pack["rejected_candidate_ids"] == [pack["candidates"][0]["candidate_id"]]
    assert (
        "VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION"
        in pack["candidates"][0]["block_reasons"]
    )

    result = runner.invoke(app, ["promotion-decision", "--decision", "promote"])
    assert result.exit_code == 0
    decision_path = data_dir / "research/promotion_decision.json"
    assert decision_path.exists()
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["promotion_id"] == f"promotion-{run_id}"
    assert decision["source_pack_id"] == pack["pack_id"]
    assert "strategy_scorecard" in decision["observed_evidence"]
    assert decision["scorecard_summary"]["schema_version"] == "strategy_authoring_scorecard.v1"

    result = runner.invoke(app, ["build-paper-intent-preview"])
    assert result.exit_code == 0
    intent_path = data_dir / "bot/paper_intent_preview.json"
    assert intent_path.exists()
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    assert intents == []


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


def test_build_signals_unknown_generator_exits_with_registered_ids(tmp_path, monkeypatch) -> None:
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
                "source_confidence": 0.9,
            }
        ]
    ).write_parquet(feature_panel_path)

    result = runner.invoke(app, ["build-signals", "--generator-id", "unknown_generator"])

    assert result.exit_code == 2
    assert "unknown_generator" in result.stdout
    assert "qqq_trend_rates_vix" in result.stdout
    assert "sp500_trend_rates_vix" in result.stdout


def test_strategy_experiment_run_reads_yaml_spec_and_preserves_spec_lineage(
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
                "source_confidence": 0.9,
            }
        ]
    ).write_parquet(feature_panel_path)
    spec_path = tmp_path / "experiment.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version: strategy_experiment_spec.v1",
                "strategy_id: custom_qqq_research_v1",
                "strategy_family: custom_momentum",
                "strategy_version: v1",
                "enabled: true",
                "description: Custom registered-generator experiment.",
                "symbol_bindings:",
                "  - execution_venue: trade_xyz",
                "    execution_symbol: XYZ100",
                "    real_market_symbol: QQQ",
                "    asset_class: basket_index",
                "generator_id: qqq_trend_rates_vix",
                "parameter_grid:",
                "  min_source_confidence: [0.7]",
                "evaluation_plan_id: initial_single_window_v1",
                "run_profile_id: strategy_lab",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-experiment-run", "--spec", str(spec_path)])

    assert result.exit_code == 0, result.stdout
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("strategy_id").to_list() == ["custom_qqq_research_v1"]
    assert signals.get_column("strategy_family").to_list() == ["custom_momentum"]
    manifest = json.loads(
        (data_dir / "research/strategy_signal_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["generator_id"] == "qqq_trend_rates_vix"
    assert manifest["strategy_id"] == "custom_qqq_research_v1"
    assert manifest["symbol_bindings"][0]["execution_symbol"] == "XYZ100"
    report = (data_dir / "reports/strategy_experiment_run.md").read_text(encoding="utf-8")
    assert "- paper_only: true" in report
    assert "- live_order_submitted: false" in report


def test_strategy_experiment_run_unknown_generator_exits_with_registered_ids(
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
                "source_confidence": 0.9,
            }
        ]
    ).write_parquet(feature_panel_path)
    spec_path = tmp_path / "experiment.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version: strategy_experiment_spec.v1",
                "strategy_id: custom_qqq_research_v1",
                "strategy_family: custom_momentum",
                "strategy_version: v1",
                "enabled: true",
                "description: Custom registered-generator experiment.",
                "symbol_bindings:",
                "  - execution_venue: trade_xyz",
                "    execution_symbol: XYZ100",
                "    real_market_symbol: QQQ",
                "    asset_class: basket_index",
                "generator_id: missing_generator",
                "parameter_grid: {}",
                "evaluation_plan_id: initial_single_window_v1",
                "run_profile_id: strategy_lab",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-experiment-run", "--spec", str(spec_path)])

    assert result.exit_code == 2
    assert "missing_generator" in result.stdout
    assert "qqq_trend_rates_vix" in result.stdout
    assert "sp500_trend_rates_vix" in result.stdout


def test_strategy_experiment_run_expands_parameter_grid_with_distinct_lineage(
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
                "source_confidence": 0.9,
            }
        ]
    ).write_parquet(feature_panel_path)
    spec_path = tmp_path / "experiment.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version: strategy_experiment_spec.v1",
                "strategy_id: custom_qqq_grid_v1",
                "strategy_family: custom_momentum",
                "strategy_version: v1",
                "enabled: true",
                "description: Custom registered-generator grid experiment.",
                "symbol_bindings:",
                "  - execution_venue: trade_xyz",
                "    execution_symbol: XYZ100",
                "    real_market_symbol: QQQ",
                "    asset_class: basket_index",
                "generator_id: qqq_trend_rates_vix",
                "parameter_grid:",
                "  min_source_confidence: [0.7, 0.8]",
                "evaluation_plan_id: initial_single_window_v1",
                "run_profile_id: strategy_lab",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-experiment-run", "--spec", str(spec_path)])

    assert result.exit_code == 0, result.stdout
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.height == 2
    parameter_hashes = signals.get_column("parameter_hash").to_list()
    assert len(set(parameter_hashes)) == 2
    assert len(set(signals.get_column("signal_id").to_list())) == 2
    assert all(
        any(str(reason).startswith("parameter_grid:") for reason in reasons)
        for reasons in signals.get_column("reason_codes").to_list()
    )
    manifest = json.loads(
        (data_dir / "research/strategy_signal_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["signal_count"] == 2


def test_strategy_experiment_run_parameter_grid_changes_signal_conditions(
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
                "source_confidence": 0.6,
            },
            {
                "ts": datetime(2026, 1, 2, tzinfo=timezone.utc),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "is_event_blackout": False,
                "close_above_sma20": True,
                "research_return_1d": 0.01,
                "t10y2y": 1.0,
                "vix_level": 20.0,
                "source_confidence": 0.9,
            },
        ]
    ).write_parquet(feature_panel_path)
    spec_path = tmp_path / "experiment.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version: strategy_experiment_spec.v1",
                "strategy_id: custom_qqq_quality_gate_v1",
                "strategy_family: custom_momentum",
                "strategy_version: v1",
                "enabled: true",
                "description: Custom registered-generator quality gate experiment.",
                "symbol_bindings:",
                "  - execution_venue: trade_xyz",
                "    execution_symbol: XYZ100",
                "    real_market_symbol: QQQ",
                "    asset_class: basket_index",
                "generator_id: qqq_trend_rates_vix",
                "parameter_grid:",
                "  min_source_confidence: [0.8]",
                "  timeframe: [1h]",
                "evaluation_plan_id: initial_single_window_v1",
                "run_profile_id: strategy_lab",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-experiment-run", "--spec", str(spec_path)])

    assert result.exit_code == 0, result.stdout
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.height == 1
    assert signals.get_column("source_confidence").to_list() == [0.9]
    assert signals.get_column("timeframe").to_list() == ["1h"]


def test_strategy_experiment_run_rejects_oversized_parameter_grid(tmp_path, monkeypatch) -> None:
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
    spec_path = tmp_path / "experiment.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version: strategy_experiment_spec.v1",
                "strategy_id: custom_qqq_grid_v1",
                "strategy_family: custom_momentum",
                "strategy_version: v1",
                "enabled: true",
                "description: Custom registered-generator grid experiment.",
                "symbol_bindings:",
                "  - execution_venue: trade_xyz",
                "    execution_symbol: XYZ100",
                "    real_market_symbol: QQQ",
                "    asset_class: basket_index",
                "generator_id: qqq_trend_rates_vix",
                "parameter_grid:",
                "  min_source_confidence: [0.7, 0.8]",
                "  vix_gate: [20, 25]",
                "evaluation_plan_id: initial_single_window_v1",
                "run_profile_id: strategy_lab",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["strategy-experiment-run", "--spec", str(spec_path), "--max-variants", "3"],
    )

    assert result.exit_code == 2
    assert "parameter_grid expands to 4 variants" in result.stdout


def test_evaluate_strategy_lab_is_idempotent_for_same_artifact(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_strategy_signals(data_dir)

    assert runner.invoke(app, ["evaluate-strategy-lab"]).exit_code == 0
    assert runner.invoke(app, ["evaluate-strategy-lab"]).exit_code == 0

    ledger_lines = (data_dir / "research/trial_ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger_lines) == 1


def test_build_paper_candidate_pack_uses_latest_signal_row(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    path = data_dir / "research/strategy_signals.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            _strategy_signal_row(
                signal_id="sig-old",
                strategy_id="equity_index_momentum_v0",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                ts_signal=base_ts,
            ),
            _strategy_signal_row(
                signal_id="sig-new",
                strategy_id="equity_index_momentum_v0",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                ts_signal=base_ts + timedelta(days=1),
            ),
        ]
    ).write_parquet(path)

    result = runner.invoke(app, ["evaluate-strategy-lab"])
    assert result.exit_code == 0
    ledger_record = json.loads((data_dir / "research/trial_ledger.jsonl").read_text())
    assert ledger_record["signal_count"] == 2
    assert ledger_record["paper_candidate_count"] == 1
    assert ledger_record["metrics"]["selected_signal_id"] == "sig-new"

    result = runner.invoke(app, ["build-paper-candidate-pack"])
    assert result.exit_code == 0
    pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert len(pack["candidates"]) == 1
    assert pack["candidates"][0]["signal_id"] == "sig-new"
    assert pack["candidates"][0]["candidate_id"].endswith("-sig-new")
    assert pack["candidates"][0]["status"] == "blocked"
    assert pack["selected_candidate_ids"] == []
    assert pack["rejected_candidate_ids"] == [pack["candidates"][0]["candidate_id"]]


def test_build_paper_candidate_pack_can_select_multiple_signal_rows(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    path = data_dir / "research/strategy_signals.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            _strategy_signal_row(
                signal_id="sig-old",
                strategy_id="equity_index_momentum_v0",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                ts_signal=base_ts,
            ),
            _strategy_signal_row(
                signal_id="sig-new",
                strategy_id="equity_index_momentum_v0",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                ts_signal=base_ts + timedelta(days=1),
            ),
        ]
    ).write_parquet(path)

    result = runner.invoke(app, ["evaluate-strategy-lab", "--candidate-limit", "0"])
    assert result.exit_code == 0
    ledger_record = json.loads((data_dir / "research/trial_ledger.jsonl").read_text())
    assert ledger_record["paper_candidate_count"] == 2
    assert ledger_record["metrics"]["candidate_selection_policy"] == (
        "all_threshold_passing_by_ts_desc"
    )
    assert ledger_record["metrics"]["selected_signal_ids"] == ["sig-new", "sig-old"]

    result = runner.invoke(app, ["build-paper-candidate-pack"])
    assert result.exit_code == 0
    pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert [candidate["signal_id"] for candidate in pack["candidates"]] == [
        "sig-new",
        "sig-old",
    ]
    assert pack["selected_candidate_ids"] == []
    assert len(pack["rejected_candidate_ids"]) == 2
    assert all(candidate["status"] == "blocked" for candidate in pack["candidates"])


def test_evaluate_strategy_lab_rejects_duplicate_signal_ids(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    path = data_dir / "research/strategy_signals.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            _strategy_signal_row(
                signal_id="sig-duplicate",
                strategy_id="equity_index_momentum_v0",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                ts_signal=base_ts,
            ),
            _strategy_signal_row(
                signal_id="sig-duplicate",
                strategy_id="equity_index_momentum_v0",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                ts_signal=base_ts + timedelta(days=1),
            ),
        ]
    ).write_parquet(path)

    result = runner.invoke(app, ["evaluate-strategy-lab"])

    assert result.exit_code == 2
    assert "duplicate signal_id" in result.output


def test_evaluate_strategy_lab_rank_threshold_sweep_records_multiple_trials(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    path = data_dir / "research/strategy_signals.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    low_rank = {
        **_strategy_signal_row(
            signal_id="sig-low",
            strategy_id="equity_index_momentum_v0",
            execution_symbol="XYZ100",
            real_market_symbol="QQQ",
            ts_signal=base_ts,
        ),
        "rank_score": 0.4,
        "percentile_rank": 0.4,
        "tail_bucket": "middle",
    }
    high_rank = _strategy_signal_row(
        signal_id="sig-high",
        strategy_id="equity_index_momentum_v0",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        ts_signal=base_ts + timedelta(days=1),
    )
    pl.DataFrame([low_rank, high_rank]).write_parquet(path)

    result = runner.invoke(
        app,
        [
            "evaluate-strategy-lab",
            "--rank-thresholds",
            "0.2,0.8",
            "--candidate-limit",
            "0",
            "--split-method",
            "walk_forward",
            "--era-unit",
            "trading_day",
        ],
    )

    assert result.exit_code == 0
    records = [
        json.loads(line)
        for line in (data_dir / "research/trial_ledger.jsonl").read_text().splitlines()
    ]
    assert len(records) == 2
    assert records[0]["candidate_count"] == 2
    assert records[0]["paper_candidate_count"] == 2
    assert records[1]["candidate_count"] == 1
    assert records[1]["paper_candidate_count"] == 1
    assert records[1]["metrics"]["selected_signal_ids"] == ["sig-high"]
    assert records[1]["metrics"]["split_method"] == "walk_forward"
    assert records[1]["metrics"]["era_count"] == 1


def test_build_paper_candidate_pack_defaults_to_current_signal_trial_group(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_strategy_signals(data_dir, signal_id="sig-old")
    assert runner.invoke(app, ["evaluate-strategy-lab"]).exit_code == 0
    old_group_id = json.loads((data_dir / "research/trial_ledger.jsonl").read_text())[
        "trial_group_id"
    ]
    _write_strategy_signals(
        data_dir,
        signal_id="sig-new",
        strategy_id="sp500_index_momentum_v0",
        execution_symbol="SP500",
        real_market_symbol="SPY",
    )
    assert runner.invoke(app, ["evaluate-strategy-lab"]).exit_code == 0
    _write_strategy_signals(data_dir, signal_id="sig-old")

    result = runner.invoke(app, ["build-paper-candidate-pack"])

    assert result.exit_code == 0
    pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert len(pack["candidates"]) == 1
    assert pack["trial_group_id"] == old_group_id
    assert pack["candidates"][0]["signal_id"] == "sig-old"
    assert pack["candidates"][0]["execution_symbol"] == "XYZ100"


def test_build_paper_candidate_pack_default_fails_without_current_run_trial_group(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_strategy_signals(data_dir, signal_id="sig-old")
    assert runner.invoke(app, ["evaluate-strategy-lab"]).exit_code == 0
    _write_strategy_signals(data_dir, signal_id="sig-new")

    result = runner.invoke(app, ["build-paper-candidate-pack"])

    assert result.exit_code == 2
    assert "No trial group matches current strategy signal artifact run_id" in result.stdout


def test_build_paper_candidate_pack_can_select_trial_group(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_strategy_signals(data_dir, signal_id="sig-old")
    assert runner.invoke(app, ["evaluate-strategy-lab"]).exit_code == 0
    old_group_id = json.loads((data_dir / "research/trial_ledger.jsonl").read_text())[
        "trial_group_id"
    ]
    _write_strategy_signals(
        data_dir,
        signal_id="sig-new",
        strategy_id="sp500_index_momentum_v0",
        execution_symbol="SP500",
        real_market_symbol="SPY",
    )
    assert runner.invoke(app, ["evaluate-strategy-lab"]).exit_code == 0

    result = runner.invoke(app, ["build-paper-candidate-pack", "--trial-group-id", old_group_id])

    assert result.exit_code == 2
    assert "run_id does not match current strategy signal artifact" in result.stdout


def test_build_paper_candidate_pack_rejects_empty_ledger(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    (data_dir / "research").mkdir(parents=True)
    (data_dir / "research/trial_ledger.jsonl").write_text("", encoding="utf-8")

    result = runner.invoke(app, ["build-paper-candidate-pack"])

    assert result.exit_code == 2
    assert "Trial ledger has no records" in result.stdout


def test_evaluate_strategy_lab_preserves_no_signal_manifest_lineage(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    feature_panel_path.parent.mkdir(parents=True)
    pl.DataFrame(
        [
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "canonical_symbol": "QQQ",
                "trade_allowed": False,
                "is_event_blackout": False,
                "close_above_sma20": True,
                "research_return_1d": 0.01,
                "t10y2y": 1.0,
                "vix_level": 20.0,
            }
        ]
    ).write_parquet(feature_panel_path)
    build_signals(data_dir)

    result = runner.invoke(app, ["evaluate-strategy-lab"])
    assert result.exit_code == 0
    ledger_record = json.loads((data_dir / "research/trial_ledger.jsonl").read_text())
    assert ledger_record["strategy_id"] == "equity_index_momentum_v0"
    assert ledger_record["trial_id"] != "trial-no-signals"
    assert ledger_record["selected_for_next_stage"] is False
    assert ledger_record["no_signal_count"] == 1

    result = runner.invoke(app, ["build-paper-candidate-pack"])
    assert result.exit_code == 0
    pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert pack["candidates"][0]["candidate_id"].endswith("-no-signal")
    assert pack["candidates"][0]["status"] == "no_signal"
    assert pack["candidates"][0]["execution_symbol"] == "XYZ100"
    assert pack["rejected_candidate_ids"] == [pack["candidates"][0]["candidate_id"]]


def test_promotion_decision_requires_source_pack(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["promotion-decision", "--decision", "hold"])

    assert result.exit_code == 2
    assert "PaperCandidatePack not found" in result.stdout


def test_build_paper_intent_preview_requires_source_pack(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    decision_path = data_dir / "research/promotion_decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "schema_version": "promotion_decision.v1",
                "promotion_id": "promotion-001",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_pack_id": "missing-pack",
                "reviewer": None,
                "from_stage": "strategy_lab",
                "to_stage": "paper_observation",
                "decision": "hold",
                "required_evidence": ["trial_ledger", "paper_candidate_pack"],
                "observed_evidence": ["trial_ledger"],
                "approval_reasons": [],
                "rejection_reasons": ["not_promoted"],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["build-paper-intent-preview"])

    assert result.exit_code == 2
    assert "PaperCandidatePack not found" in result.stdout
