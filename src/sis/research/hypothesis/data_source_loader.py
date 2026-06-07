from __future__ import annotations

from pathlib import Path

from sis.research.hypothesis.data_source_contracts import DataSourceRegistry
from sis.research.hypothesis.yaml_io import load_yaml_mapping


def load_data_source_registry(path: Path) -> DataSourceRegistry:
    return DataSourceRegistry.model_validate(load_yaml_mapping(path))
