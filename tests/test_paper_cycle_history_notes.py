from __future__ import annotations

from sis.reports.paper_cycle_history_notes import note_counts, note_value


def test_note_value_returns_first_matching_prefix_value() -> None:
    notes: list[object] = [
        "orders=2",
        "fills=1",
        "orders=3",
        123,
    ]

    assert note_value(notes, "orders=") == "2"
    assert note_value(notes, "fills=") == "1"
    assert note_value(notes, "missing=") is None


def test_note_counts_counts_matching_values_and_ignores_malformed_notes() -> None:
    items: list[dict[str, object]] = [
        {"notes": ["phase_gate_decision=GO", "orders=1"]},
        {"notes": ["phase_gate_decision=NO_GO", "orders=2"]},
        {"notes": ["phase_gate_decision=GO", "orders=3"]},
        {"notes": "phase_gate_decision=IGNORED"},
        {"notes": [123, "other=value"]},
        {},
    ]

    assert note_counts(items, "phase_gate_decision=") == {
        "GO": 2,
        "NO_GO": 1,
    }
    assert note_counts(items, "orders=") == {
        "1": 1,
        "2": 1,
        "3": 1,
    }
    assert note_counts(items, "missing=") == {}
