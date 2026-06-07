from __future__ import annotations

from sis.research.hypothesis.temporal_contracts import TemporalAvailability


def forbidden_layer_edge_pairs(temporal: TemporalAvailability) -> set[tuple[str, str]]:
    return {(str(edge.from_layer), str(edge.to)) for edge in temporal.forbidden_layer_edges}
