from __future__ import annotations

from pathlib import Path

from sis.research.hypothesis.scope_contracts import ResearchScope
from sis.research.hypothesis.yaml_io import load_yaml_mapping


def load_scope(path: Path) -> ResearchScope:
    return ResearchScope.model_validate(load_yaml_mapping(path))

