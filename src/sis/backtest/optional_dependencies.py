from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any


def project_pyproject_path() -> Path | None:
    for directory in [Path.cwd(), *Path.cwd().parents]:
        pyproject_path = directory / "pyproject.toml"
        if pyproject_path.exists():
            return pyproject_path
    return None


def project_declares_optional_extra(extra_name: str, dependency_prefixes: set[str]) -> bool:
    pyproject_path = project_pyproject_path()
    if pyproject_path is None:
        return False
    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return False
    project = payload.get("project")
    if not isinstance(project, dict):
        return False
    optional_dependencies = project.get("optional-dependencies")
    if not isinstance(optional_dependencies, dict):
        return False
    extra_dependencies = optional_dependencies.get(extra_name)
    if not isinstance(extra_dependencies, list):
        return False
    return any(
        any(str(item).startswith(prefix) for prefix in dependency_prefixes)
        for item in extra_dependencies
    )


def optional_dependency_source(
    candidate: dict[str, Any], *, extra_name: str, dependency_prefixes: set[str]
) -> str:
    if candidate.get("status") != "installed":
        return "not_installed_in_current_env"
    if project_declares_optional_extra(extra_name, dependency_prefixes):
        return "optional_extra_available"
    return "temporary_uv_with"
