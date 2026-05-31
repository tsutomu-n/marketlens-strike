import json
from pathlib import Path

from sis.validation.artifacts import validate_artifacts


def _write_registry(path, venue: str) -> None:
    payload = [
        {
            "venue": venue,
            "canonical_symbol": "SPY",
            "venue_symbol": "SPY/USD",
            "asset_class": "index",
            "pair_index": 86,
            "api_readable": True,
            "api_orderable": True,
            "active": True,
            "notes": [],
        }
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_quote(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD",'
        '"pair_index":86,"mark_price":100.0,"index_price":100.0,"market_status":"open","is_tradable":true,'
        '"source":"test","raw_payload_sha256":"abc"}\n',
        encoding="utf-8",
    )


def _write_backtest_metrics(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '[{"timeframe":"4h","trade_count":10,"avg_trade_return":0.1}]', encoding="utf-8"
    )


def _write_evidence_card(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_id": "20260522_000000",
                "created_at": "2026-05-22T00:00:00+00:00",
                "scope": {
                    "venues": ["gtrade"],
                    "symbols": ["SPY"],
                    "timeframes": ["4h"],
                    "scalping_policy": "prohibited_by_default",
                },
                "data": {},
                "decision": "GO",
                "criteria": [],
                "blockers": [],
                "next_actions": [],
            }
        ),
        encoding="utf-8",
    )


def _write_execution_summaries(root: Path) -> None:
    payloads = {
        "execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        "execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        "execution_venue_diagnostics_summary.json": '{"overall_status":"ok"}',
        "execution_gap_history_summary.json": '{"entry_count":1,"latest_status":"ok"}',
        "execution_state_comparison_history_summary.json": '{"entry_count":1,"mismatching_count":0}',
        "execution_snapshot_drift_history_summary.json": '{"entry_count":1,"mismatching_snapshot_count":0}',
        "execution_drift_overview_summary.json": '{"overall_status":"ok"}',
    }
    ops = root / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (ops / name).write_text(payload, encoding="utf-8")


def _write_trade_xyz_strict_artifacts(root: Path) -> None:
    registry = root / "registry/trade_xyz_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            [
                {
                    "venue": "trade_xyz",
                    "canonical_symbol": "NVDA",
                    "venue_symbol": "NVDA",
                    "asset_class": "equity",
                    "dex": "xyz",
                    "coin": "xyz:NVDA",
                    "asset_id": 110002,
                    "api_readable": True,
                    "api_orderable": True,
                    "active": True,
                    "notes": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    quote = root / "raw/quotes/trade_xyz/2026-05-27.jsonl"
    quote.parent.mkdir(parents=True, exist_ok=True)
    quote.write_text(
        '{"ts_client":"2026-05-27T00:00:00+00:00","venue":"trade_xyz",'
        '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
        '"raw_payload_sha256":"abc","coin":"xyz:NVDA","asset_id":110002,'
        '"recv_ts_ms":1779840000000,"best_bid":100.0,"best_ask":100.1,'
        '"mid_price":100.05,"exec_buy_price":100.1,"exec_sell_price":100.0,'
        '"spread_bps":10.0,"bid_depth_10bps_usd":1000.0,'
        '"ask_depth_10bps_usd":1000.0,"mark_price":100.0,"oracle_price":100.0,'
        '"funding_rate":0.0,"funding_interval_minutes":60,'
        '"open_interest_usd":10000.0,"fee_mode":"standard","taker_fee_bps":9.0,'
        '"maker_fee_bps":3.0,"market_status":"open",'
        '"session_type":"unknown","is_tradable":true,"block_reasons":[],'
        '"source_confidence":1.0,"venue_quality_score":1.0,'
        '"raw_payload_ref":"data/raw/quotes/trade_xyz/2026-05-27.jsonl#row=0"}\n',
        encoding="utf-8",
    )
    summary = root / "ops/trade_xyz_quote_collection_summary.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(
        '{"venue":"trade_xyz","started_at":"2026-05-27T00:00:00+00:00",'
        '"ended_at":"2026-05-27T00:01:00+00:00","duration_minutes":1,'
        '"interval_seconds":60,"requested_symbols":["NVDA"],"collected_symbols":["NVDA"],'
        '"row_count":1,"api_error_count":0,"per_symbol":{}}',
        encoding="utf-8",
    )
    normalized = root / "normalized/quotes.parquet"
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_bytes(b"placeholder")


def test_validate_artifacts_passes_with_valid_files(tmp_path) -> None:
    _write_registry(tmp_path / "data/registry/gtrade_instrument_registry.json", "gtrade")
    _write_registry(tmp_path / "data/registry/ostium_instrument_registry.json", "ostium")
    _write_quote(tmp_path / "data/raw/quotes/gtrade/2026-05-22.jsonl")
    _write_backtest_metrics(tmp_path / "data/research/backtest_metrics.json")
    _write_evidence_card(tmp_path / "data/evidence/evidence_card_20260522_000000.json")

    summary = validate_artifacts(tmp_path / "data", Path("schemas"), strict=False)

    assert summary.checked_files == 5
    assert summary.issues == []


def test_validate_artifacts_strict_flags_missing_artifacts(tmp_path) -> None:
    summary = validate_artifacts(tmp_path / "data", Path("schemas"), strict=True)

    assert summary.issues
    assert any(
        "Missing required Trade[XYZ] registry artifact" in issue.message for issue in summary.issues
    )
    assert any(
        "No Trade[XYZ] quote JSONL artifacts found" in issue.message for issue in summary.issues
    )


def test_validate_artifacts_checks_latest_evidence_card_only(tmp_path) -> None:
    _write_registry(tmp_path / "data/registry/gtrade_instrument_registry.json", "gtrade")
    _write_registry(tmp_path / "data/registry/ostium_instrument_registry.json", "ostium")
    _write_quote(tmp_path / "data/raw/quotes/gtrade/2026-05-22.jsonl")
    _write_backtest_metrics(tmp_path / "data/research/backtest_metrics.json")
    legacy = tmp_path / "data/evidence/evidence_card_20260521_000000.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text('{"run_id":"legacy"}', encoding="utf-8")
    _write_evidence_card(tmp_path / "data/evidence/evidence_card_20260522_000000.json")

    summary = validate_artifacts(tmp_path / "data", Path("schemas"), strict=False)

    assert summary.checked_files == 5
    assert summary.issues == []


def test_validate_artifacts_strict_passes_with_execution_summaries(tmp_path) -> None:
    _write_trade_xyz_strict_artifacts(tmp_path / "data")
    _write_execution_summaries(tmp_path / "data")

    summary = validate_artifacts(tmp_path / "data", Path("schemas"), strict=True)

    assert summary.issues == []
    assert summary.checked_files == 11
