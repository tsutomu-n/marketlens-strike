from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import stable_hash
from sis.profit_core_reality_check.models import (
    ActualCashSummary,
    BlockerSummary,
    BridgeSummary,
    CandidateGenerationSummary,
    LineageSummary,
    NextAction,
    OverallStatus,
    ProfitCoreRealityCheck,
    ProfitCoreRealityCheckProducer,
    ProfitReadinessSummary,
    RealityCheckInputPaths,
    RealityCheckSummary,
    RiskReviewSummary,
)
from sis.profit_core_reality_check.readers import (
    read_json_object_if_present,
    read_jsonl_objects_if_present,
    source_ref,
)


NEXT_BLOCKER_PRIORITY = (
    "SEARCH_LEDGER_MISSING",
    "SUCCESS_ONLY_REPORTING_DETECTED",
    "SEALED_TEST_USED_FOR_SELECTION",
    "AUTHORING_BRIDGE_MISSING",
    "UNSUPPORTED_FAMILY_DOMINATES",
    "UNSUPPORTED_SIDE_BIAS_DOMINATES",
    "NO_SYMBOL_DATA_DOMINATES",
    "MISSING_SOURCE_COLUMNS_DOMINATES",
    "BRIDGED_TECHNICAL_ONLY",
    "PROFIT_READINESS_INVENTORY_MISSING",
    "BLOCKED_MISSING_EVENT_OR_OUTCOME",
    "ACTUAL_CASH_SOURCE_MISSING",
    "RISK_REVIEW_MISSING",
    "NEEDS_ACTUAL_CASH",
    "ACTUAL_CASH_ROWS_MISSING",
    "ACTUAL_CASH_REPORT_GATE_MISSING",
    "NO_BLOCKER_IDENTIFIED",
)

HARD_BLOCKERS = {
    "CANDIDATE_SET_MISSING",
    "SEARCH_LEDGER_MISSING",
    "EXPORT_MANIFEST_MISSING",
    "SUCCESS_ONLY_REPORTING_DETECTED",
    "SEALED_TEST_USED_FOR_SELECTION",
    "AUTHORING_BRIDGE_MISSING",
    "BRIDGE_ALL_BLOCKED",
    "UNSUPPORTED_FAMILY_DOMINATES",
    "UNSUPPORTED_SIDE_BIAS_DOMINATES",
    "NO_SYMBOL_DATA_DOMINATES",
    "MISSING_SOURCE_COLUMNS_DOMINATES",
    "BLOCKED_MISSING_EVENT_OR_OUTCOME",
    "ACTUAL_CASH_SOURCE_MISSING",
    "BLOCKED_BY_VENUE",
    "INCONCLUSIVE_DATA",
    "KILL",
    "NEEDS_ACTUAL_CASH",
    "ACTUAL_CASH_ROWS_MISSING",
    "ACTUAL_CASH_REPORT_GATE_MISSING",
    "NON_ACTUAL_ROWS_REJECTED",
}


def build_profit_core_reality_check(
    *,
    candidate_set_path: Path,
    search_ledger_path: Path,
    export_manifest_path: Path | None = None,
    authoring_bridge_path: Path | None = None,
    profit_readiness_inventory_path: Path | None = None,
    source_availability_path: Path | None = None,
    risk_review_path: Path | None = None,
    actual_cash_rows_summary_path: Path | None = None,
    actual_cash_report_gate_path: Path | None = None,
    created_at: datetime | str | None = None,
) -> ProfitCoreRealityCheck:
    created = (
        datetime.now(timezone.utc).replace(microsecond=0)
        if created_at is None
        else ensure_utc_aware("created_at", created_at)
    )
    candidate_set = read_json_object_if_present(candidate_set_path)
    search_ledger_rows = read_jsonl_objects_if_present(search_ledger_path)
    export_manifest = read_json_object_if_present(export_manifest_path)
    authoring_bridge = read_json_object_if_present(authoring_bridge_path)
    inventory = read_json_object_if_present(profit_readiness_inventory_path)
    source_availability = read_json_object_if_present(source_availability_path)
    risk_review = read_json_object_if_present(risk_review_path)
    actual_cash_rows_summary = read_json_object_if_present(actual_cash_rows_summary_path)
    actual_cash_report_gate = read_json_object_if_present(actual_cash_report_gate_path)

    source_refs = [
        source_ref(path, payload)
        for path, payload in (
            (candidate_set_path, candidate_set),
            (export_manifest_path, export_manifest),
            (authoring_bridge_path, authoring_bridge),
            (profit_readiness_inventory_path, inventory),
            (source_availability_path, source_availability),
            (risk_review_path, risk_review),
            (actual_cash_rows_summary_path, actual_cash_rows_summary),
            (actual_cash_report_gate_path, actual_cash_report_gate),
        )
        if path is not None and payload is not None
    ]
    if search_ledger_rows is not None:
        source_refs.append(source_ref(search_ledger_path))

    blockers_by_stage: dict[str, list[str]] = defaultdict(list)
    known_gaps: list[str] = []
    candidate_generation = _candidate_generation_summary(
        candidate_set=candidate_set,
        search_ledger_rows=search_ledger_rows,
        export_manifest=export_manifest,
        blockers_by_stage=blockers_by_stage,
        known_gaps=known_gaps,
    )
    side_bias_by_candidate = _side_bias_by_candidate(candidate_set)
    bridge_summary = _bridge_summary(
        authoring_bridge=authoring_bridge,
        side_bias_by_candidate=side_bias_by_candidate,
        blockers_by_stage=blockers_by_stage,
        known_gaps=known_gaps,
    )
    profit_readiness_summary = _profit_readiness_summary(
        inventory=inventory,
        source_availability=source_availability,
        blockers_by_stage=blockers_by_stage,
        known_gaps=known_gaps,
    )
    risk_review_summary = _risk_review_summary(
        risk_review=risk_review,
        blockers_by_stage=blockers_by_stage,
        known_gaps=known_gaps,
    )
    actual_cash_summary = _actual_cash_summary(
        actual_cash_rows_summary=actual_cash_rows_summary,
        actual_cash_report_gate=actual_cash_report_gate,
        blockers_by_stage=blockers_by_stage,
        known_gaps=known_gaps,
    )
    lineage_summary = _lineage_summary(
        candidate_set=candidate_set,
        search_ledger_rows=search_ledger_rows,
        export_manifest=export_manifest,
        authoring_bridge=authoring_bridge,
        blockers_by_stage=blockers_by_stage,
        known_gaps=known_gaps,
    )

    blocker_counts = Counter(_flatten(blockers_by_stage.values()))
    next_blocker = _next_single_blocker_to_fix(blocker_counts)
    blocker_summary = BlockerSummary(
        blocker_counts=dict(sorted(blocker_counts.items())),
        blockers_by_stage={
            key: list(dict.fromkeys(values)) for key, values in blockers_by_stage.items()
        },
        blockers_by_family=bridge_summary.blocked_by_family,
        top_blockers=_top_blockers(blocker_counts),
        next_single_blocker_to_fix=next_blocker,
    )
    deduped_known_gaps = _dedupe([*known_gaps, *lineage_summary.lineage_gaps])
    overall_status = _overall_status(blocker_counts)
    summary = RealityCheckSummary(
        overall_status=overall_status,
        next_action=_next_action(next_blocker),
        candidate_count_total=candidate_generation.candidate_count_total,
        candidate_count_shortlisted=candidate_generation.candidate_count_shortlisted,
        candidate_count_rejected=candidate_generation.candidate_count_rejected,
        bridge_blocked_count=bridge_summary.bridge_blocked_count,
        bridge_bridged_count=bridge_summary.bridge_bridged_count,
        actual_cash_available_count=(
            actual_cash_summary.actual_cash_row_count
            if actual_cash_summary.report_actual_cash
            else 0
        ),
        known_gap_count=len(deduped_known_gaps),
    )
    artifact_id = stable_hash(
        [
            "profit-core-reality-check",
            serialize_utc_z(created),
            [ref.model_dump(mode="json") for ref in source_refs],
            next_blocker,
        ]
    )
    return ProfitCoreRealityCheck(
        artifact_id=artifact_id,
        created_at=created,
        producer=ProfitCoreRealityCheckProducer(command="profit-core-reality-check"),
        source_refs=source_refs,
        input_paths=RealityCheckInputPaths(
            candidate_set_path=candidate_set_path.as_posix(),
            search_ledger_path=search_ledger_path.as_posix(),
            export_manifest_path=_path_text(export_manifest_path),
            authoring_bridge_path=_path_text(authoring_bridge_path),
            profit_readiness_inventory_path=_path_text(profit_readiness_inventory_path),
            source_availability_path=_path_text(source_availability_path),
            risk_review_path=_path_text(risk_review_path),
            actual_cash_rows_summary_path=_path_text(actual_cash_rows_summary_path),
            actual_cash_report_gate_path=_path_text(actual_cash_report_gate_path),
        ),
        summary=summary,
        candidate_generation=candidate_generation,
        bridge_summary=bridge_summary,
        profit_readiness_summary=profit_readiness_summary,
        risk_review_summary=risk_review_summary,
        actual_cash_summary=actual_cash_summary,
        lineage_summary=lineage_summary,
        blocker_summary=blocker_summary,
        next_single_blocker_to_fix=next_blocker,
        known_gaps=deduped_known_gaps,
    )


def _candidate_generation_summary(
    *,
    candidate_set: dict[str, Any] | None,
    search_ledger_rows: list[dict[str, Any]] | None,
    export_manifest: dict[str, Any] | None,
    blockers_by_stage: dict[str, list[str]],
    known_gaps: list[str],
) -> CandidateGenerationSummary:
    if candidate_set is None:
        blockers_by_stage["candidate_generation"].append("CANDIDATE_SET_MISSING")
        return CandidateGenerationSummary(
            candidate_set_present=False,
            search_ledger_present=search_ledger_rows is not None,
            export_manifest_present=export_manifest is not None,
        )
    summary = _mapping(candidate_set.get("search_ledger_summary"))
    candidates = _candidate_inventory(candidate_set)
    total = _int(summary.get("candidate_count_total"), len(candidates))
    shortlisted = _int(
        summary.get("candidate_count_shortlisted"), _decision_count(candidates, "SHORTLISTED")
    )
    rejected = _int(
        summary.get("candidate_count_rejected"), _decision_count(candidates, "REJECTED")
    )
    success_only = _bool(summary.get("success_only_reporting"), False) or (
        total > 0 and shortlisted > 0 and rejected == 0
    )
    sealed_test = (
        _bool(summary.get("sealed_test_used_for_selection"), False)
        or _bool(
            _mapping(candidate_set.get("split_policy")).get("uses_sealed_test_for_selection"), False
        )
        or _bool(
            _mapping(candidate_set.get("leakage_policy")).get("uses_sealed_test_for_selection"),
            False,
        )
        or any(
            _bool(
                _mapping(candidate.get("leakage_checks")).get("uses_sealed_test_for_selection"),
                False,
            )
            for candidate in candidates
        )
    )
    if search_ledger_rows is None:
        blockers_by_stage["candidate_generation"].append("SEARCH_LEDGER_MISSING")
    if export_manifest is None:
        blockers_by_stage["candidate_generation"].append("EXPORT_MANIFEST_MISSING")
    if success_only:
        blockers_by_stage["candidate_generation"].append("SUCCESS_ONLY_REPORTING_DETECTED")
    if sealed_test:
        blockers_by_stage["candidate_generation"].append("SEALED_TEST_USED_FOR_SELECTION")
    if total > 0 and shortlisted == 0:
        blockers_by_stage["candidate_generation"].append("NO_SHORTLISTED_CANDIDATES")
    known_gaps.extend(_strings(_mapping(candidate_set.get("selection_policy")).get("known_gaps")))
    return CandidateGenerationSummary(
        candidate_set_present=True,
        search_ledger_present=search_ledger_rows is not None,
        export_manifest_present=export_manifest is not None,
        candidate_set_id=_str_or_none(candidate_set.get("candidate_set_id")),
        candidate_count_total=total,
        candidate_count_shortlisted=shortlisted,
        candidate_count_rejected=rejected,
        trial_count_total=_int(summary.get("trial_count_total"), total),
        candidate_cap=_int(summary.get("candidate_cap"), 0),
        cap_rejection_count=_int(summary.get("cap_rejection_count"), 0),
        duplicate_rejection_count=_int(summary.get("duplicate_rejection_count"), 0),
        validation_peek_count=_int(summary.get("validation_peek_count"), 0),
        rerank_count=_int(summary.get("rerank_count"), 0),
        sealed_test_used_for_selection=sealed_test,
        success_only_reporting_detected=success_only,
        shortlisted_family_counts=_family_counts(candidates, "SHORTLISTED"),
        rejected_family_counts=_family_counts(candidates, "REJECTED"),
        selection_adjusted_metrics_status_counts=_selection_status_counts(candidates),
    )


def _bridge_summary(
    *,
    authoring_bridge: dict[str, Any] | None,
    side_bias_by_candidate: dict[str, str],
    blockers_by_stage: dict[str, list[str]],
    known_gaps: list[str],
) -> BridgeSummary:
    if authoring_bridge is None:
        blockers_by_stage["authoring_bridge"].append("AUTHORING_BRIDGE_MISSING")
        return BridgeSummary(bridge_manifest_present=False)
    candidates = [
        item for item in _list(authoring_bridge.get("candidates")) if isinstance(item, dict)
    ]
    status_counts = Counter(_string(candidate.get("status")) for candidate in candidates)
    status_counts.pop("", None)
    bridged_ids = [
        _string(candidate.get("candidate_id"))
        for candidate in candidates
        if _string(candidate.get("status")) == "BRIDGED" and _string(candidate.get("candidate_id"))
    ]
    blocked = [
        candidate for candidate in candidates if _string(candidate.get("status")) != "BRIDGED"
    ]
    blocked_ids = [
        _string(candidate.get("candidate_id"))
        for candidate in blocked
        if _string(candidate.get("candidate_id"))
    ]
    reason_counts: Counter[str] = Counter()
    blocked_by_family: Counter[str] = Counter()
    blocked_by_side_bias: Counter[str] = Counter()
    blocked_by_symbol: Counter[str] = Counter()
    for candidate in blocked:
        candidate_id = _string(candidate.get("candidate_id"))
        status = _string(candidate.get("status"))
        if status:
            reason_counts[status] += 1
        for blocker in _strings(candidate.get("blockers")):
            reason_counts[blocker] += 1
        family = _string(candidate.get("family"))
        if family:
            blocked_by_family[family] += 1
        side_bias = side_bias_by_candidate.get(candidate_id)
        if side_bias:
            blocked_by_side_bias[side_bias] += 1
        for symbol in _strings(candidate.get("symbols")):
            blocked_by_symbol[symbol] += 1
    bridge_candidate_count = len(candidates)
    bridged_count = status_counts.get("BRIDGED", 0)
    blocked_count = bridge_candidate_count - bridged_count
    if bridge_candidate_count > 0 and bridged_count == 0:
        blockers_by_stage["authoring_bridge"].append("BRIDGE_ALL_BLOCKED")
    if _dominant(reason_counts, "BLOCKED_UNSUPPORTED_FAMILY_MAPPING"):
        blockers_by_stage["authoring_bridge"].append("UNSUPPORTED_FAMILY_DOMINATES")
    if _dominant(reason_counts, "BLOCKED_UNSUPPORTED_SIDE_BIAS"):
        blockers_by_stage["authoring_bridge"].append("UNSUPPORTED_SIDE_BIAS_DOMINATES")
    if _dominant(reason_counts, "BLOCKED_NO_SYMBOL_DATA"):
        blockers_by_stage["authoring_bridge"].append("NO_SYMBOL_DATA_DOMINATES")
    if _dominant(reason_counts, "BLOCKED_MISSING_SOURCE_COLUMNS"):
        blockers_by_stage["authoring_bridge"].append("MISSING_SOURCE_COLUMNS_DOMINATES")
    if bridged_count > 0:
        blockers_by_stage["authoring_bridge"].append("BRIDGED_TECHNICAL_ONLY")
    known_gaps.extend(_strings(authoring_bridge.get("known_gaps")))
    return BridgeSummary(
        bridge_manifest_present=True,
        bridge_candidate_count=bridge_candidate_count,
        bridge_bridged_count=bridged_count,
        bridge_blocked_count=blocked_count,
        bridge_status_counts=dict(sorted(status_counts.items())),
        blocked_reason_counts=dict(sorted(reason_counts.items())),
        blocked_by_family=dict(sorted(blocked_by_family.items())),
        blocked_by_side_bias=dict(sorted(blocked_by_side_bias.items())),
        blocked_by_symbol=dict(sorted(blocked_by_symbol.items())),
        technical_bridged_candidate_ids=sorted(bridged_ids),
        blocked_candidate_ids=sorted(blocked_ids),
    )


def _profit_readiness_summary(
    *,
    inventory: dict[str, Any] | None,
    source_availability: dict[str, Any] | None,
    blockers_by_stage: dict[str, list[str]],
    known_gaps: list[str],
) -> ProfitReadinessSummary:
    if inventory is None:
        blockers_by_stage["profit_readiness"].append("PROFIT_READINESS_INVENTORY_MISSING")
    if source_availability is None:
        blockers_by_stage["profit_readiness"].append("SOURCE_AVAILABILITY_MISSING")
        blockers_by_stage["profit_readiness"].append("ACTUAL_CASH_SOURCE_MISSING")
    inventory_summary = _mapping(inventory.get("summary") if inventory else None)
    inventory_status = _str_or_none(inventory.get("inventory_status") if inventory else None)
    if inventory_status == "BLOCKED_MISSING_EVENT_OR_OUTCOME":
        blockers_by_stage["profit_readiness"].append("BLOCKED_MISSING_EVENT_OR_OUTCOME")
    source_statuses = [
        item
        for item in _list(
            source_availability.get("source_statuses") if source_availability else None
        )
        if isinstance(item, dict)
    ]
    source_counts = Counter()
    for status in source_statuses:
        label = _string(status.get("reason")) or _string(status.get("source_id")) or "unknown"
        available = "available" if _bool(status.get("available"), False) else "missing"
        source_counts[f"{available}:{label}"] += 1
    can_compute_actual_cash = _bool(
        source_availability.get("can_compute_actual_cash") if source_availability else None,
        False,
    )
    if source_availability is not None and not can_compute_actual_cash:
        blockers_by_stage["profit_readiness"].append("ACTUAL_CASH_SOURCE_MISSING")
    known_gaps.extend(_strings(inventory.get("known_gaps") if inventory else None))
    known_gaps.extend(
        _strings(source_availability.get("known_gaps") if source_availability else None)
    )
    return ProfitReadinessSummary(
        inventory_present=inventory is not None,
        inventory_status=inventory_status,
        real_event_count=_int(
            inventory_summary.get("real_event_count"),
            _int(inventory_summary.get("event_count"), 0),
        ),
        matured_outcome_count=_int(
            inventory_summary.get("matured_outcome_count"),
            _int(inventory_summary.get("outcome_count"), 0),
        ),
        cash_ledger_count=_int(inventory_summary.get("cash_ledger_count"), 0),
        live_measurement_count=_int(inventory_summary.get("live_measurement_count"), 0),
        source_availability_present=source_availability is not None,
        can_compute_cost_adjusted_estimate=_bool(
            source_availability.get("can_compute_cost_adjusted_estimate")
            if source_availability
            else None,
            False,
        ),
        can_compute_actual_cash=can_compute_actual_cash,
        source_status_counts=dict(sorted(source_counts.items())),
    )


def _risk_review_summary(
    *,
    risk_review: dict[str, Any] | None,
    blockers_by_stage: dict[str, list[str]],
    known_gaps: list[str],
) -> RiskReviewSummary:
    if risk_review is None:
        blockers_by_stage["risk_review"].append("RISK_REVIEW_MISSING")
        return RiskReviewSummary(risk_review_present=False)
    status = _str_or_none(risk_review.get("review_status"))
    if status in {"BLOCKED_BY_VENUE", "INCONCLUSIVE_DATA", "KILL", "NEEDS_ACTUAL_CASH"}:
        blockers_by_stage["risk_review"].append(status)
    conditions = [item for item in _list(risk_review.get("conditions")) if isinstance(item, dict)]
    condition_statuses = {
        _string(condition.get("condition_id")): _bool(condition.get("passed"), False)
        for condition in conditions
        if _string(condition.get("condition_id"))
    }
    failed_count = sum(1 for passed in condition_statuses.values() if not passed)
    actual_cash_available = condition_statuses.get("actual_cash_available", False)
    known_gaps.extend(_strings(risk_review.get("known_gaps")))
    return RiskReviewSummary(
        risk_review_present=True,
        risk_review_status=status,
        recommended_action=_str_or_none(risk_review.get("recommended_action")),
        leader_action=_str_or_none(risk_review.get("leader_action")),
        after_cost_edge_over_no_trade_usd=_str_or_none(
            risk_review.get("after_cost_edge_over_no_trade_usd")
        ),
        stress_edge_over_no_trade_usd=_str_or_none(
            risk_review.get("stress_edge_over_no_trade_usd")
        ),
        dollars_per_hour=_str_or_none(risk_review.get("dollars_per_hour")),
        largest_loss_usd=_str_or_none(risk_review.get("largest_loss_usd")),
        profit_concentration=_str_or_none(risk_review.get("profit_concentration")),
        actual_cash_available=actual_cash_available,
        failed_condition_count=failed_count,
        condition_statuses=condition_statuses,
    )


def _actual_cash_summary(
    *,
    actual_cash_rows_summary: dict[str, Any] | None,
    actual_cash_report_gate: dict[str, Any] | None,
    blockers_by_stage: dict[str, list[str]],
    known_gaps: list[str],
) -> ActualCashSummary:
    if actual_cash_rows_summary is None:
        blockers_by_stage["actual_cash"].append("ACTUAL_CASH_ROWS_MISSING")
    if actual_cash_report_gate is None:
        blockers_by_stage["actual_cash"].append("ACTUAL_CASH_REPORT_GATE_MISSING")
    rows_summary = _mapping(
        actual_cash_rows_summary.get("summary") if actual_cash_rows_summary else None
    )
    report_summary = _mapping(
        actual_cash_report_gate.get("summary") if actual_cash_report_gate else None
    )
    report_actual_cash = _bool(report_summary.get("actual_cash"), False)
    if (
        actual_cash_rows_summary is not None
        and rows_summary.get("cash_metric_basis") != "actual_cash"
    ):
        blockers_by_stage["actual_cash"].append("NON_ACTUAL_ROWS_REJECTED")
    known_gaps.extend(
        _strings(actual_cash_rows_summary.get("known_gaps") if actual_cash_rows_summary else None)
    )
    known_gaps.extend(
        _strings(actual_cash_report_gate.get("known_gaps") if actual_cash_report_gate else None)
    )
    return ActualCashSummary(
        actual_cash_rows_summary_present=actual_cash_rows_summary is not None,
        actual_cash_row_count=_int(
            actual_cash_rows_summary.get("row_count") if actual_cash_rows_summary else None,
            0,
        ),
        actual_cash_event_count=_int(
            actual_cash_rows_summary.get("event_count") if actual_cash_rows_summary else None,
            0,
        ),
        action_set=_strings(
            actual_cash_rows_summary.get("action_set") if actual_cash_rows_summary else None
        ),
        actual_cash_report_gate_present=actual_cash_report_gate is not None,
        actual_cash_gate_status=_str_or_none(
            actual_cash_report_gate.get("gate_status") if actual_cash_report_gate else None
        ),
        report_actual_cash=report_actual_cash,
        fields_missing_for_actual_cash_result_usd=_strings(
            report_summary.get("fields_missing_for_actual_cash_result_usd")
        ),
    )


def _lineage_summary(
    *,
    candidate_set: dict[str, Any] | None,
    search_ledger_rows: list[dict[str, Any]] | None,
    export_manifest: dict[str, Any] | None,
    authoring_bridge: dict[str, Any] | None,
    blockers_by_stage: dict[str, list[str]],
    known_gaps: list[str],
) -> LineageSummary:
    if candidate_set is None:
        return LineageSummary(
            lineage_status="BROKEN",
            lineage_gaps=["CANDIDATE_SET_MISSING"],
        )
    candidates = _candidate_inventory(candidate_set)
    candidate_ids = [_string(candidate.get("idea_candidate_id")) for candidate in candidates]
    candidate_ids = [candidate_id for candidate_id in candidate_ids if candidate_id]
    shortlisted_ids = [
        _string(candidate.get("idea_candidate_id"))
        for candidate in candidates
        if _string(candidate.get("decision")) == "SHORTLISTED"
        and _string(candidate.get("idea_candidate_id"))
    ]
    ledger_ids = {
        _string(row.get("candidate_id") or row.get("idea_candidate_id"))
        for row in (search_ledger_rows or [])
    }
    ledger_ids.discard("")
    exported_ids = {
        _string(row.get("idea_candidate_id") or row.get("candidate_id"))
        for row in _list(export_manifest.get("exported_ideas") if export_manifest else None)
        if isinstance(row, dict)
    }
    exported_ids.discard("")
    bridge_ids = {
        _string(row.get("candidate_id") or row.get("idea_candidate_id"))
        for row in _list(authoring_bridge.get("candidates") if authoring_bridge else None)
        if isinstance(row, dict)
    }
    bridge_ids.discard("")
    missing_from_ledger = sorted(
        candidate_id
        for candidate_id in candidate_ids
        if search_ledger_rows is None or candidate_id not in ledger_ids
    )
    missing_from_export = sorted(
        candidate_id
        for candidate_id in shortlisted_ids
        if export_manifest is None or candidate_id not in exported_ids
    )
    missing_from_bridge = sorted(
        candidate_id
        for candidate_id in exported_ids
        if authoring_bridge is None or candidate_id not in bridge_ids
    )
    gaps: list[str] = []
    if missing_from_ledger:
        gaps.append("CANDIDATE_IDS_MISSING_FROM_LEDGER")
        blockers_by_stage["lineage"].append("CANDIDATE_IDS_MISSING_FROM_LEDGER")
    if missing_from_export:
        gaps.append("SHORTLISTED_IDS_MISSING_FROM_EXPORT_MANIFEST")
        blockers_by_stage["lineage"].append("SHORTLISTED_IDS_MISSING_FROM_EXPORT_MANIFEST")
    if missing_from_bridge:
        gaps.append("EXPORTED_IDS_MISSING_FROM_BRIDGE")
        blockers_by_stage["lineage"].append("EXPORTED_IDS_MISSING_FROM_BRIDGE")
    known_gaps.extend(gaps)
    if search_ledger_rows is None or export_manifest is None or authoring_bridge is None:
        status = "PARTIAL"
    elif gaps:
        status = "BROKEN"
    else:
        status = "COMPLETE"
    return LineageSummary(
        lineage_status=status,
        candidate_id_count=len(candidate_ids),
        candidate_ids_missing_from_ledger=missing_from_ledger,
        shortlisted_ids_missing_from_export_manifest=missing_from_export,
        exported_ids_missing_from_bridge=missing_from_bridge,
        lineage_gaps=gaps,
    )


def _candidate_inventory(candidate_set: dict[str, Any] | None) -> list[dict[str, Any]]:
    if candidate_set is None:
        return []
    return [
        item for item in _list(candidate_set.get("candidate_inventory")) if isinstance(item, dict)
    ]


def _side_bias_by_candidate(candidate_set: dict[str, Any] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for candidate in _candidate_inventory(candidate_set):
        candidate_id = _string(candidate.get("idea_candidate_id"))
        side_bias = _string(_mapping(candidate.get("parameter_set")).get("side_bias"))
        if candidate_id and side_bias:
            result[candidate_id] = side_bias
    return result


def _family_counts(candidates: list[dict[str, Any]], decision: str) -> dict[str, int]:
    counts = Counter(
        _string(candidate.get("family"))
        for candidate in candidates
        if _string(candidate.get("decision")) == decision
    )
    counts.pop("", None)
    return dict(sorted(counts.items()))


def _selection_status_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        _string(candidate.get("selection_adjusted_metrics_status")) for candidate in candidates
    )
    counts.pop("", None)
    return dict(sorted(counts.items()))


def _decision_count(candidates: list[dict[str, Any]], decision: str) -> int:
    return sum(1 for candidate in candidates if _string(candidate.get("decision")) == decision)


def _dominant(counts: Counter[str], key: str) -> bool:
    if not counts or counts.get(key, 0) <= 0:
        return False
    return counts[key] == max(counts.values())


def _next_single_blocker_to_fix(blocker_counts: Counter[str]) -> str:
    for blocker in NEXT_BLOCKER_PRIORITY:
        if blocker == "NO_BLOCKER_IDENTIFIED" or blocker_counts.get(blocker, 0) > 0:
            return blocker
    return "NO_BLOCKER_IDENTIFIED"


def _top_blockers(blocker_counts: Counter[str]) -> list[str]:
    priority_rank = {blocker: index for index, blocker in enumerate(NEXT_BLOCKER_PRIORITY)}
    return [
        blocker
        for blocker, _ in sorted(
            blocker_counts.items(),
            key=lambda item: (priority_rank.get(item[0], len(priority_rank)), -item[1], item[0]),
        )[:5]
    ]


def _overall_status(blocker_counts: Counter[str]) -> OverallStatus:
    if not blocker_counts:
        return "COMPLETE"
    if any(blocker in HARD_BLOCKERS for blocker in blocker_counts):
        return "BLOCKED"
    return "PARTIAL"


def _next_action(blocker: str) -> NextAction:
    if blocker == "NO_BLOCKER_IDENTIFIED":
        return "NO_ACTION"
    if blocker in {
        "AUTHORING_BRIDGE_MISSING",
        "PROFIT_READINESS_INVENTORY_MISSING",
        "RISK_REVIEW_MISSING",
        "ACTUAL_CASH_ROWS_MISSING",
        "ACTUAL_CASH_REPORT_GATE_MISSING",
    }:
        return "RUN_EXISTING_PIPELINE"
    if blocker in {"SEARCH_LEDGER_MISSING", "ACTUAL_CASH_SOURCE_MISSING"}:
        return "COLLECT_INPUTS"
    return "FIX_BLOCKER"


def _flatten(groups: Iterable[Iterable[str]]) -> list[str]:
    return [item for group in groups for item in group if item]


def _dedupe(values: Iterable[str]) -> list[str]:
    return [value for value in dict.fromkeys(values) if value]


def _path_text(path: Path | None) -> str | None:
    return path.as_posix() if path is not None else None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [_string(item) for item in _list(value) if _string(item)]


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _str_or_none(value: Any) -> str | None:
    text = _string(value)
    return text or None


def _int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(value, 0)
    try:
        return max(int(str(value)), 0)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return default
