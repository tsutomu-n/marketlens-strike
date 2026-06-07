from __future__ import annotations

from sis.research.dag.contracts import CoreDag
from sis.research.dag.contracts import DagEdge
from sis.research.dag.errors import CoreDagValidationError
from sis.research.hypothesis.role_contracts import CausalRoleRegistry
from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from sis.research.hypothesis.variable_contracts import VariableInventory


def validate_core_dag(dag: CoreDag) -> None:
    issues: list[str] = []
    node_ids = dag.node_ids()
    _validate_edges("edge", dag.edges, node_ids, issues)
    _validate_edges("forbidden_edge", dag.forbidden_edges, node_ids, issues)
    if issues:
        raise CoreDagValidationError(issues)


def validate_core_dag_against_research_context(
    dag: CoreDag,
    *,
    inventory: VariableInventory,
    roles: CausalRoleRegistry,
    temporal: TemporalAvailability,
) -> None:
    issues: list[str] = []
    for node in dag.nodes:
        variable = inventory.variables.get(node.id)
        assigned_role = roles.roles.get(node.id)
        temporal_layer = temporal.layer_for_variable(node.id)
        if variable is None:
            issues.append(f"core DAG node missing from variable inventory: {node.id}")
            continue
        if assigned_role is None:
            issues.append(f"core DAG node missing from causal roles: {node.id}")
        elif node.role != assigned_role:
            issues.append(
                f"core DAG node role mismatch for {node.id}: {node.role} != {assigned_role}"
            )
        if assigned_role is not None and assigned_role not in variable.role_candidates:
            issues.append(
                f"causal role not listed in variable role candidates for {node.id}: {assigned_role}"
            )
        if temporal_layer is None:
            issues.append(f"core DAG node missing from temporal availability: {node.id}")
        elif temporal_layer != variable.temporal_class:
            issues.append(
                f"temporal mismatch for {node.id}: {temporal_layer} != {variable.temporal_class}"
            )
    if issues:
        raise CoreDagValidationError(issues)


def _validate_edges(
    label: str,
    edges: list[DagEdge],
    node_ids: set[str],
    issues: list[str],
) -> None:
    seen: set[tuple[str, str]] = set()
    for edge in edges:
        if edge.from_node not in node_ids:
            issues.append(f"{label} references unknown from node: {edge.from_node}")
        if edge.to not in node_ids:
            issues.append(f"{label} references unknown to node: {edge.to}")
        if edge.from_node == edge.to:
            issues.append(f"{label} self-loop is not allowed: {edge.from_node}")
        if edge.key in seen:
            issues.append(f"{label} duplicate edge: {edge.from_node}->{edge.to}")
        seen.add(edge.key)
