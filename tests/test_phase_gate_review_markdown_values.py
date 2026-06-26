from sis.reports.phase_gate_review_markdown_values import (
    as_dict_list,
    as_list_mapping,
    as_mapping,
    as_str_dict,
    as_str_list,
    classification_counts,
)


def test_classification_counts_returns_mapping_or_empty() -> None:
    assert classification_counts({"execution_drift_classification_counts": {"P2_BLOCKER": 2}}) == {
        "P2_BLOCKER": 2,
    }
    assert classification_counts({"execution_drift_classification_counts": []}) == {}


def test_as_str_list_filters_to_strings() -> None:
    assert as_str_list(["alpha", 1, "beta", None]) == ["alpha", "beta"]
    assert as_str_list(("alpha", "beta")) == []


def test_as_dict_list_filters_to_dicts() -> None:
    assert as_dict_list([{"a": 1}, "skip", {"b": 2}, []]) == [{"a": 1}, {"b": 2}]
    assert as_dict_list({"a": 1}) == []


def test_as_mapping_returns_dict_or_empty() -> None:
    value = {"a": 1}
    assert as_mapping(value) == value
    assert as_mapping([("a", 1)]) == {}


def test_as_str_dict_stringifies_keys_and_keeps_string_values() -> None:
    assert as_str_dict({"a": "alpha", 2: "beta", "skip": 3}) == {
        "a": "alpha",
        "2": "beta",
    }
    assert as_str_dict([("a", "alpha")]) == {}


def test_as_list_mapping_filters_nested_lists_to_strings() -> None:
    assert as_list_mapping({"a": ["alpha", 1], 2: ["beta"], "empty": "skip"}) == {
        "a": ["alpha"],
        "2": ["beta"],
        "empty": [],
    }
    assert as_list_mapping(["alpha"]) == {}
