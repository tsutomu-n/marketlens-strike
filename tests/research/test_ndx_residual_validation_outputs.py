from __future__ import annotations

import json

from sis.research.ndx.artifacts import DAG_ID, sha256_json
from sis.research.ndx.residual_validation_outputs import base_payload
from sis.research.ndx.residual_validation_outputs import write_outputs


def test_base_payload_preserves_boundary_scope_and_sorts_reasons() -> None:
    payload = base_payload(
        decision="REVISE_2_3",
        reason_codes=["B", "A", "A"],
        thresholds={"approval_min_residual_rows": 60},
        start_context={"exit_decision_path": "decision.json"},
        artifact_checks={"lineage": "pass"},
        metrics={"row_count": 12},
        counter_dags={"DataSourceLag": {"status": "blocked"}},
    )

    assert payload["schema_version"] == "ndx_residual_validation_summary.v1"
    assert payload["dag_id"] == DAG_ID
    assert payload["decision"] == "REVISE_2_3"
    assert payload["reason_codes"] == ["A", "B"]
    assert payload["thresholds"] == {"approval_min_residual_rows": 60}
    assert payload["start_context"] == {"exit_decision_path": "decision.json"}
    assert payload["artifact_checks"] == {"lineage": "pass"}
    assert payload["metrics"] == {"row_count": 12}
    assert payload["counter_dags"] == {"DataSourceLag": {"status": "blocked"}}
    assert payload["scope"] == {
        "strategy_lab_export_written": False,
        "strategy_signals_written": False,
        "backtest_run": False,
        "paper_candidate_written": False,
        "paper_intent_preview_written": False,
        "live_order_written": False,
    }
    assert isinstance(payload["created_at"], str)


def test_write_outputs_writes_decision_contract_and_reports(tmp_path) -> None:
    payload = {
        "schema_version": "ndx_residual_validation_summary.v1",
        "dag_id": DAG_ID,
        "created_at": "2026-06-25T00:00:00+00:00",
        "decision": "APPROVE_STRATEGY_LAB_EXPORT",
        "reason_codes": [],
        "thresholds": {"approval_min_residual_rows": 60},
        "start_context": {},
        "artifact_checks": {},
        "metrics": {"row_count": 90, "combined": {"variance_retention": 0.42}},
        "counter_dags": {},
        "scope": {},
    }

    result = write_outputs(
        out_dir=tmp_path / "artifacts",
        reports_dir=tmp_path / "reports",
        payload=payload,
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    decision = json.loads(result.decision_path.read_text(encoding="utf-8"))

    assert result.decision == "APPROVE_STRATEGY_LAB_EXPORT"
    assert result.reason_codes == []
    assert summary == payload
    assert decision == {
        "schema_version": "ndx_residual_validation_decision.v1",
        "dag_id": DAG_ID,
        "decision_id": sha256_json(
            {
                "dag_id": DAG_ID,
                "decision": "APPROVE_STRATEGY_LAB_EXPORT",
                "reason_codes": [],
                "created_at": "2026-06-25T00:00:00+00:00",
            }
        ),
        "decision": "APPROVE_STRATEGY_LAB_EXPORT",
        "reason_codes": [],
        "summary_path": result.summary_path.as_posix(),
        "created_at": "2026-06-25T00:00:00+00:00",
        "permits_strategy_lab_research_only_export": True,
        "permits_backtest": False,
        "permits_paper_candidate": False,
        "permits_paper_intent_preview": False,
        "permits_live_order": False,
    }
    assert result.report_path.exists()
    assert result.counter_dag_report_path.exists()
