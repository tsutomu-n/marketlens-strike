from __future__ import annotations

from pathlib import Path

from sis.ops.kill_switch import KillSwitch


def build_healthcheck(
    *,
    kill_switch: KillSwitch,
    decision_summary_path: Path | None = None,
    reconciliation_store_present: bool = False,
) -> dict:
    return {
        "kill_switch_enabled": kill_switch.is_enabled(),
        "decision_summary_exists": bool(decision_summary_path and decision_summary_path.exists()),
        "reconciliation_store_present": reconciliation_store_present,
        "status": "degraded" if kill_switch.is_enabled() else "ok",
    }
