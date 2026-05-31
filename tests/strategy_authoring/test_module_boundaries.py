from __future__ import annotations

import ast
from pathlib import Path


AUTHORING_ROOT = Path("src/sis/research/strategy_lab/authoring")
MAX_LINES = 800


def _python_files() -> list[Path]:
    return sorted(AUTHORING_ROOT.rglob("*.py"))


def test_strategy_authoring_has_no_monolithic_contracts_or_compiler_files() -> None:
    assert not (AUTHORING_ROOT / "contracts.py").exists()
    assert not (AUTHORING_ROOT / "compiler.py").exists()


def test_strategy_authoring_python_files_stay_under_800_lines() -> None:
    oversized = {
        str(path): len(path.read_text(encoding="utf-8").splitlines())
        for path in _python_files()
        if len(path.read_text(encoding="utf-8").splitlines()) > MAX_LINES
    }

    assert oversized == {}


def test_strategy_authoring_imports_use_explicit_submodules() -> None:
    blocked_modules = {
        "sis.research.strategy_lab.authoring.contracts",
        "sis.research.strategy_lab.authoring.compiler",
    }
    violations: list[str] = []

    for root in (Path("src/sis"), Path("tests")):
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in blocked_modules:
                    violations.append(f"{path}:{node.lineno}: from {node.module} import ...")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in blocked_modules:
                            violations.append(f"{path}:{node.lineno}: import {alias.name}")

    assert violations == []
