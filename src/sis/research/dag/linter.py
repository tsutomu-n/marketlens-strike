from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sis.research.dag.contracts import CoreDag
from sis.research.dag.errors import CoreDagLintError
from sis.research.dag.rules import is_future_to_signal_edge
from sis.research.hypothesis.temporal_contracts import TemporalAvailability


LintSeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class DagLintIssue:
    severity: LintSeverity
    rule_id: str
    message: str


def lint_core_dag(
    dag: CoreDag,
    *,
    temporal: TemporalAvailability | None = None,
) -> list[DagLintIssue]:
    issues: list[DagLintIssue] = []
    role_by_id = dag.role_by_node_id()
    forbidden_edge_keys = {edge.key for edge in dag.forbidden_edges}

    for edge in dag.edges:
        from_role = role_by_id.get(edge.from_node)
        to_role = role_by_id.get(edge.to)
        if from_role == "outcome" and to_role == "treatment_candidate":
            issues.append(
                DagLintIssue(
                    severity="error",
                    rule_id="outcome_to_treatment",
                    message=f"outcome must not point to treatment_candidate: {edge.from_node}->{edge.to}",
                )
            )
        if edge.key in forbidden_edge_keys:
            issues.append(
                DagLintIssue(
                    severity="error",
                    rule_id="configured_forbidden_edge",
                    message=f"edge is listed as forbidden: {edge.from_node}->{edge.to}",
                )
            )
        if temporal is not None:
            from_layer = temporal.layer_for_variable(edge.from_node)
            to_layer = temporal.layer_for_variable(edge.to)
            if is_future_to_signal_edge(from_layer, to_layer):
                issues.append(
                    DagLintIssue(
                        severity="error",
                        rule_id="future_to_signal",
                        message=(
                            "future temporal layer must not point to earlier signal layer: "
                            f"{edge.from_node}->{edge.to}"
                        ),
                    )
                )

    if not dag.counter_dag_refs:
        issues.append(
            DagLintIssue(
                severity="warning",
                rule_id="missing_counter_dag",
                message="core DAG should reference at least one counter DAG.",
            )
        )
    return issues


def raise_for_lint_errors(issues: list[DagLintIssue]) -> None:
    errors = [issue.message for issue in issues if issue.severity == "error"]
    if errors:
        raise CoreDagLintError(errors)

