from __future__ import annotations

import json
from pathlib import Path


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
    summary_properties = backtest_result["properties"]["summary"]["properties"]
    assert "executed_signal_summary" in summary_properties
    assert "strategy_scorecard" in summary_properties
    assert "multi_leg_group_metrics" in summary_properties
