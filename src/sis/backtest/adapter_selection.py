from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


SELECTED_FRAMEWORKS = {
    "vectorbt": (
        "high_speed_signal_runner",
        [
            "phase_b_imported",
            "first_external_signal_runner_already_smoked",
            "adapter_design_before_optional_extra",
        ],
        "Design a source-hashed vectorbt adapter contract before adding a locked optional extra.",
    ),
    "bt": (
        "portfolio_allocation_rebalance",
        [
            "phase_b_imported",
            "portfolio_allocation_role_matches_strategy_bundle_workflow",
            "adapter_design_before_optional_extra",
        ],
        "Design a portfolio allocation comparison adapter before adding a locked optional extra.",
    ),
    "empyrical_reloaded": (
        "metrics_normalization",
        [
            "phase_b_imported",
            "metrics_library_has_narrower_surface_than_tearsheet_report",
            "report_metric_extension_before_visual_report",
        ],
        "Design a metrics normalization extension before adding a locked report extra.",
    ),
    "quantstats": (
        "report_tearsheet",
        [
            "phase_b_imported",
            "metric_extension_contract_exists",
            "report_extension_without_locked_dependency",
        ],
        "Design a report extension artifact before adding a locked report extra.",
    ),
}

DEFERRED_FRAMEWORKS = {
    "backtesting": (
        "blocked_license_or_install",
        ["license_review_required_before_lock"],
        "Keep separate until AGPL review is complete.",
    ),
    "zipline_reloaded": (
        "blocked_license_or_install",
        ["build_smoke_required_before_optional_extra"],
        "Keep separate until build smoke is stable on Python 3.13.",
    ),
    "backtrader": (
        "blocked_license_or_install",
        ["license_review_required_before_lock", "live_surface_isolation_required"],
        "Keep separate until GPL and no-live isolation are reviewed.",
    ),
    "pyfolio_reloaded": (
        "report_tearsheet",
        ["not_in_phase_b_smoke", "defer_visual_report_until_metrics_contract_exists"],
        "Revisit after metrics normalization output is stable.",
    ),
    "qstrader": (
        "separate_runner_research",
        ["not_in_phase_b_smoke", "package_maturity_review_required"],
        "Revisit after package maturity and Python 3.13 smoke are verified.",
    ),
}


@dataclass(frozen=True)
class BacktestAdapterSelectionResult:
    selection_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _smoke_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("framework_id")): item
        for item in payload.get("results") or []
        if isinstance(item, dict)
    }


def _adapter_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("framework_id")): item
        for item in payload.get("candidates") or []
        if isinstance(item, dict)
    }


def _selection_item(
    *,
    framework_id: str,
    selection_status: str,
    selection_role: str,
    rationale_codes: list[str],
    next_step: str,
    smoke_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    smoke = smoke_results.get(framework_id, {})
    return {
        "framework_id": framework_id,
        "selection_status": selection_status,
        "selection_role": selection_role,
        "adoption_classification": smoke.get("adoption_classification")
        or "separate_runner_candidate",
        "version": smoke.get("version"),
        "requires_python": smoke.get("requires_python"),
        "import_status": smoke.get("import_status") or "not_smoked",
        "rationale_codes": rationale_codes,
        "next_step": next_step,
        "dependency_added": False,
        "engine_run": False,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def _selected_items(smoke_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for framework_id, (role, rationale, next_step) in SELECTED_FRAMEWORKS.items():
        selected.append(
            _selection_item(
                framework_id=framework_id,
                selection_status="selected_for_adapter_design",
                selection_role=role,
                rationale_codes=rationale,
                next_step=next_step,
                smoke_results=smoke_results,
            )
        )
    return selected


def _deferred_items(
    adapter_candidates: dict[str, dict[str, Any]],
    smoke_results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    deferred_ids = [
        "backtesting",
        "zipline_reloaded",
        "backtrader",
        "pyfolio_reloaded",
        "qstrader",
    ]
    deferred: list[dict[str, Any]] = []
    for framework_id in deferred_ids:
        role, rationale, next_step = DEFERRED_FRAMEWORKS[framework_id]
        candidate = adapter_candidates.get(framework_id, {})
        blockers = [
            str(item)
            for item in candidate.get("adoption_blockers") or []
            if str(item) != "not_installed_in_current_env"
        ]
        rationale_codes = [*rationale, *blockers]
        deferred.append(
            _selection_item(
                framework_id=framework_id,
                selection_status="deferred",
                selection_role=role,
                rationale_codes=sorted(set(rationale_codes)),
                next_step=next_step,
                smoke_results=smoke_results,
            )
        )
    return deferred


def _summary(selected: list[dict[str, Any]], deferred: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "selected_count": len(selected),
        "deferred_count": len(deferred),
        "optional_extra_selected_count": sum(
            1 for item in selected if item["adoption_classification"] == "optional_extra_candidate"
        ),
        "report_only_selected_count": sum(
            1 for item in selected if item["adoption_classification"] == "report_only_candidate"
        ),
        "separate_runner_selected_count": sum(
            1 for item in selected if item["adoption_classification"] == "separate_runner_candidate"
        ),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Adapter Selection",
        "",
        f"- created_at: {payload['created_at']}",
        "- policy_id: phase_c_adapter_selection.v1",
        "- standard_engine: strategy_authoring_native",
        "- dependency_added: false",
        "- external_engine_run: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        f"- selected_count: {payload['summary']['selected_count']}",
        f"- deferred_count: {payload['summary']['deferred_count']}",
        "",
        "## Selected",
        "",
        "| Framework | Role | Version | Requires Python | Next Step |",
        "|---|---|---|---|---|",
    ]
    for item in payload["selected_adapters"]:
        lines.append(
            "| {framework_id} | {role} | {version} | {requires_python} | {next_step} |".format(
                framework_id=item["framework_id"],
                role=item["selection_role"],
                version=item.get("version") or "",
                requires_python=item.get("requires_python") or "",
                next_step=item["next_step"],
            )
        )
    lines.extend(["", "## Deferred", "", "| Framework | Role | Rationale |", "|---|---|---|"])
    for item in payload["deferred_adapters"]:
        lines.append(
            "| {framework_id} | {role} | {rationale} |".format(
                framework_id=item["framework_id"],
                role=item["selection_role"],
                rationale=", ".join(item["rationale_codes"]),
            )
        )
    lines.extend(
        [
            "",
            "This selection does not add dependencies, run external engines, or permit live orders.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_backtest_adapter_selection(
    *,
    adapter_spike_path: Path,
    framework_smoke_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestAdapterSelectionResult:
    adapter_payload = _read_json(adapter_spike_path)
    smoke_payload = _read_json(framework_smoke_path)
    adapter_candidates = _adapter_by_id(adapter_payload)
    smoke_results = _smoke_by_id(smoke_payload)
    selected = _selected_items(smoke_results)
    deferred = _deferred_items(adapter_candidates, smoke_results)
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_adapter_selection.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "source_adapter_spike_path": adapter_spike_path.as_posix(),
        "source_adapter_spike_hash": _sha256_file(adapter_spike_path),
        "source_framework_smoke_path": framework_smoke_path.as_posix(),
        "source_framework_smoke_hash": _sha256_file(framework_smoke_path),
        "selection_policy": {
            "policy_id": "phase_c_adapter_selection.v1",
            "standard_engine": "strategy_authoring_native",
            "locked_dependency_added": False,
            "requires_before_dependency_adoption": [
                "license_review",
                "python_3_13_uv_lock_review",
                "ci_green",
                "schema_boundary_review",
                "optional_extra_decision",
            ],
        },
        "selected_adapters": selected,
        "deferred_adapters": deferred,
        "summary": _summary(selected, deferred),
        "decision": {
            "decision": "SELECT_PHASE_C_ADAPTERS",
            "reason_codes": [
                "phase_b_smoke_imported_selected_candidates",
                "native_engine_remains_standard",
                "dependency_adoption_deferred_until_review",
            ],
            "recommended_next_step": (
                "Design source-hashed adapter contracts for vectorbt and bt, then add metrics normalization with empyrical-reloaded."
            ),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    selection_path = out_dir / "strategy_backtest_adapter_selection.json"
    selection_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_adapter_selection_report.md", payload
    )
    return BacktestAdapterSelectionResult(
        selection_path=selection_path, report_path=report_path, payload=payload
    )
