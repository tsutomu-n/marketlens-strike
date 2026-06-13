from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACTS = {
    "vectorbt": {
        "adapter_role": "high_speed_signal_runner",
        "input_contract": {
            "artifact_kind": "strategy_signals_and_quotes",
            "required_fields": [
                "source_metrics_path",
                "source_metrics_hash",
                "source_signals_path",
                "source_signals_hash",
                "source_quotes_path",
                "source_quotes_hash",
                "label_horizon_minutes",
            ],
            "optional_fields": ["fees_bps", "slippage_bps", "size_column"],
        },
        "output_contract": {
            "artifact_kind": "strategy_backtest_external_result.v1.result",
            "required_fields": [
                "framework_id",
                "run_status",
                "engine_run",
                "trade_count",
                "total_return",
                "max_drawdown",
                "cost_drag_bps",
            ],
            "optional_fields": ["portfolio_value", "positions", "orders"],
        },
        "provenance_requirements": [
            "source_metrics_hash",
            "source_signals_hash",
            "source_quotes_hash",
            "framework_version",
            "runner_mode",
        ],
        "acceptance_checks": [
            "external_result_schema_validation",
            "paper_only_boundary",
            "no_wallet_or_exchange_write",
            "source_hashes_match_inputs",
        ],
        "next_implementation_step": (
            "Add a vectorbt adapter wrapper behind temporary/optional dependency detection."
        ),
    },
    "bt": {
        "adapter_role": "portfolio_allocation_rebalance",
        "input_contract": {
            "artifact_kind": "strategy_authoring_bundle_or_weight_series",
            "required_fields": [
                "source_bundle_path",
                "source_bundle_hash",
                "price_frame_path",
                "price_frame_hash",
                "allocation_rule_id",
                "rebalance_cadence",
            ],
            "optional_fields": ["target_weight_column", "cost_model_path", "benchmark_symbol"],
        },
        "output_contract": {
            "artifact_kind": "strategy_backtest_portfolio_comparison.v1",
            "required_fields": [
                "framework_id",
                "run_status",
                "engine_run",
                "portfolio_return",
                "max_drawdown",
                "turnover",
                "rebalance_count",
            ],
            "optional_fields": ["weight_drift", "benchmark_return", "allocation_trace"],
        },
        "provenance_requirements": [
            "source_bundle_hash",
            "price_frame_hash",
            "framework_version",
            "runner_mode",
        ],
        "acceptance_checks": [
            "portfolio_comparison_schema_validation",
            "paper_only_boundary",
            "no_wallet_or_exchange_write",
            "allocation_inputs_hash_match",
        ],
        "next_implementation_step": (
            "Design a portfolio comparison artifact before adding a bt optional dependency."
        ),
    },
    "empyrical_reloaded": {
        "adapter_role": "metrics_normalization",
        "input_contract": {
            "artifact_kind": "returns_series",
            "required_fields": [
                "source_backtest_metrics_path",
                "source_backtest_metrics_hash",
                "returns_series_path",
                "returns_series_hash",
                "frequency",
            ],
            "optional_fields": ["benchmark_returns_path", "risk_free_rate"],
        },
        "output_contract": {
            "artifact_kind": "strategy_backtest_metric_extension.v1",
            "required_fields": [
                "framework_id",
                "metric_status",
                "sharpe_ratio",
                "sortino_ratio",
                "max_drawdown",
                "annual_return",
                "annual_volatility",
            ],
            "optional_fields": ["alpha", "beta", "calmar_ratio", "omega_ratio"],
        },
        "provenance_requirements": [
            "source_backtest_metrics_hash",
            "returns_series_hash",
            "framework_version",
            "runner_mode",
        ],
        "acceptance_checks": [
            "metric_extension_schema_validation",
            "paper_only_boundary",
            "no_wallet_or_exchange_write",
            "metrics_inputs_hash_match",
        ],
        "next_implementation_step": (
            "Add a metrics extension artifact before visual report or tearsheet integration."
        ),
    },
}


@dataclass(frozen=True)
class BacktestAdapterContractResult:
    contract_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _selected_by_id(selection_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("framework_id")): item
        for item in selection_payload.get("selected_adapters") or []
        if isinstance(item, dict)
    }


def _contract_item(framework_id: str, selection_item: dict[str, Any]) -> dict[str, Any]:
    contract = CONTRACTS[framework_id]
    return {
        "framework_id": framework_id,
        "contract_status": "ready_for_adapter_implementation",
        "adapter_role": contract["adapter_role"],
        "adoption_classification": selection_item.get("adoption_classification"),
        "input_contract": contract["input_contract"],
        "output_contract": contract["output_contract"],
        "provenance_requirements": contract["provenance_requirements"],
        "acceptance_checks": contract["acceptance_checks"],
        "next_implementation_step": contract["next_implementation_step"],
    }


def _contracts(selection_payload: dict[str, Any]) -> list[dict[str, Any]]:
    selected = _selected_by_id(selection_payload)
    missing = [framework_id for framework_id in CONTRACTS if framework_id not in selected]
    if missing:
        raise ValueError(
            f"selected adapter(s) missing from selection artifact: {', '.join(missing)}"
        )
    return [
        _contract_item(framework_id, selected[framework_id])
        for framework_id in ("vectorbt", "bt", "empyrical_reloaded")
    ]


def _summary(contracts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "contract_count": len(contracts),
        "optional_extra_contract_count": sum(
            1 for item in contracts if item["adoption_classification"] == "optional_extra_candidate"
        ),
        "report_only_contract_count": sum(
            1 for item in contracts if item["adoption_classification"] == "report_only_candidate"
        ),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Adapter Contract",
        "",
        f"- created_at: {payload['created_at']}",
        "- policy_id: phase_d_adapter_contract_before_dependency.v1",
        "- standard_engine: strategy_authoring_native",
        "- dependency_added: false",
        "- external_engine_run: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        f"- contract_count: {payload['summary']['contract_count']}",
        "",
        "## Contracts",
        "",
        "| Framework | Role | Input Kind | Output Kind | Next Step |",
        "|---|---|---|---|---|",
    ]
    for item in payload["contracts"]:
        lines.append(
            "| {framework_id} | {role} | {input_kind} | {output_kind} | {next_step} |".format(
                framework_id=item["framework_id"],
                role=item["adapter_role"],
                input_kind=item["input_contract"]["artifact_kind"],
                output_kind=item["output_contract"]["artifact_kind"],
                next_step=item["next_implementation_step"],
            )
        )
    lines.extend(
        [
            "",
            "This contract does not add dependencies, run external engines, or permit live orders.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_backtest_adapter_contract(
    *,
    adapter_selection_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestAdapterContractResult:
    selection_payload = _read_json(adapter_selection_path)
    contracts = _contracts(selection_payload)
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_adapter_contract.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "source_adapter_selection_path": adapter_selection_path.as_posix(),
        "source_adapter_selection_hash": _sha256_file(adapter_selection_path),
        "contract_policy": {
            "policy_id": "phase_d_adapter_contract_before_dependency.v1",
            "standard_engine": "strategy_authoring_native",
            "dependency_adoption_allowed": False,
            "external_engine_execution_allowed": False,
            "requires_source_hashes": True,
            "requires_before_dependency_adoption": [
                "license_review",
                "python_3_13_uv_lock_review",
                "ci_green",
                "schema_boundary_review",
                "optional_extra_decision",
                "golden_artifact_comparison",
            ],
        },
        "contracts": contracts,
        "summary": _summary(contracts),
        "decision": {
            "decision": "DESIGN_ADAPTER_CONTRACTS_BEFORE_DEPENDENCY",
            "reason_codes": [
                "phase_c_selected_adapters",
                "dependency_adoption_deferred",
                "source_hash_contract_required",
            ],
            "recommended_next_step": (
                "Implement vectorbt, bt, and empyrical-reloaded adapters against these contracts before locking optional extras."
            ),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    contract_path = out_dir / "strategy_backtest_adapter_contract.json"
    contract_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_adapter_contract_report.md", payload
    )
    return BacktestAdapterContractResult(
        contract_path=contract_path, report_path=report_path, payload=payload
    )
