from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.no_trade_kill_report import build_no_trade_kill_report


ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


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
        },
        "results": results,
        "paper_only": True,
        "profit_proven": False,
        "permits_live_order": False,
    }


def _report(**overrides):
    signal_rows = overrides.pop("signal_rows", _signal_rows())
    backtest = overrides.pop("backtest", _result_payload())
    stress = overrides.pop("stress", _result_payload(total="8", stress=True))
    return build_no_trade_kill_report(
        signal_rows=signal_rows,
        backtest=backtest,
        stress=stress,
        tournament_rows=overrides.pop("tournament_rows", None),
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


def test_no_trade_kill_report_cli_writes_artifacts(tmp_path: Path) -> None:
    signal_path = tmp_path / "signal_rows.jsonl"
    signal_path.write_text(
        "\n".join(json.dumps(row) for row in _signal_rows()) + "\n", encoding="utf-8"
    )
    backtest_path = tmp_path / "backtest.json"
    backtest_path.write_text(json.dumps(_result_payload()), encoding="utf-8")
    stress_path = tmp_path / "stress.json"
    stress_path.write_text(json.dumps(_result_payload(total="8", stress=True)), encoding="utf-8")
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
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert "kill_decision=HOLD_FOR_LEADERBOARD" in result.stdout
    assert (out / "no_trade_kill_report.json").exists()
    assert (out / "no_trade_kill_report.md").exists()
