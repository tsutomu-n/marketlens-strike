from __future__ import annotations

import ast
from pathlib import Path


def test_authoring_callers_import_required_column_helpers_explicitly() -> None:
    root = Path("src/sis/research/strategy_lab/authoring")
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        if path.name == "validation.py":
            continue
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module != "sis.research.strategy_lab.authoring.validation":
                continue
            if any(alias.name in {"_all_conditions", "_required_columns"} for alias in node.names):
                offenders.append(str(path))

    assert offenders == []
