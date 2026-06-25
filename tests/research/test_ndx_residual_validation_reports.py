from pathlib import Path

from sis.research.ndx.residual_validation_reports import (
    write_counter_dag_report,
    write_validation_report,
)


def test_write_validation_report_includes_decision_boundary(tmp_path: Path) -> None:
    payload = {
        "decision": "APPROVE_STRATEGY_LAB_EXPORT",
        "reason_codes": [],
        "metrics": {
            "row_count": 90,
            "combined": {"variance_retention": 0.42},
        },
    }
    report_path = write_validation_report(
        tmp_path / "validation.md",
        payload=payload,
        decision_path=tmp_path / "decision.json",
        dag_id="HYP-NDX-001",
    )

    text = report_path.read_text(encoding="utf-8")
    assert "# NDX Layer 2.4 Residual Validation Report" in text
    assert "- dag_id: HYP-NDX-001" in text
    assert "- decision: APPROVE_STRATEGY_LAB_EXPORT" in text
    assert "- reason_codes: none" in text
    assert "- residual_row_count: 90" in text
    assert "- combined_variance_retention: 0.42" in text
    assert "- permits_strategy_lab_research_only_export: True" in text
    assert "- paper_or_live_allowed: false" in text


def test_write_counter_dag_report_preserves_order_and_missing_rows(tmp_path: Path) -> None:
    payload = {
        "decision": "REVISE_2_3",
        "counter_dags": {
            "BroadMarketOnly": {
                "status": "blocked",
                "reason_code": "BROADMARKETONLY_EXPLAINS_RESIDUAL",
            },
        },
    }
    report_path = write_counter_dag_report(
        tmp_path / "counter_dag.md",
        payload=payload,
        dag_id="HYP-NDX-001",
        counter_dag_ids=["BroadMarketOnly", "RatesOnly"],
    )

    text = report_path.read_text(encoding="utf-8")
    assert "# NDX Layer 2.4 Counter-DAG Refutation Report" in text
    assert "- dag_id: HYP-NDX-001" in text
    assert "- decision: REVISE_2_3" in text
    assert "| counter_dag | status | reason |" in text
    assert "| BroadMarketOnly | blocked | BROADMARKETONLY_EXPLAINS_RESIDUAL |" in text
    assert "| RatesOnly | missing | missing |" in text
