from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sis.venues.trade_xyz import collection_status_artifacts as artifacts


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_runtime_and_account_fee_prerequisites_are_summarized(monkeypatch) -> None:
    monkeypatch.setattr(
        artifacts,
        "aws_download_command_status",
        lambda: {
            "available": True,
            "source": "aws",
            "path": "/usr/bin/aws",
            "command_prefix": ["aws"],
            "requires_network_for_tool_install": False,
        },
    )
    monkeypatch.setattr(
        artifacts.shutil, "which", lambda name: "/usr/bin/lz4" if name == "lz4" else None
    )
    monkeypatch.setenv("SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS", "0xABC")

    runtime = artifacts.runtime_prerequisites()
    account_fee = artifacts.account_fee_prerequisites()

    assert runtime["aws_cli"]["available"] is True
    assert runtime["aws_cli"]["preflight_command"] == "aws sts get-caller-identity"
    assert runtime["lz4"]["available"] is True
    assert account_fee["configured"] is True
    assert account_fee["user_address_sha256"] == hashlib.sha256(b"0xabc").hexdigest()
    assert account_fee["required_for"] == ["account_specific_fee"]


def test_account_fee_artifact_status_reads_manifest_and_compares_configured_user(
    tmp_path,
) -> None:
    user_hash = hashlib.sha256(b"0xabc").hexdigest()
    data_dir = tmp_path / "data"
    _write_json(
        data_dir / "manifests/trade_xyz_account_fee_manifest.json",
        {
            "generated_at": "2026-05-31T00:04:00+00:00",
            "status": "pass",
            "source": "hyperliquid_info_userFees",
            "raw_artifact_path": "raw/account-fee.json",
            "user_address_sha256": user_hash,
            "missing_fields": [],
            "payload_field_keys": ["userCrossRate", "userAddRate"],
            "parsed": {
                "user_taker_fee_bps": 9.0,
                "user_maker_fee_bps": 3.0,
                "user_cross_rate": "0.0009",
                "user_add_rate": "0.0003",
            },
        },
    )

    result = artifacts.account_fee_artifact_status(
        data_dir,
        account_fee_prerequisites={"user_address_sha256": user_hash},
    )

    assert result["exists"] is True
    assert result["status"] == "pass"
    assert result["matches_configured_user"] is True
    assert result["user_taker_fee_bps"] == 9.0
    assert result["payload_field_keys"] == ["userCrossRate", "userAddRate"]


def test_historical_archive_and_ws_artifact_status_read_manifest_summaries(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json",
        {
            "generated_at": "2026-05-31T00:00:00+00:00",
            "source": "hyperliquid_s3",
            "start_date": "2026-05-01",
            "end_date": "2026-05-30",
            "coins": ["xyz:NVDA"],
            "date_count": 30,
            "hours": [0, 1],
            "estimated_total_object_count": 60,
            "requester_pays_ack_required": True,
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_execution_manifest.json",
        {
            "generated_at": "2026-05-31T00:01:00+00:00",
            "status": "planned",
            "dry_run": True,
            "selected_object_count": 10,
            "command_error_count": 0,
            "aws_command_source": "aws",
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_quote_normalization_manifest.json",
        {
            "generated_at": "2026-05-31T00:02:00+00:00",
            "status": "completed",
            "normalized_file_count": 1,
            "normalized_row_count": 100,
        },
    )
    _write_json(
        data_dir / "manifests/trade_xyz_ws_capture_manifest.json",
        {"status": "pass", "row_count": 3, "error_count": 0, "reconnect_count": 1},
    )
    _write_json(
        data_dir / "manifests/trade_xyz_ws_quality_manifest.json",
        {"status": "fail", "row_count": 3, "block_reasons": ["short_window"]},
    )
    _write_json(
        data_dir / "manifests/trade_xyz_rest_parity_manifest.json",
        {"status": "fail", "request_error_count": 2, "missing_rest_symbols": ["NVDA"]},
    )

    archive = artifacts.historical_archive_artifact_status(data_dir)
    ws = artifacts.ws_artifact_status(data_dir)

    assert archive["bulk_plan"]["coin_count"] == 1
    assert archive["bulk_plan"]["hour_count"] == 2
    assert archive["bulk_plan"]["estimated_total_object_count"] == 60
    assert archive["bulk_execution"]["status"] == "planned"
    assert archive["bulk_normalization"]["normalized_row_count"] == 100
    assert ws["capture"]["reconnect_count"] == 1
    assert ws["quality"]["block_reasons"] == ["short_window"]
    assert ws["rest_parity"]["missing_rest_symbols"] == ["NVDA"]


def test_historical_archive_backfill_action_builds_blocked_requester_pays_commands(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(artifacts, "DEFAULT_COLLECTION_CONFIG_PATH", tmp_path / "missing.toml")
    action = artifacts.historical_archive_backfill_action(
        data_dir=tmp_path / "data",
        failing_symbols=["NVDA"],
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
        coverage={"min_span_days": 0.0, "max_remaining_days_exact": 29.0},
        prerequisites={
            "aws_cli": {
                "available": False,
                "preflight_command": "aws sts get-caller-identity",
            },
            "lz4": {"available": False},
        },
        archive_preflight={"status": "fail", "return_code": 255},
    )

    assert action is not None
    assert action["key"] == "historical_archive_backfill"
    assert action["status"] == "blocked_by_prerequisites"
    assert action["blocked_by"] == ["missing_aws_command", "missing_lz4", "aws_preflight_failed"]
    assert action["coins"] == ["xyz:NVDA"]
    assert action["start_date"] == "2026-05-01"
    assert action["end_date"] == "2026-05-30"
    assert "--coins xyz:NVDA" in action["plan_command"]
    assert action["dry_run_command"].endswith("--max-objects 10")
    assert "--execute --acknowledge-requester-pays" in action["execute_command"]
    assert action["requester_pays_ack_required"] is True
