from __future__ import annotations

from sis.research.dag.contracts import CoreDag
from sis.research.dag.contracts import DataRequirement
from sis.research.dag.contracts import RequirementTier
from sis.research.hypothesis.data_source_contracts import DataSourceRegistry
from sis.research.hypothesis.data_source_contracts import SourceTier
from sis.research.hypothesis.variable_contracts import VariableInventory


def build_data_requirements(
    dag: CoreDag,
    inventory: VariableInventory,
    data_sources: DataSourceRegistry | None = None,
) -> list[DataRequirement]:
    requirements: list[DataRequirement] = []
    for node in dag.nodes:
        variable = inventory.variables.get(node.id)
        if variable is None:
            continue
        requirements.append(
            DataRequirement(
                variable_id=node.id,
                source_symbol=variable.source_symbol,
                formula=variable.formula or variable.proxy,
                temporal_class=variable.temporal_class,
                provider_candidates=_provider_candidates(variable.source_symbol),
                requirement_tier=_requirement_tier(
                    data_sources.tier_for_symbol(variable.source_symbol) if data_sources else None
                ),
            )
        )
    return requirements


def _requirement_tier(source_tier: SourceTier | None) -> RequirementTier:
    if source_tier == "optional_provider_dependent":
        return "optional"
    if source_tier == "deferred":
        return "deferred"
    return "required"


def _provider_candidates(source_symbol: str | None) -> list[str]:
    if source_symbol is None:
        return []
    if source_symbol == "DGS10":
        return ["fred"]
    return ["local_fixture", "market_data_provider"]
