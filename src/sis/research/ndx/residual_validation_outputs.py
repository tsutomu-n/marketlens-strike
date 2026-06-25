from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sis.research.ndx.artifacts import DAG_ID
from sis.research.ndx.artifacts import sha256_json
from sis.research.ndx.artifacts import utc_now_iso
from sis.research.ndx.artifacts import write_json
from sis.research.ndx.residual_validation_decisions import COUNTER_DAG_IDS
from sis.research.ndx.residual_validation_decisions import ResidualValidationDecision
from sis.research.ndx.residual_validation_reports import write_counter_dag_report
from sis.research.ndx.residual_validation_reports import write_validation_report


@dataclass(frozen=True)
class ResidualValidationResult:
    summary_path: Path
    decision_path: Path
    report_path: Path
    counter_dag_report_path: Path
    decision: ResidualValidationDecision
    reason_codes: list[str]


def base_payload(
    *,
    decision: ResidualValidationDecision,
    reason_codes: list[str],
    thresholds: dict[str, float],
    start_context: dict[str, Any] | None = None,
    artifact_checks: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    counter_dags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "ndx_residual_validation_summary.v1",
        "dag_id": DAG_ID,
        "created_at": utc_now_iso(),
        "decision": decision,
        "reason_codes": sorted(set(reason_codes)),
        "thresholds": thresholds,
        "start_context": start_context or {},
        "artifact_checks": artifact_checks or {},
        "metrics": metrics or {},
        "counter_dags": counter_dags or {},
        "scope": {
            "strategy_lab_export_written": False,
            "strategy_signals_written": False,
            "backtest_run": False,
            "paper_candidate_written": False,
            "paper_intent_preview_written": False,
            "live_order_written": False,
        },
    }


def write_outputs(
    *,
    out_dir: Path,
    reports_dir: Path,
    payload: dict[str, Any],
) -> ResidualValidationResult:
    summary_path = write_json(out_dir / "residual_validation_summary.json", payload)
    decision_payload = {
        "schema_version": "ndx_residual_validation_decision.v1",
        "dag_id": DAG_ID,
        "decision_id": sha256_json(
            {
                "dag_id": DAG_ID,
                "decision": payload["decision"],
                "reason_codes": payload["reason_codes"],
                "created_at": payload["created_at"],
            }
        ),
        "decision": payload["decision"],
        "reason_codes": payload["reason_codes"],
        "summary_path": summary_path.as_posix(),
        "created_at": payload["created_at"],
        "permits_strategy_lab_research_only_export": payload["decision"]
        == "APPROVE_STRATEGY_LAB_EXPORT",
        "permits_backtest": False,
        "permits_paper_candidate": False,
        "permits_paper_intent_preview": False,
        "permits_live_order": False,
    }
    decision_path = write_json(out_dir / "residual_validation_decision.json", decision_payload)
    report_path = write_validation_report(
        reports_dir / "ndx_residual_validation_report.md",
        payload=payload,
        decision_path=decision_path,
        dag_id=DAG_ID,
    )
    counter_dag_report_path = write_counter_dag_report(
        reports_dir / "ndx_counter_dag_refutation_report.md",
        payload=payload,
        dag_id=DAG_ID,
        counter_dag_ids=COUNTER_DAG_IDS,
    )
    return ResidualValidationResult(
        summary_path=summary_path,
        decision_path=decision_path,
        report_path=report_path,
        counter_dag_report_path=counter_dag_report_path,
        decision=payload["decision"],
        reason_codes=list(payload["reason_codes"]),
    )
