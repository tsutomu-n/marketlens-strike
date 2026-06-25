from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.reports.doc_paths import recommended_read_order
from sis.storage.jsonl_store import read_json


def _read_recommended_read_order(path: Path) -> list[str] | None:
    if not path.exists():
        return None
    payload = read_json(path)
    if not isinstance(payload, dict):
        return None
    order = cast(dict[str, Any], payload).get("recommended_read_order")
    if not isinstance(order, list):
        return None
    return [str(item) for item in order]


def runtime_recommended_read_order(settings_data_dir: Path) -> list[str]:
    bundle_order = _read_recommended_read_order(
        settings_data_dir / "ops/operations_bundle_manifest.json"
    )
    if bundle_order is not None:
        return bundle_order
    dashboard_order = _read_recommended_read_order(
        settings_data_dir / "ops/operations_dashboard_summary.json"
    )
    if dashboard_order is not None:
        return dashboard_order
    return recommended_read_order(
        [
            "data/ops/execution_snapshot_summary.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
        ]
    )
