from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator

from sis.crypto_perp.cash_ledger import CashLedgerEntry, build_cash_ledger


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cash_ledger_includes_deposits_costs_and_ruined_pods() -> None:
    ledger = build_cash_ledger(
        ledger_id="ledger-1",
        observed_at="2026-06-21T07:00:00Z",
        entries=[
            CashLedgerEntry(
                entry_id="deposit-1",
                pod_id="pod-a",
                event_id=None,
                entry_type="DEPOSIT",
                amount_usd=Decimal("100"),
                occurred_at="2026-06-21T06:00:00Z",
            ),
            CashLedgerEntry(
                entry_id="pnl-1",
                pod_id="pod-a",
                event_id="event-1",
                entry_type="REALIZED_PNL",
                amount_usd=Decimal("3"),
                occurred_at="2026-06-21T06:10:00Z",
            ),
            CashLedgerEntry(
                entry_id="fee-1",
                pod_id="pod-a",
                event_id="event-1",
                entry_type="FEE",
                amount_usd=Decimal("-0.4"),
                occurred_at="2026-06-21T06:10:00Z",
            ),
            CashLedgerEntry(
                entry_id="funding-1",
                pod_id="pod-a",
                event_id="event-1",
                entry_type="FUNDING",
                amount_usd=Decimal("-0.1"),
                occurred_at="2026-06-21T06:20:00Z",
            ),
            CashLedgerEntry(
                entry_id="infra-1",
                pod_id="ops",
                event_id=None,
                entry_type="INFRA_COST",
                amount_usd=Decimal("-2"),
                occurred_at="2026-06-21T06:30:00Z",
            ),
            CashLedgerEntry(
                entry_id="ruin-1",
                pod_id="pod-dead",
                event_id="event-dead",
                entry_type="POD_RUIN",
                amount_usd=Decimal("-25"),
                occurred_at="2026-06-21T06:40:00Z",
                ruined=True,
            ),
        ],
    )

    assert ledger.total_deposits_usd == Decimal("100")
    assert ledger.total_realized_pnl_usd == Decimal("3")
    assert ledger.total_fees_usd == Decimal("-0.4")
    assert ledger.total_funding_usd == Decimal("-0.1")
    assert ledger.total_infra_cost_usd == Decimal("-2")
    assert ledger.total_ruin_usd == Decimal("-25")
    assert ledger.actual_cash_result_usd == Decimal("75.5")
    assert ledger.pod_summaries["pod-dead"].actual_cash_result_usd == Decimal("-25")


def test_cash_ledger_dump_matches_schema() -> None:
    ledger = build_cash_ledger(
        ledger_id="ledger-1",
        observed_at="2026-06-21T07:00:00Z",
        entries=[
            CashLedgerEntry(
                entry_id="deposit-1",
                pod_id="pod-a",
                event_id=None,
                entry_type="DEPOSIT",
                amount_usd=Decimal("100"),
                occurred_at="2026-06-21T06:00:00Z",
            )
        ],
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_cash_ledger.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(ledger.model_dump(mode="json"))
