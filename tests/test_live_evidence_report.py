import json
from datetime import datetime, timezone
from pathlib import Path

from sis.reports.live_evidence_report import (
    build_live_evidence_report_data,
    default_followup_output_path,
    default_html_output_path,
    default_markdown_output_path,
    parse_run_status,
    render_live_evidence_followup,
    render_live_evidence_html,
    render_live_evidence_report,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_json_pretty(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_parse_run_status_completed_and_failed(tmp_path) -> None:
    completed = tmp_path / "completed.log"
    completed.write_text("[2026-05-22T14:08:00Z] Live evidence refresh completed\n", encoding="utf-8")
    assert parse_run_status(completed) == "completed"

    failed = tmp_path / "failed.log"
    failed.write_text("ERROR:\nInsufficient gTrade pricing rows.\n", encoding="utf-8")
    assert parse_run_status(failed) == "failed"


def test_build_and_render_live_evidence_report(tmp_path) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    data_dir = tmp_path / "data"
    log_path = tmp_path / "logs/live_evidence/live_evidence_20260522_2308.log"
    output_path = tmp_path / "docs/live_evidence_reports/report.md"

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(
            [
                "[2026-05-22T14:08:00Z] Scheduled live evidence run starting",
                "[2026-05-22T16:08:30Z] Live evidence refresh completed",
            ]
        ),
        encoding="utf-8",
    )

    _write_json(
        data_dir / f"raw/quotes/gtrade/{today}.jsonl",
        {
            "ts_client": "2026-05-22T14:08:01+00:00",
            "venue": "gtrade",
            "canonical_symbol": "SPY",
            "venue_symbol": "SPY/USD",
            "pair_index": 86,
            "mark_price": 100.0,
            "index_price": 100.0,
            "market_status": "open",
            "is_tradable": True,
            "source": "test",
            "raw_payload_sha256": "abc",
            "spread_bps": 2.0,
        },
    )
    quote_path = data_dir / f"raw/quotes/gtrade/{today}.jsonl"
    quote_path.write_text(
        '{"ts_client":"2026-05-22T14:08:01+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.0,"index_price":100.0,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"abc","spread_bps":2.0}\n',
        encoding="utf-8",
    )
    (data_dir / f"raw/sidecar/gtrade/{today}.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (data_dir / f"raw/sidecar/gtrade/{today}.jsonl").write_text('{"ok":true}\n', encoding="utf-8")
    (data_dir / f"raw/sidecar/gtrade-pricing/{today}.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (data_dir / f"raw/sidecar/gtrade-pricing/{today}.jsonl").write_text('{"ok":true}\n', encoding="utf-8")
    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (data_dir / "normalized/quotes.parquet").write_bytes(b"PAR1")
    _write_json(
        data_dir / "registry/gtrade_instrument_registry.json",
        [
            {
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "asset_class": "index",
                "pair_index": 86,
                "api_readable": True,
                "api_orderable": True,
                "active": True,
                "notes": [],
            }
        ],
    )
    _write_json(
        data_dir / "registry/ostium_instrument_registry.json",
        [
            {
                "venue": "ostium",
                "canonical_symbol": "SPX_EQUIV",
                "venue_symbol": "SPX/USD",
                "asset_class": "index",
                "api_readable": True,
                "api_orderable": True,
                "active": True,
                "opening_fee_bps": 3.0,
                "max_open_interest": "1",
                "rollover_fee_per_block": "1",
                "max_leverage": 100,
                "notes": [],
            }
        ],
    )
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "venue,symbol,asset_class,open_fee_bps,close_fee_bps,spread_p50_bps,spread_p90_bps,spread_p99_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps,stale_rate,tradable_rate,notes\n"
        "gtrade,SPY,index,5,5,2,2,2,0,0,0,0.01,1.0,test note\n",
        encoding="utf-8",
    )
    _write_json(data_dir / "research/backtest_metrics.json", [{"venue": "gtrade", "canonical_symbol": "SPY", "trade_count": 1}])
    (data_dir / "research/go_no_go_report.md").write_text("# Go/No-Go Report\n", encoding="utf-8")
    _write_json_pretty(
        data_dir / "evidence/evidence_card_20260522_230800.json",
        {
            "run_id": "20260522_230800",
            "created_at": "2026-05-22T16:08:30+00:00",
            "scope": {
                "venues": ["gtrade"],
                "symbols": ["SPY"],
                "timeframes": ["4h"],
                "scalping_policy": "prohibited_by_default",
            },
            "data": {},
            "decision": "GO",
            "venue_decisions": [{"venue": "gtrade", "decision": "GO", "main_blocker": None}],
            "criteria": [],
            "blockers": [],
            "next_actions": ["none"],
        },
    )

    data = build_live_evidence_report_data(
        data_dir=data_dir,
        log_path=log_path,
        output_path=output_path,
        status="completed",
    )
    text = render_live_evidence_report(data)
    html_text = render_live_evidence_html(data)
    followup_text = render_live_evidence_followup(data)

    assert data.status == "completed"
    assert data.decision == "GO"
    assert "## GTrade Diagnostics" in text
    assert "| SPY | 1 | 1 | 1.0000 |" in text
    assert "## Backtest Snapshot" in text
    assert "## Log Tail" in text
    assert "<!DOCTYPE html>" in html_text
    assert "<h2>GTrade Diagnostics</h2>" in html_text
    assert "Live Evidence Detailed Report" in html_text
    assert "## Immediate Next Work" in followup_text
    assert "- none" in followup_text


def test_default_output_paths_use_log_stamp() -> None:
    md_path = default_markdown_output_path(Path("logs/live_evidence/live_evidence_20260522_2308.log"))
    html_path = default_html_output_path(Path("logs/live_evidence/live_evidence_20260522_2308.log"))
    followup_path = default_followup_output_path(Path("logs/live_evidence/live_evidence_20260522_2308.log"))
    assert md_path == Path("docs/live_evidence_reports/live_evidence_report_20260522_2308.md")
    assert html_path == Path("docs/live_evidence_reports/live_evidence_report_20260522_2308.html")
    assert followup_path == Path("docs/live_evidence_reports/live_evidence_followup_20260522_2308.md")
