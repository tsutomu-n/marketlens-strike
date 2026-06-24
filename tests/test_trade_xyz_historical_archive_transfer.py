from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sis.venues.trade_xyz.historical_archive_transfer import (
    HistoricalL2ArchiveRequest,
    aws_download_command_status,
    decompress_lz4,
    download_command,
    historical_archive_preflight_error,
)


def test_historical_l2_archive_request_builds_s3_and_output_paths() -> None:
    request = HistoricalL2ArchiveRequest(coin="xyz:NVDA", date=date(2026, 1, 2), hour=3)

    assert request.date_part == "20260102"
    assert request.s3_uri == ("s3://hyperliquid-archive/market_data/20260102/3/l2Book/xyz:NVDA.lz4")
    assert request.output_relative_path == Path(
        "raw/historical_archive/hyperliquid/market_data/20260102/3/l2Book/xyz:NVDA"
    )


def test_historical_l2_archive_request_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="coin is required"):
        HistoricalL2ArchiveRequest(coin="", date=date(2026, 1, 2), hour=3)
    with pytest.raises(ValueError, match="hour must be between 0 and 23"):
        HistoricalL2ArchiveRequest(coin="xyz:NVDA", date=date(2026, 1, 2), hour=24)
    with pytest.raises(ValueError, match="only l2Book"):
        HistoricalL2ArchiveRequest(
            coin="xyz:NVDA",
            date=date(2026, 1, 2),
            hour=3,
            data_type="trades",
        )


def test_aws_download_command_status_prefers_configured_command(monkeypatch) -> None:
    monkeypatch.setenv("SIS_AWS_COMMAND", "aws --profile archive")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)

    status = aws_download_command_status()

    assert status["available"] is True
    assert status["source"] == "SIS_AWS_COMMAND"
    assert status["path"] == "aws"
    assert status["command_prefix"] == ["aws", "--profile", "archive"]
    assert status["requires_network_for_tool_install"] is False


def test_download_command_includes_requester_payer(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("SIS_AWS_COMMAND", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/aws" if name == "aws" else None)

    command = download_command("s3://bucket/key.lz4", tmp_path / "key.lz4")

    assert command == [
        "/usr/bin/aws",
        "s3",
        "cp",
        "s3://bucket/key.lz4",
        str(tmp_path / "key.lz4"),
        "--request-payer",
        "requester",
    ]


def test_historical_archive_preflight_error_messages() -> None:
    assert historical_archive_preflight_error({"exists": True, "status": "pass"}) is None

    missing = historical_archive_preflight_error({"exists": False, "status": None})
    assert missing is not None
    assert "preflight has not been run" in missing

    failed = historical_archive_preflight_error({"exists": True, "status": "fail"})
    assert failed is not None
    assert "preflight has not passed" in failed


def test_decompress_lz4_delegates_to_lz4_command(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/lz4" if name == "lz4" else None)

    decompress_lz4(
        tmp_path / "source.jsonl.lz4",
        tmp_path / "nested/destination.jsonl",
        command_runner=commands.append,
    )

    assert commands == [
        [
            "/usr/bin/lz4",
            "-d",
            "-f",
            str(tmp_path / "source.jsonl.lz4"),
            str(tmp_path / "nested/destination.jsonl"),
        ]
    ]
    assert (tmp_path / "nested").is_dir()
