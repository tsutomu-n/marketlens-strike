from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.research.strategy_lab.authoring.backtest import run_authoring_backtest
from sis.research.strategy_lab.authoring.backtest_bundle_metrics import (
    _aggregate_bundle_metrics,
    _bundle_effective_weights,
)
from sis.research.strategy_lab.authoring.backtest_optimizer import (
    _optimizer_sort_value,
    _resolve_selection_direction,
)
from sis.research.strategy_lab.authoring.bundle_outputs import (
    write_authoring_bundle_outputs as write_authoring_bundle_outputs,
)
from sis.research.strategy_lab.authoring.compiler.build import build_authoring_signals
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringBundleSpec
from sis.research.strategy_lab.authoring.io import load_authoring_spec


def _resolve_member_spec_path(raw: str, bundle_path: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else bundle_path.parent / path


def run_authoring_bundle(
    bundle: StrategyAuthoringBundleSpec, *, bundle_path: Path, data_dir: Path
) -> dict[str, Any]:
    member_results: list[dict[str, Any]] = []
    for index, member in enumerate(bundle.members):
        if not member.enabled:
            continue
        spec_path = _resolve_member_spec_path(member.spec_path, bundle_path)
        spec = load_authoring_spec(spec_path)
        frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)
        _metrics, summary = run_authoring_backtest(spec, frame, data_dir=data_dir)
        member_results.append(
            {
                "member_index": index,
                "spec_path": str(spec_path),
                "strategy_id": spec.experiment.strategy_id,
                "allocation_weight": member.allocation_weight,
                "effective_allocation_weight": 0.0,
                "signal_count": frame.height,
                "summary": summary,
            }
        )
    effective_weights = _bundle_effective_weights(bundle, member_results)
    for member_result in member_results:
        member_result["effective_allocation_weight"] = effective_weights.get(
            int(member_result["member_index"]), 0.0
        )
    aggregate_metrics = _aggregate_bundle_metrics(member_results)
    metric_name = bundle.portfolio.selection_metric
    resolved_direction = _resolve_selection_direction(
        bundle.portfolio.selection_direction, metric_name
    )
    reverse = resolved_direction == "maximize"
    ranked_members = sorted(
        member_results,
        key=lambda item: _optimizer_sort_value(
            item["summary"],
            metric_name,
            maximize=reverse,
        ),
        reverse=reverse,
    )
    return {
        "schema_version": "strategy_authoring_bundle_result.v1",
        "bundle_id": bundle.bundle_id,
        "paper_only": True,
        "live_order_submitted": False,
        "portfolio": {
            **bundle.portfolio.model_dump(mode="json"),
            "resolved_selection_direction": resolved_direction,
        },
        "aggregate_metrics": aggregate_metrics,
        "best_member": ranked_members[0] if ranked_members else None,
        "members": ranked_members,
    }
