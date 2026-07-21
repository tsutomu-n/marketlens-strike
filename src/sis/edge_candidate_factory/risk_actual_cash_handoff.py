from __future__ import annotations

from datetime import datetime

from sis.edge_candidate_factory._contracts import RiskActualCashHandoffStatus
from sis.edge_candidate_factory.models import (
    ArtifactRef,
    ProducerInfo,
    RiskActualCashHandoff,
)


def build_risk_actual_cash_handoff(
    *,
    handoff_id: str,
    created_at: datetime,
    candidate_id: str,
    candidate_report_ref: ArtifactRef,
    search_ledger_ref: ArtifactRef,
    multiplicity_account_ref: ArtifactRef,
    backtest_kill_gate_ref: ArtifactRef,
    virtual_execution_gate_ref: ArtifactRef,
    actual_cash_rows_ref: ArtifactRef | None = None,
) -> RiskActualCashHandoff:
    if actual_cash_rows_ref is None:
        status = RiskActualCashHandoffStatus.BLOCKED_NEEDS_ACTUAL_CASH_ROWS
        known_gaps = [
            "actual cash rows are missing",
            "virtual/backtest evidence is not actual cash evidence",
        ]
    else:
        status = RiskActualCashHandoffStatus.READY_WITH_ACTUAL_CASH_ROWS
        known_gaps = [
            "actual cash rows ref is present but manual risk review is still required",
            "virtual/backtest evidence is not actual cash evidence",
        ]

    return RiskActualCashHandoff(
        handoff_id=handoff_id,
        created_at=created_at,
        producer=ProducerInfo(command="edge-candidate-risk-actual-cash-handoff"),
        candidate_id=candidate_id,
        candidate_report_ref=candidate_report_ref,
        search_ledger_ref=search_ledger_ref,
        multiplicity_account_ref=multiplicity_account_ref,
        backtest_kill_gate_ref=backtest_kill_gate_ref,
        virtual_execution_gate_ref=virtual_execution_gate_ref,
        risk_taker_review_input_status=status,
        actual_cash_report_gate_input_status=status,
        actual_cash_rows_required=True,
        actual_cash_rows_ref=actual_cash_rows_ref,
        virtual_or_backtest_used_as_actual_cash=False,
        known_gaps=known_gaps,
    )
