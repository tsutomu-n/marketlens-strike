from __future__ import annotations

import json
from pathlib import Path

from sis.commands.runtime_read_order import runtime_recommended_read_order


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_runtime_recommended_read_order_prefers_operations_bundle_manifest(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "ops/operations_bundle_manifest.json",
        {"recommended_read_order": ["bundle.md", 123]},
    )
    _write_json(
        tmp_path / "ops/operations_dashboard_summary.json",
        {"recommended_read_order": ["dashboard.md"]},
    )

    assert runtime_recommended_read_order(tmp_path) == ["bundle.md", "123"]


def test_runtime_recommended_read_order_falls_back_to_dashboard_summary(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "ops/operations_dashboard_summary.json",
        {"recommended_read_order": ["dashboard.md"]},
    )

    assert runtime_recommended_read_order(tmp_path) == ["dashboard.md"]


def test_runtime_recommended_read_order_ignores_non_list_values(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "ops/operations_bundle_manifest.json",
        {"recommended_read_order": "bundle.md"},
    )
    _write_json(
        tmp_path / "ops/operations_dashboard_summary.json",
        {"recommended_read_order": "dashboard.md"},
    )

    order = runtime_recommended_read_order(tmp_path)

    assert order[:7] == [
        "docs/CURRENT_STATE.md",
        "docs/CODE_STATUS.md",
        "data/ops/execution_snapshot_summary.json",
        "data/ops/operations_dashboard_summary.json",
        "data/ops/audit_dashboard_summary.json",
        "data/ops/operations_bundle_manifest.json",
        "data/ops/audit_bundle_manifest.json",
    ]
    assert order[-2:] == [
        "docs/OPERATIONS_RUNBOOK.md",
        "docs/ARCHITECTURE_AND_PHASES.md",
    ]
