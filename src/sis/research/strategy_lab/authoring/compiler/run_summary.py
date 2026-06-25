from __future__ import annotations

import json
from pathlib import Path

from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def write_authoring_run_summary(
    spec: StrategyAuthoringSpec,
    *,
    data_dir: Path,
    through: str,
    artifacts: dict[str, Path],
    signal_count: int,
    source_signal_count: int | None = None,
    evaluation_signal_count: int | None = None,
) -> Path:
    out = data_dir / "research/strategy_authoring_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_run.v1",
                "strategy_id": spec.experiment.strategy_id,
                "through": through,
                "signal_count": signal_count,
                "source_signal_count": (
                    source_signal_count if source_signal_count is not None else signal_count
                ),
                "evaluation_signal_count": (
                    evaluation_signal_count if evaluation_signal_count is not None else signal_count
                ),
                "paper_only": True,
                "live_order_submitted": False,
                "artifacts": {key: str(value) for key, value in artifacts.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out
