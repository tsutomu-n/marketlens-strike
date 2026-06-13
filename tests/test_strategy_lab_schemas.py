from __future__ import annotations

import json
from pathlib import Path

from sis.venues.ids import VENUE_IDS
from sis.venues.suitability import VENUE_SUITABILITY_CATALOG


def test_strategy_lab_schema_files_exist_and_parse() -> None:
    names = [
        "data_snapshot_manifest.v1.schema.json",
        "feature_snapshot_manifest.v1.schema.json",
        "strategy_authoring_spec.v1.schema.json",
        "strategy_experiment_spec.v1.schema.json",
        "strategy_signal_manifest.v1.schema.json",
        "strategy_signal.v1.schema.json",
        "evaluation_plan.mls.v1.schema.json",
        "trial_record.v1.schema.json",
        "trade_candidate.v1.schema.json",
        "paper_candidate_pack.v1.schema.json",
        "promotion_decision.v1.schema.json",
        "paper_intent_preview.v1.schema.json",
        "strategy_authoring_bundle_result.v1.schema.json",
        "strategy_authoring_backtest_result.v1.schema.json",
        "strategy_backtest_comparison.v1.schema.json",
        "strategy_backtest_suite.v1.schema.json",
        "strategy_backtest_suite_result.v1.schema.json",
        "strategy_backtest_adapter_contract.v1.schema.json",
        "strategy_backtest_adapter_spike.v1.schema.json",
        "strategy_backtest_adapter_selection.v1.schema.json",
        "strategy_backtest_external_result.v1.schema.json",
        "strategy_backtest_portfolio_comparison.v1.schema.json",
        "strategy_backtest_metric_extension.v1.schema.json",
        "strategy_backtest_report_extension.v1.schema.json",
        "strategy_backtest_stress.v1.schema.json",
        "strategy_backtest_framework_smoke.v1.schema.json",
        "strategy_backtest_pack.v1.schema.json",
        "strategy_backtest_pack_validation.v1.schema.json",
        "instrument_registry_snapshot.v1.schema.json",
        "funding_event.v1.schema.json",
        "fee_snapshot.v1.schema.json",
        "quote_log_v2.trade_xyz.strict.schema.json",
    ]

    for name in names:
        payload = json.loads(Path("schemas", name).read_text(encoding="utf-8"))
        assert payload["type"] == "object"


def test_strategy_lab_schema_guards_match_paper_only_boundary() -> None:
    trial = json.loads(Path("schemas/trial_record.v1.schema.json").read_text(encoding="utf-8"))
    pack = json.loads(
        Path("schemas/paper_candidate_pack.v1.schema.json").read_text(encoding="utf-8")
    )
    promotion = json.loads(
        Path("schemas/promotion_decision.v1.schema.json").read_text(encoding="utf-8")
    )
    preview = json.loads(
        Path("schemas/paper_intent_preview.v1.schema.json").read_text(encoding="utf-8")
    )
    bundle_result = json.loads(
        Path("schemas/strategy_authoring_bundle_result.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_result = json.loads(
        Path("schemas/strategy_authoring_backtest_result.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    backtest_comparison = json.loads(
        Path("schemas/strategy_backtest_comparison.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_suite_result = json.loads(
        Path("schemas/strategy_backtest_suite_result.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_adapter_contract = json.loads(
        Path("schemas/strategy_backtest_adapter_contract.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    backtest_adapter_spike = json.loads(
        Path("schemas/strategy_backtest_adapter_spike.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_adapter_selection = json.loads(
        Path("schemas/strategy_backtest_adapter_selection.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    backtest_external_result = json.loads(
        Path("schemas/strategy_backtest_external_result.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_portfolio_comparison = json.loads(
        Path("schemas/strategy_backtest_portfolio_comparison.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    backtest_metric_extension = json.loads(
        Path("schemas/strategy_backtest_metric_extension.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    backtest_report_extension = json.loads(
        Path("schemas/strategy_backtest_report_extension.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    backtest_stress = json.loads(
        Path("schemas/strategy_backtest_stress.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_framework_smoke = json.loads(
        Path("schemas/strategy_backtest_framework_smoke.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_pack = json.loads(
        Path("schemas/strategy_backtest_pack.v1.schema.json").read_text(encoding="utf-8")
    )
    backtest_pack_validation = json.loads(
        Path("schemas/strategy_backtest_pack_validation.v1.schema.json").read_text(encoding="utf-8")
    )

    for name in (
        "profitability_claimed",
        "paper_ready_claimed",
        "tiny_live_ready_claimed",
        "live_ready_claimed",
    ):
        assert trial["properties"][name]["const"] is False
        assert pack["properties"][name]["const"] is False

    for name in (
        "paper_ready_claimed",
        "tiny_live_ready_claimed",
        "live_ready_claimed",
        "wallet_used",
        "exchange_write_used",
    ):
        assert promotion["properties"][name]["const"] is False

    for name in (
        "live_conversion_allowed",
        "live_order_submitted",
        "wallet_used",
        "exchange_write_used",
    ):
        assert preview["properties"][name]["const"] is False

    assert bundle_result["properties"]["paper_only"]["const"] is True
    assert bundle_result["properties"]["live_order_submitted"]["const"] is False
    assert bundle_result["properties"]["portfolio"]["properties"]["resolved_selection_direction"][
        "enum"
    ] == ["maximize", "minimize"]
    group_metrics = bundle_result["properties"]["aggregate_metrics"]["properties"][
        "multi_leg_group_metrics"
    ]["properties"]
    assert "total_notional_usd" in group_metrics
    assert "weighted_notional_return" in group_metrics

    assert backtest_result["properties"]["paper_only"]["const"] is True
    assert backtest_result["properties"]["live_order_submitted"]["const"] is False
    for name in (
        "permits_live_order",
        "live_conversion_allowed",
        "wallet_used",
        "exchange_write_used",
    ):
        assert backtest_comparison["properties"][name]["const"] is False
        assert backtest_suite_result["properties"][name]["const"] is False
        assert backtest_adapter_contract["properties"][name]["const"] is False
        assert backtest_adapter_spike["properties"][name]["const"] is False
        assert backtest_adapter_selection["properties"][name]["const"] is False
        assert backtest_external_result["properties"][name]["const"] is False
        assert backtest_portfolio_comparison["properties"][name]["const"] is False
        assert backtest_metric_extension["properties"][name]["const"] is False
        assert backtest_report_extension["properties"][name]["const"] is False
        assert backtest_stress["properties"][name]["const"] is False
        assert backtest_framework_smoke["properties"][name]["const"] is False
        assert backtest_pack["properties"][name]["const"] is False
        assert backtest_pack_validation["properties"][name]["const"] is False
    assert "comparison_diagnostics" in backtest_comparison["properties"]
    assert backtest_suite_result["properties"]["paper_only"]["const"] is True
    assert backtest_suite_result["properties"]["live_order_submitted"]["const"] is False
    assert backtest_adapter_spike["properties"]["dependency_added"]["const"] is False
    assert backtest_adapter_spike["properties"]["external_engine_run"]["const"] is False
    assert backtest_external_result["properties"]["dependency_added"]["const"] is False
    assert backtest_stress["properties"]["dependency_added"]["const"] is False
    assert backtest_stress["properties"]["paper_only"]["const"] is True
    assert backtest_stress["properties"]["live_order_submitted"]["const"] is False
    pack_policy = backtest_pack["properties"]["external_framework_policy"]["properties"]
    validation_policy = backtest_pack_validation["properties"]["external_framework_policy"][
        "properties"
    ]
    for policy in (pack_policy, validation_policy):
        assert policy["policy_id"]["const"] == "native_primary_external_evaluation_only.v1"
        assert policy["standard_engine"]["const"] == "strategy_authoring_native"
        assert policy["decision"]["const"] == "complete_without_locked_external_dependency"
        assert policy["locked_dependency_added"]["const"] is False
        assert policy["external_adapters_required_for_completion"]["const"] is False
    validation_summary = backtest_pack_validation["properties"]["summary"]["properties"]
    assert validation_summary["external_framework_policy_decision"]["const"] == (
        "complete_without_locked_external_dependency"
    )
    assert validation_summary["locked_dependency_added"]["const"] is False
    summary_properties = backtest_result["properties"]["summary"]["properties"]
    assert "executed_signal_summary" in summary_properties
    assert "strategy_scorecard" in summary_properties
    assert "multi_leg_group_metrics" in summary_properties


def test_execution_venue_schema_enum_matches_strategy_contract_scope() -> None:
    expected = ["trade_xyz", "bitget_demo"]
    signal = json.loads(Path("schemas/strategy_signal.v1.schema.json").read_text(encoding="utf-8"))
    candidate = json.loads(
        Path("schemas/trade_candidate.v1.schema.json").read_text(encoding="utf-8")
    )
    preview = json.loads(
        Path("schemas/paper_intent_preview.v1.schema.json").read_text(encoding="utf-8")
    )

    assert signal["properties"]["execution_venue"]["enum"] == expected
    assert candidate["properties"]["execution_venue"]["enum"] == expected
    assert preview["properties"]["execution_venue"]["enum"] == expected
    assert list(VENUE_IDS) == expected
    assert "bitget_futures" in VENUE_SUITABILITY_CATALOG
    assert "hyperliquid_perp" in VENUE_SUITABILITY_CATALOG
    assert "bitget_futures" not in expected
    assert "hyperliquid_perp" not in expected
