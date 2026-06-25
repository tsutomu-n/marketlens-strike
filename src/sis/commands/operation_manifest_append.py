from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

from sis.ops.manifest_chain import (
    append_operation_manifest,
    create_operation_manifest,
    latest_operation_manifest,
)


def append_command_operation_manifest(
    settings_data_dir: Path,
    *,
    operation: str,
    mode: str,
    command: str,
    status: str,
    artifacts: Sequence[str],
    notes: Sequence[str],
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    manifest = create_operation_manifest(
        operation=operation,
        mode=mode,
        command=command,
        status=status,
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=list(artifacts),
        notes=list(notes),
    )
    return append_operation_manifest(chain_path, manifest)
