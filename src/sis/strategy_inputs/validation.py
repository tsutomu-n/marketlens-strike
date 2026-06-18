from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import ValidationError

from sis.backtest.artifact_io import sha256_file
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import (
    IdeaIntakeDecision,
    InputContractRef,
    InputValidationStatus,
    InputValidationSummary,
    ProducerInfo,
    SourceValidationResult,
    SourceValidationStatus,
    SourceValidationExpectations,
    StrategyIdea,
    StrategyInputBoundary,
    StrategyInputContract,
    StrategyInputContractValidation,
    StrategyIntakeDecision,
    IntakeDecisionSummary,
)
from sis.strategy_inputs.rendering import (
    render_input_contract_validation_markdown,
    render_strategy_intake_decision_markdown,
)
from sis.strategy_review.provenance import boundary_true_paths


@dataclass(frozen=True)
class InputContractValidationResult:
    validation: StrategyInputContractValidation
    validation_path: Path
    report_path: Path


@dataclass(frozen=True)
class StrategyIntakeValidationResult:
    decision: StrategyIntakeDecision
    decision_path: Path
    report_path: Path


class StrategyInputValidationError(ValueError):
    pass


class StrategyInputOutputExistsError(StrategyInputValidationError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _contract_id_from_payload(payload: dict[str, Any]) -> str:
    value = payload.get("contract_id")
    return value if isinstance(value, str) and value else "unknown"


def _idea_id_from_payload(payload: dict[str, Any]) -> str:
    value = payload.get("idea_id")
    return value if isinstance(value, str) and value else "unknown"


def _missing_text(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return not isinstance(value, str) or not value.strip()


def _missing_non_empty_list(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return not isinstance(value, list) or not value


def _missing_mapping(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return not isinstance(value, dict) or not value


def _parse_datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _serialize_observed_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _scan_source_frame(path: Path) -> pl.LazyFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pl.scan_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pl.scan_ndjson(path)
    if suffix == ".parquet":
        return pl.scan_parquet(path)
    raise StrategyInputValidationError(
        f"column validation supports only CSV, JSONL/NDJSON, or Parquet: {path}"
    )


def _source_data_checks(
    *,
    source_path: Path,
    expectations: SourceValidationExpectations | None,
) -> tuple[bool, list[str], bool | None, str | None, bool | None, str | None]:
    if expectations is None:
        return True, [], None, None, None, None
    try:
        frame = _scan_source_frame(source_path)
        columns = set(frame.collect_schema().names())
    except Exception as exc:
        return False, [], None, None, None, f"failed to read source columns: {exc}"

    expected_columns = set(expectations.required_columns)
    if expectations.timestamp_column is not None:
        expected_columns.add(expectations.timestamp_column)
    if expectations.available_at_column is not None:
        expected_columns.add(expectations.available_at_column)

    missing_columns = sorted(column for column in expected_columns if column not in columns)
    available_at_column_present = (
        None
        if expectations.available_at_column is None
        else expectations.available_at_column in columns
    )
    if missing_columns:
        return False, missing_columns, None, None, available_at_column_present, None

    timestamp_check_passed: bool | None = None
    max_observed_timestamp: str | None = None
    if expectations.timestamp_column is not None and expectations.max_allowed_timestamp is not None:
        try:
            result: Any = frame.select(
                pl.col(expectations.timestamp_column).max().alias("max_ts")
            ).collect()
            observed = result["max_ts"][0]
        except Exception as exc:
            return (
                False,
                [],
                None,
                None,
                available_at_column_present,
                (f"failed to read timestamp column: {exc}"),
            )
        max_observed = _parse_datetime_value(observed)
        max_allowed = expectations.max_allowed_timestamp
        if max_allowed.tzinfo is None:
            max_allowed = max_allowed.replace(tzinfo=timezone.utc)
        max_allowed = max_allowed.astimezone(timezone.utc)
        timestamp_check_passed = max_observed is not None and max_observed <= max_allowed
        max_observed_timestamp = _serialize_observed_timestamp(max_observed)
        if max_observed is None:
            return (
                False,
                [],
                False,
                None,
                available_at_column_present,
                ("timestamp column max value is not parseable as datetime"),
            )

    return (
        not missing_columns and (timestamp_check_passed is not False),
        missing_columns,
        timestamp_check_passed,
        max_observed_timestamp,
        available_at_column_present,
        None,
    )


def _write_input_validation_outputs(
    *,
    out_dir: Path,
    validation: StrategyInputContractValidation,
    replace_existing: bool,
) -> InputContractValidationResult:
    validation_path = out_dir / "strategy_input_contract_validation.json"
    report_path = out_dir / "strategy_input_contract_validation.md"
    if not replace_existing and (validation_path.exists() or report_path.exists()):
        raise StrategyInputOutputExistsError(f"output already exists: {out_dir}")
    write_json_artifact(validation_path, validation.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_input_contract_validation_markdown(validation))
    return InputContractValidationResult(
        validation=validation,
        validation_path=validation_path,
        report_path=report_path,
    )


def validate_strategy_input_contract(
    *,
    contract_path: Path,
    out_dir: Path,
    strict: bool = False,
    replace_existing: bool = False,
    validated_at: datetime | None = None,
) -> InputContractValidationResult:
    payload = read_mapping_file(contract_path)
    boundary_violations = boundary_true_paths(payload)
    if boundary_violations:
        contract_id = _contract_id_from_payload(payload)
        validation = StrategyInputContractValidation(
            contract_id=contract_id,
            validated_at=validated_at or _utc_now(),
            producer=ProducerInfo(command="strategy-input-contract-validate"),
            validation_status=InputValidationStatus.BLOCKED_BOUNDARY_VIOLATION,
            strict=strict,
            source_results=[],
            summary=InputValidationSummary(
                missing_required_count=0,
                invalid_required_count=0,
                boundary_violation_count=len(boundary_violations),
                warning_count=0,
            ),
            boundary=StrategyInputBoundary(),
        )
        return _write_input_validation_outputs(
            out_dir=out_dir, validation=validation, replace_existing=replace_existing
        )

    try:
        contract = StrategyInputContract.model_validate(payload)
    except ValidationError as exc:
        raise StrategyInputValidationError(f"invalid input contract: {exc}") from exc

    source_results: list[SourceValidationResult] = []
    missing_required_count = 0
    invalid_required_count = 0
    warning_count = 0
    column_check_failure_count = 0
    timestamp_violation_count = 0
    root = Path.cwd()
    for source in contract.sources:
        source_path = root / source.path
        generated_before_available = source.generated_at <= source.available_at
        if not source_path.exists():
            if source.required:
                missing_required_count += 1
            else:
                warning_count += 1
            source_results.append(
                SourceValidationResult(
                    source_id=source.source_id,
                    status=SourceValidationStatus.MISSING,
                    path=source.path,
                    declared_sha256=source.declared_sha256,
                    hash_matches=None,
                    available_at_present=True,
                    generated_before_available=generated_before_available,
                    required_columns_present=None,
                    missing_columns=[],
                    timestamp_check_passed=None,
                    max_observed_timestamp=None,
                    available_at_column_present=None,
                    error="required source missing"
                    if source.required
                    else "optional source missing",
                )
            )
            continue
        if not source_path.is_file():
            if source.required:
                invalid_required_count += 1
            else:
                warning_count += 1
            source_results.append(
                SourceValidationResult(
                    source_id=source.source_id,
                    status=SourceValidationStatus.INVALID,
                    path=source.path,
                    declared_sha256=source.declared_sha256,
                    hash_matches=False,
                    available_at_present=True,
                    generated_before_available=generated_before_available,
                    required_columns_present=None,
                    missing_columns=[],
                    timestamp_check_passed=None,
                    max_observed_timestamp=None,
                    available_at_column_present=None,
                    error="source path is not a file",
                )
            )
            continue
        actual_sha256 = sha256_file(source_path)
        hash_matches = source.declared_sha256 is None or source.declared_sha256 == actual_sha256
        (
            source_data_valid,
            missing_columns,
            timestamp_check_passed,
            max_observed_timestamp,
            available_at_column_present,
            data_error,
        ) = _source_data_checks(
            source_path=source_path,
            expectations=source.validation_expectations,
        )
        if missing_columns:
            column_check_failure_count += 1
        if timestamp_check_passed is False:
            timestamp_violation_count += 1
        source_valid = hash_matches and source_data_valid
        if not source_valid:
            if source.required:
                invalid_required_count += 1
            else:
                warning_count += 1
        errors = []
        if not hash_matches:
            errors.append("declared_sha256 mismatch")
        if missing_columns:
            if (
                source.validation_expectations is not None
                and source.validation_expectations.available_at_column_required
                and source.validation_expectations.available_at_column in missing_columns
            ):
                errors.append(
                    "AVAILABLE_AT_COLUMN_MISSING: "
                    + str(source.validation_expectations.available_at_column)
                )
            errors.append("MISSING_REQUIRED_COLUMN: " + ", ".join(missing_columns))
        if timestamp_check_passed is False:
            errors.append("FUTURE_DATA_VIOLATION: max source timestamp exceeds allowed timestamp")
        if data_error:
            errors.append(data_error)
        source_results.append(
            SourceValidationResult(
                source_id=source.source_id,
                status=(
                    SourceValidationStatus.PRESENT
                    if source_valid
                    else SourceValidationStatus.INVALID
                ),
                path=source.path,
                actual_sha256=actual_sha256,
                declared_sha256=source.declared_sha256,
                hash_matches=hash_matches,
                available_at_present=True,
                generated_before_available=generated_before_available,
                required_columns_present=not missing_columns
                if source.validation_expectations is not None
                else None,
                missing_columns=missing_columns,
                timestamp_check_passed=timestamp_check_passed,
                max_observed_timestamp=max_observed_timestamp,
                available_at_column_present=available_at_column_present,
                error="; ".join(errors) if errors else None,
            )
        )
        if not generated_before_available:
            warning_count += 1

    status = (
        InputValidationStatus.PASS
        if not missing_required_count and not invalid_required_count
        else InputValidationStatus.NEEDS_FIX
    )
    validation = StrategyInputContractValidation(
        contract_id=contract.contract_id,
        validated_at=validated_at or _utc_now(),
        producer=ProducerInfo(command="strategy-input-contract-validate"),
        validation_status=status,
        strict=strict,
        source_results=source_results,
        summary=InputValidationSummary(
            missing_required_count=missing_required_count,
            invalid_required_count=invalid_required_count,
            boundary_violation_count=0,
            warning_count=warning_count,
            column_check_failure_count=column_check_failure_count,
            timestamp_violation_count=timestamp_violation_count,
        ),
        boundary=StrategyInputBoundary(),
    )
    return _write_input_validation_outputs(
        out_dir=out_dir, validation=validation, replace_existing=replace_existing
    )


def _load_contract_validation_from_path(path: Path) -> StrategyInputContractValidation:
    payload = read_mapping_file(path)
    return StrategyInputContractValidation.model_validate(payload)


def _write_intake_outputs(
    *,
    out_dir: Path,
    decision: StrategyIntakeDecision,
    replace_existing: bool,
) -> StrategyIntakeValidationResult:
    decision_path = out_dir / "strategy_intake_decision.json"
    report_path = out_dir / "strategy_intake_decision.md"
    if not replace_existing and (decision_path.exists() or report_path.exists()):
        raise StrategyInputOutputExistsError(f"output already exists: {out_dir}")
    write_json_artifact(decision_path, decision.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_strategy_intake_decision_markdown(decision))
    return StrategyIntakeValidationResult(
        decision=decision,
        decision_path=decision_path,
        report_path=report_path,
    )


def validate_strategy_intake(
    *,
    idea_path: Path,
    input_contract_validation_paths: list[Path],
    out_dir: Path,
    replace_existing: bool = False,
    decided_at: datetime | None = None,
) -> StrategyIntakeValidationResult:
    payload = read_mapping_file(idea_path)
    boundary_violations = boundary_true_paths(payload)
    missing_hypothesis = _missing_text(payload, "hypothesis")
    missing_baseline = _missing_mapping(payload, "baseline")
    missing_invalidation = _missing_non_empty_list(payload, "invalidation")
    missing_risk = _missing_mapping(payload, "risk")
    missing_required_inputs = _missing_non_empty_list(payload, "required_input_contract_ids")
    if not boundary_violations and (
        missing_hypothesis
        or missing_baseline
        or missing_invalidation
        or missing_risk
        or missing_required_inputs
    ):
        required_actions: list[str] = []
        if missing_hypothesis:
            required_actions.append("Add a non-empty strategy hypothesis.")
        if missing_baseline:
            required_actions.append("Add a baseline strategy or no-trade comparator.")
        if missing_invalidation:
            required_actions.append("Add at least one invalidation condition.")
        if missing_risk:
            required_actions.append("Add max position, max daily loss, and kill conditions.")
        if missing_required_inputs:
            required_actions.append("Attach at least one validated input contract.")

        if missing_required_inputs:
            decision_value = IdeaIntakeDecision.NEEDS_DATA_CHECK
        elif missing_risk:
            decision_value = IdeaIntakeDecision.NEEDS_RISK_SPEC
        else:
            decision_value = IdeaIntakeDecision.NEEDS_SPEC

        decision = StrategyIntakeDecision(
            idea_id=_idea_id_from_payload(payload),
            decided_at=decided_at or _utc_now(),
            producer=ProducerInfo(command="strategy-intake-validate"),
            decision=decision_value,
            required_actions=required_actions,
            input_contract_refs=[],
            summary=IntakeDecisionSummary(
                missing_hypothesis=missing_hypothesis,
                missing_baseline=missing_baseline,
                missing_invalidation=missing_invalidation,
                missing_risk=missing_risk,
                missing_required_inputs=missing_required_inputs,
                boundary_violation_count=0,
            ),
            boundary=StrategyInputBoundary(),
        )
        return _write_intake_outputs(
            out_dir=out_dir, decision=decision, replace_existing=replace_existing
        )
    try:
        idea = StrategyIdea.model_validate(payload)
    except ValidationError as exc:
        if boundary_violations:
            idea_id = _idea_id_from_payload(payload)
            decision = StrategyIntakeDecision(
                idea_id=idea_id,
                decided_at=decided_at or _utc_now(),
                producer=ProducerInfo(command="strategy-intake-validate"),
                decision=IdeaIntakeDecision.REJECT,
                required_actions=["Remove live/write boundary flags from strategy idea."],
                input_contract_refs=[],
                summary=IntakeDecisionSummary(
                    missing_hypothesis=missing_hypothesis,
                    missing_baseline=missing_baseline,
                    missing_invalidation=missing_invalidation,
                    missing_risk=missing_risk,
                    missing_required_inputs=missing_required_inputs,
                    boundary_violation_count=len(boundary_violations),
                ),
                boundary=StrategyInputBoundary(),
            )
            return _write_intake_outputs(
                out_dir=out_dir, decision=decision, replace_existing=replace_existing
            )
        raise StrategyInputValidationError(f"invalid strategy idea: {exc}") from exc

    refs: list[InputContractRef] = []
    validation_by_id: dict[str, StrategyInputContractValidation] = {}
    for path in input_contract_validation_paths:
        validation = _load_contract_validation_from_path(path)
        validation_by_id[validation.contract_id] = validation
        refs.append(
            InputContractRef(
                contract_id=validation.contract_id,
                validation_status=validation.validation_status,
            )
        )

    missing_contract_ids = [
        contract_id
        for contract_id in idea.required_input_contract_ids
        if contract_id not in validation_by_id
    ]
    non_pass_contracts = [
        validation.contract_id
        for validation in validation_by_id.values()
        if validation.validation_status is not InputValidationStatus.PASS
    ]

    required_actions: list[str] = []
    decision_value = IdeaIntakeDecision.READY_FOR_AUTHORING_DRAFT
    if missing_contract_ids:
        decision_value = IdeaIntakeDecision.NEEDS_DATA_CHECK
        required_actions.append(
            "Add input contract validation for: " + ", ".join(missing_contract_ids)
        )
    if non_pass_contracts:
        decision_value = IdeaIntakeDecision.NEEDS_DATA_CHECK
        required_actions.append(
            "Fix input contract validation for: " + ", ".join(non_pass_contracts)
        )

    summary = IntakeDecisionSummary(
        missing_hypothesis=False,
        missing_baseline=False,
        missing_invalidation=False,
        missing_risk=False,
        missing_required_inputs=bool(missing_contract_ids),
        boundary_violation_count=0,
    )
    decision = StrategyIntakeDecision(
        idea_id=idea.idea_id,
        decided_at=decided_at or _utc_now(),
        producer=ProducerInfo(command="strategy-intake-validate"),
        decision=decision_value,
        required_actions=required_actions,
        input_contract_refs=refs,
        summary=summary,
        boundary=StrategyInputBoundary(),
    )
    return _write_intake_outputs(
        out_dir=out_dir, decision=decision, replace_existing=replace_existing
    )
