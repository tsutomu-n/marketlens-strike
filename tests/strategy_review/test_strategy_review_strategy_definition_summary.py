from __future__ import annotations

from pathlib import Path

from sis.strategy_review.strategy_definition_summary import (
    not_configured_strategy_definition_section,
    strategy_definition_summary,
)


def _write_authoring_spec(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: trend_pullback_test_v1
  strategy_family: trend_pullback
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
  run_profile_id: strategy_lab_research_only
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
    any:
      - column: research_return_1d
        op: gt
        value: 0
  hold:
    any:
      - column: vix_level
        op: gte
        value: 30
  exit:
    stop_loss_bps: 150
    take_profit_bps: 300
  sizing:
    position_weight: 1.0
    notional_usd: 1000
backtest:
  split_method: purged_walk_forward
  label_horizon_minutes: 240
  primary_metric: total_return
""",
        encoding="utf-8",
    )


def test_not_configured_strategy_definition_section_has_no_source_artifact() -> None:
    section = not_configured_strategy_definition_section()

    assert section.section_id == "strategy_definition"
    assert section.title == "Strategy Definition"
    assert section.status == "not_configured"
    assert section.source_artifact_keys == ()
    assert "authoring spec path was not provided or derivable" in section.markdown


def test_strategy_definition_summary_reports_invalid_authoring_spec(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "invalid-spec.yaml"
    path.write_text("schema_version: wrong\n", encoding="utf-8")

    artifact, section = strategy_definition_summary(path)

    assert artifact.artifact_key == "authoring_spec"
    assert artifact.required is False
    assert artifact.status.value == "invalid"
    assert artifact.summary["error"]
    assert section.section_id == "strategy_definition"
    assert section.status == "invalid"
    assert "invalid-spec.yaml" in section.markdown
    assert "error:" in section.markdown


def test_strategy_definition_summary_builds_present_artifact_and_markdown(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "docs/strategy_research_lab/examples/spec.yaml"
    _write_authoring_spec(path)

    artifact, section = strategy_definition_summary(path)

    assert artifact.artifact_key == "authoring_spec"
    assert artifact.required is False
    assert artifact.status.value == "present"
    assert artifact.summary["strategy_id"] == "trend_pullback_test_v1"
    assert artifact.summary["strategy_family"] == "trend_pullback"
    assert artifact.summary["execution_venue"] == "trade_xyz"
    assert artifact.summary["execution_symbol"] == "XYZ100"
    assert artifact.summary["real_market_symbol"] == "QQQ"
    assert artifact.summary["entry_rule_count"] == 2
    assert artifact.summary["hold_rule_count"] == 1
    assert artifact.summary["exit_rule_fields"] == ["stop_loss_bps", "take_profit_bps"]
    assert artifact.summary["observed_boundary_flags"]["wallet_used"] is False
    assert section.status == "present"
    assert section.source_artifact_keys == ("authoring_spec",)
    assert "strategy_id: `trend_pullback_test_v1`" in section.markdown
    assert "exit_rule_fields: `stop_loss_bps, take_profit_bps`" in section.markdown
    assert "backtest.primary_metric: `total_return`" in section.markdown
