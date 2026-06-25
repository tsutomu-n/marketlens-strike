from __future__ import annotations

from pathlib import Path


COMPILER_DIR = Path("src/sis/research/strategy_lab/authoring/compiler")


def test_compiler_numeric_row_value_callers_use_direct_module() -> None:
    legacy_import = "from sis.research.strategy_lab.authoring.compiler.row_values import"
    allowed = {COMPILER_DIR / "row_values.py"}

    offenders = sorted(
        path.as_posix()
        for path in COMPILER_DIR.glob("*.py")
        if path not in allowed and legacy_import in path.read_text(encoding="utf-8")
    )

    assert offenders == []
