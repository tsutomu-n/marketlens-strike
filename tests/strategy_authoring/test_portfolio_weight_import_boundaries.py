from __future__ import annotations

import ast
from pathlib import Path


def test_compiler_callers_import_portfolio_weight_values_explicitly() -> None:
    root = Path("src/sis/research/strategy_lab/authoring/compiler")
    blocked_names = {"_position_weight_value", "_portfolio_turnover_weight_value"}
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        if path.name == "common.py":
            continue
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module != "sis.research.strategy_lab.authoring.compiler.common":
                continue
            if any(alias.name in blocked_names for alias in node.names):
                offenders.append(str(path))

    assert offenders == []
