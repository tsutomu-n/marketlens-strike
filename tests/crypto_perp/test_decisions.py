from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.decisions import build_decision
from sis.crypto_perp.events import detect_event
from sis.crypto_perp.features import EventDetectorConfig
from sis.crypto_perp.models import CryptoPerpAction
from sis.crypto_perp.quality import validate_candle_series
from .test_features import make_bars, ticker


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _write_event(tmp_path: Path) -> Path:
    bars = make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296)
    event = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=bars,
        ticker=ticker(),
        quality_report=validate_candle_series(bars, interval="15m"),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=EventDetectorConfig(),
    )
    assert event is not None
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event.model_dump(mode="json")), encoding="utf-8")
    return event_path


def test_decision_is_immutable_pre_outcome_and_direction_neutral() -> None:
    decisions = [
        build_decision(
            event_id="event-1",
            action=action,
            actor_type="system",
            actor_id="mvp-b",
            decision_at="2026-06-21T05:01:00Z",
            information_cutoff_at="2026-06-21T05:00:00Z",
            size_cap_usd=Decimal("25"),
            reason_codes=["manual_review_required"],
            notes="prospective decision only",
            review_seconds=42,
            source_event_path="data/events/event-1.json",
            source_event_sha256="a" * 64,
        )
        for action in CryptoPerpAction
    ]

    assert {item.action for item in decisions} == set(CryptoPerpAction)
    payload = decisions[0].model_dump(mode="json")
    assert payload["action"] == "REVERSAL_SHORT"
    assert payload["size_cap_usd"] == "25"
    assert payload["information_cutoff_at"] == "2026-06-21T05:00:00Z"
    assert "outcome" not in payload
    assert "pnl" not in payload
    assert "matured" not in payload
    assert "entry_bid_vwap" not in payload
    assert "exit_ask_vwap" not in payload

    with pytest.raises(Exception, match="frozen|read-only"):
        decisions[0].action = CryptoPerpAction.NO_TRADE


def test_decision_rejects_decision_before_information_cutoff() -> None:
    with pytest.raises(ValueError, match="decision_at must be after or equal"):
        build_decision(
            event_id="event-1",
            action=CryptoPerpAction.UNKNOWN,
            actor_type="system",
            actor_id="mvp-b",
            decision_at="2026-06-21T04:59:59Z",
            information_cutoff_at="2026-06-21T05:00:00Z",
            size_cap_usd=Decimal("0"),
            reason_codes=[],
            notes="",
            review_seconds=0,
            source_event_path="data/events/event-1.json",
            source_event_sha256="a" * 64,
        )


def test_decision_dump_matches_schema() -> None:
    decision = build_decision(
        event_id="event-1",
        action=CryptoPerpAction.CONTINUATION_LONG,
        actor_type="human",
        actor_id="operator-1",
        decision_at="2026-06-21T05:01:00Z",
        information_cutoff_at="2026-06-21T05:00:00Z",
        size_cap_usd=Decimal("12.50"),
        reason_codes=["spread_ok", "funding_checked"],
        notes="manual prospective decision",
        review_seconds=180,
        source_event_path="data/events/event-1.json",
        source_event_sha256="b" * 64,
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_decision.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(decision.model_dump(mode="json"))


def test_crypto_perp_decision_record_cli_writes_prospective_artifact(tmp_path: Path) -> None:
    event_path = _write_event(tmp_path)

    result = runner.invoke(
        app,
        [
            "crypto-perp-decision-record",
            "--event",
            str(event_path),
            "--action",
            "NO_TRADE",
            "--out",
            str(tmp_path / "decisions"),
            "--actor-type",
            "human",
            "--actor-id",
            "operator-1",
            "--size-cap-usd",
            "0",
            "--reason-code",
            "insufficient_evidence",
            "--notes",
            "prospective no-trade",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "action=NO_TRADE" in result.stdout

    decision_path_line = next(
        line for line in result.stdout.splitlines() if line.startswith("decision_path=")
    )
    decision_path = Path(decision_path_line.split("=", 1)[1])
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crypto_perp_decision.v1"
    assert payload["action"] == "NO_TRADE"
    assert payload["boundary"]["exchange_write_used"] is False
    assert payload["source_event_path"] == event_path.as_posix()
    assert "outcome" not in payload


def test_crypto_perp_decision_record_cli_rejects_invalid_actor(tmp_path: Path) -> None:
    event_path = _write_event(tmp_path)

    result = runner.invoke(
        app,
        [
            "crypto-perp-decision-record",
            "--event",
            str(event_path),
            "--action",
            "REVERSAL_SHORT",
            "--actor-type",
            "bot",
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "actor_type must be system or human" in result.stdout
