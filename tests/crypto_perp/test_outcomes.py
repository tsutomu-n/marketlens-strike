from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def test_outcome_settles_long_and_short_returns_direction_neutrally() -> None:
    outcome = build_outcome(
        event_id="event-1",
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("105"),
                high_price=Decimal("110"),
                low_price=Decimal("90"),
                market_return=Decimal("0.01"),
            )
        ],
        source_refs=[
            {
                "path": "data/history/event-1-60m.json",
                "sha256": "c" * 64,
                "schema_version": "crypto_perp_market_snapshot.v1",
            }
        ],
    )

    horizon = outcome.horizons[0]
    assert horizon.raw_return == Decimal("0.05")
    assert horizon.long_return_before_cost == Decimal("0.05")
    assert horizon.short_return_before_cost == Decimal("-0.05")
    assert horizon.mfe_long == Decimal("0.1")
    assert horizon.mae_long == Decimal("-0.1")
    assert horizon.mfe_short == Decimal("0.1")
    assert horizon.mae_short == Decimal("-0.1")
    assert horizon.market_adjusted_return == Decimal("0.04")

    payload = outcome.model_dump(mode="json")
    assert payload["horizons"][0]["long_return_before_cost"] == "0.05"
    assert payload["horizons"][0]["short_return_before_cost"] == "-0.05"
    assert "entry_bid_vwap" not in json.dumps(payload)
    assert "exit_ask_vwap" not in json.dumps(payload)


def test_outcome_does_not_optimistically_resolve_ambiguous_ohlc_ordering() -> None:
    outcome = build_outcome(
        event_id="event-1",
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("98"),
                high_price=Decimal("112"),
                low_price=Decimal("88"),
            )
        ],
    )

    assert outcome.horizons[0].high_first_low_first == "AMBIGUOUS"


def test_outcome_preserves_observed_high_low_order_when_provided() -> None:
    outcome = build_outcome(
        event_id="event-1",
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("98"),
                high_price=Decimal("112"),
                low_price=Decimal("88"),
                observed_high_low_order="LOW_FIRST",
            )
        ],
    )

    assert outcome.horizons[0].high_first_low_first == "LOW_FIRST"


def test_outcome_dump_matches_schema() -> None:
    outcome = build_outcome(
        event_id="event-1",
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("95"),
                high_price=Decimal("104"),
                low_price=Decimal("92"),
            )
        ],
        near_miss_refs=["near-event-1"],
        known_gaps=["missing_books1_segment"],
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_outcome.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(outcome.model_dump(mode="json"))


def test_crypto_perp_outcome_record_cli_writes_matured_outcome(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "crypto-perp-outcome-record",
            "--event-id",
            "event-1",
            "--out",
            str(tmp_path / "outcomes"),
            "--horizon-minutes",
            "60",
            "--reference-price",
            "100",
            "--close-price",
            "105",
            "--high-price",
            "110",
            "--low-price",
            "95",
            "--market-return",
            "0.01",
            "--observed-high-low-order",
            "HIGH_FIRST",
            "--known-gap",
            "books15_missing",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "event_id=event-1" in result.stdout

    outcome_path_line = next(
        line for line in result.stdout.splitlines() if line.startswith("outcome_path=")
    )
    outcome_path = Path(outcome_path_line.split("=", 1)[1])
    payload = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crypto_perp_outcome.v1"
    assert payload["boundary"]["exchange_write_used"] is False
    assert payload["horizons"][0]["long_return_before_cost"] == "0.05"
    assert payload["horizons"][0]["short_return_before_cost"] == "-0.05"
    assert payload["horizons"][0]["high_first_low_first"] == "HIGH_FIRST"
    assert payload["known_gaps"] == ["books15_missing"]


def test_crypto_perp_outcome_record_cli_requires_event_id_or_event() -> None:
    result = runner.invoke(
        app,
        [
            "crypto-perp-outcome-record",
            "--horizon-minutes",
            "60",
            "--reference-price",
            "100",
            "--close-price",
            "101",
            "--high-price",
            "102",
            "--low-price",
            "99",
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "event_id is required" in result.stdout
