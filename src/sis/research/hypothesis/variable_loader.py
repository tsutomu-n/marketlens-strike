from __future__ import annotations

from pathlib import Path

from sis.research.hypothesis.variable_contracts import VariableInventory
from sis.research.hypothesis.yaml_io import load_yaml_mapping


def load_variable_inventory(path: Path) -> VariableInventory:
    return VariableInventory.model_validate(load_yaml_mapping(path))

