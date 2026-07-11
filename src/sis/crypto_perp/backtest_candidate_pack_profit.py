from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.tournament_rows import CryptoPerpTournamentRowsV2


def _execution_windows(
    rows: CryptoPerpTournamentRowsV2 | None,
    event_ids: Sequence[str],
    configured_holding_minutes: int,
) -> dict[str, tuple[datetime, datetime, int]]:
    if rows is None:
        if event_ids:
            raise ValueError("tournament rows with actual execution windows are required")
        return {}
    raw = rows.summary.get("execution_windows")
    if not isinstance(raw, Mapping):
        raise ValueError("tournament rows missing actual execution_windows")
    artifact_event_ids = sorted(set(rows.event_set))
    if not artifact_event_ids:
        if event_ids:
            raise ValueError("tournament rows event_set is empty")
        return {}
    parsed: dict[str, tuple[datetime, datetime, int]] = {}
    for event_id in artifact_event_ids:
        window = raw.get(event_id)
        if not isinstance(window, Mapping):
            raise ValueError(f"tournament rows missing execution window for {event_id}")
        horizon = window.get("horizon_minutes")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
            raise ValueError(f"invalid actual outcome horizon for {event_id}")
        raw_entry_at = window.get("entry_at")
        raw_settled_at = window.get("settled_at")
        if not isinstance(raw_entry_at, (datetime, str)) or not isinstance(
            raw_settled_at, (datetime, str)
        ):
            raise ValueError(f"invalid execution window timestamps for {event_id}")
        entry_at = ensure_utc_aware("entry_at", raw_entry_at)
        settled_at = ensure_utc_aware("settled_at", raw_settled_at)
        if entry_at >= settled_at:
            raise ValueError(f"invalid execution window ordering for {event_id}")
        if settled_at - entry_at != timedelta(minutes=horizon):
            raise ValueError(f"execution window duration does not match horizon for {event_id}")
        if horizon != configured_holding_minutes:
            raise ValueError(
                f"max_holding_minutes={configured_holding_minutes} does not match "
                f"actual outcome horizon={horizon} for {event_id}"
            )
        parsed[event_id] = (entry_at, settled_at, horizon)
    missing = sorted(set(event_ids).difference(parsed))
    if missing:
        raise ValueError("tournament rows missing execution windows for: " + ",".join(missing))
    return {event_id: parsed[event_id] for event_id in event_ids}


def build_profit_robustness_summary(
    *,
    signal_rows: Sequence[Mapping[str, Any]],
    results: Sequence[Mapping[str, Any]],
    holding_minutes: int,
    notional_usd: Decimal,
    tournament_rows: CryptoPerpTournamentRowsV2 | None = None,
    metric: Literal[
        "cost_adjusted_cash_estimate_usd", "stress_cash_estimate_usd"
    ] = "cost_adjusted_cash_estimate_usd",
) -> dict[str, Any]:
    executed = [row for row in results if row.get("fill_status") == "simulated"]
    event_ids = [str(row["event_id"]) for row in executed]
    windows = _execution_windows(tournament_rows, event_ids, holding_minutes)
    ordered: list[tuple[datetime, datetime, Mapping[str, Any]]] = [
        (windows[event_id][0], windows[event_id][1], row)
        for event_id, row in zip(event_ids, executed, strict=True)
    ]
    ordered.sort(key=lambda item: (item[0], str(item[2]["event_id"])))

    active_ends: list[datetime] = []
    peak_concurrent = 0
    for entry_at, settled_at, _ in ordered:
        active_ends = [end for end in active_ends if end > entry_at]
        active_ends.append(settled_at)
        peak_concurrent = max(peak_concurrent, len(active_ends))

    clusters: list[list[Mapping[str, Any]]] = []
    cluster_end: datetime | None = None
    for entry_at, settled_at, row in ordered:
        if cluster_end is None or entry_at >= cluster_end:
            clusters.append([row])
            cluster_end = settled_at
        else:
            clusters[-1].append(row)
            cluster_end = max(cluster_end, settled_at)

    next_available: datetime | None = None
    non_overlapping: list[Mapping[str, Any]] = []
    for entry_at, settled_at, row in ordered:
        if next_available is not None and entry_at < next_available:
            continue
        non_overlapping.append(row)
        next_available = settled_at

    values = [Decimal(str(row["result_usd"])) for row in executed]
    positives = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    action_values: dict[str, list[Decimal]] = {}
    for row in executed:
        action_values.setdefault(str(row["selected_action"]), []).append(
            Decimal(str(row["result_usd"]))
        )
    gross_profit = sum(positives, Decimal("0"))
    gross_loss = sum(losses, Decimal("0"))
    total = sum(values, Decimal("0"))
    cluster_totals = [
        sum((Decimal(str(row["result_usd"])) for row in cluster), Decimal("0"))
        for cluster in clusters
    ]
    static_action_totals: dict[str, Decimal] = {}
    if tournament_rows is not None:
        for row in tournament_rows.rows:
            static_action_totals[row.action] = static_action_totals.get(
                row.action, Decimal("0")
            ) + Decimal(str(getattr(row, metric)))
    best_static_action = (
        max(static_action_totals, key=static_action_totals.__getitem__)
        if static_action_totals
        else None
    )
    score_pairs: list[tuple[Decimal, Decimal]] = []
    result_by_event = {str(row["event_id"]): row for row in executed}
    for signal in signal_rows:
        result = result_by_event.get(str(signal["event_id"]))
        if result is None or signal.get("signal_score") is None:
            continue
        score_pairs.append(
            (Decimal(str(signal["signal_score"])), Decimal(str(result["result_usd"])))
        )
    score_correlation: Decimal | None = None
    if len(score_pairs) >= 2:
        mean_score = sum((pair[0] for pair in score_pairs), Decimal("0")) / len(score_pairs)
        mean_result = sum((pair[1] for pair in score_pairs), Decimal("0")) / len(score_pairs)
        covariance = sum(
            ((score - mean_score) * (result - mean_result) for score, result in score_pairs),
            Decimal("0"),
        )
        score_variance = sum(((score - mean_score) ** 2 for score, _ in score_pairs), Decimal("0"))
        result_variance = sum(
            ((result - mean_result) ** 2 for _, result in score_pairs), Decimal("0")
        )
        if score_variance > 0 and result_variance > 0:
            score_correlation = covariance / (score_variance * result_variance).sqrt()
    return {
        "holding_minutes": holding_minutes,
        "holding_minutes_source": "tournament_rows.summary.execution_windows",
        "execution_windows_verified": True,
        "peak_concurrent_positions": peak_concurrent,
        "peak_gross_notional_usd": str(notional_usd * peak_concurrent),
        "market_episode_count": len(clusters),
        "market_episode_win_count": sum(value > 0 for value in cluster_totals),
        "market_episode_totals_usd": [str(value) for value in cluster_totals],
        "non_overlapping_trade_count": len(non_overlapping),
        "single_position_total_result_usd": str(
            sum((Decimal(str(row["result_usd"])) for row in non_overlapping), Decimal("0"))
        ),
        "position_overlap_accounted": peak_concurrent <= 1,
        "gross_profit_usd": str(gross_profit),
        "gross_loss_usd": str(gross_loss),
        "profit_factor": str(gross_profit / abs(gross_loss)) if gross_loss < 0 else None,
        "top_3_win_share_of_gross_profit": (
            str(sum(sorted(positives, reverse=True)[:3], Decimal("0")) / gross_profit)
            if gross_profit > 0
            else None
        ),
        "break_even_extra_cost_per_trade_usd": str(total / len(values)) if values else None,
        "signal_score_result_correlation": (
            str(score_correlation) if score_correlation is not None else None
        ),
        "static_action_totals_usd": {
            action: str(value) for action, value in sorted(static_action_totals.items())
        },
        "best_static_action": best_static_action,
        "best_static_total_result_usd": (
            str(static_action_totals[best_static_action]) if best_static_action else None
        ),
        "selector_beats_best_static_action": (
            total > static_action_totals[best_static_action] if best_static_action else None
        ),
        "action_performance": {
            action: {
                "trade_count": len(action_results),
                "win_count": sum(value > 0 for value in action_results),
                "loss_count": sum(value < 0 for value in action_results),
                "total_result_usd": str(sum(action_results, Decimal("0"))),
            }
            for action, action_results in sorted(action_values.items())
        },
    }
