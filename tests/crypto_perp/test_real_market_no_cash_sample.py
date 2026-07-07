from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app


runner = CliRunner()


def _write_public_candle_csv(path: Path, *, row_count: int = 60) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    base = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
    lines = ["ts,available_at,symbol,open,high,low,close,base_vol,quote_vol"]
    price = 60000.0
    for index in range(row_count):
        ts = base + timedelta(minutes=5 * index)
        drift = ((index % 9) - 4) * 2.5
        open_price = price
        close = price + drift
        high = max(open_price, close) + 7.5
        low = min(open_price, close) - 7.5
        price = close
        lines.append(
            f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')},{ts.strftime('%Y-%m-%dT%H:%M:%SZ')},"
            f"BTCUSDT,{open_price:.1f},{high:.1f},{low:.1f},{close:.1f},10,{close * 10:.1f}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_real_market_no_cash_sample_uses_public_candles_without_fixture_marker(
    tmp_path: Path,
) -> None:
    input_csv = _write_public_candle_csv(tmp_path / "BTCUSDT_5m_input.csv")
    data_dir = tmp_path / "real_market_no_cash"

    sample = runner.invoke(
        app,
        [
            "crypto-perp-real-market-no-cash-sample",
            "--input-csv",
            str(input_csv),
            "--out",
            str(data_dir),
        ],
    )

    assert sample.exit_code == 0, sample.stdout
    assert "network_attempted=false" in sample.stdout
    assert "credentialed_exchange_api_used=false" in sample.stdout
    assert "exchange_write_used=false" in sample.stdout
    assert "fixture_only=false" in sample.stdout
    assert "real_market_public_source_used=true" in sample.stdout
    assert "paper_permission_granted=false" in sample.stdout
    assert "event_count=30" in sample.stdout
    manifest = json.loads((data_dir / "selection_manifest.json").read_text(encoding="utf-8"))
    assert manifest["non_goal_flags"]["real_market_public_source_used"] is True
    assert manifest["non_goal_flags"]["fixture_only"] is False
    assert "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE" not in json.dumps(manifest)
    assert manifest["selection_policy"] == (
        "time_evenly_spaced_before_outcome; no outcome-favorable filtering"
    )

    pack_out = tmp_path / "pack"
    pack = runner.invoke(
        app,
        [
            "crypto-perp-backtest-candidate-pack",
            "--data-dir",
            str(data_dir),
            "--out",
            str(pack_out),
        ],
    )

    assert pack.exit_code == 0, pack.stdout
    assert "decision=BACKTEST_COLLECT_MORE_DATA" in pack.stdout
    decision = json.loads((pack_out / "decision.json").read_text(encoding="utf-8"))
    assert decision["event_count"] == 30
    assert decision["outcome_count"] == 30
    assert decision["summary"]["pbo_status"] == "ESTIMATED"
    assert decision["summary"]["rolling_stability"]["event_count"] == 30
    evidence = decision["evidence_grade_summary"]
    assert evidence["critical_missing_count"] > 0
    assert "TICKER_SOURCE_MISSING_BEFORE_CUTOFF" in evidence["known_limits"]
    assert "FUNDING_SOURCE_MISSING" in evidence["known_limits"]
    assert "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE" not in json.dumps(decision)

    gate_out = tmp_path / "gate"
    gate = runner.invoke(
        app,
        [
            "crypto-perp-no-cash-backtest-gate",
            "--decision",
            str(pack_out / "decision.json"),
            "--data-availability",
            str(pack_out / "data_availability_ledger.json"),
            "--backtest",
            str(pack_out / "backtest_result.json"),
            "--stress",
            str(pack_out / "stress_result.json"),
            "--rolling-stability",
            str(pack_out / "rolling_stability_result.json"),
            "--out",
            str(gate_out),
        ],
    )

    assert gate.exit_code == 0, gate.stdout
    artifact = json.loads((gate_out / "no_cash_backtest_gate.json").read_text(encoding="utf-8"))
    assert artifact["gate_decision"] == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    blocker_codes = {blocker["code"] for blocker in artifact["blockers"]}
    assert "CRITICAL_SIGNAL_SOURCE_MISSING" in blocker_codes
    assert "CRITICAL_SIGNAL_SOURCE_MISSING_TICKER" in blocker_codes
    assert "CRITICAL_SIGNAL_SOURCE_MISSING_FUNDING" in blocker_codes
    source_blockers = {blocker["source_type"] for blocker in artifact["blockers"]}
    assert {"ticker", "funding"}.issubset(source_blockers)
    assert "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE" not in json.dumps(artifact)
    assert artifact["summary"]["paper_permission_granted"] is False
    assert artifact["summary"]["actual_cash_used"] is False
