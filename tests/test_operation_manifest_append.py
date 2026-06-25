from __future__ import annotations

from sis.commands.operation_manifest_append import append_command_operation_manifest
from sis.ops.manifest_chain import (
    append_operation_manifest,
    create_operation_manifest,
    latest_operation_manifest,
)


def test_append_command_operation_manifest_creates_chain_without_parent(tmp_path) -> None:
    out = append_command_operation_manifest(
        tmp_path,
        operation="remediation_evaluator",
        mode="ops",
        command="uv run sis remediation-evaluator",
        status="completed",
        artifacts=["data/ops/remediation_evaluator_summary.json"],
        notes=["evaluator_status=completed", "auto_fail_count=0"],
    )

    latest = latest_operation_manifest(out)

    assert out == tmp_path / "ops/operation_manifests.jsonl"
    assert latest is not None
    assert latest["operation"] == "remediation_evaluator"
    assert latest["mode"] == "ops"
    assert latest["command"] == "uv run sis remediation-evaluator"
    assert latest["status"] == "completed"
    assert latest["parent_run_id"] is None
    assert latest["artifacts"] == ["data/ops/remediation_evaluator_summary.json"]
    assert latest["notes"] == ["evaluator_status=completed", "auto_fail_count=0"]


def test_append_command_operation_manifest_uses_latest_parent_run_id(tmp_path) -> None:
    chain_path = tmp_path / "ops/operation_manifests.jsonl"
    parent = create_operation_manifest(
        operation="operations_snapshot",
        mode="ops",
        command="uv run sis operations-bundle",
        status="ok",
    )
    append_operation_manifest(chain_path, parent)

    out = append_command_operation_manifest(
        tmp_path,
        operation="remediation_evidence",
        mode="ops",
        command="uv run sis remediation-evidence",
        status="pending",
        artifacts=[],
        notes=[],
    )

    latest = latest_operation_manifest(out)

    assert latest is not None
    assert latest["operation"] == "remediation_evidence"
    assert latest["parent_run_id"] == parent.run_id
