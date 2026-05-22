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
    path.write_text('[{"timeframe":"4h","trade_count":10,"avg_trade_return":0.1}]', encoding="utf-8")


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
    assert any("Missing required registry artifact" in issue.message for issue in summary.issues)
