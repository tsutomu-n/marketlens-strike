from __future__ import annotations

from typing import Any

from sis.reports import phase_gate_review_markdown_values

_as_dict_list = phase_gate_review_markdown_values.as_dict_list


def diagnostics_table_lines(diagnostics: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| symbol | available | rows | tradable_rate | stale_rate | l2_only_rate | fee_mode_unknown_rate | missing_mark_price_rate | missing_index_price_rate | spread_p90_bps |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in diagnostics:
        items = _as_dict_list(item.get("items"))
        diagnostic = items[0] if items else {}
        lines.append(
            "| {symbol} | {available} | {rows} | {tradable_rate} | {stale_rate} | {l2_only} | {fee_unknown} | {missing_mark} | {missing_index} | {spread_p90} |".format(
                symbol=item.get("symbol", ""),
                available=item.get("available", ""),
                rows=diagnostic.get("rows", ""),
                tradable_rate=diagnostic.get("tradable_rate", ""),
                stale_rate=diagnostic.get("stale_rate", ""),
                l2_only=diagnostic.get("l2_only_rate", ""),
                fee_unknown=diagnostic.get("fee_mode_unknown_rate", ""),
                missing_mark=diagnostic.get("missing_mark_price_rate", ""),
                missing_index=diagnostic.get("missing_index_price_rate", ""),
                spread_p90=diagnostic.get("spread_p90_bps", ""),
            )
        )
    return lines


def venue_decision_lines(venue_decisions: list[dict[str, Any]]) -> list[str]:
    if not venue_decisions:
        return ["- venue_decisions: unavailable"]

    lines = [
        "| venue | decision | main_blocker |",
        "| --- | --- | --- |",
    ]
    for item in venue_decisions:
        lines.append(
            f"| {item.get('venue', '')} | {item.get('decision', '')} | {item.get('main_blocker', '') or ''} |"
        )
    return lines


def execution_drift_classification_lines(classifications: list[dict[str, Any]]) -> list[str]:
    if not classifications:
        return ["- execution_drift_classifications: none"]

    lines = [
        "| signal | observed | expected | classification | reason | root_source | derived_from | recommended_next_action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in classifications:
        lines.append(
            "| {signal} | {observed} | {expected} | {classification} | {reason} | {root_source} | {derived_from} | {recommended_next_action} |".format(
                signal=item.get("signal", ""),
                observed=item.get("observed", ""),
                expected=item.get("expected", ""),
                classification=item.get("classification", ""),
                reason=str(item.get("reason", "")).replace("|", "/"),
                root_source=str(item.get("root_source", "")).replace("|", "/"),
                derived_from=str(item.get("derived_from", "")).replace("|", "/"),
                recommended_next_action=str(item.get("recommended_next_action", "")).replace(
                    "|", "/"
                ),
            )
        )
    return lines
