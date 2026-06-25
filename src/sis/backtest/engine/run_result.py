from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BacktestRunResult:
    run_dir: Path
    metrics: dict[str, object]
