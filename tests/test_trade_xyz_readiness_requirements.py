from __future__ import annotations

from pathlib import Path

from sis.venues.trade_xyz.readiness_requirements import dict_or_empty
from sis.venues.trade_xyz.readiness_requirements import nonzero_counts
from sis.venues.trade_xyz.readiness_requirements import requirement


def test_requirement_builds_exact_payload_with_evidence_path() -> None:
    assert requirement(
        key="funding_events",
        status="known_gap",
        evidence_path=Path("data/manifests/funding_manifest.json"),
        reason="partial funding",
        details={"row_count": 2},
    ) == {
        "key": "funding_events",
        "status": "known_gap",
        "evidence_path": "data/manifests/funding_manifest.json",
        "reason": "partial funding",
        "details": {"row_count": 2},
    }


def test_requirement_uses_empty_details_and_none_evidence_path() -> None:
    assert requirement(
        key="quote_coverage",
        status="fail",
        evidence_path=None,
    ) == {
        "key": "quote_coverage",
        "status": "fail",
        "evidence_path": None,
        "reason": None,
        "details": {},
    }


def test_dict_or_empty_preserves_mappings_only() -> None:
    payload = {"row_count": 3}

    assert dict_or_empty(payload) is payload
    assert dict_or_empty(None) == {}
    assert dict_or_empty([("row_count", 3)]) == {}


def test_nonzero_counts_converts_positive_counts_and_skips_invalid_values() -> None:
    assert nonzero_counts(
        {
            "valid_int": 3,
            "valid_str": "4",
            "zero": 0,
            "negative": -1,
            "none": None,
            "invalid": "many",
        }
    ) == {
        "valid_int": 3,
        "valid_str": 4,
    }


def test_nonzero_counts_rejects_non_mapping_payload() -> None:
    assert nonzero_counts(None) == {}
    assert nonzero_counts([("valid", 1)]) == {}
