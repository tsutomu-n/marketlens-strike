from __future__ import annotations

from sis.research.hypothesis.role_contracts import CausalRoleRegistry
from sis.research.hypothesis.variable_contracts import VariableInventory


def validate_roles_against_inventory(
    roles: CausalRoleRegistry,
    inventory: VariableInventory,
) -> None:
    missing = sorted(set(roles.roles) - set(inventory.variables))
    if missing:
        raise ValueError("roles reference unknown variables: " + ", ".join(missing))
