from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

import typer


def dict_or_empty(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def state_snapshot_export_lines(snapshot_path: Path) -> list[str]:
    return [str(snapshot_path)]


def state_restore_ack_lines(*, restored: bool) -> list[str]:
    return [f"restored={str(restored).lower()}"]


def echo_state_snapshot_export(snapshot_path: Path) -> None:
    for line in state_snapshot_export_lines(snapshot_path):
        typer.echo(line)


def echo_state_restore_ack(*, restored: bool) -> None:
    for line in state_restore_ack_lines(restored=restored):
        typer.echo(line)


def echo_state_snapshot_summaries(
    payload: object,
    *,
    normalize_phase_gate_summary: Callable[[dict], dict],
    echo_audit_summary: Callable[[dict], None],
    echo_phase_gate_summary: Callable[[dict], None],
) -> None:
    if not isinstance(payload, dict):
        return

    snapshot = dict_or_empty(payload)
    audit = snapshot.get("audit_summary")
    if isinstance(audit, dict):
        echo_audit_summary(audit)

    phase_gate = snapshot.get("phase_gate_summary")
    if isinstance(phase_gate, dict):
        echo_phase_gate_summary(normalize_phase_gate_summary(phase_gate))
