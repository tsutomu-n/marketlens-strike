from __future__ import annotations

from sis.research.dag.contracts import CoreDag
from sis.research.dag.contracts import DagEdge
from sis.research.dag.errors import CoreDagValidationError


def validate_core_dag(dag: CoreDag) -> None:
    issues: list[str] = []
    node_ids = dag.node_ids()
    _validate_edges("edge", dag.edges, node_ids, issues)
    _validate_edges("forbidden_edge", dag.forbidden_edges, node_ids, issues)
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

