from __future__ import annotations

from pathlib import Path

from sis.research.dag.contracts import CoreDag
from sis.research.hypothesis.yaml_io import load_yaml_mapping


def load_core_dag(path: Path) -> CoreDag:
    return CoreDag.model_validate(load_yaml_mapping(path))
