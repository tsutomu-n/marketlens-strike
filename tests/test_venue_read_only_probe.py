from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import validate

from sis.venues.ids import VENUE_IDS
from sis.venues.read_only_probe import build_venue_read_only_probe_report
from sis.venues.read_only_probe import build_venue_read_only_probe_summary


EXPECTED_VENUES = {
    "trade_xyz",
    "bitget_demo",
    "bitget_futures",
    "hyperliquid_perp",
}

SAFETY_FIELDS = (
    "external_api_used",
    "credentials_used",
    "wallet_used",
    "signing_used",
    "exchange_write_used",
    "live_order_submitted",
    "network_attempted",
)


def _schema() -> dict[str, Any]:
    return json.loads(
        Path("schemas/venue_read_only_probe_summary.v1.schema.json").read_text(encoding="utf-8")
    )


def _rows_by_venue(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    venues = summary["venues"]
    assert isinstance(venues, list)
    rows = {str(row["venue_id"]): row for row in venues if isinstance(row, dict)}
    assert set(rows) == EXPECTED_VENUES
    return rows


def test_build_summary_is_fixture_only_and_schema_valid(monkeypatch) -> None:
    monkeypatch.setenv("BITGET_DEMO_API_SECRET", "super-secret-value")
    monkeypatch.setenv("HYPERLIQUID_PRIVATE_KEY", "also-secret")

    summary = build_venue_read_only_probe_summary(
        generated_at="2026-06-17T01:40:00+00:00",
        run_id="test-run-001",
    )

    validate(instance=summary, schema=_schema())
    assert summary["schema_version"] == "venue_read_only_probe_summary.v1"
    assert summary["run_id"] == "test-run-001"
    assert summary["generated_at"] == "2026-06-17T01:40:00+00:00"
    assert summary["status"] == "fixture_only"
    assert summary["venue_count"] == 4
    for field in SAFETY_FIELDS:
        assert summary[field] is False

    serialized = json.dumps(summary, ensure_ascii=False).lower()
    assert "super-secret-value" not in serialized
    assert "also-secret" not in serialized
    for forbidden in (
        "ready",
        "approved",
        "connected",
        "account_ready",
        "live_ready",
        "production_ready",
    ):
        assert forbidden not in serialized


def test_summary_rows_match_current_catalog_boundaries() -> None:
    rows = _rows_by_venue(
        build_venue_read_only_probe_summary(
            generated_at="2026-06-17T01:40:00+00:00",
            run_id="test-run-001",
        )
    )

    assert set(VENUE_IDS) == {"trade_xyz", "bitget_demo"}
    assert rows["trade_xyz"]["current_venue_id_enabled"] is True
    assert rows["bitget_demo"]["current_venue_id_enabled"] is True
    assert rows["bitget_futures"]["current_venue_id_enabled"] is False
    assert rows["hyperliquid_perp"]["current_venue_id_enabled"] is False

    trade_xyz = rows["trade_xyz"]
    assert trade_xyz["read_only_probe_status"] == "local_capability_only"
    assert trade_xyz["credential_status"] == "not_required"
    assert trade_xyz["read_only_network_enabled"] is True
    assert trade_xyz["network_attempted"] is False

    bitget_demo = rows["bitget_demo"]
    assert bitget_demo["read_only_probe_status"] == "local_capability_only"
    assert bitget_demo["credential_status"] == "not_checked"
    assert bitget_demo["evaluation_plan_enabled"] is False
    assert bitget_demo["read_only_network_enabled"] is False
    assert bitget_demo["network_attempted"] is False
    assert any("production_bitget" in item for item in bitget_demo["not_attempted_reasons"])

    for venue_id in ("bitget_futures", "hyperliquid_perp"):
        row = rows[venue_id]
        assert row["known_in_capability_catalog"] is True
        assert row["known_in_suitability_catalog"] is True
        assert row["schema_enabled"] is False
        assert row["strategy_lab_enabled"] is False
        assert row["evaluation_plan_enabled"] is False
        assert row["paper_enabled"] is False
        assert row["paper_candidate_enabled"] is False
        assert row["paper_intent_enabled"] is False
        assert row["read_only_network_enabled"] is False
        assert row["credentialed_read_only_enabled"] is False
        assert row["paper_execution_enabled"] is False
        assert row["live_enabled"] is False
        assert row["network_attempted"] is False
        assert row["read_only_probe_status"] == "blocked_by_capability"
        assert row["block_reasons"]

    assert any(
        "direct_hyperliquid" in item for item in rows["hyperliquid_perp"]["not_attempted_reasons"]
    )


def test_report_contains_boundaries_and_no_permission_claims() -> None:
    summary = build_venue_read_only_probe_summary(
        generated_at="2026-06-17T01:40:00+00:00",
        run_id="test-run-001",
    )
    report = build_venue_read_only_probe_report(summary)

    assert "# Venue Read-only Capability Probe" in report
    assert "run_id: test-run-001" in report
    assert "no external API used" in report
    assert "no credentials used" in report
    assert "no wallet used" in report
    assert "no signing used" in report
    assert "no exchange write used" in report
    assert "no network attempted" in report
    assert "`catalog known` is not `venue enabled`" in report
    assert "not paper / live permission" in report
