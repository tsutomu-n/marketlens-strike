import json
from datetime import UTC, datetime
import hashlib
from pathlib import Path

from jsonschema import validate
from typer.testing import CliRunner

from sis.cli import app
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.readiness import build_trade_xyz_data_readiness_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_ready_inputs(data_dir: Path) -> None:
    manifests = data_dir / "manifests"
    _write_json(
        manifests / "trade_xyz_quote_coverage_manifest.json",
        {
            "schema_version": "trade_xyz_quote_coverage_manifest.v1",
            "coverage_passed": True,
            "symbol_count": 1,
            "row_count": 100,
            "per_symbol": {
                "SP500": {
                    "coverage_status": "pass",
                    "row_count": 100,
                    "missing_rates": {"raw_payload_ref": 0.0},
                }
            },
        },
    )
    _write_json(
        manifests / "trade_xyz_reference_datasets_manifest.json",
        {
            "schema_version": "trade_xyz_reference_datasets_manifest.v1",
            "artifacts": {"funding_events": "data/normalized/funding_events.parquet"},
            "row_counts": {
                "instrument_registry_snapshots": 1,
                "fee_snapshots": 1,
                "session_calendar_snapshots": 1,
                "funding_events": 1,
                "quote_logs_read": 100,
            },
            "funding_skipped": {},
        },
    )
    _write_json(
        manifests / "funding_history_join_manifest.json",
        {
            "schema_version": "funding_history_join_manifest.v1",
            "artifact_path": "data/normalized/funding_events_from_history.parquet",
            "row_count": 1,
            "skipped": {},
            "max_oracle_lag_minutes": 90.0,
            "usable_as_backtest_funding_event": True,
        },
    )
    _write_json(
        manifests / "fee_manifest.json",
        {
            "schema_version": "fee_manifest.v1",
            "fee_snapshot_count": 1,
            "unresolved_symbol_count": 0,
            "fee_mode_counts": {"standard": 1},
            "fee_source_counts": {"registry": 1},
            "account_specific_fee_status": "not_collected_no_wallet_or_user_context",
            "account_specific_missing_fields": ["fee_tier"],
            "account_specific_missing_field_counts": {"fee_tier": 1},
        },
    )
    _write_json(
        manifests / "trade_xyz_real_market_reference_manifest.json",
        {
            "schema_version": "trade_xyz_real_market_reference_manifest.v1",
            "generated_at": "2026-05-31T00:00:00+00:00",
            "status": "pass",
            "provider": "fake_price",
            "interval": "1d",
            "start": "2025-05-31",
            "end": "2026-06-01",
            "row_count": 10,
            "requested_symbols": ["SPY", "^VIX"],
            "returned_symbols": ["SPY", "^VIX"],
            "mapped_symbols": ["SPY"],
            "missing_mapped_symbols": [],
            "missing_requested_symbols": [],
            "artifacts": {
                "raw_provider_frame": "data/raw/real_market/fake/trade_xyz_reference_bars.parquet",
                "normalized_reference_bars": "data/normalized/real_market_reference_bars.parquet",
            },
        },
    )
    _write_json(
        manifests / "trade_xyz_signal_candles_manifest.json",
        {
            "schema_version": "trade_xyz_signal_candles_manifest.v1",
            "generated_at": "2026-05-31T00:00:00+00:00",
            "data_dir": str(data_dir),
            "registry_path": str(data_dir / "registry/trade_xyz_instrument_registry.json"),
            "source": "hyperliquid_info_candleSnapshot",
            "start": "2025-05-31T00:00:00+00:00",
            "end": "2026-05-31T00:00:00+00:00",
            "period_days": 365,
            "intervals": ["30m", "4h", "1d", "3d"],
            "requested_intervals": ["30m", "4h", "1d", "3d"],
            "symbols": ["SP500"],
            "requested_symbols": ["SP500"],
            "row_count": 10,
            "symbol_count": 1,
            "request_error_count": 0,
            "request_errors": [],
            "artifacts": {
                "raw_candles_root": "data/raw/candles/trade_xyz",
                "normalized_signal_candles": "data/normalized/trade_xyz_signal_candles.parquet",
            },
            "notes": [],
        },
    )
    _write_json(
        manifests / "session_state_manifest.json",
        {
            "schema_version": "session_state_manifest.v1",
            "row_count": 100,
            "symbol_count": 1,
            "session_type_counts": {"regular": 80, "closed": 20},
            "calendar_source": "exchange_calendars",
            "missing_field_counts": {
                "internal_session_open": 100,
                "maintenance_window": 100,
            },
        },
    )
    _write_json(
        manifests / "oracle_timestamp_manifest.json",
        {
            "schema_version": "oracle_timestamp_manifest.v1",
            "row_count": 100,
            "oracle_ts_present_count": 100,
            "oracle_ts_missing_count": 0,
            "oracle_ts_missing_reasons": {},
            "notes": [],
        },
    )


def _write_registry(path: Path, symbols: list[str]) -> None:
    _write_json(
        path,
        [
            {
                "venue": "trade_xyz",
                "canonical_symbol": symbol,
                "venue_symbol": symbol,
                "asset_class": "equity" if symbol != "SP500" else "index",
                "dex": "xyz",
                "coin": f"xyz:{symbol}",
                "real_market_symbol": symbol,
                "active": True,
            }
            for symbol in symbols
        ],
    )


def test_build_trade_xyz_data_readiness_manifest_allows_documented_known_gaps(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["decision"] == "READY_WITH_KNOWN_GAPS"
    assert manifest["backtest_data_ready"] is True
    assert manifest["complete_observed_market_truth"] is False
    assert manifest["fail_count"] == 0
    assert manifest["known_gap_count"] == 2
    statuses = {item["key"]: item["status"] for item in manifest["requirements"]}
    assert statuses["quote_coverage"] == "pass"
    assert statuses["funding_events"] == "pass"
    assert statuses["real_market_reference"] == "pass"
    assert statuses["signal_candles"] == "pass"
    assert statuses["account_specific_fee"] == "known_gap"
    assert statuses["internal_session_and_maintenance"] == "known_gap"
    account_fee_action = next(
        item for item in manifest["next_actions"] if item["key"] == "collect_account_fee"
    )
    assert account_fee_action["command"] == (
        "uv run sis collect-trade-xyz-account-fee --user-address 0x..."
    )
    assert account_fee_action["follow_up_command"] == ("uv run sis build-trade-xyz-data-readiness")
    validate(manifest, read_json(Path("schemas/trade_xyz_data_readiness_manifest.v1.schema.json")))


def test_build_trade_xyz_data_readiness_manifest_accepts_observed_account_fee(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/trade_xyz_account_fee_manifest.json",
        {
            "schema_version": "trade_xyz_account_fee_manifest.v1",
            "generated_at": "2026-05-31T00:00:00+00:00",
            "status": "pass",
            "data_dir": str(data_dir),
            "source": "hyperliquid_info_userFees",
            "raw_artifact_path": "data/raw/fees/trade_xyz_account/example.json",
            "user_address_sha256": "a" * 64,
            "payload_field_keys": ["userAddRate", "userCrossRate"],
            "available_fields": ["userAddRate", "userCrossRate"],
            "missing_fields": [],
            "parsed": {
                "user_cross_rate": "0.000315",
                "user_add_rate": "0.000105",
                "user_taker_fee_bps": 3.15,
                "user_maker_fee_bps": 1.05,
            },
            "not_collected_fields": {
                "builder_fee_bps": "requires a specific builder address and maxBuilderFee query"
            },
            "notes": [],
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    statuses = {item["key"]: item["status"] for item in manifest["requirements"]}
    account_fee = next(
        item for item in manifest["requirements"] if item["key"] == "account_specific_fee"
    )
    assert statuses["account_specific_fee"] == "pass"
    assert account_fee["details"]["parsed"]["user_taker_fee_bps"] == 3.15
    assert manifest["known_gap_count"] == 1
    assert not any(item["key"] == "collect_account_fee" for item in manifest["next_actions"])


def test_build_trade_xyz_data_readiness_manifest_blocks_mismatched_account_fee_user(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    configured_user_hash = hashlib.sha256("0xabc".encode("utf-8")).hexdigest()
    monkeypatch.setenv("SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS", "0xabc")
    _write_json(
        data_dir / "manifests/trade_xyz_account_fee_manifest.json",
        {
            "schema_version": "trade_xyz_account_fee_manifest.v1",
            "generated_at": "2026-05-31T00:00:00+00:00",
            "status": "pass",
            "data_dir": str(data_dir),
            "source": "hyperliquid_info_userFees",
            "raw_artifact_path": "data/raw/fees/trade_xyz_account/example.json",
            "user_address_sha256": "b" * 64,
            "payload_field_keys": ["userAddRate", "userCrossRate"],
            "available_fields": ["userAddRate", "userCrossRate"],
            "missing_fields": [],
            "parsed": {
                "user_cross_rate": "0.000315",
                "user_add_rate": "0.000105",
                "user_taker_fee_bps": 3.15,
                "user_maker_fee_bps": 1.05,
            },
            "not_collected_fields": {},
            "notes": [],
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
        allow_known_gaps=False,
    )

    account_fee = next(
        item for item in manifest["requirements"] if item["key"] == "account_specific_fee"
    )
    assert account_fee["status"] == "known_gap"
    assert account_fee["reason"] == (
        "account fee manifest user hash does not match configured user address"
    )
    assert account_fee["details"]["configured_user_address_sha256"] == configured_user_hash
    assert account_fee["details"]["matches_configured_user"] is False
    assert manifest["decision"] == "NOT_READY"
    assert manifest["backtest_data_ready"] is False
    assert any(item["key"] == "collect_account_fee" for item in manifest["next_actions"])


def test_build_trade_xyz_data_readiness_manifest_flags_missing_oracle_timestamp_rows(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/oracle_timestamp_manifest.json",
        {
            "schema_version": "oracle_timestamp_manifest.v1",
            "row_count": 100,
            "oracle_ts_present_count": 0,
            "oracle_ts_missing_count": 100,
            "oracle_ts_missing_reasons": {"asset_ctx_missing_oracle_timestamp_field": 100},
            "notes": [],
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
        allow_known_gaps=False,
    )

    oracle_requirement = next(
        item for item in manifest["requirements"] if item["key"] == "oracle_timestamp_provenance"
    )
    assert oracle_requirement["status"] == "known_gap"
    assert oracle_requirement["details"]["oracle_ts_missing_rate"] == 1.0
    assert manifest["decision"] == "NOT_READY"
    assert any(
        item["key"] == "check_oracle_timestamp_provenance" for item in manifest["next_actions"]
    )


def test_build_trade_xyz_data_readiness_manifest_fails_empty_session_classification(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/session_state_manifest.json",
        {
            "schema_version": "session_state_manifest.v1",
            "row_count": 100,
            "symbol_count": 1,
            "session_type_counts": {},
            "calendar_source": "exchange_calendars+docs_trade_xyz_specification_index",
            "missing_field_counts": {},
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    session_requirement = next(
        item for item in manifest["requirements"] if item["key"] == "session_state"
    )
    assert session_requirement["status"] == "fail"
    assert session_requirement["reason"] == "session state manifest has no session_type_counts"
    assert manifest["decision"] == "NOT_READY"
    assert any(item["key"] == "build_session_state" for item in manifest["next_actions"])


def test_build_trade_xyz_data_readiness_manifest_flags_partial_funding_join(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/funding_history_join_manifest.json",
        {
            "schema_version": "funding_history_join_manifest.v1",
            "artifact_path": "data/normalized/funding_events_from_history.parquet",
            "row_count": 3,
            "skipped": {"missing_oracle_quote_within_lag": 2},
            "quote_skipped": {"missing_oracle_price": 1},
            "max_oracle_lag_minutes": 90.0,
            "usable_as_backtest_funding_event": True,
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
        allow_known_gaps=False,
    )

    funding = next(item for item in manifest["requirements"] if item["key"] == "funding_events")
    assert funding["status"] == "known_gap"
    assert funding["details"]["skipped"] == {"missing_oracle_quote_within_lag": 2}
    assert manifest["decision"] == "NOT_READY"
    assert any(item["key"] == "collect_funding_history" for item in manifest["next_actions"])


def test_build_trade_xyz_data_readiness_manifest_fails_missing_real_market_requested_symbol(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/trade_xyz_real_market_reference_manifest.json",
        {
            "schema_version": "trade_xyz_real_market_reference_manifest.v1",
            "status": "pass",
            "provider": "fake_price",
            "interval": "1d",
            "row_count": 10,
            "requested_symbols": ["SPY", "^VIX"],
            "returned_symbols": ["SPY"],
            "missing_mapped_symbols": [],
            "missing_requested_symbols": ["^VIX"],
            "artifacts": {},
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    reference = next(
        item for item in manifest["requirements"] if item["key"] == "real_market_reference"
    )
    assert reference["status"] == "fail"
    assert reference["details"]["missing_requested_symbols"] == ["^VIX"]
    assert any(item["key"] == "collect_real_market_reference" for item in manifest["next_actions"])


def test_build_trade_xyz_data_readiness_manifest_fails_partial_signal_candles(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/trade_xyz_signal_candles_manifest.json",
        {
            "schema_version": "trade_xyz_signal_candles_manifest.v1",
            "source": "hyperliquid_info_candleSnapshot",
            "row_count": 10,
            "symbol_count": 1,
            "symbols": ["SP500"],
            "requested_symbols": ["SP500", "NVDA"],
            "intervals": ["30m"],
            "requested_intervals": ["30m", "4h"],
            "request_error_count": 0,
            "request_errors": {},
            "artifacts": {},
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    candles = next(item for item in manifest["requirements"] if item["key"] == "signal_candles")
    assert candles["status"] == "fail"
    assert candles["details"]["missing_symbols"] == ["NVDA"]
    assert candles["details"]["missing_intervals"] == ["4h"]
    assert any(item["key"] == "collect_signal_candles" for item in manifest["next_actions"])


def test_build_trade_xyz_data_readiness_manifest_suggests_signal_candle_failed_subset(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/trade_xyz_signal_candles_manifest.json",
        {
            "schema_version": "trade_xyz_signal_candles_manifest.v1",
            "source": "hyperliquid_info_candleSnapshot",
            "row_count": 10,
            "symbol_count": 2,
            "symbols": ["SP500", "NVDA"],
            "requested_symbols": ["SP500", "NVDA"],
            "intervals": ["30m", "4h", "1d", "3d"],
            "requested_intervals": ["30m", "4h", "1d", "3d"],
            "request_error_count": 2,
            "request_errors": [
                {
                    "canonical_symbol": "SP500",
                    "coin": "xyz:SP500",
                    "interval": "30m",
                    "error": "TradeXyzApiError: info endpoint failed: 429 null",
                },
                {
                    "canonical_symbol": "NVDA",
                    "coin": "xyz:NVDA",
                    "interval": "4h",
                    "error": "TradeXyzApiError: info endpoint failed: 429 null",
                },
            ],
            "artifacts": {},
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    action = next(
        item for item in manifest["next_actions"] if item["key"] == "collect_signal_candles"
    )
    assert "--symbols NVDA,SP500" in action["command"]
    assert "--intervals 30m,4h" in action["command"]
    assert "--request-delay-seconds 3" in action["command"]


def test_build_trade_xyz_data_readiness_manifest_checks_signal_candles_against_registry(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_registry(data_dir / "registry/trade_xyz_instrument_registry.json", ["SP500", "NVDA"])
    _write_json(
        data_dir / "manifests/trade_xyz_signal_candles_manifest.json",
        {
            "schema_version": "trade_xyz_signal_candles_manifest.v1",
            "source": "hyperliquid_info_candleSnapshot",
            "row_count": 10,
            "symbol_count": 1,
            "symbols": ["SP500"],
            "requested_symbols": ["SP500"],
            "intervals": ["30m", "4h", "1d", "3d"],
            "requested_intervals": ["30m", "4h", "1d", "3d"],
            "request_error_count": 0,
            "request_errors": {},
            "artifacts": {},
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    candles = next(item for item in manifest["requirements"] if item["key"] == "signal_candles")
    assert candles["status"] == "fail"
    assert candles["details"]["expected_symbols"] == ["NVDA", "SP500"]
    assert candles["details"]["missing_symbols"] == ["NVDA"]


def test_build_trade_xyz_data_readiness_manifest_strict_mode_blocks_known_gaps(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
        allow_known_gaps=False,
    )

    assert manifest["decision"] == "NOT_READY"
    assert manifest["backtest_data_ready"] is False
    assert manifest["fail_count"] == 0
    assert manifest["known_gap_count"] == 2


def test_build_trade_xyz_data_readiness_manifest_fails_missing_required_manifest(
    tmp_path,
) -> None:
    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=tmp_path / "data",
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["decision"] == "NOT_READY"
    assert manifest["backtest_data_ready"] is False
    assert manifest["fail_count"] >= 1
    assert any(
        item["key"] == "quote_coverage" and item["status"] == "fail"
        for item in manifest["requirements"]
    )
    assert any(item["key"] == "collect_funding_history" for item in manifest["next_actions"])


def test_build_trade_xyz_data_readiness_manifest_records_quote_collection_next_action(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)
    _write_json(
        data_dir / "manifests/trade_xyz_quote_coverage_manifest.json",
        {
            "schema_version": "trade_xyz_quote_coverage_manifest.v1",
            "coverage_passed": False,
            "symbol_count": 1,
            "row_count": 10,
            "per_symbol": {
                "SP500": {
                    "coverage_status": "insufficient",
                    "row_count": 10,
                    "span_days": 1.25,
                    "min_days_required": 30.0,
                    "insufficient_reasons": ["span_days_below_min", "raw_payload_ref_missing"],
                    "missing_rates": {"raw_payload_ref": 1.0},
                }
            },
        },
    )

    manifest = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["decision"] == "NOT_READY"
    action = next(
        item for item in manifest["next_actions"] if item["key"] == "collect_quote_coverage"
    )
    assert action["symbols"] == ["SP500"]
    assert "collect-trade-xyz-data-cycle" in action["command"]
    assert "--duration-minutes 1440" in action["command"]
    assert "--interval-seconds 60" in action["command"]
    assert "--symbols SP500" in action["command"]
    assert action["recommended_collection_duration_minutes"] == 1440
    assert action["recommended_interval_seconds"] == 60
    assert action["estimated_collection_days_required_by_symbol"]["SP500"] == 29
    assert action["estimated_max_collection_days_required"] == 29
    assert (
        action["follow_up_command"] == "uv run sis trade-xyz-collection-status --fail-on-not-ready"
    )
    assert action["insufficient_reasons_by_symbol"]["SP500"] == [
        "span_days_below_min",
        "raw_payload_ref_missing",
    ]


def test_build_trade_xyz_data_readiness_cli_writes_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_ready_inputs(data_dir)

    result = CliRunner().invoke(
        app,
        ["build-trade-xyz-data-readiness", "--allow-known-gaps"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "decision=READY_WITH_KNOWN_GAPS" in result.stdout
    assert "backtest_data_ready=True" in result.stdout
    assert (data_dir / "manifests/trade_xyz_data_readiness_manifest.json").exists()
