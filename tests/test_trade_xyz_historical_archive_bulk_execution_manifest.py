from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sis.venues.trade_xyz.historical_archive_bulk_execution_manifest import (
    build_bulk_execution_manifest,
)


def _aws_status() -> dict:
    return {
        "available": True,
        "source": "system",
        "command_prefix": ["aws"],
        "requires_network_for_tool_install": False,
    }


def test_build_bulk_execution_manifest_preserves_blocked_preflight_payload() -> None:
    selected = [{"kind": "l2", "destination": "data/raw/l2.lz4"}]

    manifest = build_bulk_execution_manifest(
        generated=datetime(2026, 5, 31, tzinfo=UTC),
        plan_path=Path("data/manifests/plan.json"),
        dry_run=False,
        acknowledge_requester_pays=True,
        aws_status=_aws_status(),
        include_l2=True,
        include_asset_ctxs=False,
        skip_existing=True,
        decompress=True,
        max_objects=1,
        candidates=selected,
        selected=selected,
        skipped_existing=0,
        downloaded=0,
        decompressed=0,
        command_errors=[],
        preflight_status={"status": "fail"},
        blocked_preflight=True,
    )

    assert manifest["schema_version"] == "trade_xyz_historical_archive_bulk_execution_manifest.v1"
    assert manifest["generated_at"] == "2026-05-31T00:00:00+00:00"
    assert manifest["status"] == "blocked_preflight_failed"
    assert manifest["downloaded_object_count"] == 0
    assert manifest["decompressed_object_count"] == 0
    assert manifest["command_error_count"] == 0
    assert manifest["selected_objects"] == selected
    assert manifest["preflight"] == {"status": "fail"}
    assert "blocked before download" in manifest["notes"][0]


def test_build_bulk_execution_manifest_planned_dry_run_payload() -> None:
    selected = [{"kind": "asset_ctxs", "destination": "data/raw/asset.lz4"}]

    manifest = build_bulk_execution_manifest(
        generated=datetime(2026, 5, 31, tzinfo=UTC),
        plan_path=Path("data/manifests/plan.json"),
        dry_run=True,
        acknowledge_requester_pays=False,
        aws_status=_aws_status(),
        include_l2=False,
        include_asset_ctxs=True,
        skip_existing=False,
        decompress=False,
        max_objects=3,
        candidates=selected,
        selected=selected,
        skipped_existing=2,
        downloaded=0,
        decompressed=0,
        command_errors=[],
        preflight_status={},
    )

    assert manifest["status"] == "planned"
    assert manifest["requester_pays_acknowledged"] is False
    assert manifest["candidate_object_count"] == 1
    assert manifest["selected_object_count"] == 1
    assert manifest["skipped_existing_count"] == 2
    assert manifest["decompress_requested"] is False
    assert "Use max_objects" in manifest["notes"][1]


def test_build_bulk_execution_manifest_completed_with_errors_payload() -> None:
    command_errors = [{"item": {"kind": "l2"}, "error": "boom"}]

    manifest = build_bulk_execution_manifest(
        generated=datetime(2026, 5, 31, tzinfo=UTC),
        plan_path=Path("data/manifests/plan.json"),
        dry_run=False,
        acknowledge_requester_pays=True,
        aws_status=_aws_status(),
        include_l2=True,
        include_asset_ctxs=True,
        skip_existing=True,
        decompress=True,
        max_objects=None,
        candidates=[{"kind": "asset_ctxs"}, {"kind": "l2"}],
        selected=[{"kind": "l2"}],
        skipped_existing=1,
        downloaded=1,
        decompressed=0,
        command_errors=command_errors,
        preflight_status={"status": "pass"},
    )

    assert manifest["status"] == "completed_with_errors"
    assert manifest["downloaded_object_count"] == 1
    assert manifest["decompressed_object_count"] == 0
    assert manifest["command_error_count"] == 1
    assert manifest["command_errors"] == command_errors
