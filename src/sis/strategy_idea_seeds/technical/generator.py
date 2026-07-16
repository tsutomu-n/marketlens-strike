from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from itertools import product
from typing import Any

from sis.strategy_idea_seeds.common.ids import canonical_hash, stable_id
from sis.strategy_idea_seeds.common.models import (
    CaptureArchetype,
    DataReadiness,
    Direction,
    ProfitIntent,
    RequiredSource,
    SeedLineage,
    SeedPayloadReference,
    SeedProducer,
    SourceLane,
    StrategyIdeaSeed,
)
from sis.strategy_idea_seeds.source.models import (
    SourceCapability,
    SourceCapabilityClass,
    SourceCapabilitySnapshot,
)
from sis.strategy_idea_seeds.technical.models import (
    AttemptReasonCode,
    GenerationAttempt,
    MechanismPack,
    MechanismTemplate,
    OperatorCatalog,
    OperatorDefinition,
    TechnicalPayload,
    ThresholdDefinition,
)


def generate_technical_seeds(
    *,
    mechanism_pack: MechanismPack,
    operator_catalog: OperatorCatalog,
    source_snapshot: SourceCapabilitySnapshot,
    producer: SeedProducer,
    created_at: datetime,
    config_hash: str,
) -> tuple[list[GenerationAttempt], list[TechnicalPayload], list[StrategyIdeaSeed]]:
    operators = {item.operator_id: item for item in operator_catalog.operators}
    capabilities = {item.source_key: item for item in source_snapshot.capabilities}
    raw_attempts: list[dict[str, Any]] = []
    for mechanism in sorted(mechanism_pack.mechanisms, key=lambda item: item.mechanism_template_id):
        raw_attempts.extend(_expand_mechanism(mechanism))

    attempts: list[GenerationAttempt] = []
    payloads: list[TechnicalPayload] = []
    seeds: list[StrategyIdeaSeed] = []
    first_attempt_by_signature: dict[str, str] = {}
    duplicate_ordinals: Counter[str] = Counter()
    for attempt_index, draft in enumerate(raw_attempts):
        mechanism = draft["mechanism"]
        reasons, direction, capture = _validate_draft(draft, operators)
        payload = _payload_for(
            draft=draft,
            mechanism=mechanism,
            source_snapshot=source_snapshot,
        )
        signature = payload.technical_exact_signature if payload is not None else None
        if (
            mechanism_pack.attempt_budget is not None
            and attempt_index >= mechanism_pack.attempt_budget
        ):
            reasons = [AttemptReasonCode.PRUNED_BUDGET]
        duplicate_of: str | None = None
        if not reasons and signature is not None and signature in first_attempt_by_signature:
            reasons = [AttemptReasonCode.DUPLICATE_EXACT_ATTEMPT]
            duplicate_of = first_attempt_by_signature[signature]
        duplicate_key = signature or canonical_hash(draft["identity"])
        ordinal = duplicate_ordinals[duplicate_key]
        duplicate_ordinals[duplicate_key] += 1
        attempt_id = stable_id(
            "technical-attempt",
            {"identity": draft["identity"], "duplicate_ordinal": ordinal},
        )
        if not reasons and signature is not None:
            first_attempt_by_signature[signature] = attempt_id
            assert payload is not None
            required_sources = _required_sources(draft["required_sources"], capabilities)
            seed = _materialize_seed(
                mechanism=mechanism,
                direction=direction,
                capture=capture,
                horizon=draft["horizon"],
                required_sources=required_sources,
                payload=payload,
                producer=producer,
                created_at=created_at,
                config_hash=config_hash,
                source_snapshot=source_snapshot,
            )
            payloads.append(payload)
            seeds.append(seed)
            reasons = [AttemptReasonCode.SEED_MATERIALIZED]
            materialized_seed_id = seed.seed_record_id
        else:
            materialized_seed_id = None
        attempts.append(
            GenerationAttempt(
                attempt_id=attempt_id,
                attempt_index=attempt_index,
                mechanism_template_id=mechanism.mechanism_template_id,
                direction=direction,
                capture_archetype=capture,
                horizon=draft["horizon"],
                required_sources=draft["required_sources"],
                observable_proxies=mechanism.observable_proxies,
                candidate_payload=(
                    payload.model_dump(mode="json", exclude_none=True)
                    if payload is not None
                    else draft["candidate_payload"]
                ),
                technical_exact_signature=signature,
                reason_codes=reasons,
                materialized_seed_id=materialized_seed_id,
                duplicate_of_attempt_id=duplicate_of,
            )
        )
    seeds.sort(key=lambda item: item.seed_record_id)
    payloads.sort(key=lambda item: item.payload_record_id)
    return attempts, payloads, seeds


def _expand_mechanism(mechanism: MechanismTemplate) -> list[dict[str, Any]]:
    axes = product(
        sorted(mechanism.directions, key=lambda value: "" if value is None else value),
        sorted(mechanism.captures, key=lambda value: "" if value is None else value),
        sorted(mechanism.horizons, key=lambda value: "" if value is None else value),
        sorted(mechanism.lookbacks),
        sorted(
            mechanism.thresholds,
            key=lambda item: (str(item.value), item.value_type, item.unit),
        ),
        sorted(mechanism.required_source_bundles, key=lambda value: tuple(sorted(value))),
    )
    drafts: list[dict[str, Any]] = []
    for direction, capture, horizon, lookback, threshold, source_bundle in axes:
        ast = _build_ast(mechanism, threshold)
        identity = {
            "mechanism_template_id": mechanism.mechanism_template_id,
            "direction": direction,
            "capture": capture,
            "horizon": horizon,
            "lookback": lookback,
            "threshold": threshold.model_dump(mode="json"),
            "required_sources": sorted(source_bundle),
            "operator_ast": ast,
        }
        drafts.append(
            {
                "mechanism": mechanism,
                "direction": direction,
                "capture": capture,
                "horizon": horizon,
                "lookback": lookback,
                "threshold": threshold,
                "required_sources": sorted(source_bundle),
                "operator_ast": ast,
                "candidate_payload": identity,
                "identity": identity,
            }
        )
    return drafts


def _build_ast(mechanism: MechanismTemplate, threshold: ThresholdDefinition) -> dict[str, Any]:
    return {
        "kind": "operator",
        "operator": mechanism.comparison_operator,
        "output_type": "boolean",
        "unit": "boolean",
        "args": [
            {
                "kind": "field",
                "field": mechanism.primary_field,
                "value_type": mechanism.primary_field_type,
                "unit": mechanism.primary_field_unit,
            },
            {
                "kind": "literal",
                "value": threshold.value,
                "value_type": threshold.value_type,
                "unit": threshold.unit,
            },
        ],
    }


def _validate_draft(
    draft: dict[str, Any], operators: dict[str, OperatorDefinition]
) -> tuple[list[AttemptReasonCode], Direction | None, CaptureArchetype | None]:
    reasons: list[AttemptReasonCode] = []
    direction = _enum_or_none(Direction, draft["direction"])
    capture = _enum_or_none(CaptureArchetype, draft["capture"])
    if direction is None:
        reasons.append(AttemptReasonCode.MISSING_DIRECTION)
    if not draft["horizon"]:
        reasons.append(AttemptReasonCode.MISSING_HORIZON)
    if not draft["mechanism"].observable_proxies:
        reasons.append(AttemptReasonCode.MISSING_OBSERVABLE_PROXY)
    if not draft["required_sources"]:
        reasons.append(AttemptReasonCode.MISSING_SOURCE_REQUIREMENT)
    ast_reasons = _validate_ast(draft["operator_ast"], operators)
    reasons.extend(reason for reason in ast_reasons if reason not in reasons)
    return reasons, direction, capture


def _validate_ast(
    ast: dict[str, Any], operators: dict[str, OperatorDefinition]
) -> list[AttemptReasonCode]:
    operator = operators.get(str(ast.get("operator", "")))
    args = ast.get("args")
    if operator is None or not isinstance(args, list) or len(args) != operator.arity:
        return [AttemptReasonCode.INVALID_AST]
    input_types = [str(arg.get("value_type", "")) for arg in args if isinstance(arg, dict)]
    if len(input_types) != len(args) or input_types != operator.input_types:
        return [AttemptReasonCode.INVALID_TYPE]
    literal = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
    if literal.get("value_type") == "number":
        try:
            Decimal(str(literal.get("value")))
        except (InvalidOperation, ValueError):
            return [AttemptReasonCode.INVALID_TYPE]
    if operator.unit_policy == "same":
        units = [str(arg.get("unit", "")) for arg in args if isinstance(arg, dict)]
        if len(set(units)) != 1:
            return [AttemptReasonCode.INVALID_UNIT]
    if ast.get("output_type") != operator.output_type or ast.get("unit") != "boolean":
        return [AttemptReasonCode.INVALID_TYPE]
    return []


def _payload_for(
    *,
    draft: dict[str, Any],
    mechanism: MechanismTemplate,
    source_snapshot: SourceCapabilitySnapshot,
) -> TechnicalPayload:
    core = {
        "mechanism_template_id": mechanism.mechanism_template_id,
        "mechanism_status": "HYPOTHESIZED_NOT_CAUSALLY_VERIFIED",
        "operator_ast": draft["operator_ast"],
        "generation_axes": {
            "direction": str(draft["direction"] or ""),
            "capture_archetype": str(draft["capture"] or ""),
            "horizon": str(draft["horizon"] or ""),
            "required_source_bundle": "+".join(draft["required_sources"]),
        },
        "parameter_values": {
            "lookback_bars": draft["lookback"],
            "threshold": str(draft["threshold"].value),
            "threshold_unit": draft["threshold"].unit,
        },
        "technical_semantic_descriptor": {
            "mechanism_class": mechanism.mechanism_class,
            "capture_archetype": str(draft["capture"] or ""),
            "direction": str(draft["direction"] or ""),
            "horizon": str(draft["horizon"] or ""),
            "required_source_bundle": "+".join(draft["required_sources"]),
        },
        "source_capability_snapshot_ref": source_snapshot.source_root_hash,
        "authoring_compatibility": "NOT_CONNECTED_METADATA_ONLY",
    }
    exact_signature = canonical_hash(core)
    payload_record_id = stable_id("technical-payload", core)
    payload_hash = canonical_hash(
        {
            **core,
            "payload_record_id": payload_record_id,
            "technical_exact_signature": exact_signature,
        }
    )
    return TechnicalPayload(
        payload_record_id=payload_record_id,
        mechanism_template_id=mechanism.mechanism_template_id,
        mechanism_status="HYPOTHESIZED_NOT_CAUSALLY_VERIFIED",
        operator_ast=draft["operator_ast"],
        generation_axes=core["generation_axes"],
        parameter_values=core["parameter_values"],
        technical_exact_signature=exact_signature,
        technical_semantic_descriptor=core["technical_semantic_descriptor"],
        source_capability_snapshot_ref=source_snapshot.source_root_hash,
        authoring_compatibility="NOT_CONNECTED_METADATA_ONLY",
        payload_hash=payload_hash,
    )


def _required_sources(
    source_keys: list[str], capabilities: dict[str, SourceCapability]
) -> list[RequiredSource]:
    results: list[RequiredSource] = []
    for source_key in source_keys:
        capability = capabilities[source_key]
        available = capability.capability is SourceCapabilityClass.HISTORICAL
        results.append(
            RequiredSource(
                source_key=source_key,
                capability=capability.capability,
                requirement_status="AVAILABLE" if available else "DATA_REQUIRED",
                reason_codes=[] if available else capability.reason_codes,
            )
        )
    return results


def _materialize_seed(
    *,
    mechanism: MechanismTemplate,
    direction: Direction | None,
    capture: CaptureArchetype | None,
    horizon: str | None,
    required_sources: list[RequiredSource],
    payload: TechnicalPayload,
    producer: SeedProducer,
    created_at: datetime,
    config_hash: str,
    source_snapshot: SourceCapabilitySnapshot,
) -> StrategyIdeaSeed:
    assert direction is not None
    assert capture is not None
    assert horizon is not None
    data_required = any(item.requirement_status == "DATA_REQUIRED" for item in required_sources)
    readiness = DataReadiness.DATA_REQUIRED if data_required else DataReadiness.HISTORICAL_SOURCE
    known_gaps = sorted(
        {
            code
            for source in required_sources
            for code in (
                (["DATA_REQUIRED", *source.reason_codes])
                if source.requirement_status == "DATA_REQUIRED"
                else []
            )
        }
    )
    seed_record_id = build_seed_record_id(
        producer=producer,
        mechanism_template_id=mechanism.mechanism_template_id,
        technical_payload_hash=payload.payload_hash,
        parent_seed_ids=[],
    )
    provenance_signature = canonical_hash(
        {
            "producer": producer.model_dump(mode="json"),
            "config_hash": config_hash,
            "source_capability_snapshot_hash": source_snapshot.source_root_hash,
            "parent_ids": [],
            "payload_hash": payload.payload_hash,
        }
    )
    direction_text = direction.value.title()
    capture_text = capture.value.title()
    title = f"{mechanism.mechanism_class} — {direction_text} {capture_text} ({horizon})"
    hypothesis = (
        f"When {mechanism.primary_field} satisfies the configured operator over "
        f"{payload.parameter_values['lookback_bars']} bars, a {direction.value.lower()} "
        f"{capture.value.lower()} path may persist over {horizon}; this is unverified."
    )
    return StrategyIdeaSeed(
        seed_record_id=seed_record_id,
        created_at=created_at,
        producer=producer,
        data_readiness=readiness,
        title=title,
        hypothesis=hypothesis,
        profit_intent=ProfitIntent(
            mechanism_class=mechanism.mechanism_class,
            capture_archetype=capture,
            path_archetype=(
                "DIRECTIONAL_CONTINUATION"
                if capture is CaptureArchetype.CONTINUATION
                else "FAILED_MOVE_REVERSAL"
            ),
            direction_hint=direction,
            horizon_hint=horizon,
            affected_actor_or_constraint=mechanism.affected_actor_or_constraint,
            observable_proxies=mechanism.observable_proxies,
            hypothesized_persistence=mechanism.hypothesized_persistence,
            alternative_explanations=mechanism.alternative_explanations,
        ),
        required_sources=required_sources,
        known_gaps=known_gaps,
        falsification_question=mechanism.falsification_question,
        next_research_question=mechanism.next_research_question,
        lineage=SeedLineage(),
        payload=SeedPayloadReference(
            sha256=payload.payload_hash,
            record_key=payload.payload_record_id,
        ),
        provenance_signature=provenance_signature,
    )


def build_seed_record_id(
    *,
    producer: SeedProducer,
    mechanism_template_id: str,
    technical_payload_hash: str,
    parent_seed_ids: list[str],
) -> str:
    return stable_id(
        "seed",
        {
            "source_lane": SourceLane.TECHNICAL,
            "producer_id": producer.producer_id,
            "producer_version": producer.version,
            "mechanism_template_id": mechanism_template_id,
            "technical_payload_hash": technical_payload_hash,
            "parent_seed_ids": sorted(parent_seed_ids),
        },
    )


def _enum_or_none(enum_type: type[Any], value: Any) -> Any | None:
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        return None
