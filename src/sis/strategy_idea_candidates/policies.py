from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sis.strategy_idea_candidates.models import CandidateSetStatus, StrategyIdeaCandidateSet


PERP_REQUIRED_PARAMETER_FIELDS = (
    "side_bias",
    "venue",
    "product_type",
    "margin_mode",
    "margin_coin",
    "leverage",
    "funding_assumption",
    "fee_model_ref",
    "slippage_model_ref",
    "liquidation_buffer_bps",
    "max_position_notional_usd",
    "max_daily_loss_usd",
    "kill_conditions",
)


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


def validate_perp_shortlist_constraints(
    candidate_set: StrategyIdeaCandidateSet,
) -> StrategyIdeaCandidatePolicyValidationResult:
    failures: list[str] = []
    for candidate in candidate_set.candidate_inventory:
        parameter_set = candidate.parameter_set
        is_perp_candidate = candidate.family.startswith("perp_") or (
            parameter_set.get("product_type") == "USDT-FUTURES"
        )
        if not is_perp_candidate or candidate.decision.value != "SHORTLISTED":
            continue
        missing = [
            field
            for field in PERP_REQUIRED_PARAMETER_FIELDS
            if parameter_set.get(field) in (None, "", [])
        ]
        if missing:
            failures.append(
                f"{candidate.idea_candidate_id}: missing perp risk modeling fields "
                + ", ".join(missing)
            )
        if parameter_set.get("venue") != "bitget":
            failures.append(f"{candidate.idea_candidate_id}: venue must be bitget")
        if parameter_set.get("product_type") != "USDT-FUTURES":
            failures.append(f"{candidate.idea_candidate_id}: product_type must be USDT-FUTURES")
        if parameter_set.get("margin_mode") != "isolated":
            failures.append(f"{candidate.idea_candidate_id}: margin_mode must be isolated")
        if parameter_set.get("margin_coin") != "USDT":
            failures.append(f"{candidate.idea_candidate_id}: margin_coin must be USDT")
        leverage = parameter_set.get("leverage")
        if not isinstance(leverage, int | float) or leverage <= 0 or leverage > 3:
            failures.append(f"{candidate.idea_candidate_id}: leverage must be between 1 and 3")
        liquidation_buffer = parameter_set.get("liquidation_buffer_bps")
        if not isinstance(liquidation_buffer, int | float) or liquidation_buffer <= 0:
            failures.append(
                f"{candidate.idea_candidate_id}: liquidation_buffer_bps must be positive"
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
