from __future__ import annotations

from pathlib import Path

from sis.research.hypothesis.seed_contracts import SeedRegistry
from sis.research.hypothesis.yaml_io import load_yaml_mapping


def load_seed_registry(path: Path) -> SeedRegistry:
    return SeedRegistry.model_validate(load_yaml_mapping(path))
