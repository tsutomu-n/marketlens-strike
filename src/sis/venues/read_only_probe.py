from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from sis.venues.capabilities import VENUE_CAPABILITY_CATALOG
from sis.venues.capabilities import VenueCapability
from sis.venues.ids import VENUE_IDS
from sis.venues.suitability import VENUE_SUITABILITY_CATALOG

SCHEMA_VERSION = "venue_read_only_probe_summary.v1"
PROBE_MODE = "fixture_only"

SAFETY_FLAGS: dict[str, bool] = {
    "external_api_used": False,
    "credentials_used": False,
    "wallet_used": False,
    "signing_used": False,
    "exchange_write_used": False,
    "live_order_submitted": False,
    "network_attempted": False,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    return f"venue-probe-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:12]}"


def _assert_catalogs_match() -> None:
    capability_keys = set(VENUE_CAPABILITY_CATALOG)
    suitability_keys = set(VENUE_SUITABILITY_CATALOG)
    if capability_keys != suitability_keys:
        missing_from_capability = sorted(suitability_keys - capability_keys)
        missing_from_suitability = sorted(capability_keys - suitability_keys)
        raise ValueError(
            "venue catalog mismatch: "
            f"missing_from_capability={missing_from_capability}, "
            f"missing_from_suitability={missing_from_suitability}"
        )


def _credential_status(capability: VenueCapability) -> str:
    return "not_checked" if capability.requires_credentials else "not_required"


def _probe_status(capability: VenueCapability) -> str:
    if not capability.schema_enabled:
        return "blocked_by_capability"
    return "local_capability_only"


def _not_attempted_reasons(venue_id: str, capability: VenueCapability) -> list[str]:
    reasons = [
        "fixture_only_no_network_attempted",
        "no_credentials_checked",
        "no_wallet_or_signing_attempted",
        "no_exchange_write_attempted",
    ]
    if venue_id == "bitget_demo":
        reasons.append("demo_only_production_bitget_not_attempted")
    if venue_id == "hyperliquid_perp":
        reasons.append("direct_hyperliquid_not_trade_xyz_proxy")
    if not capability.schema_enabled:
        reasons.append("schema_disabled_future_venue")
    if not capability.read_only_network_enabled:
        reasons.append("read_only_network_disabled")
    if not capability.live_execution_enabled:
        reasons.append("live_execution_disabled")
    return reasons


def _notes(venue_id: str, capability: VenueCapability) -> list[str]:
    if venue_id == "trade_xyz":
        return [
            "trade_xyz_proxy_surface",
            "not_direct_hyperliquid",
            "public_operator_live_command_absent",
        ]
    if venue_id == "bitget_demo":
        return [
            "demo_only_not_production_bitget",
            "local_env_presence_is_not_network_probe",
        ]
    if venue_id == "bitget_futures":
        return [
            "future_bitget_futures_venue",
            "schema_disabled_catalog_only",
        ]
    if venue_id == "hyperliquid_perp":
        return [
            "future_direct_hyperliquid_perp_venue",
            "not_trade_xyz_proxy",
        ]
    return ["unknown_catalog_row"]


def _next_action(venue_id: str, capability: VenueCapability) -> str:
    if venue_id in {"bitget_futures", "hyperliquid_perp"}:
        return "write_separate_plan_for_credentialed_network_probe_before_any_enablement"
    if venue_id == "bitget_demo":
        return "keep_demo_boundary_and_do_not_treat_as_production_bitget"
    if capability.live_execution_enabled:
        return "review_live_boundary"
    return "keep_current_boundary"


def _build_row(venue_id: str) -> dict[str, object]:
    capability = VENUE_CAPABILITY_CATALOG[venue_id]
    suitability = VENUE_SUITABILITY_CATALOG[venue_id]
    current_venue_id_enabled = venue_id in VENUE_IDS
    paper_candidate_enabled = (
        capability.paper_candidate_enabled and suitability.paper_candidate_allowed
    )
    paper_intent_enabled = capability.paper_intent_enabled and suitability.paper_intent_allowed
    paper_execution_enabled = capability.paper_execution_enabled
    paper_enabled = paper_candidate_enabled and paper_intent_enabled and paper_execution_enabled

    return {
        "venue_id": venue_id,
        "venue_family": capability.venue_family,
        "asset_universe": capability.asset_universe,
        "known_in_capability_catalog": True,
        "known_in_suitability_catalog": True,
        "current_venue_id_enabled": current_venue_id_enabled,
        "schema_enabled": capability.schema_enabled,
        "strategy_lab_enabled": capability.strategy_lab_signal_enabled,
        "evaluation_plan_enabled": capability.strategy_lab_evaluation_plan_enabled,
        "paper_enabled": paper_enabled,
        "paper_candidate_enabled": paper_candidate_enabled,
        "paper_intent_enabled": paper_intent_enabled,
        "read_only_network_enabled": capability.read_only_network_enabled,
        "credentialed_read_only_enabled": capability.credentialed_read_only_enabled,
        "paper_execution_enabled": paper_execution_enabled,
        "live_enabled": capability.live_execution_enabled,
        **SAFETY_FLAGS,
        "read_only_probe_status": _probe_status(capability),
        "read_only_probe_mode": PROBE_MODE,
        "credential_status": _credential_status(capability),
        "not_attempted_reasons": _not_attempted_reasons(venue_id, capability),
        "block_reasons": list(capability.block_reasons) + list(suitability.reason_codes),
        "notes": _notes(venue_id, capability),
        "next_action": _next_action(venue_id, capability),
    }


def build_venue_read_only_probe_summary(
    *,
    generated_at: str | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    _assert_catalogs_match()
    rows = [_build_row(venue_id) for venue_id in sorted(VENUE_CAPABILITY_CATALOG)]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id or _new_run_id(),
        "generated_at": generated_at or _now_iso(),
        "status": PROBE_MODE,
        **SAFETY_FLAGS,
        "venue_count": len(rows),
        "venues": rows,
    }


def build_venue_read_only_probe_report(summary: Mapping[str, object]) -> str:
    venues = summary.get("venues")
    rows = venues if isinstance(venues, list) else []
    lines = [
        "# Venue Read-only Capability Probe",
        "",
        f"run_id: {summary.get('run_id')}",
        f"generated_at: {summary.get('generated_at')}",
        f"status: {summary.get('status')}",
        f"venue_count: {summary.get('venue_count')}",
        "",
        "## Non-Claims",
        "",
        "- no external API used",
        "- no credentials used",
        "- no wallet used",
        "- no signing used",
        "- no exchange write used",
        "- no live order submitted",
        "- no network attempted",
        "- not paper / live permission",
        "",
        "## Venues",
        "",
    ]
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        row = cast(Mapping[str, object], item)
        lines.extend(
            [
                f"### {row.get('venue_id')}",
                "",
                f"- venue_family: {row.get('venue_family')}",
                f"- asset_universe: {row.get('asset_universe')}",
                f"- current_venue_id_enabled: {row.get('current_venue_id_enabled')}",
                f"- schema_enabled: {row.get('schema_enabled')}",
                f"- strategy_lab_enabled: {row.get('strategy_lab_enabled')}",
                f"- evaluation_plan_enabled: {row.get('evaluation_plan_enabled')}",
                f"- paper_enabled: {row.get('paper_enabled')}",
                f"- read_only_network_enabled: {row.get('read_only_network_enabled')}",
                f"- credentialed_read_only_enabled: {row.get('credentialed_read_only_enabled')}",
                f"- live_enabled: {row.get('live_enabled')}",
                f"- read_only_probe_status: {row.get('read_only_probe_status')}",
                f"- credential_status: {row.get('credential_status')}",
                f"- network_attempted: {row.get('network_attempted')}",
                f"- block_reasons: {_string_list(row.get('block_reasons'))}",
                f"- not_attempted_reasons: {_string_list(row.get('not_attempted_reasons'))}",
                f"- next_action: {row.get('next_action')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary Note",
            "",
            "- `catalog known` is not `venue enabled`.",
            "- Read-only probe is not network readiness.",
            "- This report is not paper / live permission.",
            "",
        ]
    )
    return "\n".join(lines)


def _string_list(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return ", ".join(str(item) for item in value)
