from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sis.venues.trade_xyz.historical_archive_preflight_manifest import (
    build_historical_archive_preflight_manifest,
)


def test_build_historical_archive_preflight_manifest_records_pass_payload() -> None:
    manifest = build_historical_archive_preflight_manifest(
        generated=datetime(2026, 5, 31, 1, 2, 3, tzinfo=UTC),
        data_dir=Path("data"),
        aws_status={
            "available": True,
            "source": "SIS_AWS_COMMAND",
            "command_prefix": ["custom-aws", "--profile", "trade"],
            "requires_network_for_tool_install": False,
        },
        command=["custom-aws", "--profile", "trade", "sts", "get-caller-identity"],
        return_code=0,
        stdout="  account-ok\n",
        stderr="  \n",
    )

    assert manifest == {
        "schema_version": "trade_xyz_historical_archive_preflight_manifest.v1",
        "generated_at": "2026-05-31T01:02:03+00:00",
        "source": "hyperliquid_archive.preflight",
        "data_dir": "data",
        "aws_available": True,
        "aws_command_source": "SIS_AWS_COMMAND",
        "aws_command_prefix": ["custom-aws", "--profile", "trade"],
        "aws_requires_network_for_tool_install": False,
        "preflight_command": [
            "custom-aws",
            "--profile",
            "trade",
            "sts",
            "get-caller-identity",
        ],
        "return_code": 0,
        "status": "pass",
        "stdout": "account-ok",
        "stderr": "",
        "notes": [
            "This preflight checks AWS identity before requester-pays archive download.",
            "It does not download historical archive objects.",
        ],
    }


def test_build_historical_archive_preflight_manifest_records_missing_aws_payload() -> None:
    manifest = build_historical_archive_preflight_manifest(
        generated=datetime(2026, 5, 31, tzinfo=UTC),
        data_dir=Path("data"),
        aws_status={
            "available": False,
            "source": "missing",
            "command_prefix": ["aws"],
            "requires_network_for_tool_install": True,
        },
        command=["aws", "sts", "get-caller-identity"],
        return_code=127,
        stdout="",
        stderr=" aws command not found ",
    )

    assert manifest["status"] == "fail"
    assert manifest["aws_available"] is False
    assert manifest["aws_requires_network_for_tool_install"] is True
    assert manifest["stderr"] == "aws command not found"
