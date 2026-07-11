from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path

from click import Group
from jsonschema import Draft202012Validator
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.no_trade_kill_report import build_no_trade_kill_report
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows
from .test_profit_readiness_local_automation import _outcome


ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _kill_report_option_is_required(name: str) -> bool:
    root_command = get_command(app)
    assert isinstance(root_command, Group)
    command = root_command.commands["crypto-perp-no-trade-kill-report"]
    option = next(param for param in command.params if param.name == name)
    return option.required


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _signal_rows(event_count: int = 30, trade_count: int = 10) -> list[dict]:
    rows = []
    for index in range(event_count):
        action = "CONTINUATION_LONG" if index < trade_count else "NO_TRADE"
        rows.append(
            {
                "timestamp": "2026-07-07T00:00:00Z",
                "symbol": "BTCUSDT",
                "event_id": f"event-{index:02d}",
                "outcome_id": f"outcome-{index:02d}",
                "information_cutoff_at": "2026-07-07T00:00:00Z",
                "selected_action": action,
                "entry_allowed": action != "NO_TRADE",
            }
        )
    return rows


def _result_payload(
    *,
    event_count: int = 30,
    trade_count: int = 10,
    values: list[str] | None = None,
    total: str | None = None,
    stress: bool = False,
    beats_no_trade: bool = True,
    unknown_count: int = 0,
) -> dict:
    values = values or ["1"] * trade_count + ["0"] * (event_count - trade_count)
    if total is None:
        total = str(sum(float(value) for value in values))
    results = []
    for index in range(event_count):
        simulated = index < trade_count
        selected = (
            "UNKNOWN"
            if index < unknown_count
            else ("CONTINUATION_LONG" if simulated else "NO_TRADE")
        )
        results.append(
            {
                "event_id": f"event-{index:02d}",
                "outcome_id": f"outcome-{index:02d}",
                "selected_action": selected,
                "fill_status": "blocked_unknown_signal"
                if selected == "UNKNOWN"
                else ("simulated" if simulated else "no_trade_baseline"),
                "result_usd": values[index],
                "metric": "stress_cash_estimate_usd"
                if stress
                else "cost_adjusted_cash_estimate_usd",
            }
        )
    return {
        "schema_version": "crypto_perp_backtest_stress_result.v1"
        if stress
        else "crypto_perp_backtest_result.v1",
        "status": "complete",
        "summary": {
            "event_count": event_count,
            "executed_trade_count": trade_count,
            "no_trade_count": event_count - trade_count,
            "unknown_count": unknown_count,
            "blocked_missing_action_row_count": 0,
            "total_result_usd": total,
            "average_result_usd": "0.1",
            "win_rate": "1",
            "max_drawdown_usd": "0",
            "beats_no_trade": beats_no_trade,
            "profit_robustness": {"market_episode_totals_usd": values[:trade_count]},
        },
        "results": results,
        "paper_only": True,
        "profit_proven": False,
        "permits_live_order": False,
    }


def _tournament_summary_payload(
    *, leader_action: str = "CONTINUATION_LONG", overlap_first: int = 0
) -> dict:
    base = datetime(2026, 7, 7, tzinfo=timezone.utc)
    windows = {}
    for index in range(30):
        entry = base if index < overlap_first else base + timedelta(hours=2 * index)
        windows[f"event-{index:02d}"] = {
            "entry_at": entry.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "settled_at": (entry + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "horizon_minutes": 60,
        }
    return {"summary": {"leader_action": leader_action, "execution_windows": windows}}


def _public_gate_payload() -> dict:
    return {
        "schema_version": "crypto_perp_no_cash_backtest_gate.v1",
        "artifact_id": "gate-artifact",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": {"tool": "sis", "command": "crypto-perp-no-cash-backtest-gate"},
        "source_refs": [],
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
        "gate_decision": "NO_CASH_BACKTEST_HOLD",
        "reason_codes": [],
        "blockers": [],
        "known_gaps": [],
        "thresholds": {},
        "summary": {},
        "input_artifacts": {},
        "permits_paper_order": False,
        "paper_permission_granted": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _report(**overrides):
    signal_rows = overrides.pop("signal_rows", _signal_rows())
    backtest = overrides.pop("backtest", _result_payload())
    stress = overrides.pop("stress", _result_payload(total="8", stress=True))
    gate = overrides.pop(
        "gate",
        {
            "gate_decision": "NO_CASH_BACKTEST_HOLD",
            "reason_codes": ["NO_CASH_BACKTEST_GATE_HOLD_FOR_HUMAN_REVIEW"],
            "blockers": [],
        },
    )
    return build_no_trade_kill_report(
        signal_rows=signal_rows,
        backtest=backtest,
        stress=stress,
        gate=gate,
        tournament_rows=overrides.pop("tournament_rows", _tournament_summary_payload()),
        created_at="2026-07-09T00:00:00Z",
        input_artifacts={
            "signal_rows": "signal_rows.jsonl",
            "backtest": "backtest.json",
            "stress": "stress.json",
        },
        source_refs=[],
    )


def test_clean_hold_for_leaderboard_schema_valid() -> None:
    report = _report()

    assert report["kill_decision"] == "HOLD_FOR_LEADERBOARD"
    assert report["permits_paper_order"] is False
    Draft202012Validator(_schema("crypto_perp_no_trade_kill_report.v1.schema.json")).validate(
        report
    )


def test_upstream_reject_kills_before_local_metrics() -> None:
    report = _report(
        gate={
            "gate_decision": "NO_CASH_BACKTEST_REJECT",
            "reason_codes": ["BIAS_GUARD_BLOCKED"],
            "blockers": [{"code": "BIAS_GUARD_BLOCKED"}],
        }
    )

    assert report["kill_decision"] == "KILL_UPSTREAM_GATE_REJECTED"
    assert report["upstream_gate_decision"] == "NO_CASH_BACKTEST_REJECT"
    assert "BIAS_GUARD_BLOCKED" in report["upstream_reason_codes"]


@pytest.mark.parametrize(
    ("gate_decision", "expected"),
    [
        ("NO_CASH_BACKTEST_COLLECT_MORE_DATA", "COLLECT_MORE_DATA"),
        ("NO_CASH_BACKTEST_REVISE", "REVISE_SOURCE_OR_SIGNAL"),
        ("UNKNOWN", "COLLECT_MORE_DATA"),
    ],
)
def test_upstream_non_hold_never_reaches_leaderboard_hold(
    gate_decision: str, expected: str
) -> None:
    report = _report(gate={"gate_decision": gate_decision, "reason_codes": [], "blockers": []})

    assert report["kill_decision"] == expected


def test_no_trade_leader_kills() -> None:
    report = _report(tournament_rows={"summary": {"leader_action": "NO_TRADE"}})

    assert report["kill_decision"] == "KILL_NO_TRADE_LEADER"
    assert "TOURNAMENT_LEADER_NO_TRADE" in report["reason_codes"]


def test_after_cost_negative_kills() -> None:
    report = _report(backtest=_result_payload(total="0", beats_no_trade=False))

    assert report["kill_decision"] == "KILL_AFTER_COST_NEGATIVE"


def test_stress_negative_kills() -> None:
    report = _report(stress=_result_payload(total="0", stress=True))

    assert report["kill_decision"] == "KILL_STRESS_NEGATIVE"


def test_unknown_rows_revise() -> None:
    signal_rows = _signal_rows()
    signal_rows[0]["selected_action"] = "UNKNOWN"
    report = _report(
        signal_rows=signal_rows,
        backtest=_result_payload(unknown_count=1),
    )

    assert report["kill_decision"] == "REVISE_SOURCE_OR_SIGNAL"


def test_insufficient_sample_collects_more_data() -> None:
    report = _report(
        signal_rows=_signal_rows(event_count=20, trade_count=5),
        backtest=_result_payload(event_count=20, trade_count=5),
        stress=_result_payload(event_count=20, trade_count=5, total="4", stress=True),
    )

    assert report["kill_decision"] == "COLLECT_MORE_DATA"


def test_high_loss_concentration_kills() -> None:
    values = ["-6", "2", "2", "2", "2", "2", "2", "2", "1", "1"] + ["0"] * 20
    report = _report(backtest=_result_payload(values=values, total="10"))

    assert report["kill_decision"] == "KILL_LOSS_CONCENTRATION"


def test_high_profit_concentration_revises() -> None:
    values = ["7", "1", "1", "1", "0.1", "0.1", "0.1", "0.1", "0.1", "0.1"] + ["0"] * 20
    report = _report(backtest=_result_payload(values=values, total="10.6"))

    assert report["kill_decision"] == "REVISE_SOURCE_OR_SIGNAL"
    assert "PROFIT_CONCENTRATION_HIGH" in report["reason_codes"]
    assert report["paper_permission_granted"] is False


def test_no_trade_kill_report_cli_requires_gate(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "crypto-perp-no-trade-kill-report",
            "--signal-rows",
            str(tmp_path / "signal_rows.jsonl"),
            "--backtest",
            str(tmp_path / "backtest.json"),
            "--stress",
            str(tmp_path / "stress.json"),
        ],
    )

    assert result.exit_code == 2
    assert _kill_report_option_is_required("gate") is True


@pytest.mark.parametrize(
    "gate_payload",
    [
        {},
        {"gate_decision": "UNKNOWN", "reason_codes": [], "blockers": []},
        {"gate_decision": 42, "reason_codes": [], "blockers": []},
        {"gate_decision": "NO_CASH_BACKTEST_HOLD", "reason_codes": "bad", "blockers": []},
        {"gate_decision": "NO_CASH_BACKTEST_HOLD", "reason_codes": [], "blockers": {}},
        {
            "schema_version": "wrong.v1",
            "gate_decision": "NO_CASH_BACKTEST_HOLD",
            "reason_codes": [],
            "blockers": [],
        },
    ],
)
def test_no_trade_kill_report_cli_rejects_missing_unknown_or_invalid_gate(
    tmp_path: Path,
    gate_payload: dict,
) -> None:
    signal_path = tmp_path / "signal_rows.jsonl"
    signal_path.write_text(
        "\n".join(json.dumps(row) for row in _signal_rows()) + "\n", encoding="utf-8"
    )
    backtest_path = tmp_path / "backtest.json"
    backtest_path.write_text(json.dumps(_result_payload()), encoding="utf-8")
    stress_path = tmp_path / "stress.json"
    stress_path.write_text(json.dumps(_result_payload(total="8", stress=True)), encoding="utf-8")
    gate_path = tmp_path / "gate.json"
    gate_path.write_text(json.dumps(gate_payload), encoding="utf-8")
    out = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "crypto-perp-no-trade-kill-report",
            "--signal-rows",
            str(signal_path),
            "--backtest",
            str(backtest_path),
            "--stress",
            str(stress_path),
            "--gate",
            str(gate_path),
            "--tournament-rows",
            str(tmp_path / "rows-not-needed-because-gate-is-invalid.json"),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 2
    assert "error=gate" in result.stdout
    assert not (out / "no_trade_kill_report.json").exists()


def test_no_trade_kill_report_cli_writes_artifacts(tmp_path: Path) -> None:
    signal_path = tmp_path / "signal_rows.jsonl"
    signal_path.write_text(
        "\n".join(json.dumps(row) for row in _signal_rows()) + "\n", encoding="utf-8"
    )
    backtest_path = tmp_path / "backtest.json"
    backtest_path.write_text(json.dumps(_result_payload()), encoding="utf-8")
    stress_path = tmp_path / "stress.json"
    stress_path.write_text(json.dumps(_result_payload(total="8", stress=True)), encoding="utf-8")
    gate_path = tmp_path / "gate.json"
    gate_path.write_text(json.dumps(_public_gate_payload()), encoding="utf-8")
    tournament_rows_path = tmp_path / "tournament_rows.json"
    tournament_rows = build_cost_aware_tournament_rows(
        outcomes=[_outcome(f"event-{index:02d}") for index in range(10)],
        created_at="2026-07-09T00:00:00Z",
        notional_usd=Decimal("100"),
    )
    backtest_payload = json.loads(backtest_path.read_text(encoding="utf-8"))
    backtest_payload["summary"]["profit_robustness"]["market_episode_totals_usd"] = ["10"]
    backtest_path.write_text(json.dumps(backtest_payload), encoding="utf-8")
    tournament_rows_path.write_text(
        json.dumps(tournament_rows.model_dump(mode="json")), encoding="utf-8"
    )
    out = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "crypto-perp-no-trade-kill-report",
            "--signal-rows",
            str(signal_path),
            "--backtest",
            str(backtest_path),
            "--stress",
            str(stress_path),
            "--gate",
            str(gate_path),
            "--tournament-rows",
            str(tournament_rows_path),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert "kill_decision=REVISE_SOURCE_OR_SIGNAL" in result.stdout
    assert (out / "no_trade_kill_report.json").exists()
    assert (out / "no_trade_kill_report.md").exists()


def test_no_trade_kill_report_cli_requires_tournament_rows(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "crypto-perp-no-trade-kill-report",
            "--signal-rows",
            str(tmp_path / "signal_rows.jsonl"),
            "--backtest",
            str(tmp_path / "backtest.json"),
            "--stress",
            str(tmp_path / "stress.json"),
            "--gate",
            str(tmp_path / "gate.json"),
        ],
    )

    assert result.exit_code == 2
    assert _kill_report_option_is_required("tournament_rows") is True


def test_missing_episode_concentration_never_holds() -> None:
    backtest = _result_payload()
    backtest["summary"]["profit_robustness"] = {}

    report = _report(backtest=backtest)

    assert report["kill_decision"] == "COLLECT_MORE_DATA"
    assert "EPISODE_PROFIT_CONCENTRATION_NOT_ESTIMABLE" in report["reason_codes"]


def test_episode_profit_concentration_revises_even_when_trade_rows_look_diversified() -> None:
    backtest = _result_payload(values=["1"] * 10 + ["0"] * 20)
    backtest["summary"]["profit_robustness"] = {"market_episode_totals_usd": ["8", "1", "1"]}

    report = _report(
        backtest=backtest,
        tournament_rows=_tournament_summary_payload(overlap_first=8),
    )

    assert report["largest_win_concentration"] == "0.1"
    assert report["episode_largest_win_concentration"] == "0.8"
    assert report["kill_decision"] == "REVISE_SOURCE_OR_SIGNAL"
    assert "EPISODE_PROFIT_CONCENTRATION_HIGH" in report["reason_codes"]


def test_forged_reported_episode_totals_never_hold() -> None:
    backtest = _result_payload(values=["1"] * 10 + ["0"] * 20)
    backtest["summary"]["profit_robustness"] = {"market_episode_totals_usd": ["1"] * 10}

    report = _report(
        backtest=backtest,
        tournament_rows=_tournament_summary_payload(overlap_first=8),
    )

    assert report["episode_concentration_estimated"] is False
    assert report["kill_decision"] == "COLLECT_MORE_DATA"
    assert "EPISODE_PROFIT_CONCENTRATION_NOT_ESTIMABLE" in report["reason_codes"]
