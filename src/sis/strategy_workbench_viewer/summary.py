from __future__ import annotations

from typing import Any


STATUS_KEYS = (
    "cycle_status",
    "gate_status",
    "tournament_status",
    "decision_status",
    "plan_status",
    "ingest_status",
    "review_status",
    "status",
    "decision",
    "validation_status",
    "readiness_status",
    "recommended_action",
)

LATEST_STATUS_AS_ARTIFACT_STATUS_SCHEMAS = frozenset(
    {
        "strategy_case_lite.v1",
        "strategy_case_index.v1",
    }
)

SUMMARY_KEYS = (
    "gate_id",
    "gate_status",
    "cycle_status",
    "human_summary",
    "report_id",
    "tournament_status",
    "leader_action",
    "primary_metric",
    "event_count",
    "leader_actual_cash_result_usd",
    "proxy_gap_count",
    "failed_condition_count",
    "present_stage_count",
    "missing_artifact_path_count",
    "known_gap_count",
    "stop_reason_count",
    "strategy_id",
    "first_observed_at",
    "last_observed_at",
    "pnl_unavailable_reason",
    "proposal_id",
    "review_id",
    "decision",
    "decision_id",
    "plan_id",
    "manifest_id",
    "recommended_action",
    "latest_status",
    "open_action_count",
    "pending_human_review_count",
    "boundary_violation_count",
    "scanned_json_count",
    "total_item_count",
    "broken_artifact_count",
    "crypto_perp_gate_follow_up_count",
    "crypto_perp_truth_cycle_follow_up_count",
    "normal_paper_gap_count",
    "drift_review_needed_count",
    "learning_request_pending_count",
    "artifact_count",
    "timeline_count",
    "index_id",
    "case_count",
    "strategy_count",
    "latest_case_path",
    "case_index_source_hash",
    "first_source_artifact_type",
    "first_source_artifact_path",
    "first_source_artifact_schema_version",
    "first_source_artifact_hash",
    "first_brief_item_category",
    "first_brief_item_severity",
    "first_brief_item_status",
    "first_brief_item_schema_version",
    "first_brief_item_action",
    "first_brief_item_reason",
    "first_brief_item_path",
    "ledger_entry_count",
    "paper_order_count",
    "paper_fill_count",
    "no_fill_count",
    "blocked_count",
    "unique_intent_count",
    "unique_symbol_count",
    "max_observed_quote_age_ms",
    "filled_notional_usd_total",
    "max_observed_spread_bps",
    "pnl_available",
    "backtest_passed",
    "trade_count",
    "total_return",
    "max_drawdown",
    "net_pnl_usd",
    "ending_equity_usd",
    "max_drawdown_loss_usd",
    "executed_count",
    "check_count",
    "passed_count",
    "failed_count",
    "pack_artifact_count",
    "suite_method_count",
    "suite_run_count",
    "suite_passed_count",
    "external_result_count",
    "external_engine_run",
    "external_adapters_required_for_completion",
    "standard_engine",
    "suite_id",
    "run_count",
    "method_count",
    "cost_drag_bps",
    "best_run_id",
    "best_run_method_id",
    "best_run_case_id",
    "best_run_total_return",
    "best_run_trade_count",
    "comparison_id",
    "method_result_count",
    "framework_adapter_count",
    "native_total_return",
    "native_trade_count",
    "suite_failed_run_count",
    "threshold_failure_count",
    "suite_best_run_method_id",
    "suite_best_run_case_id",
    "suite_best_run_total_return",
    "suite_best_run_trade_count",
    "weakest_era",
    "weakest_era_total_return",
    "weakest_era_trade_count",
    "portfolio_run_status",
    "portfolio_framework_id",
    "metric_status",
    "metric_framework_id",
    "report_status",
    "report_framework_id",
    "paper_only",
    "live_order_submitted",
    "locked_dependency_added",
    "external_framework_policy_decision",
    "source_proposal_status",
    "proposed_change_count",
    "first_proposed_change_target_section",
    "first_proposed_change_source_reason",
    "first_proposed_change_evidence_summary",
    "approved_change_count",
    "required_action_count",
    "manual_contract_update_input_allowed",
    "requires_human_contract_update",
    "direct_contract_edit_allowed",
    "auto_applied",
    "paper_execution_allowed",
    "live_allowed",
    "first_open_action",
    "first_blocked_reason",
)

SUMMARY_STRING_KEYS = frozenset(
    {
        "gate_id",
        "gate_status",
        "cycle_status",
        "human_summary",
        "report_id",
        "tournament_status",
        "leader_action",
        "primary_metric",
        "strategy_id",
        "first_observed_at",
        "last_observed_at",
        "pnl_unavailable_reason",
        "external_framework_policy_decision",
        "standard_engine",
        "suite_id",
        "best_run_id",
        "best_run_method_id",
        "best_run_case_id",
        "comparison_id",
        "suite_best_run_method_id",
        "suite_best_run_case_id",
        "weakest_era",
        "portfolio_run_status",
        "portfolio_framework_id",
        "metric_status",
        "metric_framework_id",
        "report_status",
        "report_framework_id",
        "proposal_id",
        "review_id",
        "decision",
        "decision_id",
        "plan_id",
        "manifest_id",
        "recommended_action",
        "latest_status",
        "first_stop_reason",
        "first_next_step",
        "first_next_step_purpose",
        "first_next_step_command",
        "first_stage_blocker",
        "first_stage_blocker_status",
        "first_stage_blocker_expected_cli_option",
        "first_stage_blocker_expected_artifact_hint",
        "first_stage_blocker_artifact_path",
        "approval_boundary",
        "first_source_artifact_type",
        "first_source_artifact_path",
        "first_source_artifact_schema_version",
        "first_source_artifact_hash",
        "first_brief_item_category",
        "first_brief_item_severity",
        "first_brief_item_status",
        "first_brief_item_schema_version",
        "first_brief_item_action",
        "first_brief_item_reason",
        "first_brief_item_path",
        "index_id",
        "latest_case_path",
        "case_index_source_hash",
        "source_proposal_status",
        "first_proposed_change_target_section",
        "first_proposed_change_source_reason",
        "first_proposed_change_evidence_summary",
        "first_open_action",
        "first_blocked_reason",
    }
)

SUMMARY_INTEGER_KEYS = frozenset(
    {
        "event_count",
        "proxy_gap_count",
        "failed_condition_count",
        "present_stage_count",
        "missing_artifact_path_count",
        "known_gap_count",
        "stop_reason_count",
        "open_action_count",
        "pending_human_review_count",
        "boundary_violation_count",
        "scanned_json_count",
        "total_item_count",
        "broken_artifact_count",
        "crypto_perp_gate_follow_up_count",
        "crypto_perp_truth_cycle_follow_up_count",
        "normal_paper_gap_count",
        "drift_review_needed_count",
        "learning_request_pending_count",
        "artifact_count",
        "timeline_count",
        "case_count",
        "strategy_count",
        "proposed_change_count",
        "approved_change_count",
        "required_action_count",
        "ledger_entry_count",
        "paper_order_count",
        "paper_fill_count",
        "no_fill_count",
        "blocked_count",
        "unique_intent_count",
        "unique_symbol_count",
        "max_observed_quote_age_ms",
        "trade_count",
        "executed_count",
        "check_count",
        "passed_count",
        "failed_count",
        "pack_artifact_count",
        "suite_method_count",
        "suite_run_count",
        "suite_passed_count",
        "external_result_count",
        "run_count",
        "method_count",
        "best_run_trade_count",
        "method_result_count",
        "framework_adapter_count",
        "native_trade_count",
        "suite_failed_run_count",
        "threshold_failure_count",
        "suite_best_run_trade_count",
        "weakest_era_trade_count",
    }
)

SUMMARY_NUMBER_KEYS = frozenset(
    {
        "leader_actual_cash_result_usd",
        "filled_notional_usd_total",
        "max_observed_spread_bps",
        "total_return",
        "max_drawdown",
        "net_pnl_usd",
        "ending_equity_usd",
        "max_drawdown_loss_usd",
        "cost_drag_bps",
        "best_run_total_return",
        "native_total_return",
        "suite_best_run_total_return",
        "weakest_era_total_return",
    }
)

SUMMARY_BOOLEAN_KEYS = frozenset(
    {
        "first_next_step_requires_explicit_approval",
        "backtest_passed",
        "paper_only",
        "live_order_submitted",
        "locked_dependency_added",
        "external_engine_run",
        "external_adapters_required_for_completion",
        "manual_contract_update_input_allowed",
        "requires_human_contract_update",
        "direct_contract_edit_allowed",
        "auto_applied",
        "paper_execution_allowed",
        "live_allowed",
        "pnl_available",
    }
)

SUMMARY_FALSE_ONLY_KEYS = frozenset(
    {
        "first_next_step_network_allowed",
        "first_next_step_exchange_write_allowed",
        "first_next_step_live_order_allowed",
    }
)


def _first_status(payload: dict[str, Any]) -> str | None:
    for key in STATUS_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def artifact_status(payload: dict[str, Any], summary: dict[str, Any]) -> str | None:
    status = _first_status(payload)
    if status is not None:
        return status
    if payload.get("schema_version") in LATEST_STATUS_AS_ARTIFACT_STATUS_SCHEMAS:
        latest_status = summary.get("latest_status")
        if isinstance(latest_status, str) and latest_status:
            return latest_status
    return None


def _compact_summary_value(key: str, value: Any) -> str | int | float | bool | None:
    if key in SUMMARY_STRING_KEYS:
        return value if isinstance(value, str) else None
    if key in SUMMARY_INTEGER_KEYS:
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    if key in SUMMARY_NUMBER_KEYS:
        return value if isinstance(value, int | float) and not isinstance(value, bool) else None
    if key in SUMMARY_BOOLEAN_KEYS:
        return value if isinstance(value, bool) else None
    if key in SUMMARY_FALSE_ONLY_KEYS:
        return value if value is False else None
    if isinstance(value, str | int | float | bool):
        return value
    return None


def _set_compact_summary_value(summary: dict[str, Any], key: str, value: Any) -> None:
    compact_value = _compact_summary_value(key, value)
    if compact_value is not None and key not in summary:
        summary[key] = compact_value


def _set_compact_summary_values(
    summary: dict[str, Any],
    source: dict[str, Any],
    pairs: tuple[tuple[str, str], ...],
) -> None:
    for source_key, summary_key in pairs:
        _set_compact_summary_value(summary, summary_key, source.get(source_key))


def compact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    schema_version = payload.get("schema_version")
    status = payload.get("gate_status") or payload.get("cycle_status")
    if (
        schema_version in {"crypto_perp_tournament_gate.v1", "crypto_perp_truth_cycle_status.v1"}
        and status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
    ):
        summary["approval_boundary"] = (
            "separate human approval is required before any tiny live measurement; "
            "this is not live execution permission"
        )
    for key in SUMMARY_KEYS:
        value = payload.get(key)
        _set_compact_summary_value(summary, key, value)
    nested = payload.get("summary")
    if isinstance(nested, dict):
        for key in SUMMARY_KEYS:
            value = nested.get(key)
            _set_compact_summary_value(summary, key, value)
    if schema_version in {
        "strategy_authoring_backtest_result.v1",
        "strategy_backtest_pack.v1",
    } and isinstance(nested, dict):
        aggregate_metrics = nested.get("aggregate_metrics")
        if isinstance(aggregate_metrics, dict):
            _set_compact_summary_values(
                summary,
                aggregate_metrics,
                (
                    ("trade_count", "trade_count"),
                    ("total_return", "total_return"),
                    ("max_drawdown", "max_drawdown"),
                ),
            )
        capital = nested.get("capital")
        if isinstance(capital, dict):
            _set_compact_summary_values(
                summary,
                capital,
                (
                    ("net_pnl_usd", "net_pnl_usd"),
                    ("ending_equity_usd", "ending_equity_usd"),
                    ("max_drawdown_loss_usd", "max_drawdown_loss_usd"),
                ),
            )
    if schema_version == "strategy_backtest_pack.v1":
        artifacts = payload.get("artifacts")
        if isinstance(artifacts, dict):
            _set_compact_summary_value(summary, "pack_artifact_count", len(artifacts))
        external_policy = payload.get("external_framework_policy")
        if isinstance(external_policy, dict):
            _set_compact_summary_values(
                summary,
                external_policy,
                (
                    ("decision", "external_framework_policy_decision"),
                    ("standard_engine", "standard_engine"),
                    ("locked_dependency_added", "locked_dependency_added"),
                    (
                        "external_adapters_required_for_completion",
                        "external_adapters_required_for_completion",
                    ),
                ),
            )
    if schema_version == "strategy_backtest_suite_result.v1":
        aggregate = payload.get("aggregate")
        if isinstance(aggregate, dict):
            _set_compact_summary_values(
                summary,
                aggregate,
                (
                    ("run_count", "run_count"),
                    ("passed_count", "passed_count"),
                    ("failed_count", "failed_count"),
                    ("trade_count", "trade_count"),
                    ("total_return", "total_return"),
                    ("cost_drag_bps", "cost_drag_bps"),
                ),
            )
        method_matrix = payload.get("method_matrix")
        if isinstance(method_matrix, dict):
            _set_compact_summary_value(summary, "method_count", method_matrix.get("method_count"))
        best_run = payload.get("best_run")
        if isinstance(best_run, dict):
            _set_compact_summary_values(
                summary,
                best_run,
                (
                    ("run_id", "best_run_id"),
                    ("method_id", "best_run_method_id"),
                    ("case_id", "best_run_case_id"),
                ),
            )
            best_summary = best_run.get("summary")
            if isinstance(best_summary, dict):
                best_metrics = best_summary.get("aggregate_metrics")
                if isinstance(best_metrics, dict):
                    _set_compact_summary_values(
                        summary,
                        best_metrics,
                        (
                            ("total_return", "best_run_total_return"),
                            ("trade_count", "best_run_trade_count"),
                        ),
                    )
    if schema_version == "strategy_backtest_comparison.v1":
        for source_key, summary_key in (
            ("method_results", "method_result_count"),
            ("external_results", "external_result_count"),
            ("framework_adapters", "framework_adapter_count"),
        ):
            source_value = payload.get(source_key)
            if isinstance(source_value, list):
                _set_compact_summary_value(summary, summary_key, len(source_value))
        native_result = payload.get("native_result")
        if isinstance(native_result, dict):
            _set_compact_summary_values(
                summary,
                native_result,
                (
                    ("total_return", "native_total_return"),
                    ("trade_count", "native_trade_count"),
                ),
            )
        diagnostics = payload.get("comparison_diagnostics")
        if isinstance(diagnostics, dict):
            for source_key, summary_key in (
                ("suite_failed_runs", "suite_failed_run_count"),
                ("threshold_failures", "threshold_failure_count"),
            ):
                source_value = diagnostics.get(source_key)
                if isinstance(source_value, list):
                    _set_compact_summary_value(summary, summary_key, len(source_value))
            suite_best_runs = diagnostics.get("suite_best_runs")
            if isinstance(suite_best_runs, list) and suite_best_runs:
                first_best_run = next(
                    (item for item in suite_best_runs if isinstance(item, dict)),
                    None,
                )
                if first_best_run is not None:
                    _set_compact_summary_values(
                        summary,
                        first_best_run,
                        (
                            ("method_id", "suite_best_run_method_id"),
                            ("case_id", "suite_best_run_case_id"),
                            ("total_return", "suite_best_run_total_return"),
                            ("trade_count", "suite_best_run_trade_count"),
                        ),
                    )
            weakest_eras = diagnostics.get("weakest_eras")
            if isinstance(weakest_eras, list) and weakest_eras:
                first_weakest = next(
                    (item for item in weakest_eras if isinstance(item, dict)),
                    None,
                )
                if first_weakest is not None:
                    _set_compact_summary_values(
                        summary,
                        first_weakest,
                        (
                            ("era", "weakest_era"),
                            ("total_return", "weakest_era_total_return"),
                            ("trade_count", "weakest_era_trade_count"),
                        ),
                    )
        for source_key, pairs in (
            (
                "portfolio_comparison",
                (
                    ("run_status", "portfolio_run_status"),
                    ("framework_id", "portfolio_framework_id"),
                ),
            ),
            (
                "metric_extension",
                (
                    ("metric_status", "metric_status"),
                    ("framework_id", "metric_framework_id"),
                ),
            ),
            (
                "report_extension",
                (
                    ("report_status", "report_status"),
                    ("framework_id", "report_framework_id"),
                ),
            ),
        ):
            source_value = payload.get(source_key)
            if isinstance(source_value, dict):
                _set_compact_summary_values(summary, source_value, pairs)
    if schema_version == "strategy_case_index.v1":
        _set_compact_summary_value(summary, "index_id", payload.get("index_id"))
        _set_compact_summary_value(summary, "case_count", payload.get("case_count"))
        _set_compact_summary_value(summary, "strategy_count", payload.get("strategy_count"))
        cases = payload.get("cases")
        if isinstance(cases, list) and cases:
            case_items = [case for case in cases if isinstance(case, dict)]
            if case_items:
                latest_case = sorted(
                    case_items,
                    key=lambda case: (
                        str(case.get("updated_at") or ""),
                        str(case.get("case_path") or ""),
                    ),
                )[-1]
                _set_compact_summary_value(
                    summary, "latest_status", latest_case.get("latest_status")
                )
                _set_compact_summary_value(
                    summary, "latest_case_path", latest_case.get("case_path")
                )
                open_actions = latest_case.get("open_actions")
                if isinstance(open_actions, list) and open_actions:
                    _set_compact_summary_value(summary, "first_open_action", str(open_actions[0]))
                blocked_reasons = latest_case.get("blocked_reasons")
                if isinstance(blocked_reasons, list) and blocked_reasons:
                    _set_compact_summary_value(
                        summary, "first_blocked_reason", str(blocked_reasons[0])
                    )
        source_artifacts = payload.get("source_artifacts")
        if isinstance(source_artifacts, list) and source_artifacts:
            first_source = source_artifacts[0]
            if isinstance(first_source, dict):
                _set_compact_summary_value(
                    summary, "case_index_source_hash", first_source.get("sha256")
                )
    if schema_version == "strategy_case_lite.v1":
        case_summary = payload.get("summary")
        if isinstance(case_summary, dict):
            open_actions = case_summary.get("open_actions")
            if isinstance(open_actions, list) and open_actions:
                _set_compact_summary_value(summary, "first_open_action", str(open_actions[0]))
            blocked_reasons = case_summary.get("blocked_reasons")
            if isinstance(blocked_reasons, list) and blocked_reasons:
                _set_compact_summary_value(summary, "first_blocked_reason", str(blocked_reasons[0]))
        source_artifacts = payload.get("source_artifacts")
        if isinstance(source_artifacts, list) and source_artifacts:
            first_source = next(
                (artifact for artifact in source_artifacts if isinstance(artifact, dict)),
                None,
            )
            if first_source is not None:
                _set_compact_summary_values(
                    summary,
                    first_source,
                    (
                        ("artifact_type", "first_source_artifact_type"),
                        ("path", "first_source_artifact_path"),
                        ("schema_version", "first_source_artifact_schema_version"),
                        ("sha256", "first_source_artifact_hash"),
                    ),
                )
    if schema_version == "strategy_daily_brief.v1":
        items = payload.get("items")
        if isinstance(items, list) and items:
            first_item = next((item for item in items if isinstance(item, dict)), None)
            if first_item is not None:
                _set_compact_summary_values(
                    summary,
                    first_item,
                    (
                        ("category", "first_brief_item_category"),
                        ("severity", "first_brief_item_severity"),
                        ("status", "first_brief_item_status"),
                        ("schema_version", "first_brief_item_schema_version"),
                        ("action", "first_brief_item_action"),
                        ("reason", "first_brief_item_reason"),
                        ("path", "first_brief_item_path"),
                    ),
                )
    if schema_version == "strategy_input_contract_update_proposal.v1":
        proposed_changes = payload.get("proposed_changes")
        if isinstance(proposed_changes, list):
            _set_compact_summary_value(summary, "proposed_change_count", len(proposed_changes))
            first_change = next(
                (change for change in proposed_changes if isinstance(change, dict)),
                None,
            )
            if first_change is not None:
                for source_key, summary_key in (
                    ("target_section", "first_proposed_change_target_section"),
                    ("source_reason", "first_proposed_change_source_reason"),
                    ("evidence_summary", "first_proposed_change_evidence_summary"),
                ):
                    _set_compact_summary_value(summary, summary_key, first_change.get(source_key))
    if schema_version == "strategy_input_contract_update_review.v1":
        approved_change_ids = payload.get("approved_change_ids")
        if isinstance(approved_change_ids, list):
            _set_compact_summary_value(summary, "approved_change_count", len(approved_change_ids))
        required_actions = payload.get("required_actions")
        if isinstance(required_actions, list):
            _set_compact_summary_value(summary, "required_action_count", len(required_actions))
        source_proposal = payload.get("source_proposal")
        if isinstance(source_proposal, dict):
            _set_compact_summary_value(
                summary, "source_proposal_status", source_proposal.get("proposal_status")
            )
    stop_reasons = payload.get("stop_reasons")
    if isinstance(stop_reasons, list) and stop_reasons and "first_stop_reason" not in summary:
        summary["first_stop_reason"] = str(stop_reasons[0])
    next_steps = payload.get("next_steps")
    if isinstance(next_steps, list) and next_steps:
        first_step = next_steps[0]
        if isinstance(first_step, dict):
            step_id = first_step.get("step_id")
            if isinstance(step_id, str) and step_id and "first_next_step" not in summary:
                summary["first_next_step"] = step_id
            for source_key, summary_key in (
                ("purpose", "first_next_step_purpose"),
                ("command", "first_next_step_command"),
                ("requires_explicit_approval", "first_next_step_requires_explicit_approval"),
                ("network_allowed", "first_next_step_network_allowed"),
                ("exchange_write_allowed", "first_next_step_exchange_write_allowed"),
                ("live_order_allowed", "first_next_step_live_order_allowed"),
            ):
                value = first_step.get(source_key)
                _set_compact_summary_value(summary, summary_key, value)
    stage_checklist = payload.get("stage_checklist")
    if isinstance(stage_checklist, list):
        for item in stage_checklist:
            if not isinstance(item, dict) or item.get("blocks_progress") is not True:
                continue
            stage_id = item.get("stage_id")
            if isinstance(stage_id, str) and stage_id and "first_stage_blocker" not in summary:
                summary["first_stage_blocker"] = stage_id
            for source_key, summary_key in (
                ("status", "first_stage_blocker_status"),
                ("expected_cli_option", "first_stage_blocker_expected_cli_option"),
                ("expected_artifact_hint", "first_stage_blocker_expected_artifact_hint"),
                ("artifact_path", "first_stage_blocker_artifact_path"),
            ):
                value = item.get(source_key)
                _set_compact_summary_value(summary, summary_key, value)
            break
    return summary
