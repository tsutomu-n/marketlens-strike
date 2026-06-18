from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_runtime_observation.models import RuntimeObservationSourceStage
from sis.strategy_runtime_observation.service import ingest_runtime_observation


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_runtime_observation_manifest.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _session_manifest(tmp_path: Path, *, ledger_path: Path, session_id: str = "smoke-001") -> Path:
    return _write_json(
        tmp_path / f"data/paper/observations/{session_id}/paper_observation_session_manifest.json",
        {
            "schema_version": "paper_observation_session_manifest.v1",
            "session_id": session_id,
            "created_at": "2026-06-18T12:00:00Z",
            "data_dir": (tmp_path / "data").as_posix(),
            "session_dir": (tmp_path / f"data/paper/observations/{session_id}").as_posix(),
            "observation_ledger_path": ledger_path.as_posix(),
            "paper_orders_path": (tmp_path / "data/paper/orders.parquet").as_posix(),
            "paper_fills_path": (tmp_path / "data/paper/fills.parquet").as_posix(),
            "paper_positions_path": (tmp_path / "data/paper/positions.parquet").as_posix(),
            "source_backtest_acceptance_path": "data/research/strategy_lifecycle/backtest_acceptance_decision.json",
            "source_backtest_acceptance_sha256": "sha256:" + "a" * 64,
            "source_operator_promotion_path": "data/research/ndx/operator_promotion_decision.json",
            "source_operator_promotion_sha256": "sha256:" + "b" * 64,
            "source_intent_preview_path": "data/paper/observations/smoke-001/source_artifacts/paper_intent_preview.json",
            "source_intent_preview_sha256": "sha256:" + "c" * 64,
            "thresholds": {
                "min_fills_for_pass": 1,
                "min_trading_days_for_pass": 1,
                "max_blocked_rate": 0.5,
                "max_consecutive_blocked": 3,
                "max_open_position_age_hours": 0.0,
            },
            "smoke": True,
            "external_api_used": False,
            "credentials_used": False,
            "permits_live_order": False,
            "wallet_used": False,
            "venue_write_used": False,
            "exchange_write_used": False,
        },
    )


def _ledger_rows() -> list[dict]:
    return [
        {
            "created_at": "2026-06-18T12:01:00+00:00",
            "intent_id": "intent-1",
            "candidate_id": "candidate-1",
            "venue": "bitget_demo",
            "execution_symbol": "BTCUSDT",
            "real_market_symbol": "BTCUSDT",
            "status": "paper_filled",
            "block_reasons": [],
            "quote_age_ms": 120,
            "spread_bps": 8.5,
            "notional_usd": 100.0,
            "quantity": 1.0,
            "order_id": "order-1",
            "fill_id": "fill-1",
            "live_order_submitted": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "venue_write_used": False,
        },
        {
            "created_at": "2026-06-18T12:02:00+00:00",
            "intent_id": "intent-2",
            "candidate_id": "candidate-1",
            "venue": "bitget_demo",
            "execution_symbol": "BTCUSDT",
            "real_market_symbol": "BTCUSDT",
            "status": "blocked",
            "block_reasons": ["LATEST_QUOTE_MISSING"],
            "quote_age_ms": None,
            "spread_bps": None,
            "notional_usd": 100.0,
            "quantity": 1.0,
            "order_id": None,
            "fill_id": None,
            "live_order_submitted": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "venue_write_used": False,
        },
    ]


def test_runtime_observation_ingest_writes_schema_valid_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    ledger_path = _write_jsonl(
        tmp_path / "data/paper/observations/smoke-001/paper_observation_ledger.jsonl",
        _ledger_rows(),
    )
    session_manifest = _session_manifest(tmp_path, ledger_path=ledger_path)

    result = ingest_runtime_observation(
        strategy_id="ndx-breakout-001",
        session_manifest_path=session_manifest,
        out_dir=tmp_path / "data/runtime_observations/ndx-breakout-001/smoke-001",
        source_stage=RuntimeObservationSourceStage.PAPER_SMOKE,
    )

    assert result.manifest.ingest_status.value == "INGESTED"
    assert result.manifest.summary.ledger_entry_count == 2
    assert result.manifest.summary.paper_fill_count == 1
    assert result.manifest.summary.blocked_count == 1
    assert result.manifest.summary.no_fill_count == 1
    assert result.manifest.summary.block_reasons == {"LATEST_QUOTE_MISSING": 1}
    assert result.manifest.summary.max_observed_spread_bps == 8.5
    assert result.manifest.summary.pnl_available is False
    assert result.manifest.summary.pnl_unavailable_reason is not None
    assert result.manifest.summary.order_lifecycle_counts == {"blocked": 1, "paper_filled": 1}
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["summary"]["pnl_available"] is False
    assert result.ledger_path.read_text(encoding="utf-8").count("\n") == 2
    report = result.report_path.read_text(encoding="utf-8")
    assert "Drift Review" in report
    assert "pnl_available" in report
    assert "Order Lifecycle" in report


def test_runtime_observation_ingest_summarizes_pnl_cost_and_lifecycle(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rows = _ledger_rows()
    rows[0].update(
        {
            "realized_pnl_usd": 12.5,
            "gross_pnl_usd": 13.0,
            "fee_usd": 0.5,
            "slippage_usd": -0.2,
            "slippage_bps": -2.0,
            "fill_price_drift_bps": 1.25,
            "filled_notional_usd": 100.0,
            "order_status": "filled",
        }
    )
    rows[1].update({"order_status": "blocked"})
    ledger_path = _write_jsonl(
        tmp_path / "data/paper/observations/normal-001/paper_observation_ledger.jsonl",
        rows,
    )
    session_manifest = _session_manifest(tmp_path, ledger_path=ledger_path, session_id="normal-001")

    result = ingest_runtime_observation(
        strategy_id="ndx-breakout-001",
        session_manifest_path=session_manifest,
        out_dir=tmp_path / "data/runtime_observations/ndx-breakout-001/normal-001",
        source_stage=RuntimeObservationSourceStage.NORMAL_PAPER_OBSERVATION,
    )

    summary = result.manifest.summary
    assert summary.pnl_available is True
    assert summary.pnl_unavailable_reason is None
    assert summary.realized_pnl_usd_total == 12.5
    assert summary.gross_pnl_usd_total == 13.0
    assert summary.fee_usd_total == 0.5
    assert summary.slippage_usd_total == -0.2
    assert summary.avg_slippage_bps == -2.0
    assert summary.max_abs_slippage_bps == 2.0
    assert summary.avg_fill_price_drift_bps == 1.25
    assert summary.max_abs_fill_price_drift_bps == 1.25
    assert summary.filled_notional_usd_total == 100.0
    assert summary.order_lifecycle_counts == {"blocked": 1, "filled": 1}

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["summary"]["realized_pnl_usd_total"] == 12.5


def test_runtime_observation_ingest_empty_ledger(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    ledger_path = _write_jsonl(
        tmp_path / "data/paper/observations/smoke-001/paper_observation_ledger.jsonl", []
    )
    session_manifest = _session_manifest(tmp_path, ledger_path=ledger_path)

    result = ingest_runtime_observation(
        strategy_id="ndx-breakout-001",
        session_manifest_path=session_manifest,
        out_dir=tmp_path / "data/runtime_observations/ndx-breakout-001/smoke-001",
        source_stage=RuntimeObservationSourceStage.PAPER_SMOKE,
    )

    assert result.manifest.ingest_status.value == "EMPTY_LEDGER"
    assert result.manifest.summary.ledger_entry_count == 0


def test_runtime_observation_ingest_detects_boundary_violation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rows = _ledger_rows()
    rows[0]["exchange_write_used"] = True
    ledger_path = _write_jsonl(
        tmp_path / "data/paper/observations/smoke-001/paper_observation_ledger.jsonl", rows
    )
    session_manifest = _session_manifest(tmp_path, ledger_path=ledger_path)

    result = ingest_runtime_observation(
        strategy_id="ndx-breakout-001",
        session_manifest_path=session_manifest,
        out_dir=tmp_path / "data/runtime_observations/ndx-breakout-001/smoke-001",
        source_stage=RuntimeObservationSourceStage.PAPER_SMOKE,
    )

    assert result.manifest.ingest_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert result.manifest.includes_exchange_write is False
