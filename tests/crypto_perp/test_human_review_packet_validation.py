from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.human_review_packet_validation import (
    _event_outcome_pair_violations,
)
from .human_review_packet_fixtures import (
    _packet_cli_args,
    _write_ready_cli_inputs,
)


runner = CliRunner()


_STRUCTURE_CASES = [
    ("selection_manifest", "selection", "created_at"),
    ("decision", "decision", "artifact_id"),
    ("tournament_rows", "rows", "row_set_id"),
    ("bias_guard", "guard", "guard_id"),
    ("data_availability", "availability", "schema_version"),
    ("signal_rows", "signal", "event_id"),
    ("backtest", "backtest", "status"),
    ("stress", "stress", "stress_kind"),
    ("rolling_stability", "rolling", "status"),
    ("gate", "gate", "artifact_id"),
    ("kill_report", "kill", "artifact_id"),
    ("leaderboard", "leaderboard", "artifact_id"),
]


@pytest.mark.parametrize("mode", ["missing", "wrong_type", "extra"])
@pytest.mark.parametrize("artifact_name,path_key,required_field", _STRUCTURE_CASES)
def test_cli_blocks_structurally_invalid_review_inputs(
    tmp_path: Path,
    artifact_name: str,
    path_key: str,
    required_field: str,
    mode: str,
) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    target = paths[path_key]
    if artifact_name == "signal_rows":
        payload = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    else:
        payload = json.loads(target.read_text(encoding="utf-8"))

    if mode == "missing":
        payload.pop(required_field)
    elif mode == "wrong_type":
        payload[required_field] = []
    else:
        payload["unexpected_field"] = "must fail closed"
    target.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    out = tmp_path / f"out-{artifact_name}-{mode}"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert packet["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert f"{artifact_name.upper()}_STRUCTURE_INVALID" in packet["reason_codes"]


_NESTED_STRUCTURE_CASES = [
    ("selection_manifest", "selection", ("producer",), "tool"),
    (
        "selection_manifest",
        "selection",
        ("source_coverage",),
        "ticker_available_count",
    ),
    ("data_availability", "availability", ("summary",), "event_count"),
    ("data_availability", "availability", ("rows", 0), "event_id"),
    ("backtest", "backtest", ("summary",), "event_count"),
    ("backtest", "backtest", ("results", 0), "event_id"),
    ("stress", "stress", ("summary",), "event_count"),
    ("stress", "stress", ("results", 0), "event_id"),
    ("rolling_stability", "rolling", ("summary",), "event_count"),
    ("rolling_stability", "rolling", ("points", 0), "event_id"),
]


@pytest.mark.parametrize("mode", ["missing", "wrong_type", "extra"])
@pytest.mark.parametrize(
    "artifact_name,path_key,container_path,required_field", _NESTED_STRUCTURE_CASES
)
def test_cli_blocks_nested_structural_corruption(
    tmp_path: Path,
    artifact_name: str,
    path_key: str,
    container_path: tuple[str | int, ...],
    required_field: str,
    mode: str,
) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    target = paths[path_key]
    payload = json.loads(target.read_text(encoding="utf-8"))
    container = payload
    for segment in container_path:
        container = container[segment]

    if mode == "missing":
        container.pop(required_field)
    elif mode == "wrong_type":
        container[required_field] = []
    else:
        container["unexpected_nested_field"] = "must fail closed"
    target.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    out = tmp_path / f"out-nested-{artifact_name}-{mode}"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert packet["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert f"{artifact_name.upper()}_STRUCTURE_INVALID" in packet["reason_codes"]


def test_cli_blocks_validly_typed_event_count_disagreement(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    stress = json.loads(paths["stress"].read_text(encoding="utf-8"))
    stress["summary"]["event_count"] = 2
    paths["stress"].write_text(json.dumps(stress), encoding="utf-8")

    out = tmp_path / "out-event-count-mismatch"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert packet["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "EVENT_COUNT_MISMATCH" in packet["reason_codes"]


def test_cli_blocks_signal_event_set_disagreement(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    signal = json.loads(paths["signal"].read_text(encoding="utf-8"))
    signal["event_id"] = "different-event"
    paths["signal"].write_text(json.dumps(signal) + "\n", encoding="utf-8")

    out = tmp_path / "out-signal-event-set-mismatch"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert packet["packet_decision"] == "BLOCKED_BY_ARTIFACT_LINEAGE"
    assert "SIGNAL_ROWS_EVENT_SET_MISMATCH" in packet["reason_codes"]


def test_cli_blocks_availability_event_set_disagreement(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    availability = json.loads(paths["availability"].read_text(encoding="utf-8"))
    availability["rows"][0]["event_id"] = "different-event"
    paths["availability"].write_text(json.dumps(availability), encoding="utf-8")

    out = tmp_path / "out-availability-event-set-mismatch"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert "DATA_AVAILABILITY_EVENT_SET_MISMATCH" in packet["reason_codes"]


def test_cli_blocks_availability_row_count_disagreement(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    availability = json.loads(paths["availability"].read_text(encoding="utf-8"))
    availability["summary"]["row_count"] = 2
    paths["availability"].write_text(json.dumps(availability), encoding="utf-8")

    out = tmp_path / "out-availability-row-count-mismatch"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert "DATA_AVAILABILITY_ROW_COUNT_MISMATCH" in packet["reason_codes"]


def test_cli_blocks_bias_guard_event_count_disagreement(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    guard = json.loads(paths["guard"].read_text(encoding="utf-8"))
    guard["event_count"] = 2
    paths["guard"].write_text(json.dumps(guard), encoding="utf-8")

    out = tmp_path / "out-guard-event-count-mismatch"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert "BIAS_GUARD_EVENT_COUNT_MISMATCH" in packet["reason_codes"]


def test_event_outcome_pair_permutation_is_not_lineage_equivalent() -> None:
    selection = {
        "execution_windows": [
            {
                "event_id": "event-1",
                "outcome_id": "outcome-1",
                "information_cutoff_at": "2026-07-09T00:00:00Z",
                "entry_at": "2026-07-09T00:05:00Z",
                "settled_at": "2026-07-09T01:05:00Z",
                "horizon_minutes": 60,
            },
            {
                "event_id": "event-2",
                "outcome_id": "outcome-2",
                "information_cutoff_at": "2026-07-09T01:00:00Z",
                "entry_at": "2026-07-09T01:05:00Z",
                "settled_at": "2026-07-09T02:05:00Z",
                "horizon_minutes": 60,
            },
        ]
    }
    tournament_rows = {
        "summary": {
            "execution_windows": {
                "event-1": {
                    "entry_at": "2026-07-09T00:05:00Z",
                    "settled_at": "2026-07-09T01:05:00Z",
                    "horizon_minutes": 60,
                },
                "event-2": {
                    "entry_at": "2026-07-09T01:05:00Z",
                    "settled_at": "2026-07-09T02:05:00Z",
                    "horizon_minutes": 60,
                },
            }
        }
    }
    correct = [
        {"event_id": "event-1", "outcome_id": "outcome-1"},
        {"event_id": "event-2", "outcome_id": "outcome-2"},
    ]
    permuted = [
        {"event_id": "event-1", "outcome_id": "outcome-2"},
        {"event_id": "event-2", "outcome_id": "outcome-1"},
    ]

    violations = _event_outcome_pair_violations(
        selection_manifest=selection,
        tournament_rows=tournament_rows,
        signal_rows=permuted,
        backtest={"results": correct},
        stress={"results": correct},
    )

    assert "SIGNAL_ROWS_EVENT_OUTCOME_PAIR_MISMATCH" in violations


def test_cli_blocks_non_utc_execution_window_timestamp(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    selection = json.loads(paths["selection"].read_text(encoding="utf-8"))
    selection["execution_windows"][0]["entry_at"] = "garbage"
    paths["selection"].write_text(json.dumps(selection), encoding="utf-8")

    out = tmp_path / "out-invalid-window-timestamp"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert "SELECTION_MANIFEST_STRUCTURE_INVALID" in packet["reason_codes"]


def test_cli_blocks_execution_window_chronology_violation(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    selection = json.loads(paths["selection"].read_text(encoding="utf-8"))
    selection["execution_windows"][0]["entry_at"] = "2026-07-08T23:55:00Z"
    paths["selection"].write_text(json.dumps(selection), encoding="utf-8")

    out = tmp_path / "out-window-chronology"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert "SELECTION_MANIFEST_EXECUTION_WINDOW_CHRONOLOGY_INVALID" in packet["reason_codes"]


def test_cli_blocks_execution_window_horizon_disagreement(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    selection = json.loads(paths["selection"].read_text(encoding="utf-8"))
    selection["execution_windows"][0]["settled_at"] = "2026-07-09T01:00:00Z"
    paths["selection"].write_text(json.dumps(selection), encoding="utf-8")

    out = tmp_path / "out-window-horizon"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert "SELECTION_MANIFEST_EXECUTION_WINDOW_HORIZON_MISMATCH" in packet["reason_codes"]


def test_cli_blocks_signal_entry_window_disagreement(tmp_path: Path) -> None:
    paths = _write_ready_cli_inputs(tmp_path)
    signal = json.loads(paths["signal"].read_text(encoding="utf-8"))
    signal["entry_at"] = "2026-07-09T00:10:00Z"
    paths["signal"].write_text(json.dumps(signal) + "\n", encoding="utf-8")

    out = tmp_path / "out-signal-window-mismatch"
    result = runner.invoke(app, _packet_cli_args(paths, out))

    assert result.exit_code == 0, result.stdout
    packet = json.loads((out / "human_review_packet.json").read_text(encoding="utf-8"))
    assert "SIGNAL_ROWS_EXECUTION_WINDOWS_MISMATCH" in packet["reason_codes"]
