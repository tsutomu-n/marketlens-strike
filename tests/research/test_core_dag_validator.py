from __future__ import annotations

import pytest

from sis.research.dag.contracts import CoreDag
from sis.research.dag.errors import CoreDagValidationError
from sis.research.dag.validator import validate_core_dag, validate_core_dag_against_research_context
from sis.research.hypothesis.role_contracts import CausalRoleRegistry
from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from sis.research.hypothesis.variable_contracts import VariableInventory
from research.helpers import core_dag_payload


def test_core_dag_validator_accepts_valid_payload() -> None:
    validate_core_dag(CoreDag.model_validate(core_dag_payload()))


def test_core_dag_validator_rejects_unknown_node_self_loop_and_duplicate_edge() -> None:
    payload = core_dag_payload()
    payload["edges"] = [
        {"from": "missing", "to": "treatment"},
        {"from": "treatment", "to": "treatment"},
        {"from": "treatment", "to": "outcome"},
        {"from": "treatment", "to": "outcome"},
    ]

    with pytest.raises(CoreDagValidationError) as exc_info:
        validate_core_dag(CoreDag.model_validate(payload))

    message = str(exc_info.value)
    assert "unknown from node" in message
    assert "self-loop" in message
    assert "duplicate edge" in message


def test_core_dag_context_validation_rejects_inventory_role_and_temporal_mismatch() -> None:
    dag = CoreDag.model_validate(core_dag_payload())
    inventory = VariableInventory.model_validate(
        {
            "schema_version": "research_variable_inventory.v1",
            "variables": {
                "treatment": {
                    "formula": "x",
                    "temporal_class": "t_after_open",
                    "role_candidates": ["treatment_candidate"],
                },
                "outcome": {
                    "formula": "y",
                    "temporal_class": "t_after_close",
                    "role_candidates": ["outcome"],
                },
            },
        }
    )
    roles = CausalRoleRegistry.model_validate(
        {
            "schema_version": "research_causal_roles.v1",
            "roles": {
                "treatment": "outcome",
                "outcome": "outcome",
            },
        }
    )
    temporal = TemporalAvailability.model_validate(
        {
            "schema_version": "research_temporal_availability.v1",
            "layers": {
                "t_after_close": ["treatment"],
                "t_after_open": ["outcome"],
            },
        }
    )

    with pytest.raises(CoreDagValidationError) as exc_info:
        validate_core_dag_against_research_context(
            dag,
            inventory=inventory,
            roles=roles,
            temporal=temporal,
        )

    message = str(exc_info.value)
    assert "missing from variable inventory: confounder" in message
    assert "role mismatch for treatment" in message
    assert "temporal mismatch for treatment" in message
