from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from crypto_perp_portfolio_capacity.models import (  # type: ignore[import-not-found]
        PortfolioCapacityPolicy,
        PortfolioCapacityResult,
    )
    from crypto_perp_portfolio_capacity.pack_reader import (  # type: ignore[import-not-found]
        CandidatePack,
        build_capacity_case,
        build_runtime_inventory,
        load_candidate_pack,
    )
    from crypto_perp_portfolio_capacity.reference_path import (  # type: ignore[import-not-found]
        run_reference_path,
    )
    from crypto_perp_portfolio_capacity.vectorbt_diff import (  # type: ignore[import-not-found]
        run_vectorbt_differential,
    )
else:
    from .models import PortfolioCapacityPolicy, PortfolioCapacityResult
    from .pack_reader import (
        CandidatePack,
        build_capacity_case,
        build_runtime_inventory,
        load_candidate_pack,
    )
    from .reference_path import run_reference_path
    from .vectorbt_diff import run_vectorbt_differential


ACTION_POLICIES = (
    "CURRENT_SELECTOR",
    "ALWAYS_CONTINUATION",
    "ALWAYS_REVERSAL",
    "NO_TRADE",
)
POSITION_LIMITS = (1, 2, 3, None)
METRIC_SCENARIOS = ("BASE", "STRESS")
TIMESTAMP_POLICIES = ("NO_SAME_TIMESTAMP_REUSE", "EXIT_THEN_ENTRY")
GOLDEN_CASE_IDS = tuple(f"G{index:02d}" for index in range(1, 19))


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_scenario_matrix(
    pack: CandidatePack,
    *,
    initial_cash_usd: Decimal,
) -> tuple[list[dict[str, Any]], list[PortfolioCapacityResult]]:
    rows: list[dict[str, Any]] = []
    results: list[PortfolioCapacityResult] = []
    for action_policy in ACTION_POLICIES:
        for max_positions in POSITION_LIMITS:
            for metric_scenario in METRIC_SCENARIOS:
                for timestamp_policy in TIMESTAMP_POLICIES:
                    policy = PortfolioCapacityPolicy(
                        initial_cash_usd=initial_cash_usd,
                        max_open_positions=max_positions,
                        action_policy=action_policy,
                        metric_scenario=metric_scenario,
                        same_timestamp_cash_policy=timestamp_policy,
                    )
                    result = run_reference_path(build_capacity_case(pack, policy))
                    results.append(result)
                    rows.append(
                        {
                            "case_id": result.case_id,
                            "result_id": result.result_id,
                            "action_policy": action_policy,
                            "max_open_positions": max_positions,
                            "metric_scenario": metric_scenario,
                            "same_timestamp_cash_policy": timestamp_policy,
                            "accepted_trade_count": result.accepted_trade_count,
                            "rejected_trade_count": result.rejected_trade_count,
                            "skipped_trade_count": result.skipped_trade_count,
                            "final_available_cash_usd": str(result.final_available_cash_usd),
                            "simulated_account_pnl_estimate_usd": str(
                                result.simulated_account_pnl_estimate_usd
                            ),
                            "economic_result_estimate_usd": str(
                                result.economic_result_estimate_usd
                            ),
                            "peak_reserved_cash_usd": str(result.peak_reserved_cash_usd),
                            "settled_cash_drawdown_estimate_usd": str(
                                result.settled_cash_drawdown_estimate_usd
                            ),
                            "rejected_reason_counts": result.rejected_reason_counts,
                            "run_status": result.run_status,
                        }
                    )
    return rows, results


def _find_row(
    rows: list[dict[str, Any]],
    *,
    action: str,
    maximum: int | None,
    scenario: str,
    timestamp_policy: str,
) -> dict[str, Any]:
    return next(
        row
        for row in rows
        if row["action_policy"] == action
        and row["max_open_positions"] == maximum
        and row["metric_scenario"] == scenario
        and row["same_timestamp_cash_policy"] == timestamp_policy
    )


def _existing_backtest_summary(pack: CandidatePack) -> dict[str, Any]:
    path = pack.root / "backtest_result.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _decision(
    *,
    pack: CandidatePack,
    inventory: Any,
    rows: list[dict[str, Any]],
    vectorbt: Any,
) -> tuple[str, list[str], dict[str, Any]]:
    main = _find_row(
        rows,
        action="CURRENT_SELECTOR",
        maximum=1,
        scenario="BASE",
        timestamp_policy="NO_SAME_TIMESTAMP_REUSE",
    )
    exit_first = _find_row(
        rows,
        action="CURRENT_SELECTOR",
        maximum=1,
        scenario="BASE",
        timestamp_policy="EXIT_THEN_ENTRY",
    )
    main_stress = _find_row(
        rows,
        action="CURRENT_SELECTOR",
        maximum=1,
        scenario="STRESS",
        timestamp_policy="NO_SAME_TIMESTAMP_REUSE",
    )
    continuation = _find_row(
        rows,
        action="ALWAYS_CONTINUATION",
        maximum=1,
        scenario="BASE",
        timestamp_policy="NO_SAME_TIMESTAMP_REUSE",
    )
    reversal = _find_row(
        rows,
        action="ALWAYS_REVERSAL",
        maximum=1,
        scenario="BASE",
        timestamp_policy="NO_SAME_TIMESTAMP_REUSE",
    )
    no_trade = _find_row(
        rows,
        action="NO_TRADE",
        maximum=1,
        scenario="BASE",
        timestamp_policy="NO_SAME_TIMESTAMP_REUSE",
    )
    max_rows = [
        _find_row(
            rows,
            action="CURRENT_SELECTOR",
            maximum=maximum,
            scenario="BASE",
            timestamp_policy="NO_SAME_TIMESTAMP_REUSE",
        )
        for maximum in (1, 2, 3)
    ]
    all_reasons: Counter[str] = Counter()
    for row in rows:
        all_reasons.update(row["rejected_reason_counts"])
    backtest = _existing_backtest_summary(pack)
    robustness = backtest.get("profit_robustness", {})
    existing_single_count = robustness.get("non_overlapping_trade_count")
    existing_single_total = robustness.get("single_position_total_result_usd")
    matches_existing_single = (
        existing_single_count == main["accepted_trade_count"]
        and existing_single_total == main["simulated_account_pnl_estimate_usd"]
    )
    max_limit_changes_result = (
        len(
            {
                (
                    row["accepted_trade_count"],
                    row["simulated_account_pnl_estimate_usd"],
                )
                for row in max_rows
            }
        )
        > 1
    )
    timestamp_changes_result = (
        main["accepted_trade_count"],
        main["simulated_account_pnl_estimate_usd"],
    ) != (
        exit_first["accepted_trade_count"],
        exit_first["simulated_account_pnl_estimate_usd"],
    )
    evidence = {
        "candidate_pack_decision": pack.decision.decision,
        "unique_symbol_count": inventory.unique_symbol_count,
        "peak_overlap": inventory.execution_window_peak_overlap,
        "main_accepted_trade_count": main["accepted_trade_count"],
        "main_rejected_trade_count": main["rejected_trade_count"],
        "max_position_rejected_counts_base": {
            str(row["max_open_positions"]): row["rejected_trade_count"] for row in max_rows
        },
        "insufficient_cash_rejections": all_reasons["INSUFFICIENT_AVAILABLE_CASH"],
        "max_position_limits_change_result": max_limit_changes_result,
        "timestamp_policy_changes_result": timestamp_changes_result,
        "current_selector_base_pnl_usd": main["simulated_account_pnl_estimate_usd"],
        "current_selector_stress_pnl_usd": main_stress["simulated_account_pnl_estimate_usd"],
        "always_continuation_base_pnl_usd": continuation["simulated_account_pnl_estimate_usd"],
        "always_reversal_base_pnl_usd": reversal["simulated_account_pnl_estimate_usd"],
        "no_trade_base_pnl_usd": no_trade["simulated_account_pnl_estimate_usd"],
        "matches_existing_single_position_diagnostic": matches_existing_single,
        "vectorbt_decision": vectorbt.decision,
        "vectorbt_absolute_difference_usd": str(vectorbt.absolute_difference_usd),
    }
    if vectorbt.decision == "MISMATCH":
        return (
            "DO_NOT_USE_VECTORBT_FOR_PORTFOLIO",
            ["VectorBT differential is not explained within tolerance."],
            evidence,
        )
    if inventory.execution_window_peak_overlap <= 1 or main["rejected_trade_count"] == 0:
        return (
            "USE_EXISTING_CANDIDATE_PACK_ONLY",
            ["Current runtime sample does not expose a material capacity constraint."],
            evidence,
        )
    if (
        inventory.unique_symbol_count < 2
        and all_reasons["INSUFFICIENT_AVAILABLE_CASH"] == 0
        and not max_limit_changes_result
        and matches_existing_single
    ):
        return (
            "KEEP_SPIKE_ONLY",
            [
                "The current sample is single-symbol, so per-symbol capacity dominates.",
                "Initial cash never binds and max position 1/2/3 produces the same result.",
                "The main path reproduces the existing single-position diagnostic.",
                "Keep the evidence harness, but wait for a multi-symbol or cash-binding pack.",
            ],
            evidence,
        )
    return (
        "PROMOTE_PORTFOLIO_CAPACITY",
        [
            "The runtime sample exposes material overlap or cash rejection.",
            "The capacity path adds decision information beyond the current aggregate.",
        ],
        evidence,
    )


def _decision_markdown(
    decision: str,
    reasons: list[str],
    evidence: dict[str, Any],
    rows: list[dict[str, Any]],
) -> str:
    current_rows = [
        row
        for row in rows
        if row["action_policy"] == "CURRENT_SELECTOR" and row["metric_scenario"] == "BASE"
    ]
    lines = [
        "# Crypto Perp Portfolio Capacity Discovery Decision",
        "",
        f"Decision: `{decision}`",
        "",
        "## Reasons",
        "",
        *[f"- {reason}" for reason in reasons],
        "",
        "## Evidence",
        "",
        *[f"- `{key}`: `{value}`" for key, value in evidence.items()],
        "",
        "## CURRENT_SELECTOR BASE",
        "",
        "| max positions | timestamp policy | accepted | rejected | account pnl |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in current_rows:
        lines.append(
            "| "
            f"{row['max_open_positions']} | {row['same_timestamp_cash_policy']} | "
            f"{row['accepted_trade_count']} | {row['rejected_trade_count']} | "
            f"{row['simulated_account_pnl_estimate_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- BAR_PROXY only.",
            "- No actual cash, mark-to-market, liquidation, partial fill, or live order evidence.",
            "- This decision does not authorize PR-BT1 or any later stage.",
            "",
        ]
    )
    return "\n".join(lines)


def _run_focused_tests() -> dict[str, Any]:
    tests_dir = Path(__file__).resolve().parent / "tests"
    command = [sys.executable, "-m", "pytest", tests_dir.as_posix(), "-q"]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "golden_case_ids": list(GOLDEN_CASE_IDS),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-pack-dir", type=Path, required=True)
    parser.add_argument("--initial-cash-usd", type=Decimal, default=Decimal("3000"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    focused = _run_focused_tests()
    args.out.mkdir(parents=True, exist_ok=True)
    _json_dump(args.out / "golden_case_results.json", focused)
    if focused["returncode"] != 0:
        print("status=fail")
        print("reason=FOCUSED_TEST_FAILURE")
        return 2
    pack = load_candidate_pack(args.candidate_pack_dir)
    inventory = build_runtime_inventory(pack)
    rows, results = run_scenario_matrix(pack, initial_cash_usd=args.initial_cash_usd)
    main_policy = PortfolioCapacityPolicy(
        initial_cash_usd=args.initial_cash_usd,
        max_open_positions=1,
        action_policy="CURRENT_SELECTOR",
        metric_scenario="BASE",
        same_timestamp_cash_policy="NO_SAME_TIMESTAMP_REUSE",
    )
    main_case = build_capacity_case(pack, main_policy)
    main_result = run_reference_path(main_case)
    vectorbt = run_vectorbt_differential(main_case, main_result)
    decision, reasons, evidence = _decision(
        pack=pack,
        inventory=inventory,
        rows=rows,
        vectorbt=vectorbt,
    )
    _json_dump(args.out / "runtime_inventory.json", inventory.model_dump(mode="json"))
    _json_dump(args.out / "case.json", main_case.model_dump(mode="json"))
    (args.out / "reference_results.jsonl").write_text(
        "".join(result.model_dump_json() + "\n" for result in results),
        encoding="utf-8",
    )
    _json_dump(
        args.out / "scenario_matrix.json",
        {
            "schema_version": "crypto_perp_portfolio_capacity_scenario_matrix.v1",
            "created_at": datetime.now(UTC).isoformat(),
            "case_count": len(rows),
            "rows": rows,
        },
    )
    _json_dump(args.out / "vectorbt_differential.json", vectorbt.model_dump(mode="json"))
    _json_dump(
        args.out / "decision.json",
        {
            "schema_version": "crypto_perp_portfolio_capacity_discovery_decision.v1",
            "decision": decision,
            "reasons": reasons,
            "evidence": evidence,
            "permits_productization": decision == "PROMOTE_PORTFOLIO_CAPACITY",
            "actual_cash_used": False,
            "profit_proven": False,
        },
    )
    (args.out / "decision.md").write_text(
        _decision_markdown(decision, reasons, evidence, rows),
        encoding="utf-8",
    )
    print("status=pass")
    print(f"case_count={len(rows)}")
    print(f"decision={decision}")
    print(f"out={args.out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
