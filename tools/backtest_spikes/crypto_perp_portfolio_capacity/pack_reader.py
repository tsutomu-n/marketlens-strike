from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, NoReturn, cast

from sis.crypto_perp.backtest_candidate_pack_models import (
    CryptoPerpBacktestCandidatePackDecision,
)
from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.tournament_rows import (
    CostAwareTournamentRow,
    CryptoPerpTournamentRowsV2,
)

from .models import (
    PortfolioCapacityCase,
    PortfolioCapacityPolicy,
    PortfolioSkip,
    PortfolioTradeIntent,
    RuntimeInventory,
)


REQUIRED_FILES = (
    "decision.json",
    "signal_rows.jsonl",
    "tournament_rows_v2.json",
    "execution_assumptions.json",
)
TradeAction = Literal["REVERSAL_SHORT", "CONTINUATION_LONG"]
SkipAction = Literal["NO_TRADE", "UNKNOWN"]

TRADE_ACTIONS: tuple[TradeAction, ...] = ("REVERSAL_SHORT", "CONTINUATION_LONG")
ALL_ACTIONS = {"REVERSAL_SHORT", "CONTINUATION_LONG", "NO_TRADE"}
FORMULA_TOLERANCE_USD = Decimal("0.000000000001")


class CandidatePackError(ValueError):
    pass


@dataclass(frozen=True)
class CandidatePack:
    root: Path
    decision: CryptoPerpBacktestCandidatePackDecision
    signals: tuple[dict[str, Any], ...]
    rows: CryptoPerpTournamentRowsV2
    assumptions: dict[str, Any]
    outcomes: dict[str, CryptoPerpOutcome]


def _fail(code: str, detail: str) -> NoReturn:
    raise CandidatePackError(f"{code}: {detail}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _fail("INVALID_JSON", f"{path}: {exc}")
    if not isinstance(value, dict):
        _fail("INVALID_JSON_OBJECT", str(path))
    return value


def _read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail("INVALID_JSONL", f"{path}:{index + 1}: {exc}")
        if not isinstance(value, dict):
            _fail("INVALID_JSONL_ROW", f"{path}:{index + 1}")
        rows.append(value)
    return tuple(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected_sha(value: object) -> str:
    text = str(value or "")
    if not text.startswith("sha256:") or len(text) != 71:
        _fail("INVALID_COMPONENT_SHA256", text)
    return text.removeprefix("sha256:")


def _resolve_source_ref(pack_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    candidates = [path] if path.is_absolute() else []
    if not path.is_absolute():
        candidates.append(Path.cwd() / path)
        candidates.extend(parent / path for parent in pack_dir.parents)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    _fail("SOURCE_REF_NOT_FOUND", raw_path)


def _verify_component_refs(
    pack_dir: Path,
    decision: CryptoPerpBacktestCandidatePackDecision,
) -> None:
    refs = decision.summary.get("pack_component_refs")
    if not isinstance(refs, Mapping):
        _fail("PACK_COMPONENT_REFS_MISSING", "decision.summary.pack_component_refs")
    refs_map = cast(Mapping[str, Any], refs)
    for required in REQUIRED_FILES[1:]:
        if required not in refs_map:
            _fail("PACK_COMPONENT_REF_MISSING", required)
    for name, raw_ref in refs_map.items():
        if not isinstance(name, str) or not isinstance(raw_ref, Mapping):
            _fail("INVALID_PACK_COMPONENT_REF", str(name))
        local_path = pack_dir / Path(str(raw_ref.get("path", ""))).name
        if not local_path.is_file():
            _fail("PACK_COMPONENT_FILE_MISSING", name)
        if _sha256(local_path) != _expected_sha(raw_ref.get("sha256")):
            _fail("PACK_COMPONENT_HASH_MISMATCH", name)


def _load_outcomes(
    pack_dir: Path,
    decision: CryptoPerpBacktestCandidatePackDecision,
) -> dict[str, CryptoPerpOutcome]:
    outcomes: dict[str, CryptoPerpOutcome] = {}
    for ref in decision.source_refs:
        if ref.get("schema_version") != "crypto_perp_outcome.v1":
            continue
        path = _resolve_source_ref(pack_dir, str(ref.get("path", "")))
        if _sha256(path) != _expected_sha(ref.get("sha256")):
            _fail("SOURCE_REF_HASH_MISMATCH", path.as_posix())
        outcome = CryptoPerpOutcome.model_validate(_read_json(path))
        if outcome.outcome_id in outcomes:
            _fail("DUPLICATE_OUTCOME_REF", outcome.outcome_id)
        outcomes[outcome.outcome_id] = outcome
    return outcomes


def _decimal(mapping: Mapping[str, Any], key: str) -> Decimal:
    try:
        return Decimal(str(mapping[key]))
    except (InvalidOperation, KeyError, ValueError):
        _fail("INVALID_DECIMAL_FIELD", key)


def _timestamp(
    mapping: Mapping[str, Any],
    key: str,
    *,
    field_name: str | None = None,
) -> datetime:
    value = mapping.get(key)
    if not isinstance(value, (datetime, str)):
        _fail("INVALID_TIMESTAMP_FIELD", key)
    return ensure_utc_aware(field_name or key, value)


def _validate_assumptions(
    assumptions: Mapping[str, Any],
    rows: CryptoPerpTournamentRowsV2,
) -> None:
    costs = rows.summary.get("cost_assumptions")
    if not isinstance(costs, Mapping):
        _fail("COST_ASSUMPTIONS_MISSING", "tournament_rows_v2.summary")
    costs_map = cast(Mapping[str, Any], costs)
    comparisons = (
        ("position_size_usd", "notional_usd"),
        ("fee_rate", "fee_rate"),
        ("funding_rate_assumption", "funding_rate"),
        ("slippage_bps", "slippage_bps"),
    )
    for assumption_key, row_key in comparisons:
        if _decimal(assumptions, assumption_key) != _decimal(costs_map, row_key):
            _fail("ASSUMPTION_MISMATCH", f"{assumption_key}!={row_key}")


def _validate_event_contract(
    signals: tuple[dict[str, Any], ...],
    rows: CryptoPerpTournamentRowsV2,
    assumptions: Mapping[str, Any],
    outcomes: Mapping[str, CryptoPerpOutcome],
) -> None:
    signal_by_event: dict[str, dict[str, Any]] = {}
    for signal in signals:
        event_id = str(signal.get("event_id", ""))
        if not event_id:
            _fail("MISSING_SIGNAL_EVENT_ID", repr(signal))
        if event_id in signal_by_event:
            _fail("DUPLICATE_SIGNAL_ROW", event_id)
        signal_by_event[event_id] = signal
    if set(signal_by_event) != set(rows.event_set):
        _fail("EVENT_SET_MISMATCH", "signal rows != tournament rows")

    action_rows: dict[tuple[str, str], CostAwareTournamentRow] = {}
    for row in rows.rows:
        key = (row.event_id, row.action)
        if key in action_rows:
            _fail("DUPLICATE_ACTION_ROW", f"{row.event_id}:{row.action}")
        action_rows[key] = row
        if row.evidence_level != "cost_adjusted_estimate" or row.actual_cash_result_usd is not None:
            _fail("UNSUPPORTED_ACTUAL_CASH_INPUT", f"{row.event_id}:{row.action}")
    for event_id in rows.event_set:
        actual = {action for candidate_event, action in action_rows if candidate_event == event_id}
        if actual != ALL_ACTIONS:
            _fail("MISSING_ACTION_ROW", f"{event_id}:{sorted(ALL_ACTIONS - actual)}")

    windows = rows.summary.get("execution_windows")
    if not isinstance(windows, Mapping):
        _fail("EXECUTION_WINDOWS_MISSING", "tournament_rows_v2.summary")
    windows_map = cast(Mapping[str, Any], windows)
    max_holding = int(assumptions.get("max_holding_minutes", 0))
    notional = Decimal(str(assumptions.get("position_size_usd")))
    for source_index, event_id in enumerate(rows.event_set):
        signal = signal_by_event[event_id]
        raw_window = windows_map.get(event_id)
        if not isinstance(raw_window, Mapping):
            _fail("EXECUTION_WINDOW_MISSING", event_id)
        window = cast(Mapping[str, Any], raw_window)
        cutoff = _timestamp(signal, "information_cutoff_at")
        entry_at = _timestamp(window, "entry_at")
        settled_at = _timestamp(window, "settled_at")
        horizon = int(window.get("horizon_minutes", 0))
        if not cutoff < entry_at < settled_at:
            _fail("INVALID_EXECUTION_WINDOW", event_id)
        if int((settled_at - entry_at).total_seconds() // 60) != horizon:
            _fail("EXECUTION_WINDOW_HORIZON_MISMATCH", event_id)
        if horizon != max_holding:
            _fail("ASSUMPTION_MISMATCH", f"max_holding_minutes:{event_id}")
        if _timestamp(signal, "entry_at", field_name="signal.entry_at") != entry_at:
            _fail("SIGNAL_ENTRY_WINDOW_MISMATCH", event_id)
        if int(signal.get("outcome_horizon_minutes", 0)) != horizon:
            _fail("SIGNAL_HORIZON_MISMATCH", event_id)
        outcome_id = str(signal.get("outcome_id", ""))
        outcome = outcomes.get(outcome_id)
        if outcome is None:
            _fail("OUTCOME_REF_MISSING", outcome_id)
        if outcome.event_id != event_id or outcome.settled_at != settled_at:
            _fail("OUTCOME_EVENT_WINDOW_MISMATCH", event_id)
        matured = [value for value in outcome.horizons if value.matured]
        if len(matured) != 1 or matured[0].horizon_minutes != horizon:
            _fail("OUTCOME_HORIZON_MISMATCH", event_id)
        price = matured[0]
        expected = {
            "CONTINUATION_LONG": notional
            * (price.close_price - price.reference_price)
            / price.reference_price,
            "REVERSAL_SHORT": notional
            * (price.reference_price - price.close_price)
            / price.reference_price,
        }
        for action in TRADE_ACTIONS:
            actual = action_rows[(event_id, action)].before_cost_proxy_usd
            if abs(actual - expected[action]) > FORMULA_TOLERANCE_USD:
                _fail(
                    "BEFORE_COST_PROXY_FORMULA_MISMATCH",
                    f"{event_id}:{action}:index={source_index}",
                )


def load_candidate_pack(candidate_pack_dir: Path) -> CandidatePack:
    pack_dir = candidate_pack_dir.resolve()
    for name in REQUIRED_FILES:
        if not (pack_dir / name).is_file():
            _fail("PACK_REQUIRED_FILE_MISSING", name)
    decision = CryptoPerpBacktestCandidatePackDecision.model_validate(
        _read_json(pack_dir / "decision.json")
    )
    if not decision.pack_id:
        _fail("PACK_ID_MISSING", "decision.pack_id")
    for name in REQUIRED_FILES:
        path_ref = decision.artifact_paths.get(name)
        if path_ref is None or Path(path_ref).name != name:
            _fail("PACK_ARTIFACT_PATH_MISMATCH", name)
    _verify_component_refs(pack_dir, decision)
    signals = _read_jsonl(pack_dir / "signal_rows.jsonl")
    rows = CryptoPerpTournamentRowsV2.model_validate(
        _read_json(pack_dir / "tournament_rows_v2.json")
    )
    assumptions = _read_json(pack_dir / "execution_assumptions.json")
    outcomes = _load_outcomes(pack_dir, decision)
    _validate_assumptions(assumptions, rows)
    _validate_event_contract(signals, rows, assumptions, outcomes)
    return CandidatePack(pack_dir, decision, signals, rows, assumptions, outcomes)


def build_capacity_case(
    pack: CandidatePack,
    policy: PortfolioCapacityPolicy,
) -> PortfolioCapacityCase:
    rows_by_key = {(row.event_id, row.action): row for row in pack.rows.rows}
    raw_windows = pack.rows.summary["execution_windows"]
    raw_costs = pack.rows.summary["cost_assumptions"]
    if not isinstance(raw_windows, Mapping) or not isinstance(raw_costs, Mapping):
        _fail("PACK_CONTRACT_NOT_VALIDATED", "execution_windows or cost_assumptions")
    windows = cast(Mapping[str, Any], raw_windows)
    costs = cast(Mapping[str, Any], raw_costs)
    stress_multiplier = Decimal(str(costs.get("stress_slippage_multiplier", "2")))
    notional = Decimal(str(pack.assumptions["position_size_usd"]))
    intents: list[PortfolioTradeIntent] = []
    skips: list[PortfolioSkip] = []
    for source_index, signal in enumerate(pack.signals):
        event_id = str(signal["event_id"])
        if policy.action_policy == "CURRENT_SELECTOR":
            action = str(signal.get("selected_action", "UNKNOWN"))
        elif policy.action_policy == "ALWAYS_CONTINUATION":
            action = "CONTINUATION_LONG"
        elif policy.action_policy == "ALWAYS_REVERSAL":
            action = "REVERSAL_SHORT"
        else:
            action = "NO_TRADE"
        raw_window = windows[event_id]
        if not isinstance(raw_window, Mapping):
            _fail("EXECUTION_WINDOW_MISSING", event_id)
        window = cast(Mapping[str, Any], raw_window)
        entry_at = _timestamp(window, "entry_at")
        if action in {"NO_TRADE", "UNKNOWN"}:
            skip_action = cast(SkipAction, action)
            skips.append(
                PortfolioSkip(
                    event_id=event_id,
                    symbol=str(signal["symbol"]),
                    action=skip_action,
                    entry_at=entry_at,
                    reason_code=(
                        "NO_TRADE_SKIPPED" if skip_action == "NO_TRADE" else "UNKNOWN_SKIPPED"
                    ),
                )
            )
            continue
        if action not in TRADE_ACTIONS:
            _fail("UNSUPPORTED_SELECTED_ACTION", f"{event_id}:{action}")
        trade_action = cast(TradeAction, action)
        row = rows_by_key[(event_id, trade_action)]
        outcome = pack.outcomes[str(signal["outcome_id"])]
        horizon = next(value for value in outcome.horizons if value.matured)
        stress_slippage = row.slippage_estimate_usd * stress_multiplier
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
        intents.append(
            PortfolioTradeIntent(
                event_id=event_id,
                outcome_id=outcome.outcome_id,
                symbol=str(signal["symbol"]),
                action=trade_action,
                side="LONG" if trade_action == "CONTINUATION_LONG" else "SHORT",
                information_cutoff_at=_timestamp(signal, "information_cutoff_at"),
                entry_at=entry_at,
                exit_at=_timestamp(window, "settled_at"),
                source_row_index=source_index,
                signal_score=(
                    Decimal(str(signal["signal_score"]))
                    if signal.get("signal_score") is not None
                    else None
                ),
                notional_usd=notional,
                entry_price_proxy=horizon.reference_price,
                exit_price_proxy=horizon.close_price,
                before_cost_proxy_usd=row.before_cost_proxy_usd,
                fee_estimate_usd=row.fee_estimate_usd,
                funding_estimate_usd=row.funding_estimate_usd,
                slippage_estimate_usd=row.slippage_estimate_usd,
                operator_time_cost_usd=row.operator_time_cost_usd,
                stress_slippage_estimate_usd=stress_slippage,
                account_delta_base_usd=account_base,
                account_delta_stress_usd=account_stress,
                economic_delta_base_usd=account_base - row.operator_time_cost_usd,
                economic_delta_stress_usd=account_stress - row.operator_time_cost_usd,
                reserve_base_usd=(
                    notional
                    + row.fee_estimate_usd
                    + row.funding_estimate_usd
                    + row.slippage_estimate_usd
                ),
                reserve_stress_usd=(
                    notional + row.fee_estimate_usd + row.funding_estimate_usd + stress_slippage
                ),
                known_gaps=list(row.known_gaps),
            )
        )
    case_payload = {
        "pack_id": pack.decision.pack_id,
        "row_set_id": pack.rows.row_set_id,
        "policy": policy.model_dump(mode="json"),
    }
    return PortfolioCapacityCase(
        case_id=stable_hash(["crypto-perp-portfolio-capacity-case", case_payload]),
        pack_id=pack.decision.pack_id,
        row_set_id=pack.rows.row_set_id,
        policy=policy,
        intents=intents,
        skips=skips,
    )


def build_runtime_inventory(pack: CandidatePack) -> RuntimeInventory:
    raw_windows = pack.rows.summary["execution_windows"]
    if not isinstance(raw_windows, Mapping):
        _fail("PACK_CONTRACT_NOT_VALIDATED", "execution_windows")
    windows = cast(Mapping[str, Any], raw_windows)
    intervals = [
        (
            _timestamp(cast(Mapping[str, Any], window), "entry_at"),
            _timestamp(cast(Mapping[str, Any], window), "settled_at"),
        )
        for window in windows.values()
        if isinstance(window, Mapping)
    ]
    if len(intervals) != len(windows):
        _fail("INVALID_EXECUTION_WINDOW", "runtime inventory")
    points = sorted(
        [(entry, 1) for entry, _ in intervals] + [(exit_at, -1) for _, exit_at in intervals],
        key=lambda value: (value[0], value[1]),
    )
    concurrent = 0
    peak = 0
    for _, delta in points:
        concurrent += delta
        peak = max(peak, concurrent)
    entries = Counter(entry for entry, _ in intervals)
    exits = Counter(exit_at for _, exit_at in intervals)
    same_timestamp = sum(entries[timestamp] * exits[timestamp] for timestamp in entries & exits)
    evidence = pack.decision.evidence_grade_summary
    coverage: dict[str, int] = {}
    known_gaps = list(pack.rows.known_gaps)
    if evidence is not None:
        coverage.update(
            {f"available:{key}": value for key, value in evidence.source_available_counts.items()}
        )
        coverage.update(
            {f"missing:{key}": value for key, value in evidence.source_missing_counts.items()}
        )
        known_gaps.extend(evidence.known_limits)
    assumptions = pack.assumptions
    start = min((entry for entry, _ in intervals), default=None)
    end = max((exit_at for _, exit_at in intervals), default=None)
    return RuntimeInventory(
        pack_id=pack.decision.pack_id,
        row_set_id=pack.rows.row_set_id,
        event_count=len(pack.rows.event_set),
        unique_symbol_count=len({str(signal["symbol"]) for signal in pack.signals}),
        time_range={
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
        },
        selected_action_counts=dict(
            sorted(
                Counter(str(row.get("selected_action", "UNKNOWN")) for row in pack.signals).items()
            )
        ),
        notional_usd=Decimal(str(assumptions["position_size_usd"])),
        fee_rate=Decimal(str(assumptions["fee_rate"])),
        funding_rate=Decimal(str(assumptions["funding_rate_assumption"])),
        slippage_bps=Decimal(str(assumptions["slippage_bps"])),
        operator_cost_non_zero_count=sum(row.operator_time_cost_usd != 0 for row in pack.rows.rows),
        execution_window_peak_overlap=peak,
        same_timestamp_entry_exit_count=same_timestamp,
        source_coverage_counts=dict(sorted(coverage.items())),
        known_gaps=list(dict.fromkeys(known_gaps)),
    )
