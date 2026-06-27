from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from sis.backtest.artifact_io import sha256_file, write_json_object
from sis.crypto_perp.tournament import TournamentEventResult, build_tournament_report
from sis.crypto_perp.workbench_bridge import build_tournament_strategy_input_contract
from sis.strategy_workbench_viewer.service import build_strategy_workbench_viewer


REPO_ROOT = Path(__file__).resolve().parents[2]


def _report():
    rows = []
    for event_id in ("event-1", "event-2"):
        rows.extend(
            [
                TournamentEventResult(
                    event_id=event_id,
                    action="REVERSAL_SHORT",
                    actual_cash_result_usd=Decimal("-1"),
                    market_adjusted_return=Decimal("-0.01"),
                    operator_time_minutes=Decimal("1"),
                ),
                TournamentEventResult(
                    event_id=event_id,
                    action="CONTINUATION_LONG",
                    actual_cash_result_usd=Decimal("2"),
                    market_adjusted_return=Decimal("0.01"),
                    operator_time_minutes=Decimal("1"),
                ),
                TournamentEventResult(
                    event_id=event_id,
                    action="NO_TRADE",
                    actual_cash_result_usd=Decimal("0"),
                    market_adjusted_return=Decimal("0"),
                    operator_time_minutes=Decimal("0"),
                ),
            ]
        )
    return build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=rows,
        min_events=2,
    )


def test_workbench_bridge_exports_strategy_input_contract(tmp_path: Path) -> None:
    report = _report()
    report_path = tmp_path / "data/crypto_perp/tournament.json"
    write_json_object(report_path, report.model_dump(mode="json"))

    contract = build_tournament_strategy_input_contract(
        report=report,
        report_path="data/crypto_perp/tournament.json",
        report_sha256=sha256_file(report_path),
        instruments=["BTCUSDT"],
        timeframe="15m",
        created_at="2026-06-21T07:01:00Z",
    )
    payload = contract.model_dump(mode="json", exclude_none=True)
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_input_contract.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator(schema).validate(payload)
    assert payload["strategy_scope"]["strategy_family"] == "crypto_perp_truth_cycle"
    assert payload["sources"][0]["source_type"] == "runtime_observation"
    assert payload["sources"][0]["schema_version"] == "crypto_perp_tournament_report.v1"
    assert payload["sources"][0]["execution_reality"]["includes_fills"] is True
    assert payload["boundary"]["permits_live_order"] is False


@pytest.mark.parametrize(
    ("report_path", "report_sha256"),
    [
        ("/abs/data/crypto_perp/tournament.json", "sha256:" + "a" * 64),
        ("data/secrets/crypto_perp/tournament.json", "sha256:" + "a" * 64),
        ("data/crypto_perp/tournament.json", "a" * 64),
    ],
)
def test_workbench_bridge_rejects_unsafe_strategy_input_source(
    report_path: str, report_sha256: str
) -> None:
    with pytest.raises(ValidationError):
        build_tournament_strategy_input_contract(
            report=_report(),
            report_path=report_path,
            report_sha256=report_sha256,
            instruments=["BTCUSDT"],
            timeframe="15m",
            created_at="2026-06-21T07:01:00Z",
        )


def test_existing_workbench_viewer_consumes_tournament_json(tmp_path: Path) -> None:
    report = _report()
    report_path = tmp_path / "data/crypto_perp/tournament.json"
    write_json_object(report_path, report.model_dump(mode="json"))

    result = build_strategy_workbench_viewer(
        artifacts=[report_path],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    source = result.manifest.source_artifacts[0]
    assert source.schema_version == "crypto_perp_tournament_report.v1"
    assert source.status == "COMPLETE"
    assert source.summary["leader_action"] == "CONTINUATION_LONG"
    assert source.summary["primary_metric"] == "actual_cash_result_usd"


def test_workbench_bridge_does_not_mark_proxy_gap_report_as_including_fills(
    tmp_path: Path,
) -> None:
    report = build_tournament_report(
        report_id="tournament-proxy",
        generated_at="2026-06-21T07:00:00Z",
        rows=_report().rows,
        min_events=2,
        known_gaps=[
            "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH",
            "FEES_FUNDING_AND_FILL_SLIPPAGE_NOT_INCLUDED",
        ],
    )
    report_path = tmp_path / "data/crypto_perp/tournament_proxy.json"
    write_json_object(report_path, report.model_dump(mode="json"))

    contract = build_tournament_strategy_input_contract(
        report=report,
        report_path="data/crypto_perp/tournament_proxy.json",
        report_sha256=sha256_file(report_path),
        instruments=["BTCUSDT"],
        timeframe="15m",
        created_at="2026-06-21T07:01:00Z",
    )

    reality = contract.sources[0].execution_reality
    assert reality.includes_fills is False
    assert reality.includes_slippage is False
    assert reality.assumed_order_type == "crypto_perp_estimate_or_before_cost_proxy"
