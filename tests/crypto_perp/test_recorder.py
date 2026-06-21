from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.crypto_perp.recorder import CaptureRequest, run_candidate_capture
from sis.crypto_perp.segments import read_gzip_jsonl


REPO_ROOT = Path(__file__).resolve().parents[2]


def _book_payload(seq: int, checksum: int = 0) -> dict:
    return {
        "action": "snapshot",
        "arg": {"instType": "USDT-FUTURES", "channel": "books1", "instId": "BTCUSDT"},
        "data": [
            {
                "asks": [["101", "1"]],
                "bids": [["100", "1"]],
                "checksum": checksum,
                "seq": seq,
                "ts": "1710000000000",
            }
        ],
        "ts": 1710000000000,
    }


def test_candidate_capture_writes_raw_trade_and_book_segments(tmp_path: Path) -> None:
    raw_messages = [
        {
            "arg": {"instType": "USDT-FUTURES", "channel": "trade", "instId": "BTCUSDT"},
            "data": [{"tradeId": "1", "price": "100", "size": "0.1", "side": "buy"}],
            "ts": 1710000000000,
        },
        _book_payload(seq=1),
    ]

    manifest = run_candidate_capture(
        CaptureRequest(
            event_id="event-1",
            provider_id="bitget",
            native_symbol="BTCUSDT",
            channels=["trades", "books1"],
            duration_minutes=10,
            output_root=tmp_path / "capture",
        ),
        raw_messages=raw_messages,
        received_at="2026-06-21T04:00:00Z",
    )

    payload = manifest.model_dump(mode="json")
    assert payload["event_id"] == "event-1"
    assert payload["backend"] == "native"
    assert payload["channels"] == ["trades", "books1"]
    assert payload["row_count"] == 2
    assert payload["coverage_status"] == "COMPLETE"
    rows = []
    for segment in manifest.segments:
        rows.extend(read_gzip_jsonl(Path(segment.path)))
    assert rows[0]["raw_payload"] == raw_messages[0]
    assert rows[1]["raw_payload"] == raw_messages[1]


def test_candidate_capture_records_checksum_failure_as_unfillable_gap(tmp_path: Path) -> None:
    manifest = run_candidate_capture(
        CaptureRequest(
            event_id="event-1",
            provider_id="bitget",
            native_symbol="BTCUSDT",
            channels=["books1"],
            duration_minutes=10,
            output_root=tmp_path / "capture",
        ),
        raw_messages=[_book_payload(seq=1, checksum=123)],
        received_at="2026-06-21T04:00:00Z",
    )

    assert manifest.checksum_failure_count == 1
    assert manifest.sequence_gap_count == 0
    assert manifest.coverage_status == "GAPPED"
    assert manifest.known_gaps[0].reason_code == "CHECKSUM_FAILURE"


def test_candidate_capture_manifest_dump_matches_schema(tmp_path: Path) -> None:
    manifest = run_candidate_capture(
        CaptureRequest(
            event_id="event-1",
            provider_id="bitget",
            native_symbol="BTCUSDT",
            channels=["trades"],
            duration_minutes=10,
            output_root=tmp_path / "capture",
        ),
        raw_messages=[
            {
                "arg": {"instType": "USDT-FUTURES", "channel": "trade", "instId": "BTCUSDT"},
                "data": [{"tradeId": "1", "price": "100", "size": "0.1", "side": "buy"}],
                "ts": 1710000000000,
            }
        ],
        received_at="2026-06-21T04:00:00Z",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_capture_manifest.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest.model_dump(mode="json"))


def test_candidate_capture_rejects_non_candidate_all_symbol_capture(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="candidate symbol"):
        CaptureRequest(
            event_id="event-1",
            provider_id="bitget",
            native_symbol="*",
            channels=["books1"],
            duration_minutes=10,
            output_root=tmp_path / "capture",
        )
