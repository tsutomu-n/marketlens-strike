from datetime import datetime, timezone
from pathlib import Path

from sis.storage.jsonl_store import append_jsonl, write_json
from sis.validation.artifacts import validate_artifacts


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_trade_xyz_artifacts(data_dir: Path, *, omit: str | None = None) -> None:
    write_json(
        data_dir / "registry/trade_xyz_instrument_registry.json",
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
            }
        ],
    )
    row = {
        "ts_client": datetime(2026, 5, 27, tzinfo=timezone.utc).isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "NVDA",
        "venue_symbol": "NVDA",
        "source": "test",
        "raw_payload_sha256": "abc",
        "coin": "xyz:NVDA",
        "asset_id": 110002,
        "recv_ts_ms": 1770000000000,
        "best_bid": 100.0,
        "best_ask": 100.1,
        "mid_price": 100.05,
        "spread_bps": 10.0,
        "bid_depth_10bps_usd": 1000.0,
        "ask_depth_10bps_usd": 1000.0,
        "mark_price": 100.0,
        "oracle_price": 100.0,
        "funding_rate": -0.00001,
        "open_interest_usd": 10000.0,
        "market_status": "open",
        "session_type": "unknown",
        "is_tradable": True,
        "block_reasons": [],
        "venue_quality_score": 1.0,
    }
    if omit:
        row.pop(omit)
    append_jsonl(data_dir / "raw/quotes/trade_xyz/2026-05-27.jsonl", row)
    write_json(
        data_dir / "ops/trade_xyz_quote_collection_summary.json",
        {
            "venue": "trade_xyz",
            "started_at": "2026-05-27T00:00:00+00:00",
            "ended_at": "2026-05-27T00:00:00+00:00",
            "duration_minutes": 1,
            "interval_seconds": 60,
            "requested_symbols": ["NVDA"],
            "collected_symbols": ["NVDA"],
            "row_count": 1,
            "api_error_count": 0,
            "per_symbol": {},
        },
    )
    normalized = data_dir / "normalized/quotes.parquet"
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_bytes(b"placeholder")


def test_validate_artifacts_trade_xyz_strict_passes(tmp_path) -> None:
    _write_trade_xyz_artifacts(tmp_path / "data")

    summary = validate_artifacts(tmp_path / "data", PROJECT_ROOT / "schemas", strict=True)

    assert summary.issues == []


def test_validate_artifacts_trade_xyz_strict_requires_funding(tmp_path) -> None:
    _write_trade_xyz_artifacts(tmp_path / "data", omit="funding_rate")

    summary = validate_artifacts(tmp_path / "data", PROJECT_ROOT / "schemas", strict=True)

    assert any(issue.message == "TRADE_XYZ_STRICT_FUNDING_MISSING" for issue in summary.issues)
