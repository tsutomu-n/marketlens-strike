from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sis.storage.jsonl_store import append_jsonl, read_jsonl


@dataclass(frozen=True)
class OperationManifest:
    run_id: str
    created_at: str
    operation: str
    mode: str
    command: str
    status: str
    scheduled_for: str | None
    parent_run_id: str | None
    artifacts: list[str]
    notes: list[str]


def create_operation_manifest(
    *,
    operation: str,
    mode: str,
    command: str,
    status: str,
    scheduled_for: str | None = None,
    parent_run_id: str | None = None,
    artifacts: list[str] | None = None,
    notes: list[str] | None = None,
    now: datetime | None = None,
) -> OperationManifest:
    current = now.astimezone(timezone.utc) if now and now.tzinfo else (now or datetime.now(timezone.utc))
    return OperationManifest(
        run_id=current.strftime("%Y%m%d_%H%M%S"),
        created_at=current.isoformat(),
        operation=operation,
        mode=mode,
        command=command,
        status=status,
        scheduled_for=scheduled_for,
        parent_run_id=parent_run_id,
        artifacts=artifacts or [],
        notes=notes or [],
    )


def append_operation_manifest(path: Path, manifest: OperationManifest) -> Path:
    append_jsonl(
        path,
        {
            "run_id": manifest.run_id,
            "created_at": manifest.created_at,
            "operation": manifest.operation,
            "mode": manifest.mode,
            "command": manifest.command,
            "status": manifest.status,
            "scheduled_for": manifest.scheduled_for,
            "parent_run_id": manifest.parent_run_id,
            "artifacts": manifest.artifacts,
            "notes": manifest.notes,
        },
    )
    return path


def latest_operation_manifest(path: Path) -> dict | None:
    if not path.exists():
        return None
    latest: dict | None = None
    for item in read_jsonl(path):
        latest = item
    return latest
