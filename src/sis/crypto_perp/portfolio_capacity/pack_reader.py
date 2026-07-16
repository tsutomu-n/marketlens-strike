from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Literal, cast

from sis.crypto_perp.backtest_candidate_pack_models import (
    CryptoPerpBacktestCandidatePackDecision,
)
from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.io import file_artifact_ref, file_sha256
from sis.crypto_perp.models import CryptoPerpProducer, stable_hash
from sis.crypto_perp.portfolio_capacity.models import (
    PortfolioCapacityCase,
    PortfolioCapacityPolicy,
    PortfolioSkippedSignal,
    PortfolioTradeIntent,
    TradeAction,
)
from sis.crypto_perp.tournament_rows import (
    CostAwareTournamentRow,
    CryptoPerpTournamentRowsV2,
)

_REQUIRED_FILES = (
    "decision.json",
    "signal_rows.jsonl",
    "tournament_rows_v2.json",
    "execution_assumptions.json",
)
_HASHED_COMPONENTS = (
    "signal_rows.jsonl",
    "tournament_rows_v2.json",
    "execution_assumptions.json",
)
_REQUIRED_ACTIONS = {"REVERSAL_SHORT", "CONTINUATION_LONG", "NO_TRADE"}
_SELECTED_ACTIONS = _REQUIRED_ACTIONS | {"UNKNOWN"}


@dataclass(frozen=True)
class LoadedCandidatePack:
    root: Path
    decision: CryptoPerpBacktestCandidatePackDecision
    signals: list[dict[str, Any]]
    rows: CryptoPerpTournamentRowsV2
    assumptions: dict[str, Any]
    component_paths: dict[str, Path]


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(payload)
    return rows


def _normalize_sha(value: object) -> str:
    raw = str(value or "").strip().lower()
    return raw.removeprefix("sha256:")


def _component_refs(decision: CryptoPerpBacktestCandidatePackDecision) -> Mapping[str, Any]:
    value = decision.summary.get("pack_component_refs")
    if not isinstance(value, Mapping):
        raise ValueError("PACK_COMPONENT_REFS_MISSING")
    return value


def _validate_component_hashes(
    decision: CryptoPerpBacktestCandidatePackDecision,
    component_paths: Mapping[str, Path],
) -> None:
    refs = _component_refs(decision)
    for name in _HASHED_COMPONENTS:
        path = component_paths[name]
        ref = refs.get(name)
        if not isinstance(ref, Mapping):
            raise ValueError(f"PACK_COMPONENT_REF_MISSING: {name}")
        expected = _normalize_sha(ref.get("sha256"))
        actual = file_sha256(path)
        if not expected or expected != actual:
            raise ValueError(f"PACK_COMPONENT_HASH_MISMATCH: {name}")


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - Decimal error detail varies
        raise ValueError(f"invalid decimal {field_name}: {value}") from exc


def _timestamp(value: object, field_name: str) -> datetime:
    if not isinstance(value, (datetime, str)):
        raise ValueError(f"{field_name} must be an ISO UTC timestamp")
    return ensure_utc_aware(field_name, value)


def _validate_assumptions(
    rows: CryptoPerpTournamentRowsV2,
    assumptions: Mapping[str, Any],
) -> Decimal:
    cost_assumptions = rows.summary.get("cost_assumptions")
    if not isinstance(cost_assumptions, Mapping):
        raise ValueError("TOURNAMENT_COST_ASSUMPTIONS_MISSING")
    comparisons = {
        "position_size_usd": "notional_usd",
        "fee_rate": "fee_rate",
        "funding_rate_assumption": "funding_rate",
        "slippage_bps": "slippage_bps",
    }
    for assumption_name, rows_name in comparisons.items():
        left = _decimal(assumptions.get(assumption_name), assumption_name)
        right = _decimal(cost_assumptions.get(rows_name), rows_name)
        if left != right:
            raise ValueError(f"PACK_ASSUMPTION_MISMATCH: {assumption_name}")
    holding = assumptions.get("max_holding_minutes")
    if isinstance(holding, bool) or not isinstance(holding, int) or holding <= 0:
        raise ValueError("PACK_HOLDING_MINUTES_INVALID")
    return _decimal(cost_assumptions.get("notional_usd"), "notional_usd")


def _validate_signal_rows(
    signals: list[dict[str, Any]],
    rows: CryptoPerpTournamentRowsV2,
    assumptions: Mapping[str, Any],
) -> None:
    signal_by_event: dict[str, dict[str, Any]] = {}
    for signal in signals:
        event_id = str(signal.get("event_id") or "").strip()
        if not event_id:
            raise ValueError("SIGNAL_EVENT_ID_MISSING")
        if event_id in signal_by_event:
            raise ValueError(f"DUPLICATE_SIGNAL_ROW: {event_id}")
        action = str(signal.get("selected_action") or "UNKNOWN")
        if action not in _SELECTED_ACTIONS:
            raise ValueError(f"SIGNAL_ACTION_UNSUPPORTED: {event_id}:{action}")
        if not str(signal.get("outcome_id") or "").strip():
            raise ValueError(f"SIGNAL_OUTCOME_ID_MISSING: {event_id}")
        if not str(signal.get("symbol") or "").strip():
            raise ValueError(f"SIGNAL_SYMBOL_MISSING: {event_id}")
        signal_by_event[event_id] = signal
    if set(signal_by_event) != set(rows.event_set):
        raise ValueError("PACK_EVENT_SET_MISMATCH")

    row_actions: dict[str, set[str]] = {}
    for row in rows.rows:
        row_actions.setdefault(row.event_id, set()).add(row.action)
    for event_id in rows.event_set:
        actions = row_actions.get(event_id, set())
        if actions != _REQUIRED_ACTIONS:
            raise ValueError(f"ACTION_ROW_SET_MISMATCH: {event_id}")
        if sum(1 for row in rows.rows if row.event_id == event_id) != 3:
            raise ValueError(f"DUPLICATE_ACTION_ROW: {event_id}")

    windows = rows.summary.get("execution_windows")
    if not isinstance(windows, Mapping):
        raise ValueError("EXECUTION_WINDOWS_MISSING")
    expected_holding = int(cast(int, assumptions["max_holding_minutes"]))
    for event_id, signal in signal_by_event.items():
        window = windows.get(event_id)
        if not isinstance(window, Mapping):
            raise ValueError(f"EXECUTION_WINDOW_MISSING: {event_id}")
        cutoff = _timestamp(signal.get("information_cutoff_at"), "information_cutoff_at")
        entry = _timestamp(window.get("entry_at"), "entry_at")
        settled = _timestamp(window.get("settled_at"), "settled_at")
        if not cutoff < entry < settled:
            raise ValueError(f"EXECUTION_WINDOW_ORDER_INVALID: {event_id}")
        signal_entry = _timestamp(signal.get("entry_at"), "signal.entry_at")
        if signal_entry != entry:
            raise ValueError(f"SIGNAL_EXECUTION_WINDOW_MISMATCH: {event_id}")
        horizon = window.get("horizon_minutes")
        if isinstance(horizon, bool) or not isinstance(horizon, int):
            raise ValueError(f"EXECUTION_HORIZON_INVALID: {event_id}")
        if horizon != expected_holding:
            raise ValueError(f"EXECUTION_HORIZON_MISMATCH: {event_id}")


def load_candidate_pack(candidate_pack_dir: Path) -> LoadedCandidatePack:
    root = candidate_pack_dir.resolve()
    if not root.is_dir():
        raise ValueError(f"CANDIDATE_PACK_DIR_NOT_FOUND: {candidate_pack_dir}")
    component_paths = {name: root / name for name in _REQUIRED_FILES}
    missing = [name for name, path in component_paths.items() if not path.is_file()]
    if missing:
        raise ValueError("CANDIDATE_PACK_COMPONENTS_MISSING: " + ",".join(missing))

    decision = CryptoPerpBacktestCandidatePackDecision.model_validate(
        _read_json_object(component_paths["decision.json"])
    )
    for name in _REQUIRED_FILES:
        if name not in decision.artifact_paths:
            raise ValueError(f"DECISION_ARTIFACT_PATH_MISSING: {name}")
    _validate_component_hashes(decision, component_paths)

    signals = _read_jsonl_objects(component_paths["signal_rows.jsonl"])
    rows = CryptoPerpTournamentRowsV2.model_validate(
        _read_json_object(component_paths["tournament_rows_v2.json"])
    )
    assumptions = _read_json_object(component_paths["execution_assumptions.json"])
    _validate_assumptions(rows, assumptions)
    _validate_signal_rows(signals, rows, assumptions)

    for row in rows.rows:
        if row.actual_cash_result_usd is not None or row.evidence_level == "actual_cash":
            raise ValueError("UNSUPPORTED_ACTUAL_CASH_INPUT")

    return LoadedCandidatePack(
        root=root,
        decision=decision,
        signals=signals,
        rows=rows,
        assumptions=assumptions,
        component_paths=component_paths,
    )


def _row_map(rows: CryptoPerpTournamentRowsV2) -> dict[tuple[str, str], CostAwareTournamentRow]:
    return {(row.event_id, row.action): row for row in rows.rows}


def _selected_action(signal: Mapping[str, Any], policy: PortfolioCapacityPolicy) -> str:
    if policy.action_policy == "CURRENT_SELECTOR":
        return str(signal.get("selected_action") or "UNKNOWN")
    if policy.action_policy == "ALWAYS_CONTINUATION":
        return "CONTINUATION_LONG"
    if policy.action_policy == "ALWAYS_REVERSAL":
        return "REVERSAL_SHORT"
    return "NO_TRADE"


def _signal_score(signal: Mapping[str, Any]) -> Decimal | None:
    value = signal.get("signal_score")
    return None if value in {None, ""} else _decimal(value, "signal_score")


def _intent_from_row(
    *,
    signal: Mapping[str, Any],
    source_row_index: int,
    row: CostAwareTournamentRow,
    notional_usd: Decimal,
    window: Mapping[str, Any],
) -> PortfolioTradeIntent:
    stress_slippage = (
        row.before_cost_proxy_usd
        - row.fee_estimate_usd
        - row.funding_estimate_usd
        - row.operator_time_cost_usd
        - row.stress_cash_estimate_usd
    )
    if stress_slippage < row.slippage_estimate_usd:
        raise ValueError(f"STRESS_SLIPPAGE_INCONSISTENT: {row.event_id}")
    account_base = (
        row.before_cost_proxy_usd
        - row.fee_estimate_usd
        - row.funding_estimate_usd
        - row.slippage_estimate_usd
    )
    account_stress = (
        row.before_cost_proxy_usd
        - row.fee_estimate_usd
        - row.funding_estimate_usd
        - stress_slippage
    )
    expected_economic_base = account_base - row.operator_time_cost_usd
    if expected_economic_base != row.cost_adjusted_cash_estimate_usd:
        raise ValueError(f"BASE_ECONOMIC_DELTA_MISMATCH: {row.event_id}")
    if account_stress - row.operator_time_cost_usd != row.stress_cash_estimate_usd:
        raise ValueError(f"STRESS_ECONOMIC_DELTA_MISMATCH: {row.event_id}")
    return PortfolioTradeIntent(
        event_id=row.event_id,
        outcome_id=str(signal.get("outcome_id") or ""),
        symbol=str(signal.get("symbol") or ""),
        action=cast(TradeAction, row.action),
        side="LONG" if row.action == "CONTINUATION_LONG" else "SHORT",
        information_cutoff_at=signal.get("information_cutoff_at"),
        entry_at=window.get("entry_at"),
        exit_at=window.get("settled_at"),
        source_row_index=source_row_index,
        signal_score=_signal_score(signal),
        notional_usd=notional_usd,
        before_cost_proxy_usd=row.before_cost_proxy_usd,
        fee_estimate_usd=row.fee_estimate_usd,
        funding_estimate_usd=row.funding_estimate_usd,
        slippage_estimate_usd=row.slippage_estimate_usd,
        operator_time_cost_usd=row.operator_time_cost_usd,
        stress_slippage_estimate_usd=stress_slippage,
        account_delta_base_usd=account_base,
        account_delta_stress_usd=account_stress,
        economic_delta_base_usd=row.cost_adjusted_cash_estimate_usd,
        economic_delta_stress_usd=row.stress_cash_estimate_usd,
        reserve_base_usd=(
            notional_usd
            + row.fee_estimate_usd
            + row.funding_estimate_usd
            + row.slippage_estimate_usd
        ),
        reserve_stress_usd=(
            notional_usd
            + row.fee_estimate_usd
            + row.funding_estimate_usd
            + stress_slippage
        ),
        known_gaps=list(row.known_gaps),
    )


def build_portfolio_capacity_case(
    loaded: LoadedCandidatePack,
    *,
    policy: PortfolioCapacityPolicy,
    created_at: datetime | str,
) -> PortfolioCapacityCase:
    created = ensure_utc_aware("created_at", created_at)
    notional_usd = _validate_assumptions(loaded.rows, loaded.assumptions)
    windows = cast(Mapping[str, Mapping[str, Any]], loaded.rows.summary["execution_windows"])
    rows_by_key = _row_map(loaded.rows)
    intents: list[PortfolioTradeIntent] = []
    skipped: list[PortfolioSkippedSignal] = []
    for source_row_index, signal in enumerate(loaded.signals):
        event_id = str(signal["event_id"])
        action = _selected_action(signal, policy)
        if action in {"NO_TRADE", "UNKNOWN"}:
            skipped.append(
                PortfolioSkippedSignal(
                    event_id=event_id,
                    symbol=str(signal["symbol"]),
                    selected_action=cast(Literal["NO_TRADE", "UNKNOWN"], action),
                    information_cutoff_at=signal["information_cutoff_at"],
                    source_row_index=source_row_index,
                )
            )
            continue
        row = rows_by_key.get((event_id, action))
        if row is None:
            raise ValueError(f"ACTION_ROW_MISSING: {event_id}:{action}")
        intents.append(
            _intent_from_row(
                signal=signal,
                source_row_index=source_row_index,
                row=row,
                notional_usd=notional_usd,
                window=windows[event_id],
            )
        )
    schema_versions = {
        "decision.json": loaded.decision.schema_version,
        "tournament_rows_v2.json": loaded.rows.schema_version,
        "execution_assumptions.json": str(
            loaded.assumptions.get("schema_version")
            or "crypto_perp_backtest_execution_assumptions.v1"
        ),
    }
    source_refs = [
        file_artifact_ref(path, schema_versions.get(name))
        for name, path in sorted(loaded.component_paths.items())
    ]
    known_limits = [
        "BAR_PROXY_EXECUTION_PRICES",
        "EVENT_LEVEL_COST_ESTIMATES",
        "PRO_RATA_FUNDING_ESTIMATE",
        "NO_MARK_TO_MARKET",
        "NO_LIQUIDATION_MODEL",
        "NO_PARTIAL_FILL_MODEL",
        "CONSERVATIVE_CAPITAL_RESERVATION",
    ]
    case_id = stable_hash(
        [
            "crypto-perp-portfolio-capacity-case",
            loaded.decision.pack_id,
            loaded.rows.row_set_id,
            policy.model_dump(mode="json"),
            [intent.model_dump(mode="json") for intent in intents],
            [item.model_dump(mode="json") for item in skipped],
        ]
    )
    return PortfolioCapacityCase(
        case_id=case_id,
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-portfolio-capacity"),
        source_refs=source_refs,
        pack_id=loaded.decision.pack_id,
        row_set_id=loaded.rows.row_set_id,
        policy=policy,
        intents=intents,
        skipped_signals=skipped,
        known_limits=known_limits,
    )
