import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from sis.models import InstrumentSpec
from sis.storage.jsonl_store import read_jsonl
from sis.storage.normalize import normalize_quotes
from sis.storage.normalize import normalize_trade_xyz_ws_quotes
from sis.venues.trade_xyz.collector import collect_trade_xyz_quote_window, collect_trade_xyz_quotes


def _fixture(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _active_instrument() -> InstrumentSpec:
    return InstrumentSpec(
        venue="trade_xyz",
        canonical_symbol="NVDA",
        venue_symbol="NVDA",
        asset_class="equity",
        dex="xyz",
        coin="xyz:NVDA",
        asset_id=130002,
        real_market_symbol="NVDA",
        fee_mode="standard",
        taker_fee_bps=9.0,
        maker_fee_bps=3.0,
        api_readable=True,
        api_orderable=True,
        active=True,
    )


def test_collector_writes_jsonl_with_raw_hash(tmp_path) -> None:
    out_path = tmp_path / "data/raw/quotes/trade_xyz/2026-05-26.jsonl"
    count = collect_trade_xyz_quotes(
        instruments=[_active_instrument()],
        out_path=out_path,
        all_mids_payload={"xyz:NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )
    assert count == 1
    rows = list(read_jsonl(out_path))
    assert len(rows) == 1
    assert rows[0]["raw_payload_sha256"]
    assert rows[0]["raw_payload_ref"].endswith("#row=0")
    assert rows[0]["fee_mode"] == "standard"
    assert rows[0]["taker_fee_bps"] == 9.0
    assert rows[0]["maker_fee_bps"] == 3.0
    assert rows[0]["exec_buy_price"] == rows[0]["best_ask"]
    assert rows[0]["exec_sell_price"] == rows[0]["best_bid"]
    assert rows[0]["fee_source"] == "instrument_registry"


def test_collector_enriches_quote_from_meta_and_asset_ctxs(tmp_path) -> None:
    out_path = tmp_path / "data/raw/quotes/trade_xyz/2026-05-26.jsonl"
    count = collect_trade_xyz_quotes(
        instruments=[_active_instrument()],
        out_path=out_path,
        all_mids_payload={"NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        meta_and_asset_ctxs_payload=(
            {"universe": [{"name": "xyz:NVDA"}]},
            [
                {
                    "markPx": "100.2",
                    "oraclePx": "100.1",
                    "midPx": "100.15",
                    "funding": "-0.00001",
                    "openInterest": "1234",
                    "oracleTs": "1770000000000",
                    "premium": "-0.1",
                    "prevDayPx": "99.0",
                    "dayNtlVlm": "4567",
                }
            ],
        ),
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )
    rows = list(read_jsonl(out_path))

    assert count == 1
    assert rows[0]["mark_price"] == 100.2
    assert rows[0]["oracle_price"] == 100.1
    assert rows[0]["index_price"] == 100.15
    assert rows[0]["funding_rate"] == -0.00001
    assert rows[0]["funding_interval_minutes"] == 60
    assert rows[0]["open_interest_usd"] == 1234.0
    assert rows[0]["oracle_ts_ms"] == 1770000000000
    assert rows[0]["oracle_ts_status"] == "observed"
    assert rows[0]["oracle_ts_source"] == "oracleTs"
    assert rows[0]["bid_depth_10bps_usd"] > 0
    assert rows[0]["ask_depth_10bps_usd"] > 0
    assert "BLOCK_API_ERROR" not in rows[0]["block_reasons"]


def test_normalize_quotes_accepts_trade_xyz_v2(tmp_path) -> None:
    out_path = tmp_path / "data/raw/quotes/trade_xyz/2026-05-26.jsonl"
    collect_trade_xyz_quotes(
        instruments=[_active_instrument()],
        out_path=out_path,
        all_mids_payload={"xyz:NVDA": "1000.0"},
        book_payloads={"xyz:NVDA": _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")},
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )
    count = normalize_quotes(
        tmp_path / "data/raw/quotes",
        tmp_path / "data/normalized/quotes.parquet",
        tmp_path / "data/normalized/sis.duckdb",
    )
    assert count == 1
    assert (tmp_path / "data/normalized/quotes.parquet").exists()
    assert (tmp_path / "data/normalized/sis.duckdb").exists()
    frame = pl.read_parquet(tmp_path / "data/normalized/quotes.parquet")
    assert frame.get_column("raw_payload_ref").to_list()[0].endswith("#row=0")
    assert (
        frame.get_column("exec_buy_price").to_list()[0] == frame.get_column("best_ask").to_list()[0]
    )


def test_normalize_trade_xyz_ws_quotes_builds_quote_log_dataset(tmp_path) -> None:
    raw_root = tmp_path / "data/raw/ws/trade_xyz"
    bbo_path = raw_root / "date=2026-06-02/subscription=bbo/symbol=NVDA/part-000001.jsonl"
    ctx_path = (
        raw_root / "date=2026-06-02/subscription=activeAssetCtx/symbol=NVDA/part-000001.jsonl"
    )
    trades_path = raw_root / "date=2026-06-02/subscription=trades/symbol=NVDA/part-000001.jsonl"
    control_path = (
        raw_root / "date=2026-06-02/subscription=__control__/symbol=__all__/part-000001.jsonl"
    )
    bbo_path.parent.mkdir(parents=True)
    ctx_path.parent.mkdir(parents=True)
    trades_path.parent.mkdir(parents=True)
    control_path.parent.mkdir(parents=True)
    bbo_row = {
        "subscription": "bbo",
        "channel": "bbo",
        "message_kind": "data",
        "recv_ts_ms": 1780394603762,
        "source_ts_ms": 1780394603466,
        "canonical_symbol": "NVDA",
        "venue_symbol": "xyz:NVDA",
        "coin": "xyz:NVDA",
        "payload_sha256": "sha256:bbo",
        "payload": {
            "channel": "bbo",
            "data": {
                "coin": "xyz:NVDA",
                "time": 1780394603466,
                "bbo": [
                    {"px": "100.0", "sz": "1.5"},
                    {"px": "100.2", "sz": "2.0"},
                ],
            },
        },
    }
    bbo_path.write_text(
        json.dumps(bbo_row) + "\n" + json.dumps(bbo_row) + "\n",
        encoding="utf-8",
    )
    ctx_path.write_text(
        json.dumps(
            {
                "subscription": "activeAssetCtx",
                "channel": "activeAssetCtx",
                "message_kind": "data",
                "recv_ts_ms": 1780394604000,
                "canonical_symbol": "NVDA",
                "venue_symbol": "xyz:NVDA",
                "coin": "xyz:NVDA",
                "payload_sha256": "sha256:ctx",
                "payload": {
                    "channel": "activeAssetCtx",
                    "data": {
                        "coin": "xyz:NVDA",
                        "ctx": {
                            "oraclePx": "100.3",
                            "markPx": "100.1",
                            "midPx": "100.15",
                            "funding": "0.00001",
                            "openInterest": "1234",
                        },
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    trades_path.write_text(
        json.dumps({"subscription": "trades", "channel": "trades", "message_kind": "data"}) + "\n",
        encoding="utf-8",
    )
    control_path.write_text(
        json.dumps(
            {
                "subscription": "__control__",
                "channel": "subscriptionResponse",
                "message_kind": "control",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    count = normalize_trade_xyz_ws_quotes(
        raw_root,
        tmp_path / "data/normalized/trade_xyz_ws_quotes.parquet",
        tmp_path / "data/normalized/sis.duckdb",
        instruments=[_active_instrument()],
        manifest_path=tmp_path / "data/normalized/trade_xyz_ws_quotes.manifest.json",
        quality_manifest_path=Path("data/manifests/trade_xyz_ws_quality_manifest.json"),
        rest_parity_manifest_path=Path("data/manifests/trade_xyz_rest_parity_manifest.json"),
    )

    assert count == 2
    frame = pl.read_parquet(tmp_path / "data/normalized/trade_xyz_ws_quotes.parquet")
    assert frame.get_column("source").to_list() == [
        "trade_xyz_ws_activeAssetCtx",
        "trade_xyz_ws_bbo",
    ]
    bbo = frame.filter(pl.col("source") == "trade_xyz_ws_bbo").row(0, named=True)
    assert bbo["asset_id"] == 130002
    assert bbo["taker_fee_bps"] == 9.0
    assert bbo["exec_buy_price"] == 100.2
    assert bbo["raw_payload_ref"].endswith("#row=0")
    ctx = frame.filter(pl.col("source") == "trade_xyz_ws_activeAssetCtx").row(0, named=True)
    assert ctx["is_tradable"] is False
    assert ctx["oracle_ts_ms"] is None
    manifest = json.loads(
        (tmp_path / "data/normalized/trade_xyz_ws_quotes.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == "trade_xyz_ws_backtest_artifact_manifest.v1"
    assert manifest["raw_ws_root"] == str(raw_root)
    assert manifest["quality_manifest_path"] == "data/manifests/trade_xyz_ws_quality_manifest.json"
    assert manifest["rest_parity_manifest_path"] == (
        "data/manifests/trade_xyz_rest_parity_manifest.json"
    )
    assert manifest["quote_count_written"] == 2
    assert manifest["bbo_quote_count"] == 1
    assert manifest["active_asset_ctx_quote_count"] == 1
    assert manifest["trade_row_count_skipped"] == 1
    assert manifest["control_row_count_skipped"] == 1
    assert manifest["duplicate_count_skipped"] == 1
    assert "Do not derive oracle_ts_ms" in manifest["oracle_timestamp_policy"]


def test_quote_window_summary_records_oracle_timestamp_probe(tmp_path) -> None:
    class FakeClient:
        def all_mids(self):
            return {"xyz:NVDA": "1000.0"}

        def meta_and_asset_ctxs(self):
            return (
                {"universe": [{"name": "xyz:NVDA"}]},
                [{"oraclePx": "100.1", "funding": "-0.00001", "openInterest": "1234"}],
            )

        def l2_book(self, _coin):
            return _fixture("tests/fixtures/trade_xyz_l2_book.sample.json")

        def close(self):
            return None

    summary = collect_trade_xyz_quote_window(
        data_dir=tmp_path / "data",
        instruments=[_active_instrument()],
        duration_minutes=1,
        interval_seconds=60,
        normalize=True,
        replace=False,
        write_summary=True,
        write_report=True,
        client=FakeClient(),
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )

    assert summary["per_symbol"]["NVDA"]["missing_oracle_ts_rate"] == 1.0
    assert summary["oracle_ts_missing_reasons"] == {"asset_ctx_missing_oracle_timestamp_field": 1}
    assert (tmp_path / "data/ops/trade_xyz_quote_collection_summary.json").exists()
    report = (tmp_path / "data/reports/trade_xyz_quote_collection_report.md").read_text(
        encoding="utf-8"
    )
    assert "## Oracle Timestamp Probe" in report
    assert "asset_ctx_missing_oracle_timestamp_field" in report
