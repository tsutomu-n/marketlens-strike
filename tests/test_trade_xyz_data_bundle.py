import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jsonschema import validate
import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.research.providers import PriceProvider, ResearchFetchRequest
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.data_bundle import build_trade_xyz_data_collection_bundle


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "venue": "trade_xyz",
                    "canonical_symbol": "SP500",
                    "venue_symbol": "SP500",
                    "asset_class": "index",
                    "dex": "xyz",
                    "coin": "xyz:SP500",
                    "real_market_symbol": "SPY",
                    "fee_mode": "standard",
                    "taker_fee_bps": 9.0,
                    "maker_fee_bps": 3.0,
                    "discovery_bound_bps": 500.0,
                    "oi_cap_usd": 1000000.0,
                    "external_session": "xnys_regular",
                    "internal_session": "trade_xyz_internal",
                    "active": True,
                }
            ]
        ),
        encoding="utf-8",
    )


def _quote_row(ts: datetime, *, ref: str) -> dict:
    ts_ms = int(ts.timestamp() * 1000)
    return {
        "ts_client": ts.isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "SP500",
        "venue_symbol": "SP500",
        "source": "trade_xyz_test_quote",
        "raw_payload_sha256": f"hash-{ts_ms}",
        "recv_ts_ms": ts_ms,
        "source_ts_ms": ts_ms,
        "dex": "xyz",
        "coin": "xyz:SP500",
        "mark_price": 5200.1,
        "oracle_price": 5200.0,
        "oracle_ts_ms": ts_ms,
        "oracle_ts_source": "asset_ctx.oracleTs",
        "oracle_ts_status": "observed",
        "best_bid": 5199.5,
        "best_ask": 5200.5,
        "mid_price": 5200.0,
        "exec_buy_price": 5200.5,
        "exec_sell_price": 5199.5,
        "spread_bps": 1.923,
        "funding_rate": 0.00001,
        "funding_interval_minutes": 60,
        "open_interest_usd": 10000.0,
        "oi_cap_usd": 1000000.0,
        "oi_cap_usage": 0.01,
        "discovery_bound_pct": 0.05,
        "bound_distance": 0.03,
        "fee_mode": "standard",
        "taker_fee_bps": 9.0,
        "maker_fee_bps": 3.0,
        "market_status": "open",
        "session_type": "regular",
        "external_session_open": True,
        "is_tradable": True,
        "source_confidence": 1.0,
        "venue_quality_score": 1.0,
        "block_reasons": [],
        "raw_payload_ref": ref,
    }


def _write_raw_quotes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    first = datetime(2026, 5, 26, 14, 0, tzinfo=UTC)
    second = datetime(2026, 5, 26, 14, 1, tzinfo=UTC)
    rows = [
        _quote_row(first, ref=str(path) + "#row=0"),
        _quote_row(second, ref=str(path) + "#row=1"),
    ]
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class FakeFundingClient:
    def __init__(self) -> None:
        self.requests = []
        self.user_fee_requests: list[str] = []
        self.candle_requests = []

    def funding_history(self, coin: str, *, start_time_ms: int, end_time_ms: int | None = None):
        self.requests.append((coin, start_time_ms, end_time_ms))
        return [
            {
                "coin": coin,
                "fundingRate": "0.00001",
                "premium": "0.00002",
                "time": 1770000000000,
            }
        ]

    def user_fees(self, user: str) -> dict:
        self.user_fee_requests.append(user)
        return {
            "feeSchedule": {"cross": "0.00045", "add": "0.00015"},
            "userCrossRate": "0.000315",
            "userAddRate": "0.000105",
            "activeReferralDiscount": "0.0",
        }

    def candle_snapshot(self, coin: str, interval: str, start_ms: int, end_ms: int):
        self.candle_requests.append((coin, interval, start_ms, end_ms))
        return [
            {
                "t": start_ms,
                "T": start_ms + 1_799_999,
                "s": coin,
                "i": interval,
                "o": "5200.0",
                "h": "5210.0",
                "l": "5190.0",
                "c": "5205.0",
                "v": "123.45",
                "n": 12,
            }
        ]

    def close(self):
        return None


class FakePriceProvider(PriceProvider):
    name = "fake_price"

    def fetch_ohlcv(self, request: ResearchFetchRequest) -> pl.DataFrame:
        start = datetime(2026, 5, 1, tzinfo=UTC)
        rows: list[dict] = []
        for symbol in request.symbols:
            for offset in range(2):
                close = 100.0 + offset
                rows.append(
                    {
                        "ts": start + timedelta(days=offset),
                        "symbol": symbol,
                        "open": close - 1,
                        "high": close + 1,
                        "low": close - 2,
                        "close": close,
                        "volume": 1000 + offset,
                        "provider_symbol": symbol,
                        "interval": request.interval,
                        "adjustment": "none",
                    }
                )
        return pl.DataFrame(rows)


def test_build_trade_xyz_data_collection_bundle_generates_derived_manifests(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")
    client = FakeFundingClient()

    manifest = build_trade_xyz_data_collection_bundle(
        data_dir=data_dir,
        min_days=0,
        max_gap_minutes=2,
        real_market_provider=FakePriceProvider(),
        signal_candle_client=client,  # type: ignore[arg-type]
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["status"] == "completed"
    assert manifest["failed_step_count"] == 0
    assert manifest["readiness_decision"] == "READY_WITH_KNOWN_GAPS"
    assert manifest["backtest_data_ready"] is True
    assert (data_dir / "manifests/trade_xyz_quote_coverage_manifest.json").exists()
    assert (data_dir / "manifests/trade_xyz_reference_datasets_manifest.json").exists()
    assert (data_dir / "manifests/session_state_manifest.json").exists()
    assert (data_dir / "manifests/funding_manifest.json").exists()
    assert (data_dir / "manifests/trade_xyz_real_market_reference_manifest.json").exists()
    assert (data_dir / "manifests/trade_xyz_data_readiness_manifest.json").exists()
    assert (data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json").exists()
    validate(
        manifest,
        read_json(Path("schemas/trade_xyz_data_collection_bundle_manifest.v1.schema.json")),
    )


def test_build_trade_xyz_data_collection_bundle_cli_writes_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")

    result = CliRunner().invoke(
        app,
        [
            "build-trade-xyz-data-bundle",
            "--min-days",
            "0",
            "--max-gap-minutes",
            "2",
            "--skip-real-market-reference",
            "--skip-signal-candles",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "status=completed" in result.stdout
    assert "readiness_decision=NOT_READY" in result.stdout
    assert "backtest_data_ready=False" in result.stdout


def test_build_trade_xyz_data_collection_bundle_cli_can_collect_funding_history(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")

    class ContextFundingClient(FakeFundingClient):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("sis.commands.quotes.TradeXyzClient", ContextFundingClient)

    result = CliRunner().invoke(
        app,
        [
            "build-trade-xyz-data-bundle",
            "--symbols",
            "SP500",
            "--min-days",
            "0",
            "--max-gap-minutes",
            "2",
            "--max-oracle-lag-minutes",
            "10000",
            "--funding-start-time-ms",
            "1770000000000",
            "--funding-end-time-ms",
            "1770003600000",
            "--skip-real-market-reference",
            "--skip-signal-candles",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "status=completed" in result.stdout
    assert "backtest_data_ready=False" in result.stdout
    payload = read_json(data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json")
    step_status = {item["name"]: item["status"] for item in payload["steps"]}
    assert step_status["funding_history"] == "completed"
    assert step_status["funding_events_from_history"] == "completed"


def test_build_trade_xyz_data_collection_bundle_cli_can_collect_account_fee(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")

    class ContextFundingClient(FakeFundingClient):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("sis.venues.trade_xyz.data_bundle.TradeXyzClient", ContextFundingClient)

    result = CliRunner().invoke(
        app,
        [
            "build-trade-xyz-data-bundle",
            "--symbols",
            "SP500",
            "--min-days",
            "0",
            "--max-gap-minutes",
            "2",
            "--skip-real-market-reference",
            "--skip-signal-candles",
            "--account-fee-user-address",
            "0x1111111111111111111111111111111111111111",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    payload = read_json(data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json")
    assert payload["account_fee_user_address_provided"] is True
    step_status = {item["name"]: item["status"] for item in payload["steps"]}
    assert step_status["account_fee"] == "completed"
    assert (data_dir / "manifests/trade_xyz_account_fee_manifest.json").exists()


def test_build_trade_xyz_data_collection_bundle_cli_can_infer_funding_window(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")

    class ContextFundingClient(FakeFundingClient):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("sis.commands.quotes.TradeXyzClient", ContextFundingClient)

    result = CliRunner().invoke(
        app,
        [
            "build-trade-xyz-data-bundle",
            "--symbols",
            "SP500",
            "--min-days",
            "0",
            "--max-gap-minutes",
            "2",
            "--auto-funding-window",
            "--skip-real-market-reference",
            "--skip-signal-candles",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    payload = read_json(data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json")
    assert payload["auto_funding_window"] is True
    assert payload["funding_window_source"] == "auto"
    step_status = {item["name"]: item["status"] for item in payload["steps"]}
    assert step_status["funding_window"] == "completed"
    assert step_status["funding_history"] == "completed"


def test_build_trade_xyz_data_collection_bundle_can_collect_and_join_funding_history(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")
    client = FakeFundingClient()

    manifest = build_trade_xyz_data_collection_bundle(
        data_dir=data_dir,
        symbols=["SP500"],
        min_days=0,
        max_gap_minutes=2,
        max_oracle_lag_minutes=10_000,
        funding_start_time_ms=1770000000000,
        funding_end_time_ms=1770003600000,
        funding_client=client,
        real_market_provider=FakePriceProvider(),
        signal_candle_client=client,  # type: ignore[arg-type]
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert client.requests == [("xyz:SP500", 1770000000000, 1770003600000)]
    assert manifest["backtest_data_ready"] is True
    step_status = {item["name"]: item["status"] for item in manifest["steps"]}
    assert step_status["funding_history"] == "completed"
    assert step_status["funding_events_from_history"] == "completed"
    assert step_status["signal_candles"] == "completed"
    assert (data_dir / "manifests/trade_xyz_signal_candles_manifest.json").exists()
    assert (data_dir / "normalized/funding_history_events.parquet").exists()
    assert (data_dir / "normalized/funding_events_from_history.parquet").exists()


def test_build_trade_xyz_data_collection_bundle_can_collect_account_fee(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")
    client = FakeFundingClient()

    manifest = build_trade_xyz_data_collection_bundle(
        data_dir=data_dir,
        symbols=["SP500"],
        min_days=0,
        max_gap_minutes=2,
        account_fee_user_address="0x1111111111111111111111111111111111111111",
        account_fee_client=client,  # type: ignore[arg-type]
        real_market_provider=FakePriceProvider(),
        signal_candle_client=client,  # type: ignore[arg-type]
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert client.user_fee_requests == ["0x1111111111111111111111111111111111111111"]
    assert manifest["account_fee_user_address_provided"] is True
    step_status = {item["name"]: item["status"] for item in manifest["steps"]}
    assert step_status["account_fee"] == "completed"
    readiness = read_json(data_dir / "manifests/trade_xyz_data_readiness_manifest.json")
    statuses = {item["key"]: item["status"] for item in readiness["requirements"]}
    assert statuses["account_specific_fee"] == "pass"
    assert (data_dir / "manifests/trade_xyz_account_fee_manifest.json").exists()


def test_build_trade_xyz_data_collection_bundle_can_infer_funding_window_from_quotes(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")
    client = FakeFundingClient()

    manifest = build_trade_xyz_data_collection_bundle(
        data_dir=data_dir,
        symbols=["SP500"],
        min_days=0,
        max_gap_minutes=2,
        max_oracle_lag_minutes=10_000,
        auto_funding_window=True,
        funding_client=client,
        real_market_provider=FakePriceProvider(),
        signal_candle_client=client,  # type: ignore[arg-type]
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    first = int(datetime(2026, 5, 26, 14, 0, tzinfo=UTC).timestamp() * 1000)
    second = int(datetime(2026, 5, 26, 14, 1, tzinfo=UTC).timestamp() * 1000)
    assert client.requests == [("xyz:SP500", first, second + 3_600_000)]
    assert manifest["auto_funding_window"] is True
    assert manifest["funding_start_time_ms"] == first
    assert manifest["funding_end_time_ms"] == second + 3_600_000
    assert manifest["funding_window_source"] == "auto"
    step_status = {item["name"]: item["status"] for item in manifest["steps"]}
    assert step_status["funding_window"] == "completed"
    assert step_status["funding_history"] == "completed"


def test_build_trade_xyz_data_collection_bundle_skips_fresh_signal_candles(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json")
    _write_raw_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-26.jsonl")
    first_client = FakeFundingClient()
    build_trade_xyz_data_collection_bundle(
        data_dir=data_dir,
        symbols=["SP500"],
        min_days=0,
        max_gap_minutes=2,
        real_market_provider=FakePriceProvider(),
        signal_candle_client=first_client,  # type: ignore[arg-type]
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    second_client = FakeFundingClient()

    manifest = build_trade_xyz_data_collection_bundle(
        data_dir=data_dir,
        symbols=["SP500"],
        min_days=0,
        max_gap_minutes=2,
        real_market_provider=FakePriceProvider(),
        signal_candle_client=second_client,  # type: ignore[arg-type]
        generated_at=datetime(2026, 5, 31, 1, tzinfo=UTC),
    )

    assert first_client.candle_requests
    assert second_client.candle_requests == []
    signal_step = next(item for item in manifest["steps"] if item["name"] == "signal_candles")
    assert signal_step["status"] == "skipped"
    assert signal_step["details"]["reason"] == "signal_candles_fresh"
