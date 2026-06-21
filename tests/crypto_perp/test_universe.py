from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.crypto_perp.bitget.normalizers import normalize_instruments
from sis.crypto_perp.universe import build_universe_snapshot


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures/crypto_perp/bitget/public"


def _instrument(**overrides: str) -> dict[str, str]:
    base = normalize_instruments(
        json.loads((FIXTURE_ROOT / "instruments.json").read_text(encoding="utf-8"))
    )[0]
    base.update(overrides)
    return base


def test_universe_diff_detects_added_removed_status_and_metadata_changes() -> None:
    previous = build_universe_snapshot(
        provider_id="bitget",
        product_type="USDT-FUTURES",
        observed_at="2026-06-21T04:00:00Z",
        instruments=[
            _instrument(native_symbol="BTCUSDT", canonical_symbol="BTCUSDT"),
            _instrument(native_symbol="ETHUSDT", canonical_symbol="ETHUSDT", status="online"),
            _instrument(native_symbol="DOGEUSDT", canonical_symbol="DOGEUSDT"),
        ],
    )

    current = build_universe_snapshot(
        provider_id="bitget",
        product_type="USDT-FUTURES",
        observed_at="2026-06-21T04:05:00Z",
        instruments=[
            _instrument(
                native_symbol="BTCUSDT",
                canonical_symbol="BTCUSDT",
                maker_fee_rate="0.0003",
                price_precision="2",
                funding_interval_hours="4",
            ),
            _instrument(native_symbol="ETHUSDT", canonical_symbol="ETHUSDT", status="offline"),
            _instrument(native_symbol="SOLUSDT", canonical_symbol="SOLUSDT"),
        ],
        previous_snapshot=previous,
    )

    payload = current.model_dump(mode="json")
    assert payload["diff"]["added"] == ["SOLUSDT"]
    assert payload["diff"]["removed"] == ["DOGEUSDT"]
    assert payload["diff"]["status_changed"] == [
        {"native_symbol": "ETHUSDT", "previous": "online", "current": "offline"}
    ]
    assert payload["diff"]["metadata_changed"] == [
        {
            "native_symbol": "BTCUSDT",
            "changed_fields": ["funding_interval_hours", "maker_fee_rate", "price_precision"],
        }
    ]
    assert payload["eligibility"][1]["eligible_for_screening"] is False
    assert "STATUS_NOT_ONLINE" in payload["eligibility"][1]["reason_codes"]


def test_universe_partial_response_cannot_become_mass_removal() -> None:
    previous = build_universe_snapshot(
        provider_id="bitget",
        product_type="USDT-FUTURES",
        observed_at="2026-06-21T04:00:00Z",
        instruments=[
            _instrument(native_symbol="BTCUSDT", canonical_symbol="BTCUSDT"),
            _instrument(native_symbol="ETHUSDT", canonical_symbol="ETHUSDT"),
            _instrument(native_symbol="SOLUSDT", canonical_symbol="SOLUSDT"),
        ],
    )

    partial = build_universe_snapshot(
        provider_id="bitget",
        product_type="USDT-FUTURES",
        observed_at="2026-06-21T04:05:00Z",
        instruments=[_instrument(native_symbol="BTCUSDT", canonical_symbol="BTCUSDT")],
        previous_snapshot=previous,
        response_complete=False,
    )

    assert partial.diff.added == []
    assert partial.diff.removed == []


def test_universe_snapshot_dump_matches_schema() -> None:
    snapshot = build_universe_snapshot(
        provider_id="bitget",
        product_type="USDT-FUTURES",
        observed_at="2026-06-21T04:00:00Z",
        instruments=[_instrument(native_symbol="BTCUSDT", canonical_symbol="BTCUSDT")],
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_universe_snapshot.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(snapshot.model_dump(mode="json"))
