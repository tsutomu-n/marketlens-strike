from __future__ import annotations

from collections.abc import Iterable


CURRENT_STATE_DOC = "docs/CURRENT_STATE.md"
OPERATIONS_RUNBOOK_DOC = "docs/OPERATIONS_RUNBOOK.md"
ARCHITECTURE_AND_PHASES_DOC = "docs/ARCHITECTURE_AND_PHASES.md"
CODE_STATUS_DOC = "docs/CODE_STATUS.md"

CURRENT_STATE_INDEX_REPORT = "data/reports/current_state_index.md"
READINESS_SNAPSHOT_REPORT = "data/reports/readiness_snapshot.md"
PHASE_GATE_REVIEW_REPORT = "data/reports/phase_gate_review.md"
OPERATIONS_DASHBOARD_REPORT = "data/reports/operations_dashboard.md"
REMEDIATION_SCOREBOARD_REPORT = "data/reports/remediation_scoreboard.md"


def recommended_read_order(extra: Iterable[str] = ()) -> list[str]:
    """Return the canonical restart order with caller-specific artifacts included."""
    items = [
        CURRENT_STATE_DOC,
        CODE_STATUS_DOC,
        *extra,
        CURRENT_STATE_INDEX_REPORT,
        READINESS_SNAPSHOT_REPORT,
        PHASE_GATE_REVIEW_REPORT,
        OPERATIONS_DASHBOARD_REPORT,
        REMEDIATION_SCOREBOARD_REPORT,
        OPERATIONS_RUNBOOK_DOC,
        ARCHITECTURE_AND_PHASES_DOC,
    ]
    return list(dict.fromkeys(items))
