from __future__ import annotations

from sis.research.strategy_lifecycle.paper_observation_sessions import (
    count_gap,
    dict_field,
    int_field,
    latest_normal_requirement_gaps,
    latest_session,
    session_decision,
    session_id,
    session_sort_key,
    string_field,
    string_list,
)


def test_session_helpers_sort_latest_and_extract_decision_fields() -> None:
    old = {
        "session_id": "normal-001",
        "created_at": "2026-06-12T21:07:00+00:00",
        "review_decision": "NEEDS_MORE_PAPER_OBSERVATION",
    }
    invalid = {
        "session_id": "normal-000",
        "created_at": "not-a-timestamp",
        "review_decision": "",
    }
    naive = {
        "session_id": "normal-002",
        "created_at": "2026-06-12T21:07:00",
        "review_decision": "PASS_PAPER_OBSERVATION_REVIEW",
    }

    ordered = sorted([old, invalid, naive], key=session_sort_key)

    assert [item["session_id"] for item in ordered] == [
        "normal-000",
        "normal-001",
        "normal-002",
    ]
    assert latest_session(ordered) == naive
    assert latest_session([]) is None
    assert session_decision(naive) == "PASS_PAPER_OBSERVATION_REVIEW"
    assert session_decision(None) == ""
    assert session_id(old) == "normal-001"
    assert session_id(None) == ""


def test_latest_normal_requirement_gaps_counts_missing_and_present_sessions() -> None:
    assert latest_normal_requirement_gaps(None) == {
        "session_id": "",
        "available": False,
        "fills": {"observed": 0, "required": 0, "remaining": 0, "met": False},
        "trading_days": {"observed": 0, "required": 0, "remaining": 0, "met": False},
        "timestamp_quality": {
            "observed": "",
            "required": "complete",
            "met": False,
        },
    }

    gaps = latest_normal_requirement_gaps(
        {
            "session_id": "normal-001",
            "thresholds": {
                "min_fills_for_pass": "20",
                "min_trading_days_for_pass": 10.9,
            },
            "metrics": {
                "fills_count": 3,
                "trading_day_count": "12",
                "timestamp_quality": "complete",
            },
        }
    )

    assert gaps == {
        "session_id": "normal-001",
        "available": True,
        "fills": {"observed": 3, "required": 20, "remaining": 17, "met": False},
        "trading_days": {"observed": 12, "required": 10, "remaining": 0, "met": True},
        "timestamp_quality": {
            "observed": "complete",
            "required": "complete",
            "met": True,
        },
    }


def test_field_coercion_helpers_preserve_existing_edge_cases() -> None:
    payload = {
        "string": 123,
        "strings": [1, "two", None],
        "dict": {"ok": True},
        "int": "7",
        "float": 3.9,
        "negative": -2,
        "bool": True,
        "bad_int": "7.1",
    }

    assert string_field(payload, "string") == "123"
    assert string_field(None, "string") == ""
    assert string_list(payload, "strings") == ["1", "two", "None"]
    assert string_list(payload, "missing") == []
    assert dict_field(payload, "dict") == {"ok": True}
    assert dict_field(payload, "strings") == {}
    assert int_field(payload, "int") == 7
    assert int_field(payload, "float") == 3
    assert int_field(payload, "negative") == 0
    assert int_field(payload, "bool") == 0
    assert int_field(payload, "bad_int") == 0
    assert count_gap(observed=2, required=5) == {
        "observed": 2,
        "required": 5,
        "remaining": 3,
        "met": False,
    }
    assert count_gap(observed=5, required=5)["met"] is True
    assert count_gap(observed=5, required=0)["met"] is False
