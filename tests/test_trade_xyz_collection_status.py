import json
from datetime import UTC, datetime
from pathlib import Path

from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.collection_status import build_trade_xyz_collection_status


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_trade_xyz_collection_status_reports_raw_inventory_breakdown(tmp_path) -> None:
    data_dir = tmp_path / "data"
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        "\n".join(
            [
                (
                    '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
                    '"canonical_symbol":"NVDA","venue_symbol":"NVDA",'
                    '"source":"trade_xyz_l2Book","raw_payload_ref":"fixture://row0"}'
                ),
                (
                    '{"ts_client":"2026-05-31T00:01:00+00:00","venue":"trade_xyz",'
                    '"symbol":"sp500","source":"trade_xyz_l2Book"}'
                ),
                (
                    '{"ts_client":"2026-05-31T00:02:00+00:00","venue":"trade_xyz",'
                    '"source":"trade_xyz_l2Book"}'
                ),
                "not-json",
                "[]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    status = build_trade_xyz_collection_status(
        data_dir=data_dir,
        refresh_coverage=False,
        refresh_readiness=False,
        generated_at=datetime(2026, 5, 31, 0, 3, tzinfo=UTC),
    )

    inventory = status["raw_quote_inventory"]
    assert inventory["row_count"] == 5
    assert inventory["traceable_row_count"] == 1
    assert inventory["untraceable_row_count"] == 4
    assert inventory["malformed_row_count"] == 2
    assert inventory["missing_symbol_row_count"] == 1
    assert inventory["symbol_counts"] == {"<missing>": 1, "NVDA": 1, "SP500": 1}
    assert inventory["source_counts"] == {"trade_xyz_l2Book": 3}
    assert inventory["files"][0]["symbol_counts"] == {"<missing>": 1, "NVDA": 1, "SP500": 1}
    assert inventory["files"][0]["malformed_row_count"] == 2

    report = (data_dir / "reports/trade_xyz_collection_status.md").read_text(encoding="utf-8")
    assert "malformed_rows: 2" in report
    assert "missing_symbol_rows: 1" in report
    assert "raw_symbol_counts: <missing>:1,NVDA:1,SP500:1" in report
    assert "raw_source_counts: trade_xyz_l2Book:3" in report


def test_trade_xyz_collection_status_surfaces_readiness_next_actions(tmp_path) -> None:
    data_dir = tmp_path / "data"
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    _write_json(
        data_dir / "manifests/trade_xyz_quote_coverage_manifest.json",
        {
            "schema_version": "trade_xyz_quote_coverage_manifest.v1",
            "coverage_passed": False,
            "traceable_only": True,
            "row_count": 1,
            "raw_row_count": 1,
            "excluded_missing_raw_payload_ref_count": 0,
            "per_symbol": {
                "NVDA": {
                    "coverage_status": "insufficient",
                    "row_count": 1,
                    "raw_row_count": 1,
                    "span_days": 0.0,
                    "min_days_required": 30.0,
                    "insufficient_reasons": ["span_days_below_min"],
                    "missing_rates": {},
                }
            },
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_data_readiness_manifest.json",
        {
            "decision": "NOT_READY",
            "backtest_data_ready": False,
            "fail_count": 1,
            "known_gap_count": 1,
            "requirements": [
                {"key": "quote_coverage", "status": "fail"},
                {"key": "account_specific_fee", "status": "known_gap"},
                {
                    "key": "funding_events",
                    "status": "known_gap",
                    "reason": "funding history join is partial",
                    "details": {
                        "row_count": 3,
                        "skipped": {"missing_oracle_quote_within_lag": 2},
                        "max_oracle_lag_minutes": 90.0,
                    },
                },
                {
                    "key": "oracle_timestamp_provenance",
                    "status": "known_gap",
                    "details": {
                        "row_count": 10,
                        "oracle_ts_present_count": 0,
                        "oracle_ts_missing_count": 10,
                        "oracle_ts_missing_rate": 1.0,
                        "oracle_freshness_proxy": {
                            "observed_count": 8,
                            "missing_count": 2,
                            "observed_rate": 0.8,
                            "status_counts": {
                                "observed_snapshot_lag": 8,
                                "missing_snapshot_timestamp": 2,
                            },
                        },
                    },
                },
                {
                    "key": "signal_candles",
                    "status": "pass",
                    "details": {
                        "row_count": 10,
                        "request_error_count": 0,
                        "missing_symbols": [],
                        "missing_intervals": [],
                    },
                },
            ],
            "next_actions": [
                {
                    "key": "collect_quote_coverage",
                    "command": "uv run sis collect-trade-xyz-quotes",
                },
                {
                    "key": "collect_account_fee",
                    "command": "uv run sis collect-trade-xyz-account-fee --user-address 0x...",
                    "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
                },
            ],
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_historical_archive_preflight_manifest.json",
        {
            "schema_version": "trade_xyz_historical_archive_preflight_manifest.v1",
            "status": "fail",
            "return_code": 255,
            "aws_command_source": "fixture",
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json",
        {
            "schema_version": "trade_xyz_historical_archive_bulk_plan_manifest.v1",
            "generated_at": "2026-05-31T00:00:00+00:00",
            "source": "hyperliquid_historical_archive",
            "start_date": "2026-05-01",
            "end_date": "2026-05-30",
            "coins": ["xyz:NVDA"],
            "hours": [0, 1],
            "date_count": 30,
            "estimated_l2_object_count": 60,
            "estimated_asset_ctx_object_count": 30,
            "estimated_total_object_count": 90,
            "requester_pays_ack_required": True,
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_execution_manifest.json",
        {
            "schema_version": "trade_xyz_historical_archive_bulk_execution_manifest.v1",
            "generated_at": "2026-05-31T00:02:00+00:00",
            "status": "planned",
            "dry_run": True,
            "max_objects": 10,
            "candidate_object_count": 90,
            "selected_object_count": 10,
            "downloaded_object_count": 0,
            "decompressed_object_count": 0,
            "skipped_existing_count": 0,
            "command_error_count": 0,
            "requester_pays_acknowledged": False,
            "aws_command_source": "fixture",
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_quote_normalization_manifest.json",
        {
            "schema_version": "trade_xyz_historical_archive_bulk_quote_normalization_manifest.v1",
            "generated_at": "2026-05-31T00:03:00+00:00",
            "status": "completed",
            "normalized_file_count": 1,
            "rows_written": 2,
            "normalized_row_count": 2,
            "skipped_existing_count": 0,
            "missing_l2_count": 0,
            "missing_asset_ctxs_count": 0,
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_account_fee_manifest.json",
        {
            "schema_version": "trade_xyz_account_fee_manifest.v1",
            "generated_at": "2026-05-31T00:04:00+00:00",
            "status": "pass",
            "source": "hyperliquid_info_userFees",
            "raw_artifact_path": str(data_dir / "raw/fees/trade_xyz_account/example.json"),
            "user_address_sha256": "fee-user-sha",
            "payload_field_keys": ["userAddRate", "userCrossRate"],
            "available_fields": ["userCrossRate", "userAddRate"],
            "missing_fields": [],
            "parsed": {
                "user_cross_rate": "0.0009",
                "user_add_rate": "0.0003",
                "user_taker_fee_bps": 9.0,
                "user_maker_fee_bps": 3.0,
            },
        },
    )

    status = build_trade_xyz_collection_status(
        data_dir=data_dir,
        refresh_coverage=False,
        refresh_readiness=False,
        collector_process_rows=[],
        supervisor_process_rows=[],
        generated_at=datetime(2026, 5, 31, 0, 1, tzinfo=UTC),
    )

    action_keys = [item["key"] for item in status["next_actions"]]
    assert action_keys == [
        "collect_trade_xyz_data_cycle",
        "historical_archive_backfill",
        "start_trade_xyz_data_cycle",
        "collect_account_fee",
    ]
    assert status["collector_process"]["running"] is False
    assert status["supervisor_process"]["running"] is False
    report = (data_dir / "reports/trade_xyz_collection_status.md").read_text(encoding="utf-8")
    assert "collector_running: False" in report
    assert "supervisor_running: False" in report
    assert "aws_cli_available:" in report
    assert "aws_command_source:" in report
    assert "historical_archive_preflight_status:" in report
    assert "lz4_available:" in report
    assert "account_fee_user_address_configured: False" in report
    assert "failing_requirements: quote_coverage" in report
    assert "known_gap_requirements: account_specific_fee" in report
    assert "funding_events_status: known_gap" in report
    assert "oracle_ts_missing_rate: 1.0" in report
    assert "oracle_freshness_proxy_observed_rate: 0.8" in report
    assert "signal_candles_status: pass" in report
    assert "collect_trade_xyz_data_cycle.sh" in report
    assert "plan_command:" in report
    assert "preflight_command:" in report
    assert "preflight_status:" in report
    assert "historical_archive_bulk_plan_exists: True" in report
    assert "historical_archive_bulk_plan_estimated_total_object_count: 90" in report
    assert "historical_archive_bulk_execution_status: planned" in report
    assert "historical_archive_bulk_execution_dry_run: True" in report
    assert "historical_archive_bulk_execution_selected_object_count: 10" in report
    assert "historical_archive_bulk_execution_downloaded_object_count: 0" in report
    assert "historical_archive_bulk_execution_command_error_count: 0" in report
    assert "historical_archive_bulk_normalization_status: completed" in report
    assert "historical_archive_bulk_normalization_normalized_file_count: 1" in report
    assert "ws_capture_manifest_exists: False" in report
    assert "ws_quality_manifest_exists: False" in report
    assert "ws_rest_parity_manifest_exists: False" in report
    assert "account_fee_manifest_exists: True" in report
    assert "account_fee_manifest_status: pass" in report
    assert "account_fee_user_taker_fee_bps: 9.0" in report
    assert "account_fee_user_maker_fee_bps: 3.0" in report
    assert "dry_run_command:" in report
    assert "execute_command:" in report
    assert "follow_up_command:" in report
    assert "execute-trade-xyz-historical-archive-bulk" in report
    assert "--execute --acknowledge-requester-pays" in report
    assert "collect-trade-xyz-account-fee" in report
    persisted = read_json(data_dir / "ops/trade_xyz_collection_status.json")
    assert persisted["next_actions"][1]["key"] == "historical_archive_backfill"
    assert persisted["next_actions"][1]["plan_command"].startswith(
        "uv run sis plan-trade-xyz-historical-archive-bulk"
    )
    assert "sts get-caller-identity" in persisted["next_actions"][1]["preflight_command"]
    assert persisted["next_actions"][1]["dry_run_command"].endswith("--max-objects 10")
    assert "aws_preflight_failed" in persisted["next_actions"][1]["blocked_by"]
    assert persisted["next_actions"][1]["preflight_status"] == "fail"
    assert (
        "--execute --acknowledge-requester-pays" in persisted["next_actions"][1]["execute_command"]
    )
    assert persisted["next_actions"][-1]["key"] == "collect_account_fee"
    assert persisted["next_actions"][-1]["env_var"] == "SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS"
    assert persisted["next_actions"][-1]["env_configured"] is False
    assert persisted["historical_archive_preflight"]["exists"] is True
    assert persisted["historical_archive_preflight"]["status"] == "fail"
    assert persisted["historical_archive_artifacts"]["bulk_plan"]["exists"] is True
    assert (
        persisted["historical_archive_artifacts"]["bulk_plan"]["estimated_total_object_count"] == 90
    )
    assert persisted["historical_archive_artifacts"]["bulk_plan"]["coin_count"] == 1
    assert persisted["historical_archive_artifacts"]["bulk_plan"]["hour_count"] == 2
    assert persisted["historical_archive_artifacts"]["bulk_execution"]["status"] == "planned"
    assert persisted["historical_archive_artifacts"]["bulk_execution"]["dry_run"] is True
    assert (
        persisted["historical_archive_artifacts"]["bulk_execution"]["selected_object_count"] == 10
    )
    assert (
        persisted["historical_archive_artifacts"]["bulk_normalization"]["normalized_file_count"]
        == 1
    )
    assert persisted["ws_artifacts"]["capture"]["exists"] is False
    assert persisted["ws_artifacts"]["quality"]["exists"] is False
    assert persisted["ws_artifacts"]["rest_parity"]["exists"] is False
    assert persisted["account_fee_prerequisites"]["configured"] is False
    assert persisted["account_fee_artifact"]["exists"] is True
    assert persisted["account_fee_artifact"]["status"] == "pass"
    assert persisted["account_fee_artifact"]["user_address_sha256"] == "fee-user-sha"
    assert persisted["account_fee_artifact"]["matches_configured_user"] is None
    assert persisted["account_fee_artifact"]["user_taker_fee_bps"] == 9.0
    assert persisted["account_fee_artifact"]["user_maker_fee_bps"] == 3.0
    assert "aws_cli" in persisted["runtime_prerequisites"]
    assert "source" in persisted["runtime_prerequisites"]["aws_cli"]
    assert "command_prefix" in persisted["runtime_prerequisites"]["aws_cli"]
    assert "preflight_command" in persisted["runtime_prerequisites"]["aws_cli"]
    assert "lz4" in persisted["runtime_prerequisites"]
    assert persisted["readiness_requirements"]["fail"] == ["quote_coverage"]
    assert persisted["readiness_requirements"]["known_gap"] == [
        "account_specific_fee",
        "funding_events",
        "oracle_timestamp_provenance",
    ]
    assert (
        persisted["readiness_requirement_details"]["funding_events"]["skipped"][
            "missing_oracle_quote_within_lag"
        ]
        == 2
    )
    assert (
        persisted["readiness_requirement_details"]["oracle_timestamp_provenance"][
            "oracle_ts_missing_rate"
        ]
        == 1.0
    )
    assert (
        persisted["readiness_requirement_details"]["oracle_timestamp_provenance"][
            "oracle_freshness_proxy"
        ]["observed_rate"]
        == 0.8
    )


def test_trade_xyz_collection_status_records_running_collector(tmp_path) -> None:
    data_dir = tmp_path / "data"
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    _write_json(
        data_dir / "manifests/trade_xyz_quote_coverage_manifest.json",
        {
            "schema_version": "trade_xyz_quote_coverage_manifest.v1",
            "coverage_passed": False,
            "traceable_only": True,
            "row_count": 1,
            "raw_row_count": 1,
            "excluded_missing_raw_payload_ref_count": 0,
            "per_symbol": {
                "NVDA": {
                    "coverage_status": "insufficient",
                    "row_count": 1,
                    "raw_row_count": 1,
                    "span_days": 0.0,
                    "min_days_required": 30.0,
                    "insufficient_reasons": ["span_days_below_min"],
                    "missing_rates": {},
                }
            },
        },
    )

    status = build_trade_xyz_collection_status(
        data_dir=data_dir,
        refresh_coverage=False,
        refresh_readiness=False,
        collector_process_rows=[
            "123 uv run sis collect-trade-xyz-data-cycle --duration-minutes 1440"
        ],
        supervisor_process_rows=["456 bash scripts/collect_trade_xyz_data_until_ready.sh"],
        generated_at=datetime(2026, 5, 31, 0, 1, tzinfo=UTC),
    )

    assert status["collector_process"]["running"] is True
    assert status["collector_process"]["process_count"] == 1
    assert status["supervisor_process"]["running"] is True
    assert status["supervisor_process"]["process_count"] == 1
    assert status["coverage"]["min_span_days"] == 0.0
    assert status["coverage"]["max_remaining_days_exact"] == 30.0
    assert status["coverage"]["slowest_symbols"] == ["NVDA"]
    action_keys = [item["key"] for item in status["next_actions"]]
    assert "start_trade_xyz_data_cycle" not in action_keys
    assert status["locks"]["cycle"]["exists"] is False
    assert status["locks"]["cycle"]["stale"] is False


def test_trade_xyz_collection_status_records_progress_since_previous_status(tmp_path) -> None:
    data_dir = tmp_path / "data"
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
            '{"ts_client":"2026-05-31T00:01:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"b","raw_payload_ref":"fixture://row1"}\n'
        ),
        encoding="utf-8",
    )
    _write_json(
        data_dir / "manifests/trade_xyz_quote_coverage_manifest.json",
        {
            "schema_version": "trade_xyz_quote_coverage_manifest.v1",
            "coverage_passed": False,
            "traceable_only": True,
            "row_count": 2,
            "raw_row_count": 2,
            "excluded_missing_raw_payload_ref_count": 0,
            "per_symbol": {
                "NVDA": {
                    "coverage_status": "insufficient",
                    "row_count": 2,
                    "raw_row_count": 2,
                    "span_days": 0.001,
                    "min_days_required": 30.0,
                    "max_gap_seconds": 60.0,
                    "insufficient_reasons": ["span_days_below_min"],
                    "missing_rates": {},
                }
            },
        },
    )
    _write_json(
        data_dir / "ops/trade_xyz_collection_status.json",
        {
            "generated_at": "2026-05-31T00:00:00+00:00",
            "raw_quote_inventory": {"row_count": 1, "traceable_row_count": 1},
        },
    )

    status = build_trade_xyz_collection_status(
        data_dir=data_dir,
        refresh_coverage=False,
        refresh_readiness=False,
        collector_process_rows=[
            "123 uv run sis collect-trade-xyz-data-cycle --duration-minutes 1440"
        ],
        interval_seconds=60,
        generated_at=datetime(2026, 5, 31, 0, 3, tzinfo=UTC),
    )

    progress = status["progress_since_previous_status"]
    assert progress["previous_status_exists"] is True
    assert progress["seconds_since_previous_status"] == 180.0
    assert progress["row_count_delta"] == 1
    assert progress["traceable_row_count_delta"] == 1
    assert progress["status"] == "collecting_ok"


def test_trade_xyz_collection_status_warns_when_running_without_traceable_growth(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    _write_json(
        data_dir / "manifests/trade_xyz_quote_coverage_manifest.json",
        {
            "schema_version": "trade_xyz_quote_coverage_manifest.v1",
            "coverage_passed": False,
            "traceable_only": True,
            "row_count": 1,
            "raw_row_count": 1,
            "excluded_missing_raw_payload_ref_count": 0,
            "per_symbol": {
                "NVDA": {
                    "coverage_status": "insufficient",
                    "row_count": 1,
                    "raw_row_count": 1,
                    "span_days": 0.0,
                    "min_days_required": 30.0,
                    "insufficient_reasons": ["span_days_below_min"],
                    "missing_rates": {},
                }
            },
        },
    )
    _write_json(
        data_dir / "ops/trade_xyz_collection_status.json",
        {
            "generated_at": "2026-05-31T00:00:00+00:00",
            "raw_quote_inventory": {"row_count": 1, "traceable_row_count": 1},
        },
    )

    status = build_trade_xyz_collection_status(
        data_dir=data_dir,
        refresh_coverage=False,
        refresh_readiness=False,
        collector_process_rows=[
            "123 uv run sis collect-trade-xyz-data-cycle --duration-minutes 1440"
        ],
        interval_seconds=60,
        generated_at=datetime(2026, 5, 31, 0, 3, tzinfo=UTC),
    )

    progress = status["progress_since_previous_status"]
    assert progress["status"] == "warning"
    assert "no_traceable_row_growth_since_previous_status" in progress["warnings"]
    report = (data_dir / "reports/trade_xyz_collection_status.md").read_text(encoding="utf-8")
    assert "progress_status: warning" in report
    assert "traceable_row_count_delta: 0" in report
    assert "coverage_min_span_days: 0.0" in report
    assert "coverage_slowest_symbols: NVDA" in report


def test_trade_xyz_collection_status_reports_stale_locks(tmp_path) -> None:
    data_dir = tmp_path / "data"
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    _write_json(
        data_dir / "manifests/trade_xyz_quote_coverage_manifest.json",
        {
            "schema_version": "trade_xyz_quote_coverage_manifest.v1",
            "coverage_passed": False,
            "traceable_only": True,
            "row_count": 1,
            "raw_row_count": 1,
            "excluded_missing_raw_payload_ref_count": 0,
            "per_symbol": {
                "NVDA": {
                    "coverage_status": "insufficient",
                    "row_count": 1,
                    "raw_row_count": 1,
                    "span_days": 0.0,
                    "min_days_required": 30.0,
                    "insufficient_reasons": ["span_days_below_min"],
                    "missing_rates": {},
                }
            },
        },
    )
    cycle_lock = tmp_path / ".tmp/trade_xyz_data_cycle.lock"
    supervisor_lock = tmp_path / ".tmp/trade_xyz_data_until_ready.lock"
    cycle_lock.mkdir(parents=True)
    supervisor_lock.mkdir(parents=True)
    (cycle_lock / "pid").write_text("99999999\n", encoding="utf-8")

    status = build_trade_xyz_collection_status(
        data_dir=data_dir,
        refresh_coverage=False,
        refresh_readiness=False,
        collector_process_rows=[],
        supervisor_process_rows=[],
        cycle_lock_dir=cycle_lock,
        supervisor_lock_dir=supervisor_lock,
        generated_at=datetime(2026, 5, 31, 0, 1, tzinfo=UTC),
    )

    assert status["locks"]["cycle"]["exists"] is True
    assert status["locks"]["cycle"]["pid"] == 99999999
    assert status["locks"]["cycle"]["pid_running"] is False
    assert status["locks"]["cycle"]["stale"] is True
    assert status["locks"]["cycle"]["error"] == "pid_not_running"
    assert status["locks"]["supervisor"]["exists"] is True
    assert status["locks"]["supervisor"]["stale"] is True
    assert status["locks"]["supervisor"]["error"] == "missing_pid_file"
    report = (data_dir / "reports/trade_xyz_collection_status.md").read_text(encoding="utf-8")
    assert "cycle_lock_stale: True" in report
    assert "supervisor_lock_stale: True" in report
