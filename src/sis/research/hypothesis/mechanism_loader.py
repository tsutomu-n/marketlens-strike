from __future__ import annotations

from pathlib import Path

from sis.research.hypothesis.mechanism_contracts import MechanismPartsRegistry
from sis.research.hypothesis.yaml_io import load_yaml_mapping


def load_mechanism_parts(path: Path) -> MechanismPartsRegistry:
    return MechanismPartsRegistry.model_validate(load_yaml_mapping(path))
