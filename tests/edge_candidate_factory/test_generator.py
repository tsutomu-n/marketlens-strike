from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.edge_candidate_factory.generator import (
    EdgeCandidateFactoryConfig,
    EdgeCandidateFactoryOutputExistsError,
    build_edge_candidate_factory_run,
    write_edge_candidate_factory_run,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_build_edge_candidate_factory_run_tracks_cap_and_duplicates() -> None:
    run = build_edge_candidate_factory_run(
        EdgeCandidateFactoryConfig(
            run_id="edge-run-001",
            generated_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
            source_root="data/prep/watchdeck",
            symbols=["BTCUSDT"],
            product_type="USDT-FUTURES",
            timeframe="5m",
            families=[
                "liquidation_exhaustion_reversal",
                "spread_widening_no_trade",
                "spread_widening_no_trade",
                "funding_pressure_reversion",
            ],
            candidate_cap=2,
            venue_id="bitget",
        )
    )

    assert run.report.candidate_count_total == 2
    assert run.report.candidate_count_accepted == 2
    assert run.report.candidate_count_rejected == 0
    assert run.multiplicity_account.candidate_count_total == 4
    assert run.multiplicity_account.candidate_count_shortlisted == 2
    assert run.multiplicity_account.candidate_count_rejected == 2
    assert [row.row_kind.value for row in run.search_ledger_rows] == [
        "candidate",
        "candidate",
        "duplicate",
        "cap_rejection",
    ]
    assert [row.row_kind.value for row in run.rejection_rows] == ["duplicate", "cap_rejection"]
    assert run.report.boundary.permits_live_order is False
    assert run.report.generator_config.network_attempted is False
    assert run.report.generator_config.credentials_used is False
    assert run.report.generator_config.production_exchange_write_used is False


def test_write_edge_candidate_factory_run_outputs_schema_valid_artifacts(tmp_path: Path) -> None:
    run = build_edge_candidate_factory_run(
        EdgeCandidateFactoryConfig(
            run_id="edge-run-002",
            generated_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
            source_root="data/prep/watchdeck",
            symbols=["BTCUSDT"],
            product_type="USDT-FUTURES",
            timeframe="5m",
            families=["liquidation_exhaustion_reversal", "funding_pressure_reversion"],
            candidate_cap=1,
            venue_id="bitget",
        )
    )

    result = write_edge_candidate_factory_run(run=run, out_dir=tmp_path)

    assert result.report_path.exists()
    assert result.report_markdown_path.exists()
    assert result.search_ledger_path.exists()
    assert result.multiplicity_account_path.exists()
    assert result.rejection_ledger_path.exists()
    Draft202012Validator(_schema("smart_candidate_prior_report.v1.schema.json")).validate(
        json.loads(result.report_path.read_text(encoding="utf-8"))
    )
    Draft202012Validator(_schema("trial_multiplicity_account.v1.schema.json")).validate(
        json.loads(result.multiplicity_account_path.read_text(encoding="utf-8"))
    )
    ledger_rows = [
        json.loads(line)
        for line in result.search_ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    rejection_rows = [
        json.loads(line)
        for line in result.rejection_ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["row_kind"] for row in ledger_rows] == ["candidate", "cap_rejection"]
    assert [row["row_kind"] for row in rejection_rows] == ["cap_rejection"]
    Draft202012Validator(_schema("edge_candidate_search_ledger.v1.schema.json")).validate(
        ledger_rows[0]
    )

    with pytest.raises(EdgeCandidateFactoryOutputExistsError):
        write_edge_candidate_factory_run(run=run, out_dir=tmp_path)
