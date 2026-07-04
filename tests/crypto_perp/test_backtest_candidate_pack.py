from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.backtest_candidate_pack import (
    BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES,
    build_crypto_perp_backtest_candidate_pack,
)
from sis.crypto_perp.source_availability import build_source_availability
from .test_profit_readiness_local_automation import _event, _outcome, _schema, _write_json


runner = CliRunner()


def _write_ready_inputs(tmp_path: Path) -> Path:
    event = _event()
    outcome = _outcome(event.event_id)
    _write_json(tmp_path / "event.json", event)
    _write_json(tmp_path / "outcome.json", outcome)
    source = build_source_availability(
        event=event,
        created_at="2026-06-21T07:00:00Z",
        available_sources={"bars": True, "ticker": True, "funding": True, "outcome": True},
        row_counts={"bars": 20, "ticker": 1, "funding": 1, "outcome": 1},
        source_metadata={
            "ticker": {
                "coverage_class": "snapshot",
                "coverage_end_ms": int(event.information_cutoff_at.timestamp() * 1000),
                "exchange": "bitget",
                "market_type": "linear_perp",
                "symbols": ["BTCUSDT"],
            }
        },
    )
    _write_json(tmp_path / "source_availability.json", source)
    return tmp_path


def test_backtest_candidate_pack_writes_required_artifacts_and_hold_decision(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    out_dir = tmp_path / "pack"

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=out_dir,
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
        fee_rate=Decimal("0.0006"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )

    assert set(result.paths) == set(BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES)
    for path in result.paths.values():
        assert path.exists()
    assert result.decision.decision == "BACKTEST_CANDIDATE_HOLD"
    assert result.decision.non_goal_flags["profit_proven"] is False
    assert result.decision.boundary.permits_live_order is False

    signal_rows = [
        json.loads(line)
        for line in (out_dir / "signal_rows.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert signal_rows[0]["selected_action"] == "CONTINUATION_LONG"
    assert signal_rows[0]["entry_allowed"] is True

    decision_payload = json.loads((out_dir / "decision.json").read_text(encoding="utf-8"))
    schema = _schema("crypto_perp_backtest_candidate_pack.v1.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(decision_payload)


def test_backtest_candidate_pack_collects_more_data_when_sources_are_missing(
    tmp_path: Path,
) -> None:
    event = _event()
    _write_json(tmp_path / "event.json", event)
    _write_json(tmp_path / "outcome.json", _outcome(event.event_id))

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=tmp_path,
        out_dir=tmp_path / "pack",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    assert result.decision.decision == "BACKTEST_COLLECT_MORE_DATA"
    assert "CRITICAL_SIGNAL_SOURCE_MISSING" in result.decision.reason_codes
    assert "SELECTED_ACTION_UNKNOWN_DUE_TO_MISSING_SOURCE" in result.decision.reason_codes


def test_backtest_candidate_pack_rejects_zero_cost_assumptions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fee_rate must be positive"):
        build_crypto_perp_backtest_candidate_pack(
            data_dir=tmp_path,
            out_dir=tmp_path / "pack",
            created_at="2026-06-21T08:00:00Z",
            notional_usd=Decimal("100"),
            fee_rate=Decimal("0"),
        )
    with pytest.raises(ValueError, match="slippage_bps must be positive"):
        build_crypto_perp_backtest_candidate_pack(
            data_dir=tmp_path,
            out_dir=tmp_path / "pack",
            created_at="2026-06-21T08:00:00Z",
            notional_usd=Decimal("100"),
            slippage_bps=Decimal("0"),
        )


def test_backtest_candidate_pack_cli_generates_pack(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    out_dir = tmp_path / "cli-pack"

    result = runner.invoke(
        app,
        [
            "crypto-perp-backtest-candidate-pack",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--min-events",
            "1",
            "--min-events-for-stability",
            "1",
            "--fold-count",
            "2",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "profit_proven=false" in result.stdout
    assert "decision=BACKTEST_CANDIDATE_HOLD" in result.stdout
    assert (out_dir / "decision.json").exists()
