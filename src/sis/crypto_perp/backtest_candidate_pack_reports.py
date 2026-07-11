from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, cast

from sis.crypto_perp.backtest_candidate_pack_models import (
    BacktestCandidateDecisionName,
    CryptoPerpBacktestCandidatePackDecision,
    _EventOutcomePair,
    _PerEventArtifacts,
)
from sis.crypto_perp.backtest_candidate_pack_profit import (
    build_profit_robustness_summary,
)
from sis.crypto_perp.bias_guards import CryptoPerpBiasGuard
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.cost_model import (
    CRYPTO_PERP_PROJECT_FUNDING_RATE,
    CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
    CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
)
from sis.crypto_perp.source_availability import (
    CryptoPerpSourceAvailability,
    SourceAvailabilityStatus,
)
from sis.crypto_perp.tournament_rows import (
    CostAwareTournamentRow,
    CryptoPerpTournamentRowsV2,
)


def _score(artifact: _PerEventArtifacts) -> str:
    edge = artifact.edge_score
    first = sorted(edge.action_scores, key=lambda row: row.rank)[0] if edge.action_scores else None
    return str(first.score) if first is not None else "0"


def _outcome_execution_window(pair: _EventOutcomePair) -> tuple[datetime, int]:
    matured = [horizon for horizon in pair.outcome.horizons if horizon.matured]
    if not matured:
        raise ValueError(f"outcome has no matured horizon: {pair.outcome.outcome_id}")
    horizon = matured[0]
    return pair.outcome.settled_at - timedelta(
        minutes=horizon.horizon_minutes
    ), horizon.horizon_minutes


def build_signal_rows(
    *,
    pairs: Sequence[_EventOutcomePair],
    artifacts: Sequence[_PerEventArtifacts],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair, artifact in zip(pairs, artifacts, strict=True):
        edge = artifact.edge_score
        selected = edge.selected_action
        no_trade_reason = list(edge.why_no_trade)
        if selected == "UNKNOWN":
            no_trade_reason.append("SELECTED_ACTION_UNKNOWN")
        if selected == "NO_TRADE":
            no_trade_reason.append("NO_TRADE_SELECTED")
        entry_at, outcome_horizon_minutes = _outcome_execution_window(pair)
        rows.append(
            {
                "timestamp": serialize_utc_z(pair.event.information_cutoff_at),
                "entry_at": serialize_utc_z(entry_at),
                "outcome_horizon_minutes": outcome_horizon_minutes,
                "symbol": pair.event.canonical_symbol,
                "event_id": pair.event.event_id,
                "outcome_id": pair.outcome.outcome_id,
                "information_cutoff_at": serialize_utc_z(pair.event.information_cutoff_at),
                "source_availability_id": artifact.source_availability.artifact_id,
                "feature_pack_id": artifact.feature_pack.feature_pack_id,
                "edge_score_id": edge.edge_score_id,
                "selected_action": selected,
                "signal_score": _score(artifact),
                "entry_allowed": selected not in {"UNKNOWN", "NO_TRADE"},
                "no_trade_reason": list(dict.fromkeys(no_trade_reason)),
                "artifact_origin": {
                    "source_availability": artifact.source_origin.__dict__,
                    "feature_pack": artifact.feature_origin.__dict__,
                    "edge_score": artifact.edge_origin.__dict__,
                },
            }
        )
    return rows


def _metadata_available_at(
    status: SourceAvailabilityStatus,
    fallback: datetime,
) -> tuple[datetime | None, str]:
    raw_ms = status.metadata.get("coverage_end_ms")
    if isinstance(raw_ms, int | float) and not isinstance(raw_ms, bool):
        return datetime.fromtimestamp(raw_ms / 1000, tz=UTC), "metadata.coverage_end_ms"
    return fallback if status.available else None, "information_cutoff_fallback"


def _source_status_by_id(
    source: CryptoPerpSourceAvailability,
) -> dict[str, SourceAvailabilityStatus]:
    return {status.source_id: status for status in source.source_statuses}


def build_availability_ledger(
    *,
    pairs: Sequence[_EventOutcomePair],
    artifacts: Sequence[_PerEventArtifacts],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    critical_sources = {"event", "bars", "ticker", "funding"}
    signal_sources = {"event", "bars", "ticker", "funding", "trades", "books", "replay"}
    future_signal_source_count = 0
    critical_missing_count = 0
    for pair, artifact in zip(pairs, artifacts, strict=True):
        cutoff = pair.event.information_cutoff_at
        statuses = _source_status_by_id(artifact.source_availability)
        for source_type, status in sorted(statuses.items()):
            usage_role = "evaluation_label" if source_type == "outcome" else "signal_input"
            if source_type == "outcome":
                is_available = True
                available_at = pair.outcome.settled_at
                used_at = pair.outcome.settled_at
                missing_reason = None
                row_count = 1
                available_at_policy = "outcome.settled_at"
            else:
                is_available = status.available
                available_at, available_at_policy = _metadata_available_at(status, cutoff)
                used_at = cutoff
                missing_reason = None if is_available else status.reason
                row_count = status.row_count
            if source_type in critical_sources and not is_available:
                critical_missing_count += 1
            future_signal_source = (
                source_type in signal_sources
                and is_available
                and available_at is not None
                and available_at > cutoff
            )
            future_signal_source_count += int(future_signal_source)
            staleness_seconds = (
                int((used_at - available_at).total_seconds())
                if available_at is not None and used_at >= available_at
                else None
            )
            rows.append(
                {
                    "timestamp": serialize_utc_z(cutoff),
                    "symbol": pair.event.canonical_symbol,
                    "event_id": pair.event.event_id,
                    "source_type": source_type,
                    "source_artifact_id": artifact.source_availability.artifact_id,
                    "available_at": serialize_utc_z(available_at) if available_at else None,
                    "used_at": serialize_utc_z(used_at),
                    "usage_role": usage_role,
                    "is_available": is_available,
                    "missing_reason": missing_reason,
                    "staleness_seconds": staleness_seconds,
                    "row_count": row_count,
                    "source_ref_count": len(status.source_refs),
                    "available_at_policy": available_at_policy,
                    "metadata": _json_ready(status.metadata),
                }
            )
    return {
        "schema_version": "crypto_perp_backtest_data_availability_ledger.v1",
        "summary": {
            "event_count": len(pairs),
            "row_count": len(rows),
            "critical_missing_count": critical_missing_count,
            "future_signal_source_count": future_signal_source_count,
            "network_used": False,
            "external_api_called": False,
        },
        "rows": rows,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def build_execution_assumptions(
    *,
    notional_usd: Decimal,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    max_holding_minutes: int,
) -> dict[str, Any]:
    return {
        "schema_version": "crypto_perp_backtest_execution_assumptions.v1",
        "entry_price_rule": "next_5m_open_proxy_after_signal",
        "exit_price_rule": "matured_outcome_first_horizon_close_proxy",
        "fee_rate": str(fee_rate),
        "slippage_bps": str(slippage_bps),
        "funding_rate_assumption": str(funding_rate),
        "max_holding_minutes": max_holding_minutes,
        "position_size_usd": str(notional_usd),
        "no_fill_policy": "UNKNOWN blocks entry; NO_TRADE records zero exposure baseline",
        "zero_cost_forbidden": True,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _check_row(
    check_id: str, status: str, message: str, event_id: str | None = None
) -> dict[str, Any]:
    return {"check_id": check_id, "status": status, "message": message, "event_id": event_id}


def build_no_lookahead_report(
    *,
    pairs: Sequence[_EventOutcomePair],
    artifacts: Sequence[_PerEventArtifacts],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    ledger_rows = cast(list[dict[str, Any]], ledger.get("rows", []))
    for pair, artifact in zip(pairs, artifacts, strict=True):
        cutoff = pair.event.information_cutoff_at
        entry_at, _ = _outcome_execution_window(pair)
        checks.append(
            _check_row(
                "signal_timestamp_before_entry_timestamp",
                "pass" if cutoff < entry_at else "fail",
                "signal timestamp must be before simulated entry timestamp",
                pair.event.event_id,
            )
        )
        checks.append(
            _check_row(
                "feature_used_at_not_after_signal",
                "pass" if artifact.feature_pack.information_cutoff_at <= cutoff else "fail",
                "feature pack cutoff must not be after signal timestamp",
                pair.event.event_id,
            )
        )
        checks.append(
            _check_row(
                "outcome_not_used_for_signal",
                "pass",
                "outcome is only used for backtest evaluation after signal generation",
                pair.event.event_id,
            )
        )
    for row in ledger_rows:
        if row.get("usage_role") != "signal_input" or not row.get("is_available"):
            continue
        available_at = ensure_utc_aware("available_at", row["available_at"])
        used_at = ensure_utc_aware("used_at", row["used_at"])
        checks.append(
            _check_row(
                "source_available_at_not_after_used_at",
                "pass" if available_at <= used_at else "fail",
                f"{row['source_type']} available_at must be <= used_at",
                cast(str, row.get("event_id")),
            )
        )
    critical_missing = int(cast(Mapping[str, Any], ledger["summary"])["critical_missing_count"])
    if critical_missing:
        checks.append(
            _check_row(
                "critical_signal_sources_available",
                "unverified",
                "one or more critical signal sources are missing; backtest must collect more data",
            )
        )
    checks.append(
        _check_row(
            "train_test_split_time_ordered",
            "pass",
            "no train/test optimization is performed in this deterministic candidate pack",
        )
    )
    checks.append(
        _check_row(
            "recursive_feature_warmup_absent",
            "pass",
            "features and edge scores are rebuilt independently per event by the current non-recursive pipeline",
        )
    )
    counts = Counter(str(check["status"]) for check in checks)
    status = "fail" if counts.get("fail", 0) else "pass"
    return {
        "schema_version": "crypto_perp_backtest_no_lookahead_report.v1",
        "status": status,
        "summary": {
            "check_count": len(checks),
            "failed_count": counts.get("fail", 0),
            "unverified_count": counts.get("unverified", 0),
            "coverage_status": "unverified" if counts.get("unverified", 0) else "covered",
            "outcome_used_for_signal": False,
        },
        "checks": checks,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _row_by_event_action(
    rows: CryptoPerpTournamentRowsV2 | None,
) -> dict[tuple[str, str], CostAwareTournamentRow]:
    if rows is None:
        return {}
    return {(row.event_id, row.action): row for row in rows.rows}


def _drawdown(values: Sequence[Decimal]) -> Decimal:
    peak = Decimal("0")
    cumulative = Decimal("0")
    worst = Decimal("0")
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        worst = min(worst, cumulative - peak)
    return worst


def _simulation_results(
    *,
    signal_rows: Sequence[Mapping[str, Any]],
    rows: CryptoPerpTournamentRowsV2 | None,
    metric: Literal["cost_adjusted_cash_estimate_usd", "stress_cash_estimate_usd"],
    holding_minutes: int,
    notional_usd: Decimal,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    row_map = _row_by_event_action(rows)
    results: list[dict[str, Any]] = []
    returns: list[Decimal] = []
    for signal in signal_rows:
        event_id = str(signal["event_id"])
        selected = str(signal["selected_action"])
        source_row = row_map.get((event_id, selected))
        if selected == "UNKNOWN":
            result = Decimal("0")
            fill_status = "blocked_unknown_signal"
        elif selected == "NO_TRADE":
            result = Decimal("0")
            fill_status = "no_trade_baseline"
        elif source_row is None:
            result = Decimal("0")
            fill_status = "blocked_missing_action_row"
        else:
            result = getattr(source_row, metric)
            fill_status = "simulated"
        returns.append(result)
        results.append(
            {
                "event_id": event_id,
                "outcome_id": signal["outcome_id"],
                "selected_action": selected,
                "fill_status": fill_status,
                "result_usd": str(result),
                "metric": metric,
            }
        )
    executed = [row for row in results if row["fill_status"] == "simulated"]
    total = sum(returns, Decimal("0"))
    wins = sum(1 for row in executed if Decimal(str(row["result_usd"])) > 0)
    summary = {
        "event_count": len(signal_rows),
        "executed_trade_count": len(executed),
        "no_trade_count": sum(1 for row in results if row["fill_status"] == "no_trade_baseline"),
        "unknown_count": sum(
            1 for row in results if row["fill_status"] == "blocked_unknown_signal"
        ),
        "blocked_missing_action_row_count": sum(
            1 for row in results if row["fill_status"] == "blocked_missing_action_row"
        ),
        "total_result_usd": str(total),
        "average_result_usd": str(total / Decimal(len(results))) if results else "0",
        "win_rate": str(Decimal(wins) / Decimal(len(executed))) if executed else None,
        "max_drawdown_usd": str(_drawdown(returns)),
        "beats_no_trade": total > 0,
        "profit_robustness": build_profit_robustness_summary(
            signal_rows=signal_rows,
            results=results,
            holding_minutes=holding_minutes,
            notional_usd=notional_usd,
            tournament_rows=rows,
            metric=metric,
        ),
    }
    return results, summary


def build_backtest_result(
    signal_rows: Sequence[Mapping[str, Any]],
    rows: CryptoPerpTournamentRowsV2 | None,
    *,
    holding_minutes: int = 60,
    notional_usd: Decimal = Decimal("100"),
) -> dict[str, Any]:
    results, summary = _simulation_results(
        signal_rows=signal_rows,
        rows=rows,
        metric="cost_adjusted_cash_estimate_usd",
        holding_minutes=holding_minutes,
        notional_usd=notional_usd,
    )
    return {
        "schema_version": "crypto_perp_backtest_result.v1",
        "status": "complete",
        "summary": summary,
        "results": results,
        "paper_only": True,
        "profit_proven": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def build_stress_result(
    signal_rows: Sequence[Mapping[str, Any]],
    rows: CryptoPerpTournamentRowsV2 | None,
    *,
    holding_minutes: int = 60,
    notional_usd: Decimal = Decimal("100"),
) -> dict[str, Any]:
    results, summary = _simulation_results(
        signal_rows=signal_rows,
        rows=rows,
        metric="stress_cash_estimate_usd",
        holding_minutes=holding_minutes,
        notional_usd=notional_usd,
    )
    return {
        "schema_version": "crypto_perp_backtest_stress_result.v1",
        "status": "complete",
        "stress_kind": "row_level_conservative_cost_slippage",
        "summary": summary,
        "results": results,
        "paper_only": True,
        "profit_proven": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def build_regime_split_result(
    *,
    pairs: Sequence[_EventOutcomePair],
    backtest_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    families = {pair.event.event_id: pair.event.event_family for pair in pairs}
    buckets: dict[str, list[Decimal]] = {}
    for result in backtest_results:
        family = families.get(str(result["event_id"]), "unknown")
        buckets.setdefault(family, []).append(Decimal(str(result["result_usd"])))
    regimes = [
        {
            "regime": regime,
            "event_count": len(values),
            "total_result_usd": str(sum(values, Decimal("0"))),
            "average_result_usd": str(sum(values, Decimal("0")) / Decimal(len(values)))
            if values
            else "0",
        }
        for regime, values in sorted(buckets.items())
    ]
    return {
        "schema_version": "crypto_perp_backtest_regime_split_result.v1",
        "status": "complete" if regimes else "sample_insufficient",
        "summary": {"regime_count": len(regimes), "event_count": len(pairs)},
        "regimes": regimes,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def build_rolling_stability_result(
    backtest_results: Sequence[Mapping[str, Any]],
    min_events_for_stability: int,
) -> dict[str, Any]:
    cumulative = Decimal("0")
    points: list[dict[str, Any]] = []
    for index, result in enumerate(backtest_results, start=1):
        cumulative += Decimal(str(result["result_usd"]))
        points.append(
            {
                "index": index,
                "event_id": result["event_id"],
                "cumulative_result_usd": str(cumulative),
            }
        )
    status = (
        "complete" if len(backtest_results) >= min_events_for_stability else "sample_insufficient"
    )
    return {
        "schema_version": "crypto_perp_backtest_rolling_stability_result.v1",
        "status": status,
        "summary": {
            "event_count": len(backtest_results),
            "min_events_for_stability": min_events_for_stability,
            "final_cumulative_result_usd": str(cumulative),
            "min_cumulative_result_usd": min(
                (Decimal(str(point["cumulative_result_usd"])) for point in points),
                default=Decimal("0"),
            ),
            "max_cumulative_result_usd": max(
                (Decimal(str(point["cumulative_result_usd"])) for point in points),
                default=Decimal("0"),
            ),
        },
        "points": points,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def non_goal_flags() -> dict[str, bool]:
    return {
        "actual_cash_used": False,
        "profit_proven": False,
        "actual_cash_readiness_claimed": False,
        "tiny_live_readiness_claimed": False,
        "live_trading_readiness_claimed": False,
        "wallet_or_signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "backtest_promote_to_live_available": False,
        "ml_or_llm_trade_decision_used": False,
    }


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def decide_backtest_candidate(
    *,
    event_count: int,
    outcome_count: int,
    min_events: int,
    ledger: Mapping[str, Any],
    no_lookahead: Mapping[str, Any],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    rolling: Mapping[str, Any],
    guard: CryptoPerpBiasGuard | None,
    fixture_only: bool = False,
    event_source_provenance_verified: bool = True,
) -> tuple[BacktestCandidateDecisionName, list[str]]:
    reasons: list[str] = []
    if event_count == 0 or outcome_count == 0:
        return "BACKTEST_COLLECT_MORE_DATA", ["NO_EVENT_OUTCOME_PAIRS"]
    if event_count < min_events or outcome_count < min_events:
        reasons.append("MIN_EVENT_OUTCOME_SAMPLE_NOT_MET")
    if fixture_only:
        reasons.append("DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE")
    if not event_source_provenance_verified:
        reasons.append("EVENT_SOURCE_PROVENANCE_NOT_VERIFIABLE")
    if int(cast(Mapping[str, Any], ledger["summary"])["critical_missing_count"]) > 0:
        reasons.append("CRITICAL_SIGNAL_SOURCE_MISSING")
    nl_summary = cast(Mapping[str, Any], no_lookahead["summary"])
    if int(nl_summary["failed_count"]) > 0:
        reasons.append("NO_LOOKAHEAD_FAILED")
        return "BACKTEST_REJECT", _unique(reasons)
    if int(nl_summary["unverified_count"]) > 0:
        reasons.append("NO_LOOKAHEAD_UNVERIFIED")
    bt_summary = cast(Mapping[str, Any], backtest["summary"])
    stress_summary = cast(Mapping[str, Any], stress["summary"])
    if int(bt_summary["unknown_count"]) > 0 and "CRITICAL_SIGNAL_SOURCE_MISSING" in reasons:
        reasons.append("SELECTED_ACTION_UNKNOWN_DUE_TO_MISSING_SOURCE")
    elif int(bt_summary["unknown_count"]) > 0:
        reasons.append("SELECTED_ACTION_UNKNOWN")
    if guard is None:
        reasons.append("BIAS_GUARD_MISSING_OR_NOT_ESTIMABLE")
    elif guard.guard_status == "BLOCKED":
        reasons.extend(["BIAS_GUARD_BLOCKED", *guard.stop_reasons])
    elif guard.guard_status != "PASS":
        reasons.append("BIAS_GUARD_MISSING_OR_NOT_ESTIMABLE")
    elif guard.pbo_status == "NOT_ESTIMABLE":
        reasons.append("BIAS_GUARD_MISSING_OR_NOT_ESTIMABLE")
    elif guard.pbo_status != "COMPUTED_PASS":
        reasons.append("PBO_NOT_COMPUTED")
    rolling_status = rolling.get("status")
    if rolling_status == "sample_insufficient":
        reasons.append("ROLLING_STABILITY_SAMPLE_INSUFFICIENT")
    elif rolling_status != "complete":
        reasons.append("ROLLING_STABILITY_STATUS_UNKNOWN")
    if int(bt_summary["executed_trade_count"]) == 0 or int(bt_summary["unknown_count"]) > 0:
        reasons.append("NO_EXECUTABLE_SIGNAL_ROWS")
    if int(bt_summary.get("blocked_missing_action_row_count", 0)) > 0:
        reasons.append("ACTION_ROWS_MISSING")
    robustness = cast(Mapping[str, Any], bt_summary.get("profit_robustness", {}))
    if int(robustness.get("peak_concurrent_positions", 0)) > 1 and not bool(
        robustness.get("position_overlap_accounted")
    ):
        reasons.append("POSITION_OVERLAP_NOT_ACCOUNTED")
    if (
        "market_episode_count" in robustness
        and int(robustness["market_episode_count"]) < min_events
    ):
        reasons.append("INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET")
    if robustness.get("selector_beats_best_static_action") is False:
        reasons.append("SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION")
    collection_reasons = {
        "MIN_EVENT_OUTCOME_SAMPLE_NOT_MET",
        "CRITICAL_SIGNAL_SOURCE_MISSING",
        "NO_LOOKAHEAD_UNVERIFIED",
        "SELECTED_ACTION_UNKNOWN_DUE_TO_MISSING_SOURCE",
        "BIAS_GUARD_MISSING_OR_NOT_ESTIMABLE",
        "PBO_NOT_COMPUTED",
        "ROLLING_STABILITY_SAMPLE_INSUFFICIENT",
        "ROLLING_STABILITY_STATUS_UNKNOWN",
        "INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET",
        "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE",
        "EVENT_SOURCE_PROVENANCE_NOT_VERIFIABLE",
    }
    revision_reasons = {
        "NO_EXECUTABLE_SIGNAL_ROWS",
        "ACTION_ROWS_MISSING",
        "POSITION_OVERLAP_NOT_ACCOUNTED",
        "SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION",
    }
    if "BIAS_GUARD_BLOCKED" in reasons:
        return "BACKTEST_REJECT", _unique(reasons)
    if collection_reasons.intersection(reasons):
        return "BACKTEST_COLLECT_MORE_DATA", _unique(reasons)
    if revision_reasons.intersection(reasons):
        return "BACKTEST_REVISE", _unique(reasons)
    total = Decimal(str(bt_summary["total_result_usd"]))
    stress_total = Decimal(str(stress_summary["total_result_usd"]))
    if total <= 0:
        reasons.append("NO_TRADE_NOT_BEATEN_AFTER_COST")
    if stress_total <= 0:
        reasons.append("STRESS_RESULT_NOT_POSITIVE")
    if Decimal(str(bt_summary["max_drawdown_usd"])) < total * Decimal("-1"):
        reasons.append("DRAWDOWN_TOO_LARGE_FOR_TOTAL_RESULT")
    if reasons:
        return "BACKTEST_REJECT", _unique(reasons)
    reasons.append("SIMULATION_CANDIDATE_REMAINS_AFTER_LOCAL_BACKTEST")
    reasons.append("ACTUAL_CASH_PAPER_TINY_LIVE_NOT_IN_SCOPE")
    return "BACKTEST_CANDIDATE_HOLD", reasons


def decision_markdown(artifact: CryptoPerpBacktestCandidatePackDecision) -> str:
    strongest_evidence_level = (
        artifact.evidence_grade_summary.strongest_evidence_level
        if artifact.evidence_grade_summary is not None
        else "unknown"
    )
    return "\n".join(
        [
            "# Crypto Perp Backtest Candidate Pack Decision",
            "",
            f"- created_at: `{serialize_utc_z(artifact.created_at)}`",
            f"- pack_id: `{artifact.pack_id}`",
            f"- event_count: `{artifact.event_count}`",
            f"- outcome_count: `{artifact.outcome_count}`",
            f"- decision: `{artifact.decision}`",
            f"- reason_codes: `{', '.join(artifact.reason_codes)}`",
            f"- strongest_evidence_level: `{strongest_evidence_level}`",
            "- actual_cash_used: `false`",
            "- profit_proven: `false`",
            "- permits_live_order: `false`",
            "- live_trading_readiness_claimed: `false`",
            "",
            "This pack is timestamp-safe simulation evidence only. It does not prove profit, actual-cash readiness, tiny-live readiness, or live trading readiness.",
        ]
    )


def validate_backtest_assumptions(
    *,
    notional_usd: Decimal,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    min_events: int,
    min_events_for_stability: int,
    fold_count: int,
    max_holding_minutes: int,
) -> None:
    if notional_usd <= 0:
        raise ValueError("notional_usd must be positive")
    if fee_rate <= 0:
        raise ValueError("fee_rate must be positive; zero-cost backtest is forbidden")
    if fee_rate < CRYPTO_PERP_PROJECT_TAKER_FEE_RATE:
        raise ValueError("fee_rate must not be below the project cost floor")
    if funding_rate < 0:
        raise ValueError("funding_rate must be non-negative")
    if funding_rate < CRYPTO_PERP_PROJECT_FUNDING_RATE:
        raise ValueError("funding_rate must not be below the project cost floor")
    if slippage_bps <= 0:
        raise ValueError("slippage_bps must be positive; zero-cost backtest is forbidden")
    if slippage_bps < CRYPTO_PERP_PROJECT_SLIPPAGE_BPS:
        raise ValueError("slippage_bps must not be below the project cost floor")
    if min_events <= 0:
        raise ValueError("min_events must be positive")
    if min_events_for_stability <= 0:
        raise ValueError("min_events_for_stability must be positive")
    if fold_count < 0:
        raise ValueError("fold_count must be non-negative")
    if max_holding_minutes <= 0:
        raise ValueError("max_holding_minutes must be positive")


def _json_ready(value: Any) -> Any:
    import json

    return json.loads(json.dumps(value, ensure_ascii=False, default=str))
