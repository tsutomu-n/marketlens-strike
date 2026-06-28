from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

import duckdb
import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.research.strategy_lab.authoring.io import (
    load_authoring_bundle_spec,
    load_authoring_spec,
    load_backtest_suite_spec,
)
from sis.strategy_idea_candidates.authoring_bridge import (
    build_strategy_idea_candidate_authoring_bridge,
)
from sis.strategy_idea_candidates.prep_watchdeck_source import load_prep_watchdeck_source
from sis.strategy_inputs.io import write_json_artifact
from support.cli import normalized_stdout

from .fixtures import HASH_A, HASH_B, HASH_C, candidate_boundary


runner = CliRunner()


def _candidate(
    candidate_id: str,
    *,
    family: str,
    decision: str = "SHORTLISTED",
    parameter_set: dict[str, Any] | None = None,
    instruments: list[str] | None = None,
) -> dict[str, Any]:
    params = {
        "side_bias": "long",
        "venue": "bitget",
        "product_type": "USDT-FUTURES",
        "margin_mode": "isolated",
        "margin_coin": "USDT",
        "leverage": 3,
        "funding_assumption": "funding paid or received during hold is modeled",
        "fee_model_ref": "bitget_usdt_futures_taker_fee_estimate",
        "slippage_model_ref": "bps_stress_model",
        "slippage_bps": 2.5,
        "funding_rate_bps_per_8h": 1.0,
        "liquidation_buffer_bps": 2500,
        "max_position_notional_usd": 100,
        "max_daily_loss_usd": 25,
        "kill_conditions": ["spread_bps_gt_15", "funding_missing", "source_gap"],
    }
    if family == "perp_momentum_continuation":
        params.update({"lookback": 2, "breakout_z": 0.1})
    if family == "perp_funding_rate_carry_filter":
        params.update(
            {
                "side_bias": "short",
                "funding_rate_threshold_bps": 1.0,
                "holding_bars": 2,
            }
        )
    if parameter_set:
        params.update(parameter_set)
    payload: dict[str, Any] = {
        "idea_candidate_id": candidate_id,
        "candidate_status": "UNVERIFIED_CANDIDATE",
        "decision": decision,
        "family": family,
        "title": f"{candidate_id} {family}",
        "hypothesis_template": "Fixture perp hypothesis.",
        "mechanism_status": "UNVERIFIED_TEMPLATE",
        "signal_expression": "fixture_signal_expression_not_parsed",
        "parameter_set": params,
        "parameter_grid_ref": f"grid:{family}:v1",
        "target_definition": "next_window_cost_adjusted_return_estimate",
        "prediction_horizon": "quick_validation_window",
        "timeframe": "5m",
        "instruments": instruments or ["BTCUSDT"],
        "label_window": {
            "start": "2026-06-17T00:00:00Z",
            "end": "2026-06-17T12:00:00Z",
        },
        "feature_observation_window": {
            "start": "2026-06-16T00:00:00Z",
            "end": "2026-06-17T12:00:00Z",
        },
        "feature_columns_used": ["mark_price", "funding_rate", "realized_volatility"],
        "available_at_policy": "features must be available at or before decision timestamp",
        "source_artifact_sha256": HASH_B,
        "trial_count_refs": ["trial-001"],
        "baseline_refs": ["cash_or_no_trade"],
        "novelty_checks": {"duplicate_signal": False},
        "raw_validation_metrics": {"validation_return": 0.01},
        "selection_adjusted_metrics_status": "NOT_ESTIMABLE",
        "leakage_checks": {
            "uses_sealed_test_for_selection": False,
            "available_at_checked": True,
        },
        "boundary": candidate_boundary(),
    }
    if decision == "SHORTLISTED":
        payload["shortlist_reason"] = "fixture shortlisted candidate"
    else:
        payload["rejection_reason"] = "fixture rejected candidate"
    return payload


def _candidate_set_payload(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    shortlisted = [
        candidate["idea_candidate_id"]
        for candidate in candidates
        if candidate["decision"] == "SHORTLISTED"
    ]
    rejected = [
        candidate["idea_candidate_id"]
        for candidate in candidates
        if candidate["decision"] == "REJECTED"
    ]
    families = sorted({candidate["family"] for candidate in candidates})
    return {
        "schema_version": "strategy_idea_candidate_set.v1",
        "candidate_set_id": "bitget-perp-candidates-001",
        "generated_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "strategy-idea-candidates-build-fixture"},
        "generator_version": "fixture-0.1",
        "candidate_set_status": "BUILT",
        "input_contract_validation_refs": [
            {
                "contract_id": "bitget-perp-inputs-001",
                "validation_path": "data/strategy_inputs/bitget/validation.json",
                "validation_sha256": HASH_A,
                "validation_status": "PASS",
            }
        ],
        "source_artifacts": [
            {
                "source_id": "bitget_perp_features",
                "path": "data/research/crypto_perp/source/BTCUSDT_5m.csv",
                "sha256": HASH_B,
                "required": True,
                "source_validation_status": "present",
                "available_at": "2026-06-18T00:05:00Z",
                "max_observed_timestamp": "2026-06-17T21:00:00Z",
            }
        ],
        "candidate_inventory": candidates,
        "parameter_grids": {
            family: [
                candidate["parameter_set"]
                for candidate in candidates
                if candidate["family"] == family
            ]
            for family in families
        },
        "search_ledger_summary": {
            "family_count": len(families),
            "candidate_count_total": len(candidates),
            "candidate_count_shortlisted": len(shortlisted),
            "candidate_count_rejected": len(rejected),
            "trial_count_total": len(candidates),
            "parameter_grid_hash": HASH_C,
            "candidate_cap": len(candidates),
            "cap_rejection_count": 0,
            "validation_peek_count": 0,
            "rerank_count": 0,
            "duplicate_rejection_count": 0,
            "success_only_reporting": False,
            "sealed_test_used_for_selection": False,
        },
        "selection_policy": {
            "policy_id": "fixture-policy",
            "description": "Fixture shortlist policy.",
            "shortlisted_candidate_ids": shortlisted,
            "rejected_candidate_ids": rejected,
            "known_gaps": ["fixture candidate set"],
        },
        "split_policy": {
            "split_method": "blocked_time_split",
            "train_window": {
                "start": "2026-06-16T00:00:00Z",
                "end": "2026-06-16T23:55:00Z",
            },
            "validation_window": {
                "start": "2026-06-17T00:00:00Z",
                "end": "2026-06-17T12:00:00Z",
            },
            "sealed_test_window": {
                "start": "2026-06-18T00:00:00Z",
                "end": "2026-06-18T00:00:00Z",
            },
            "uses_sealed_test_for_selection": False,
        },
        "leakage_policy": {
            "feature_available_at_policy": "features must be available before decision",
            "purge_policy": "policy_record_only:not_implemented",
            "embargo_policy": "policy_record_only:not_implemented",
            "uses_sealed_test_for_selection": False,
        },
        "dependency_versions": {"python": "3.13", "sis": "local-test"},
        "boundary": candidate_boundary(),
    }


def _write_candidate_inputs(
    tmp_path: Path, candidates: list[dict[str, Any]]
) -> tuple[Path, Path, Path]:
    base = tmp_path / "candidate_inputs"
    candidate_set_path = base / "strategy_idea_candidate_set.json"
    export_manifest_path = base / "strategy_idea_candidate_export_manifest.json"
    ledger_path = base / "search_ledger.jsonl"
    payload = _candidate_set_payload(candidates)
    write_json_artifact(candidate_set_path, payload)
    exported = [
        {
            "idea_candidate_id": candidate["idea_candidate_id"],
            "strategy_idea_path": f"data/exported/{candidate['idea_candidate_id']}.json",
            "strategy_idea_sha256": HASH_B,
            "export_decision": "SHORTLISTED",
        }
        for candidate in candidates
        if candidate["decision"] == "SHORTLISTED"
    ]
    write_json_artifact(
        export_manifest_path,
        {
            "schema_version": "strategy_idea_candidate_export_manifest.v1",
            "manifest_id": "bitget-perp-candidates-001-export",
            "created_at": "2026-06-18T12:45:00Z",
            "producer": {"tool": "sis", "command": "strategy-idea-candidate-export-fixture"},
            "candidate_set_id": "bitget-perp-candidates-001",
            "candidate_set_path": "candidate_inputs/strategy_idea_candidate_set.json",
            "candidate_set_sha256": HASH_A,
            "exported_ideas": exported,
            "boundary": candidate_boundary(),
        },
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "candidate_id": candidate["idea_candidate_id"],
                    "decision": candidate["decision"],
                    "family": candidate["family"],
                },
                sort_keys=True,
            )
            for candidate in candidates
        )
        + "\n",
        encoding="utf-8",
    )
    return candidate_set_path, export_manifest_path, ledger_path


def _write_prep_watchdeck_root(root: Path, *, include_funding: bool = True) -> None:
    data = root / "data"
    snapshot_dir = root / "var/snapshots"
    data.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(data / "scanner.duckdb"))
    con.execute(
        """
        CREATE TABLE contracts (
          symbol TEXT,
          product_type TEXT,
          base_coin TEXT,
          quote_coin TEXT,
          symbol_type TEXT,
          symbol_status TEXT,
          min_trade_usdt DOUBLE,
          max_lever DOUBLE,
          is_rwa BOOLEAN,
          updated_at_ms BIGINT
        )
        """
    )
    con.execute(
        """
        INSERT INTO contracts VALUES
        ('BTCUSDT', 'USDT-FUTURES', 'BTC', 'USDT', 'perpetual', 'online',
         5, 75, false, 1781726700000)
        """
    )
    ticker_columns = (
        "run_id TEXT, symbol TEXT, ts BIGINT, last_price DOUBLE, change_24h DOUBLE, "
        "usdt_volume_24h DOUBLE, funding_rate DOUBLE, holding_amount DOUBLE"
    )
    con.execute(f"CREATE TABLE tickers_snapshot ({ticker_columns})")
    funding_value = 0.0002 if include_funding else None
    con.execute(
        "INSERT INTO tickers_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ["run-1", "BTCUSDT", 1781726700000, 100.0, 0.02, 1_000_000.0, funding_value, 10.0],
    )
    con.execute(
        """
        CREATE TABLE candles_5m (
          symbol TEXT,
          ts BIGINT,
          open DOUBLE,
          high DOUBLE,
          low DOUBLE,
          close DOUBLE,
          base_vol DOUBLE,
          quote_vol DOUBLE
        )
        """
    )
    start = datetime(2026, 6, 17, tzinfo=timezone.utc)
    rows = []
    for index in range(8):
        ts_ms = int((start + timedelta(minutes=5 * index)).timestamp() * 1000)
        close = 100.0 + index * 1.5
        rows.append(
            (
                "BTCUSDT",
                ts_ms,
                close - 1.0,
                close + 0.5,
                close - 1.5,
                close,
                10.0,
                1000.0 + index,
            )
        )
    con.executemany("INSERT INTO candles_5m VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    con.close()
    parquet_rows = [
        {
            "symbol": row[0],
            "ts": row[1],
            "open": row[2],
            "high": row[3],
            "low": row[4],
            "close": row[5],
            "base_vol": row[6],
            "quote_vol": row[7],
        }
        for row in rows
    ]
    candles_dir = data / "candles_5m/date=2026-06-17"
    candles_dir.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(parquet_rows).write_parquet(candles_dir / "candles.parquet")
    (snapshot_dir / "latest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runId": "run-1",
                "generatedAt": 1781726700000,
                "dataAsOf": 1781726700000,
                "source": {
                    "exchange": "bitget",
                    "productType": "USDT-FUTURES",
                    "dataSource": "fixture",
                    "isFallback": False,
                },
                "rows": [
                    {
                        "symbol": "BTCUSDT",
                        "ts": 1781726700000,
                        "close": "100.0",
                        "data_quality": "OK",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_source_discovery_reads_scanner_parquet_snapshot_and_records_locked_service(
    tmp_path: Path, monkeypatch
) -> None:
    prep_root = tmp_path / "prep-watchdeck"
    _write_prep_watchdeck_root(prep_root)
    real_connect = duckdb.connect

    def locked_connect(path: str, *args: Any, **kwargs: Any) -> Any:
        if str(path).endswith("watchdeck.duckdb"):
            raise duckdb.IOException("IO Error: Could not set lock on file watchdeck.duckdb")
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(duckdb, "connect", locked_connect)
    (prep_root / "var").mkdir(exist_ok=True)
    (prep_root / "var/watchdeck.duckdb").write_text("locked placeholder", encoding="utf-8")

    source = load_prep_watchdeck_source(prep_root, symbols=["BTCUSDT"])

    assert "BTCUSDT" in source.candles_by_symbol
    assert source.contracts_by_symbol["BTCUSDT"].product_type == "USDT-FUTURES"
    assert source.tickers_by_symbol["BTCUSDT"].funding_rate == 0.0002
    assert "scanner.duckdb" in {item.source_id for item in source.sources}
    assert "candles_5m_parquet" in {item.source_id for item in source.sources}
    assert "latest_snapshot_json" in {item.source_id for item in source.sources}
    assert "SOURCE_LOCKED" in source.source_statuses


def test_authoring_bridge_generates_candidate_scoped_artifacts_and_backtest_pack(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    prep_root = tmp_path / "prep-watchdeck"
    _write_prep_watchdeck_root(prep_root)
    rejected = _candidate(
        "cand-999-rejected",
        family="perp_basis_mark_index_spread",
        decision="REJECTED",
    )
    candidate_set_path, export_manifest_path, ledger_path = _write_candidate_inputs(
        tmp_path,
        [
            _candidate("cand-001-momentum", family="perp_momentum_continuation"),
            _candidate("cand-002-funding", family="perp_funding_rate_carry_filter"),
            rejected,
        ],
    )

    result = build_strategy_idea_candidate_authoring_bridge(
        candidate_set_path=candidate_set_path,
        export_manifest_path=export_manifest_path,
        ledger_path=ledger_path,
        prep_watchdeck_root=prep_root,
        out_dir=tmp_path / "bridge_out",
        replace_existing=False,
    )

    assert result.manifest.summary["status_counts"]["BRIDGED"] == 2
    for candidate_id in ["cand-001-momentum", "cand-002-funding"]:
        candidate_dir = tmp_path / "bridge_out" / candidate_id
        assert (candidate_dir / "prep_watchdeck_source_manifest.json").exists()
        assert (candidate_dir / "feature_panel.parquet").exists()
        assert (candidate_dir / "quotes.parquet").exists()
        assert (candidate_dir / "venue_cost_matrix.csv").exists()
        assert (candidate_dir / "strategy_authoring_spec.yaml").exists()
        assert (candidate_dir / "strategy_backtest_suite.yaml").exists()
        assert (candidate_dir / "strategy_authoring_bundle.yaml").exists()
        assert (candidate_dir / "backtest_pack/strategy_backtest_pack.json").exists()
        assert (
            candidate_dir / "backtest_pack/strategy_backtest_pack_validation.json"
        ).exists()
        assert load_authoring_spec(candidate_dir / "strategy_authoring_spec.yaml")
        assert load_backtest_suite_spec(candidate_dir / "strategy_backtest_suite.yaml")
        assert load_authoring_bundle_spec(candidate_dir / "strategy_authoring_bundle.yaml")
    feature = pl.read_parquet(tmp_path / "bridge_out/cand-001-momentum/feature_panel.parquet")
    assert {
        "canonical_symbol",
        "ts",
        "mark_return_2bars",
        "realized_volatility_2bars",
        "funding_rate_bps",
        "spread_bps_estimate",
    }.issubset(set(feature.columns))
    cost = pl.read_csv(tmp_path / "bridge_out/cand-001-momentum/venue_cost_matrix.csv")
    assert cost["notes"].str.contains("ESTIMATE_ONLY").all()
    assert not (tmp_path / "data/research/backtest_pack/strategy_backtest_pack.json").exists()


def test_authoring_bridge_relative_out_uses_existing_artifact_paths_and_clears_stale_blocker(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    prep_root = tmp_path / "prep-watchdeck"
    _write_prep_watchdeck_root(prep_root)
    candidate_set_path, export_manifest_path, ledger_path = _write_candidate_inputs(
        tmp_path,
        [
            _candidate("cand-relative-out", family="perp_momentum_continuation"),
            _candidate("cand-rejected", family="perp_funding_rate_carry_filter", decision="REJECTED"),
        ],
    )
    candidate_dir = tmp_path / "bridge_out/cand-relative-out"
    candidate_dir.mkdir(parents=True)
    stale_blocker = candidate_dir / "bridge_blocker.json"
    stale_blocker.write_text('{"status":"BLOCKED_BACKTEST_PACK"}\n', encoding="utf-8")

    result = build_strategy_idea_candidate_authoring_bridge(
        candidate_set_path=candidate_set_path,
        export_manifest_path=export_manifest_path,
        ledger_path=ledger_path,
        prep_watchdeck_root=prep_root,
        out_dir=Path("bridge_out"),
        replace_existing=True,
    )

    assert result.manifest.summary["status_counts"] == {"BRIDGED": 1}
    assert result.manifest.candidates[0].status == "BRIDGED"
    assert (candidate_dir / "backtest_pack/strategy_backtest_pack.json").exists()
    assert (
        candidate_dir / "backtest_pack/strategy_backtest_pack_validation.json"
    ).exists()
    spec = load_authoring_spec(candidate_dir / "strategy_authoring_spec.yaml")
    data_paths = [
        Path(spec.data.feature_panel_path),
        Path(spec.data.quote_data_path),
        Path(spec.data.cost_model_path),
    ]
    assert all(path.is_absolute() for path in data_paths)
    assert all(path.exists() for path in data_paths)
    assert not stale_blocker.exists()


def test_authoring_bridge_writes_blocker_for_unsupported_family(tmp_path: Path) -> None:
    prep_root = tmp_path / "prep-watchdeck"
    _write_prep_watchdeck_root(prep_root)
    candidate_set_path, export_manifest_path, ledger_path = _write_candidate_inputs(
        tmp_path,
        [
            _candidate("cand-unsupported", family="perp_basis_mark_index_spread"),
            _candidate("cand-rejected", family="perp_momentum_continuation", decision="REJECTED"),
        ],
    )

    result = build_strategy_idea_candidate_authoring_bridge(
        candidate_set_path=candidate_set_path,
        export_manifest_path=export_manifest_path,
        ledger_path=ledger_path,
        prep_watchdeck_root=prep_root,
        out_dir=tmp_path / "bridge_out",
        replace_existing=False,
    )

    assert result.manifest.candidates[0].status == "BLOCKED_UNSUPPORTED_FAMILY_MAPPING"
    blocker = json.loads(
        (tmp_path / "bridge_out/cand-unsupported/bridge_blocker.json").read_text(
            encoding="utf-8"
        )
    )
    assert blocker["status"] == "BLOCKED_UNSUPPORTED_FAMILY_MAPPING"
    assert not (tmp_path / "bridge_out/cand-unsupported/strategy_authoring_spec.yaml").exists()


def test_authoring_bridge_blocks_missing_symbol_data(tmp_path: Path) -> None:
    prep_root = tmp_path / "prep-watchdeck"
    _write_prep_watchdeck_root(prep_root)
    missing_symbol_candidate = _candidate(
        "cand-missing-symbol",
        family="perp_momentum_continuation",
        instruments=["ETHUSDT"],
    )
    candidate_set_path, export_manifest_path, ledger_path = _write_candidate_inputs(
        tmp_path,
        [
            missing_symbol_candidate,
            _candidate(
                "cand-rejected",
                family="perp_funding_rate_carry_filter",
                decision="REJECTED",
            ),
        ],
    )

    result = build_strategy_idea_candidate_authoring_bridge(
        candidate_set_path=candidate_set_path,
        export_manifest_path=export_manifest_path,
        ledger_path=ledger_path,
        prep_watchdeck_root=prep_root,
        out_dir=tmp_path / "bridge_out",
        replace_existing=False,
    )

    assert result.manifest.candidates[0].status == "BLOCKED_NO_SYMBOL_DATA"
    blocker = json.loads(
        (tmp_path / "bridge_out/cand-missing-symbol/bridge_blocker.json").read_text(
            encoding="utf-8"
        )
    )
    assert blocker["candidate_id"] == "cand-missing-symbol"


def test_authoring_bridge_cli_help_and_no_replace_existing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    help_result = runner.invoke(app, ["strategy-idea-candidates-authoring-bridge", "--help"])
    assert help_result.exit_code == 0
    help_stdout = normalized_stdout(help_result)
    assert "prep-watchdeck" in help_stdout
    assert "repository root" in help_stdout
    prep_root = tmp_path / "prep-watchdeck"
    _write_prep_watchdeck_root(prep_root)
    candidate_set_path, export_manifest_path, ledger_path = _write_candidate_inputs(
        tmp_path,
        [
            _candidate("cand-001-momentum", family="perp_momentum_continuation"),
            _candidate(
                "cand-rejected",
                family="perp_funding_rate_carry_filter",
                decision="REJECTED",
            ),
        ],
    )
    args = [
        "strategy-idea-candidates-authoring-bridge",
        "--candidate-set",
        str(candidate_set_path),
        "--export-manifest",
        str(export_manifest_path),
        "--ledger",
        str(ledger_path),
        "--prep-watchdeck-root",
        str(prep_root),
        "--out",
        str(tmp_path / "bridge_out"),
    ]

    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.stdout
    second = runner.invoke(app, args + ["--no-replace-existing"])
    assert second.exit_code == 2
    assert "output already exists" in second.stdout
