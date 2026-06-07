from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sis.research.dag.contracts import CoreDag
from sis.research.dag.errors import CoreDagLintError
from sis.research.dag.rules import is_future_to_signal_edge
from sis.research.hypothesis.data_source_contracts import DataSourceRegistry
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
    data_sources: DataSourceRegistry | None = None,
) -> list[DagLintIssue]:
    issues: list[DagLintIssue] = []
    role_by_id = dag.role_by_node_id()
    forbidden_edge_keys = {edge.key for edge in dag.forbidden_edges}
    if len(dag.nodes) > 15:
        issues.append(
            DagLintIssue(
                severity="warning",
                rule_id="too_many_nodes",
                message=f"initial core DAG should stay at 15 nodes or fewer: {len(dag.nodes)}",
            )
        )
    if len(dag.edges) > 20:
        issues.append(
            DagLintIssue(
                severity="warning",
                rule_id="too_many_edges",
                message=f"initial core DAG should stay at 20 edges or fewer: {len(dag.edges)}",
            )
        )

    for edge in dag.edges:
        from_role = role_by_id.get(edge.from_node)
        to_role = role_by_id.get(edge.to)
        if from_role == "outcome" and to_role in {
            "treatment_candidate",
            "observed_proxy",
            "modeled_latent",
        }:
            issues.append(
                DagLintIssue(
                    severity="error",
                    rule_id="no_outcome_to_treatment",
                    message=(
                        "outcome must not point to signal-side variables: "
                        f"{edge.from_node}->{edge.to}"
                    ),
                )
            )
        if from_role == "outcome" and to_role == "modeled_latent":
            issues.append(
                DagLintIssue(
                    severity="error",
                    rule_id="no_model_output_to_input",
                    message=f"outcome must not feed modeled_latent input: {edge.from_node}->{edge.to}",
                )
            )
        if edge.key in forbidden_edge_keys:
            issues.append(
                DagLintIssue(
                    severity="error",
                    rule_id="no_forbidden_edge_in_edges",
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
                        rule_id="no_future_to_signal",
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
    if data_sources is not None:
        for requirement in dag.data_requirements:
            source_tier = data_sources.tier_for_symbol(requirement.source_symbol)
            if source_tier in {"optional_provider_dependent", "deferred"} and (
                requirement.requirement_tier == "required"
            ):
                issues.append(
                    DagLintIssue(
                        severity="warning",
                        rule_id="optional_provider_required",
                        message=(
                            "provider-dependent or deferred source is marked required: "
                            f"{requirement.variable_id} ({source_tier})"
                        ),
                    )
                )
    return issues


def raise_for_lint_errors(issues: list[DagLintIssue]) -> None:
    errors = [issue.message for issue in issues if issue.severity == "error"]
    if errors:
        raise CoreDagLintError(errors)
