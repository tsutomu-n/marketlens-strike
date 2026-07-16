from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError
import yaml

from sis.strategy_idea_seeds.common.errors import SeedInputError
from sis.strategy_idea_seeds.technical.models import MechanismPack, OperatorCatalog


ModelT = TypeVar("ModelT", bound=BaseModel)


def load_operator_catalog(path: Path) -> OperatorCatalog:
    return _load_model(path, OperatorCatalog)


def load_mechanism_pack(path: Path) -> MechanismPack:
    return _load_model(path, MechanismPack)


def _load_model(path: Path, model_type: type[ModelT]) -> ModelT:
    if not path.exists() or not path.is_file():
        raise SeedInputError(f"config missing: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SeedInputError(f"invalid config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SeedInputError(f"config must be a mapping: {path}")
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise SeedInputError(f"config contract invalid {path}: {exc}") from exc
