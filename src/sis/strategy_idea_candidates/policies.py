from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sis.strategy_idea_candidates.models import CandidateSetStatus, StrategyIdeaCandidateSet


@dataclass(frozen=True)
class StrategyIdeaCandidatePolicyValidationResult:
    candidate_set_id: str
    passed: bool
    failures: list[str]


def validate_split_and_leakage_policy(
    candidate_set: StrategyIdeaCandidateSet,
) -> StrategyIdeaCandidatePolicyValidationResult:
    failures: list[str] = []
    split = candidate_set.split_policy
    leakage = candidate_set.leakage_policy

    if candidate_set.candidate_set_status is not CandidateSetStatus.BUILT:
        failures.append("policy validation requires BUILT candidate_set_status")

    if _after(split.train_window.end, split.validation_window.start):
        failures.append("train_window.end must be before or equal to validation_window.start")

    if split.sealed_test_window is not None:
        if not _before(split.validation_window.end, split.sealed_test_window.start):
            failures.append("validation_window.end must be before sealed_test_window.start")
        for candidate in candidate_set.candidate_inventory:
            if not _before(candidate.label_window.end, split.sealed_test_window.start):
                failures.append(
                    f"{candidate.idea_candidate_id}: label_window.end must be before "
                    "sealed_test_window.start"
                )
            if not _before(
                candidate.feature_observation_window.end,
                split.sealed_test_window.start,
            ):
                failures.append(
                    f"{candidate.idea_candidate_id}: feature_observation_window.end must be "
                    "before sealed_test_window.start"
                )

    if split.uses_sealed_test_for_selection:
        failures.append("split_policy.uses_sealed_test_for_selection must be false")
    if leakage.uses_sealed_test_for_selection:
        failures.append("leakage_policy.uses_sealed_test_for_selection must be false")

    if leakage.purge_policy.startswith("not_evaluated"):
        failures.append("purge_policy must be recorded for BUILT candidate sets")
    if leakage.embargo_policy.startswith("not_evaluated"):
        failures.append("embargo_policy must be recorded for BUILT candidate sets")

    for source in candidate_set.source_artifacts:
        if source.max_observed_timestamp is None:
            failures.append(f"{source.source_id}: max_observed_timestamp is required")
        elif _after(source.max_observed_timestamp, source.available_at):
            failures.append(
                f"{source.source_id}: max_observed_timestamp must not be after available_at"
            )

    for candidate in candidate_set.candidate_inventory:
        if candidate.leakage_checks.get("uses_sealed_test_for_selection") is not False:
            failures.append(
                f"{candidate.idea_candidate_id}: leakage_checks must keep sealed test unused"
            )
        if _after(candidate.feature_observation_window.end, candidate.label_window.end):
            failures.append(
                f"{candidate.idea_candidate_id}: feature_observation_window.end must not be "
                "after label_window.end"
            )

    return StrategyIdeaCandidatePolicyValidationResult(
        candidate_set_id=candidate_set.candidate_set_id,
        passed=not failures,
        failures=failures,
    )


def _before(left: datetime, right: datetime) -> bool:
    return _utc(left) < _utc(right)


def _after(left: datetime, right: datetime) -> bool:
    return _utc(left) > _utc(right)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
