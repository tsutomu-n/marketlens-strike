from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ValidationError
import pytest

from sis.strategy_idea_seeds.common.ids import canonical_hash
from sis.strategy_idea_seeds.common.models import SeedBoundary, SeedProducer
from sis.strategy_idea_seeds.source.probe import probe_source_root
from sis.strategy_idea_seeds.technical.catalog import (
    load_mechanism_pack,
    load_operator_catalog,
)
from sis.strategy_idea_seeds.technical.generator import (
    build_seed_record_id,
    generate_technical_seeds,
)
from sis.strategy_idea_seeds.technical.models import (
    AttemptReasonCode,
    MechanismPack,
    ThresholdDefinition,
)

from .conftest import MECHANISM_PACK, OPERATOR_CATALOG


CREATED_AT = datetime(2026, 7, 16, tzinfo=timezone.utc)
PRODUCER = SeedProducer(
    producer_id="sis.strategy_idea_seeds.technical",
    version="1.0.0",
)


def _generate(fixture_source_root, mechanism_pack: MechanismPack):
    return generate_technical_seeds(
        mechanism_pack=mechanism_pack,
        operator_catalog=load_operator_catalog(OPERATOR_CATALOG),
        source_snapshot=probe_source_root(fixture_source_root),
        producer=PRODUCER,
        created_at=CREATED_AT,
        config_hash=canonical_hash({"test": "config"}),
    )


def test_boundary_true_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SeedBoundary(live_allowed=True)


def test_title_is_not_part_of_seed_record_id() -> None:
    identity = {
        "producer": PRODUCER,
        "mechanism_template_id": "funding-crowding-v1",
        "technical_payload_hash": "sha256:" + "a" * 64,
        "parent_seed_ids": [],
    }

    first = build_seed_record_id(**identity)
    title = "Completely different display title"
    second = build_seed_record_id(**identity)

    assert title
    assert first == second


def test_axis_order_does_not_change_seed_set(fixture_source_root) -> None:
    pack = load_mechanism_pack(MECHANISM_PACK)
    reordered = pack.model_copy(deep=True)
    reordered.mechanisms.reverse()
    for mechanism in reordered.mechanisms:
        mechanism.directions.reverse()
        mechanism.captures.reverse()
        mechanism.horizons.reverse()
        mechanism.required_source_bundles.reverse()

    _, first_payloads, first_seeds = _generate(fixture_source_root, pack)
    _, second_payloads, second_seeds = _generate(fixture_source_root, reordered)

    assert {seed.seed_record_id for seed in first_seeds} == {
        seed.seed_record_id for seed in second_seeds
    }
    assert {payload.payload_hash for payload in first_payloads} == {
        payload.payload_hash for payload in second_payloads
    }


@pytest.mark.parametrize(
    ("threshold", "reason"),
    [
        (
            ThresholdDefinition(value="not-a-number", value_type="number", unit="ratio"),
            AttemptReasonCode.INVALID_TYPE,
        ),
        (
            ThresholdDefinition(value="0.5", value_type="number", unit="usd"),
            AttemptReasonCode.INVALID_UNIT,
        ),
    ],
)
def test_invalid_type_or_unit_remains_attempt_only(
    fixture_source_root,
    threshold: ThresholdDefinition,
    reason: AttemptReasonCode,
) -> None:
    pack = load_mechanism_pack(MECHANISM_PACK)
    mechanism = pack.mechanisms[0].model_copy(deep=True)
    mechanism.thresholds = [threshold]
    invalid_pack = MechanismPack(
        schema_version="strategy_idea_seed_mechanism_pack.v1",
        mechanisms=[mechanism],
    )

    attempts, payloads, seeds = _generate(fixture_source_root, invalid_pack)

    assert attempts
    assert all(reason in attempt.reason_codes for attempt in attempts)
    assert not payloads
    assert not seeds


def test_duplicate_attempt_is_retained_in_ledger(fixture_source_root) -> None:
    pack = load_mechanism_pack(MECHANISM_PACK)
    mechanism = pack.mechanisms[0].model_copy(deep=True)
    mechanism.directions = ["LONG", "LONG"]
    duplicate_pack = MechanismPack(
        schema_version="strategy_idea_seed_mechanism_pack.v1",
        mechanisms=[mechanism],
    )

    attempts, _, seeds = _generate(fixture_source_root, duplicate_pack)

    duplicate_attempts = [
        attempt
        for attempt in attempts
        if AttemptReasonCode.DUPLICATE_EXACT_ATTEMPT in attempt.reason_codes
    ]
    assert duplicate_attempts
    assert all(attempt.duplicate_of_attempt_id for attempt in duplicate_attempts)
    assert len(seeds) * 2 == len(attempts)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("directions", [None], AttemptReasonCode.MISSING_DIRECTION),
        ("horizons", [None], AttemptReasonCode.MISSING_HORIZON),
        ("observable_proxies", [], AttemptReasonCode.MISSING_OBSERVABLE_PROXY),
        ("required_source_bundles", [[]], AttemptReasonCode.MISSING_SOURCE_REQUIREMENT),
    ],
)
def test_minimum_seed_contract_failures_remain_attempt_only(
    fixture_source_root,
    field: str,
    value,
    reason: AttemptReasonCode,
) -> None:
    pack = load_mechanism_pack(MECHANISM_PACK)
    mechanism = pack.mechanisms[0].model_copy(deep=True)
    setattr(mechanism, field, value)
    invalid_pack = MechanismPack(
        schema_version="strategy_idea_seed_mechanism_pack.v1",
        mechanisms=[mechanism],
    )

    attempts, payloads, seeds = _generate(fixture_source_root, invalid_pack)

    assert attempts
    assert all(reason in attempt.reason_codes for attempt in attempts)
    assert not payloads
    assert not seeds


def test_attempt_budget_records_pruned_attempts_and_materializes_only_budget(
    fixture_source_root,
) -> None:
    pack = load_mechanism_pack(MECHANISM_PACK)
    budgeted = pack.model_copy(deep=True)
    budgeted.attempt_budget = 3

    attempts, payloads, seeds = _generate(fixture_source_root, budgeted)

    assert len(attempts) == 16
    assert len(payloads) == len(seeds) == 3
    assert all(AttemptReasonCode.PRUNED_BUDGET in attempt.reason_codes for attempt in attempts[3:])
