from __future__ import annotations

from pathlib import Path

import pytest

from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.historical_archive_download import execute_archive_manifest_plan
from sis.venues.trade_xyz.historical_archive_manifest import HistoricalArchiveManifestPlan


def _plan(tmp_path: Path) -> HistoricalArchiveManifestPlan:
    return HistoricalArchiveManifestPlan(
        manifest_path=tmp_path / "data/manifests/archive_manifest.json",
        lz4_path=tmp_path / "data/raw/archive.jsonl.lz4",
        decompressed_path=tmp_path / "data/raw/archive.jsonl",
        download_command=["aws", "s3", "cp", "s3://bucket/archive.lz4", "archive.lz4"],
        manifest={
            "schema_version": "test_archive_manifest.v1",
            "status": "planned",
            "download_command": ["aws", "s3", "cp", "s3://bucket/archive.lz4", "archive.lz4"],
        },
    )


def test_execute_archive_manifest_plan_persists_dry_run(tmp_path) -> None:
    plan = _plan(tmp_path)

    manifest = execute_archive_manifest_plan(
        data_dir=tmp_path / "data",
        plan=plan,
        acknowledge_requester_pays=False,
        dry_run=True,
        decompress=True,
        aws_status={"available": False},
        requester_pays_error="requester-pays",
        command_runner=lambda command: None,
        decompress_lz4_fn=lambda source, destination: None,
        preflight_status_fn=lambda data_dir: {"status": "pass"},
        preflight_error_fn=lambda status: None,
    )

    assert manifest["status"] == "planned"
    assert read_json(plan.manifest_path)["status"] == "planned"


def test_execute_archive_manifest_plan_blocks_without_requester_pays_ack(tmp_path) -> None:
    plan = _plan(tmp_path)

    with pytest.raises(ValueError, match="requester-pays"):
        execute_archive_manifest_plan(
            data_dir=tmp_path / "data",
            plan=plan,
            acknowledge_requester_pays=False,
            dry_run=False,
            decompress=True,
            aws_status={"available": True},
            requester_pays_error="requester-pays",
            command_runner=lambda command: None,
            decompress_lz4_fn=lambda source, destination: None,
            preflight_status_fn=lambda data_dir: {"status": "pass"},
            preflight_error_fn=lambda status: None,
        )

    assert read_json(plan.manifest_path)["status"] == "blocked_requires_requester_pays_ack"


def test_execute_archive_manifest_plan_persists_blocked_preflight(tmp_path) -> None:
    plan = _plan(tmp_path)

    with pytest.raises(RuntimeError, match="preflight has not passed"):
        execute_archive_manifest_plan(
            data_dir=tmp_path / "data",
            plan=plan,
            acknowledge_requester_pays=True,
            dry_run=False,
            decompress=True,
            aws_status={"available": True},
            requester_pays_error="requester-pays",
            command_runner=lambda command: None,
            decompress_lz4_fn=lambda source, destination: None,
            preflight_status_fn=lambda data_dir: {"status": "fail"},
            preflight_error_fn=lambda status: "preflight has not passed",
        )

    persisted = read_json(plan.manifest_path)
    assert persisted["status"] == "blocked_preflight_failed"
    assert persisted["preflight"] == {"status": "fail"}


def test_execute_archive_manifest_plan_downloads_and_decompresses(tmp_path) -> None:
    plan = _plan(tmp_path)
    commands: list[list[str]] = []

    def fake_runner(command: list[str]) -> None:
        commands.append(command)
        plan.lz4_path.write_bytes(b"lz4")

    def fake_decompress(source: Path, destination: Path) -> None:
        assert source == plan.lz4_path
        destination.write_bytes(b"jsonl")

    manifest = execute_archive_manifest_plan(
        data_dir=tmp_path / "data",
        plan=plan,
        acknowledge_requester_pays=True,
        dry_run=False,
        decompress=True,
        aws_status={"available": True},
        requester_pays_error="requester-pays",
        command_runner=fake_runner,
        decompress_lz4_fn=fake_decompress,
        preflight_status_fn=lambda data_dir: {"status": "pass"},
        preflight_error_fn=lambda status: None,
    )

    assert commands == [plan.download_command]
    assert manifest["status"] == "downloaded_and_decompressed"
    assert manifest["raw_lz4_bytes"] == 3
    assert manifest["decompressed_bytes"] == 5
    assert read_json(plan.manifest_path)["decompressed_bytes"] == 5
