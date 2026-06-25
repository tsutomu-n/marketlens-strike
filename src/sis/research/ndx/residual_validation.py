from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.research.ndx.residual_validation_artifacts import (
    artifact_reason_codes as _artifact_reason_codes,
)
from sis.research.ndx.residual_validation_artifacts import artifact_paths as _artifact_paths
from sis.research.ndx.residual_validation_artifacts import (
    load_and_check_artifacts as _load_and_check_artifacts,
)
from sis.research.ndx.residual_validation_outputs import ResidualValidationResult
from sis.research.ndx.residual_validation_outputs import (
    base_payload as _base_payload,
)
from sis.research.ndx.residual_validation_outputs import (
    write_outputs as _write_outputs,
)
from sis.research.ndx.residual_validation_metrics import (
    validation_metrics as _validation_metrics,
)
from sis.research.ndx.residual_validation_decisions import (
    ResidualValidationDecision,
)
from sis.research.ndx.residual_validation_decisions import (
    counter_dag_statuses as _counter_dag_statuses,
)
from sis.research.ndx.residual_validation_decisions import (
    decision_from_metrics as _decision_from_metrics,
)
from sis.research.ndx.residual_validation_decisions import (
    metric_reason_codes as _metric_reason_codes,
)
from sis.research.ndx.start_conditions import require_layer23_start_conditions


DEFAULT_THRESHOLDS = {
    "approval_min_residual_rows": 60,
    "approval_min_era_count": 3,
    "approval_min_rows_per_era": 10,
    "approval_min_combined_variance_retention": 0.25,
    "approval_min_abs_neutralized_ic": 0.02,
    "reject_max_combined_variance_retention": 0.25,
    "reject_max_abs_neutralized_ic": 0.01,
}


def run_residual_validation_gate(
    *,
    root: Path,
    artifact_dir: Path,
    reports_dir: Path,
    out_dir: Path,
    thresholds: dict[str, float] | None = None,
) -> ResidualValidationResult:
    effective_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    reason_codes: list[str] = []
    start_context: dict[str, Any] = {}
    try:
        start = require_layer23_start_conditions(root=root, artifact_dir=artifact_dir)
        start_context = {
            "layer_2_2_pack_hash": start.pack_hash,
            "exit_decision_path": start.decision_path.as_posix(),
            "freeze_manifest_path": start.freeze_manifest_path.as_posix(),
        }
    except Exception as exc:  # noqa: BLE001 - gate converts all start failures into decision artifacts.
        reason_codes.append("REVISE_2_2_START_CONDITIONS_FAILED")
        payload = _base_payload(
            decision="REVISE_2_2",
            reason_codes=reason_codes,
            thresholds=effective_thresholds,
            start_context={"error": str(exc)},
        )
        return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)

    paths = _artifact_paths(artifact_dir=artifact_dir, reports_dir=reports_dir)
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        reason_codes.append("REVISE_2_3_MISSING_ARTIFACT")
        payload = _base_payload(
            decision="REVISE_2_3",
            reason_codes=reason_codes,
            thresholds=effective_thresholds,
            start_context=start_context,
            artifact_checks={"missing": missing},
        )
        return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)

    try:
        checks = _load_and_check_artifacts(paths)
    except ValueError as exc:
        reason_codes.append(str(exc))
        decision: ResidualValidationDecision = (
            "REVISE_2_2" if str(exc).startswith("REVISE_2_2") else "REVISE_2_3"
        )
        payload = _base_payload(
            decision=decision,
            reason_codes=reason_codes,
            thresholds=effective_thresholds,
            start_context=start_context,
            artifact_checks={"error": str(exc)},
        )
        return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)

    metrics = _validation_metrics(
        residuals=checks["residuals"],
        neutralized=checks["neutralized"],
    )
    counter_dags = _counter_dag_statuses(metrics=metrics, artifact_checks=checks["artifact_checks"])
    reason_codes.extend(_artifact_reason_codes(checks["artifact_checks"]))
    reason_codes.extend(_metric_reason_codes(metrics, effective_thresholds))
    reason_codes.extend(
        status["reason_code"] for status in counter_dags.values() if status["status"] == "blocked"
    )
    decision = _decision_from_metrics(reason_codes, metrics, counter_dags, effective_thresholds)
    payload = _base_payload(
        decision=decision,
        reason_codes=reason_codes,
        thresholds=effective_thresholds,
        start_context=start_context,
        artifact_checks=checks["artifact_checks"],
        metrics=metrics,
        counter_dags=counter_dags,
    )
    return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)
