from __future__ import annotations

from sis.research.hypothesis.role_contracts import CausalRoleRegistry
from sis.research.hypothesis.variable_contracts import VariableInventory


def validate_roles_against_inventory(
    roles: CausalRoleRegistry,
    inventory: VariableInventory,
) -> None:
    issues: list[str] = []
    missing = sorted(set(roles.roles) - set(inventory.variables))
    if missing:
        issues.append("roles reference unknown variables: " + ", ".join(missing))
    unassigned = sorted(set(inventory.variables) - set(roles.roles))
    if unassigned:
        issues.append("variables missing causal role assignments: " + ", ".join(unassigned))
    mismatched_candidates = [
        variable_id
        for variable_id, role in roles.roles.items()
        if variable_id in inventory.variables
        and role not in inventory.variables[variable_id].role_candidates
    ]
    if mismatched_candidates:
        issues.append(
            "roles not listed in variable role candidates: " + ", ".join(mismatched_candidates)
        )
    if issues:
        raise ValueError("; ".join(issues))
