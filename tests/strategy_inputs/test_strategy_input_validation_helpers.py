from __future__ import annotations

from datetime import datetime, timezone

from sis.strategy_inputs.validation_helpers import contract_id_from_payload
from sis.strategy_inputs.validation_helpers import idea_id_from_payload
from sis.strategy_inputs.validation_helpers import missing_mapping
from sis.strategy_inputs.validation_helpers import missing_non_empty_list
from sis.strategy_inputs.validation_helpers import missing_text
from sis.strategy_inputs.validation_helpers import parse_datetime_value
from sis.strategy_inputs.validation_helpers import serialize_observed_timestamp


def test_payload_id_helpers_return_known_ids_or_unknown() -> None:
    assert contract_id_from_payload({"contract_id": "contract-1"}) == "contract-1"
    assert contract_id_from_payload({"contract_id": ""}) == "unknown"
    assert idea_id_from_payload({"idea_id": "idea-1"}) == "idea-1"
    assert idea_id_from_payload({"idea_id": 123}) == "unknown"


def test_missing_helpers_classify_empty_values() -> None:
    assert missing_text({"hypothesis": " breakout "}, "hypothesis") is False
    assert missing_text({"hypothesis": " "}, "hypothesis") is True
    assert missing_text({"hypothesis": ["not text"]}, "hypothesis") is True

    assert missing_non_empty_list({"items": ["x"]}, "items") is False
    assert missing_non_empty_list({"items": []}, "items") is True
    assert missing_non_empty_list({"items": "x"}, "items") is True

    assert missing_mapping({"risk": {"max_loss": 1}}, "risk") is False
    assert missing_mapping({"risk": {}}, "risk") is True
    assert missing_mapping({"risk": []}, "risk") is True


def test_parse_datetime_value_normalizes_supported_inputs() -> None:
    assert parse_datetime_value("2026-06-18T12:00:00Z") == datetime(
        2026, 6, 18, 12, 0, tzinfo=timezone.utc
    )
    assert parse_datetime_value("2026-06-18T21:00:00+09:00") == datetime(
        2026, 6, 18, 12, 0, tzinfo=timezone.utc
    )
    assert parse_datetime_value(datetime(2026, 6, 18, 12, 0)) == datetime(
        2026, 6, 18, 12, 0, tzinfo=timezone.utc
    )
    assert parse_datetime_value("") is None
    assert parse_datetime_value("not-a-date") is None
    assert parse_datetime_value(123) is None


def test_serialize_observed_timestamp_uses_zulu_without_microseconds() -> None:
    value = datetime(2026, 6, 18, 12, 0, 1, 123456, tzinfo=timezone.utc)

    assert serialize_observed_timestamp(value) == "2026-06-18T12:00:01Z"
    assert serialize_observed_timestamp(None) is None
