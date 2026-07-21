from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any


BASE_TIME = datetime(2026, 7, 16, 0, 0, tzinfo=UTC)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_pack(
    root: Path,
    *,
    missing_action: bool = False,
    notional_mismatch: bool = False,
    formula_mismatch: bool = False,
) -> Path:
    pack_dir = root / "pack"
    pack_dir.mkdir(parents=True)
    event_id = "event-1"
    outcome_id = "outcome-1"
    entry_at = BASE_TIME + timedelta(minutes=5)
    settled_at = entry_at + timedelta(minutes=60)
    outcome_path = root / "source" / "outcome.json"
    write_json(
        outcome_path,
        {
            "schema_version": "crypto_perp_outcome.v1",
            "artifact_id": "outcome-artifact-1",
            "created_at": settled_at.isoformat().replace("+00:00", "Z"),
            "producer": {"tool": "sis", "command": "fixture"},
            "source_refs": [
                {
                    "path": "fixture.csv",
                    "sha256": "0" * 64,
                    "schema_version": "fixture.v1",
                }
            ],
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "live_order_submitted": False,
            },
            "outcome_id": outcome_id,
            "event_id": event_id,
            "settled_at": settled_at.isoformat().replace("+00:00", "Z"),
            "horizons": [
                {
                    "horizon_minutes": 60,
                    "matured": True,
                    "reference_price": "100",
                    "close_price": "110",
                    "raw_return": "0.1",
                    "short_return_before_cost": "-0.1",
                    "long_return_before_cost": "0.1",
                    "mfe_long": "0.1",
                    "mae_long": "0",
                    "mfe_short": "0",
                    "mae_short": "-0.1",
                    "high_first_low_first": "AMBIGUOUS",
                    "market_adjusted_return": "0.1",
                }
            ],
            "near_miss_refs": [],
            "known_gaps": ["FIXTURE_ONLY"],
        },
    )
    signals = [
        {
            "timestamp": BASE_TIME.isoformat().replace("+00:00", "Z"),
            "entry_at": entry_at.isoformat().replace("+00:00", "Z"),
            "outcome_horizon_minutes": 60,
            "symbol": "BTCUSDT",
            "event_id": event_id,
            "outcome_id": outcome_id,
            "information_cutoff_at": BASE_TIME.isoformat().replace("+00:00", "Z"),
            "selected_action": "CONTINUATION_LONG",
            "signal_score": "3.5",
            "entry_allowed": True,
            "no_trade_reason": [],
        }
    ]
    signal_path = pack_dir / "signal_rows.jsonl"
    signal_path.write_text(json.dumps(signals[0]) + "\n", encoding="utf-8")
    before_long = "11" if formula_mismatch else "10"
    rows = [
        {
            "event_id": event_id,
            "action": "REVERSAL_SHORT",
            "before_cost_proxy_usd": "-10",
            "fee_estimate_usd": "0.08",
            "funding_estimate_usd": "0.00125",
            "slippage_estimate_usd": "0.02",
            "operator_time_cost_usd": "0",
            "cost_adjusted_cash_estimate_usd": "-10.10125",
            "stress_cash_estimate_usd": "-10.12125",
            "evidence_level": "cost_adjusted_estimate",
            "actual_cash_result_usd": None,
            "market_adjusted_return": "-0.1",
            "operator_time_minutes": "0",
            "known_gaps": ["FIXTURE_ONLY"],
            "near_miss": False,
        },
        {
            "event_id": event_id,
            "action": "CONTINUATION_LONG",
            "before_cost_proxy_usd": before_long,
            "fee_estimate_usd": "0.08",
            "funding_estimate_usd": "0.00125",
            "slippage_estimate_usd": "0.02",
            "operator_time_cost_usd": "0",
            "cost_adjusted_cash_estimate_usd": "9.89875",
            "stress_cash_estimate_usd": "9.87875",
            "evidence_level": "cost_adjusted_estimate",
            "actual_cash_result_usd": None,
            "market_adjusted_return": "0.1",
            "operator_time_minutes": "0",
            "known_gaps": ["FIXTURE_ONLY"],
            "near_miss": False,
        },
        {
            "event_id": event_id,
            "action": "NO_TRADE",
            "before_cost_proxy_usd": "0",
            "fee_estimate_usd": "0",
            "funding_estimate_usd": "0",
            "slippage_estimate_usd": "0",
            "operator_time_cost_usd": "0",
            "cost_adjusted_cash_estimate_usd": "0",
            "stress_cash_estimate_usd": "0",
            "evidence_level": "cost_adjusted_estimate",
            "actual_cash_result_usd": None,
            "market_adjusted_return": "0",
            "operator_time_minutes": "0",
            "known_gaps": ["FIXTURE_ONLY"],
            "near_miss": False,
        },
    ]
    if missing_action:
        rows.pop()
    rows_path = pack_dir / "tournament_rows_v2.json"
    write_json(
        rows_path,
        {
            "schema_version": "crypto_perp_tournament_rows.v2",
            "artifact_id": "rows-artifact-1",
            "created_at": BASE_TIME.isoformat().replace("+00:00", "Z"),
            "producer": {"tool": "sis", "command": "fixture"},
            "source_refs": [],
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "live_order_submitted": False,
            },
            "row_set_id": "row-set-1",
            "primary_metric": "cost_adjusted_cash_estimate_usd",
            "event_set": [event_id],
            "rows": rows,
            "known_gaps": ["FIXTURE_ONLY"],
            "summary": {
                "execution_windows": {
                    event_id: {
                        "entry_at": entry_at.isoformat().replace("+00:00", "Z"),
                        "settled_at": settled_at.isoformat().replace("+00:00", "Z"),
                        "horizon_minutes": 60,
                    }
                },
                "cost_assumptions": {
                    "notional_usd": "101" if notional_mismatch else "100",
                    "fee_rate": "0.0004",
                    "funding_rate": "0.0001",
                    "slippage_bps": "2",
                    "stress_slippage_multiplier": "2",
                },
            },
        },
    )
    assumptions_path = pack_dir / "execution_assumptions.json"
    write_json(
        assumptions_path,
        {
            "schema_version": "crypto_perp_backtest_execution_assumptions.v1",
            "entry_price_rule": "next_5m_open_proxy_after_signal",
            "exit_price_rule": "matured_outcome_first_horizon_close_proxy",
            "fee_rate": "0.0004",
            "slippage_bps": "2",
            "funding_rate_assumption": "0.0001",
            "max_holding_minutes": 60,
            "position_size_usd": "100",
            "zero_cost_forbidden": True,
            "paper_only": True,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
    )
    refs = {
        name: {
            "path": (pack_dir / name).as_posix(),
            "sha256": f"sha256:{sha256(pack_dir / name)}",
        }
        for name in (
            "signal_rows.jsonl",
            "tournament_rows_v2.json",
            "execution_assumptions.json",
        )
    }
    decision_path = pack_dir / "decision.json"
    write_json(
        decision_path,
        {
            "schema_version": "crypto_perp_backtest_candidate_pack.v1",
            "artifact_id": "decision-artifact-1",
            "created_at": BASE_TIME.isoformat().replace("+00:00", "Z"),
            "producer": {"tool": "sis", "command": "fixture"},
            "source_refs": [
                {
                    "path": outcome_path.as_posix(),
                    "sha256": f"sha256:{sha256(outcome_path)}",
                    "schema_version": "crypto_perp_outcome.v1",
                }
            ],
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "live_order_submitted": False,
            },
            "pack_id": "pack-1",
            "decision": "BACKTEST_CANDIDATE_HOLD",
            "reason_codes": [],
            "event_count": 1,
            "outcome_count": 1,
            "artifact_paths": {
                name: (pack_dir / name).as_posix()
                for name in (
                    "decision.json",
                    "signal_rows.jsonl",
                    "tournament_rows_v2.json",
                    "execution_assumptions.json",
                )
            },
            "summary": {"pack_component_refs": refs},
            "non_goal_flags": {},
        },
    )
    return pack_dir


def d(value: str | int) -> Decimal:
    return Decimal(str(value))
