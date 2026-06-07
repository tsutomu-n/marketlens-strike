from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.hypothesis.role_contracts import CausalRoleRegistry
from sis.research.hypothesis.role_validator import validate_roles_against_inventory
from sis.research.hypothesis.variable_loader import load_variable_inventory
from sis.research.hypothesis.yaml_io import load_yaml_mapping
from research.helpers import CONFIG_DIR


def test_causal_roles_match_variable_inventory() -> None:
    roles = CausalRoleRegistry.model_validate(load_yaml_mapping(CONFIG_DIR / "causal_roles.yaml"))
    inventory = load_variable_inventory(CONFIG_DIR / "variable_inventory.yaml")

    validate_roles_against_inventory(roles, inventory)
    assert roles.roles["open_gap_residual"] == "treatment_candidate"
    assert roles.roles["qqq_open_to_close_return"] == "outcome"


def test_causal_roles_reject_unknown_role_and_unknown_variable() -> None:
    with pytest.raises(ValidationError):
        CausalRoleRegistry.model_validate(
            {"schema_version": "research_causal_roles.v1", "roles": {"x": "bad"}}
        )

    inventory = load_variable_inventory(CONFIG_DIR / "variable_inventory.yaml")
    roles = CausalRoleRegistry.model_validate(
        {"schema_version": "research_causal_roles.v1", "roles": {"missing": "confounder"}}
    )
    with pytest.raises(ValueError):
        validate_roles_against_inventory(roles, inventory)
