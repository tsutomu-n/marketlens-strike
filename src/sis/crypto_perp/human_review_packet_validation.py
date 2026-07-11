from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import timedelta
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.io import file_artifact_ref


EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES = (
    "selection_manifest",
    "decision",
    "tournament_rows",
    "bias_guard",
    "data_availability",
    "signal_rows",
    "backtest",
    "stress",
    "rolling_stability",
    "gate",
    "kill_report",
    "leaderboard",
)
_SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "schemas"
_INPUT_SCHEMA_FILES = {
    "selection_manifest": "crypto_perp_real_market_no_cash_sample.v1.schema.json",
    "decision": "crypto_perp_backtest_candidate_pack.v1.schema.json",
    "tournament_rows": "crypto_perp_tournament_rows.v2.schema.json",
    "bias_guard": "crypto_perp_bias_guard.v1.schema.json",
    "data_availability": "crypto_perp_backtest_data_availability_ledger.v1.schema.json",
    "signal_rows": "crypto_perp_backtest_signal_row.v1.schema.json",
    "backtest": "crypto_perp_backtest_result.v1.schema.json",
    "stress": "crypto_perp_backtest_stress_result.v1.schema.json",
    "rolling_stability": "crypto_perp_backtest_rolling_stability_result.v1.schema.json",
    "gate": "crypto_perp_no_cash_backtest_gate.v1.schema.json",
    "kill_report": "crypto_perp_no_trade_kill_report.v1.schema.json",
    "leaderboard": "crypto_perp_candidate_leaderboard.v1.schema.json",
}


def _mapping(value: object) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return cast(Sequence[Any], value)
    return []


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(str(value))
    except ValueError:
        return default


def _bool(value: object) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(payload.get("summary"))


@lru_cache(maxsize=None)
def _input_validator(name: str) -> Any:
    schema_path = _SCHEMA_ROOT / _INPUT_SCHEMA_FILES[name]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _artifact_structure_violations(
    *,
    selection_manifest: Mapping[str, Any],
    decision: Mapping[str, Any],
    tournament_rows: Mapping[str, Any],
    bias_guard: Mapping[str, Any],
    data_availability: Mapping[str, Any],
    signal_rows: Sequence[Mapping[str, Any]],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    rolling_stability: Mapping[str, Any],
    gate: Mapping[str, Any],
    kill_report: Mapping[str, Any],
    leaderboard: Mapping[str, Any],
) -> list[str]:
    payloads: dict[str, object] = {
        "selection_manifest": selection_manifest,
        "decision": decision,
        "tournament_rows": tournament_rows,
        "bias_guard": bias_guard,
        "data_availability": data_availability,
        "backtest": backtest,
        "stress": stress,
        "rolling_stability": rolling_stability,
        "gate": gate,
        "kill_report": kill_report,
        "leaderboard": leaderboard,
    }
    violations: list[str] = []
    for name, payload in payloads.items():
        if any(_input_validator(name).iter_errors(payload)):
            violations.append(f"{name.upper()}_STRUCTURE_INVALID")
    if not signal_rows:
        violations.append("SIGNAL_ROWS_STRUCTURE_INVALID")
    elif any(any(_input_validator("signal_rows").iter_errors(row)) for row in signal_rows):
        violations.append("SIGNAL_ROWS_STRUCTURE_INVALID")
    return violations


def _nested_mappings(value: object) -> Sequence[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        mapping = cast(Mapping[str, Any], value)
        containers.append(mapping)
        for nested in mapping.values():
            containers.extend(_nested_mappings(nested))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            containers.extend(_nested_mappings(nested))
    return containers


def _boundary_violation(payloads: Sequence[Mapping[str, Any]]) -> bool:
    forbidden = (
        "paper_permission_granted",
        "permits_paper_order",
        "permits_live_order",
        "actual_cash_used",
        "profit_proven",
        "wallet_used",
        "signing_used",
        "exchange_write_used",
        "live_order_submitted",
    )
    return any(
        key in container and container.get(key) is not False
        for payload in payloads
        for container in _nested_mappings(payload)
        for key in forbidden
    )


def _normalized_sha256(value: object) -> str:
    return str(value).removeprefix("sha256:")


def _ref_matches(
    ref: Mapping[str, Any],
    path: Path,
    schema_version: str | None = None,
) -> bool:
    expected = file_artifact_ref(path, schema_version)
    return (
        str(ref.get("path")) == expected["path"]
        and _normalized_sha256(ref.get("sha256")) == _normalized_sha256(expected["sha256"])
        and (schema_version is None or str(ref.get("schema_version")) == schema_version)
    )


def _source_ref_matches(
    payload: Mapping[str, Any],
    path: Path,
    schema_version: str | None = None,
) -> bool:
    return any(
        isinstance(ref, Mapping) and _ref_matches(ref, path, schema_version)
        for ref in _sequence(payload.get("source_refs"))
    )


def _component_ref_matches(
    decision: Mapping[str, Any],
    name: str,
    path: Path,
    schema_version: str | None,
) -> bool:
    refs = _mapping(_summary(decision).get("pack_component_refs"))
    ref = _mapping(refs.get(name))
    return bool(ref) and _ref_matches(ref, path, schema_version)


def _warning_codes(payload: Mapping[str, Any]) -> list[str]:
    return sorted(
        str(value)
        for value in _sequence(payload.get("known_gaps"))
        if str(value).startswith("BIAS_GUARD_WARNING_")
    )


def _event_outcome_pair_violations(
    *,
    selection_manifest: Mapping[str, Any],
    tournament_rows: Mapping[str, Any],
    signal_rows: Sequence[Mapping[str, Any]],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
) -> list[str]:
    windows = [
        window
        for window in _sequence(selection_manifest.get("execution_windows"))
        if isinstance(window, Mapping)
    ]
    expected_pairs = [
        (str(window.get("event_id")), str(window.get("outcome_id"))) for window in windows
    ]
    violations: list[str] = []
    if not expected_pairs or len(expected_pairs) != len(set(expected_pairs)):
        violations.append("SELECTION_MANIFEST_EVENT_OUTCOME_PAIRS_INVALID")
    expected_event_ids = [event_id for event_id, _ in expected_pairs]
    expected_outcome_ids = [outcome_id for _, outcome_id in expected_pairs]
    if len(expected_event_ids) != len(set(expected_event_ids)):
        violations.append("SELECTION_MANIFEST_EXECUTION_WINDOW_EVENT_IDS_NOT_UNIQUE")
    if len(expected_outcome_ids) != len(set(expected_outcome_ids)):
        violations.append("SELECTION_MANIFEST_EXECUTION_WINDOW_OUTCOME_IDS_NOT_UNIQUE")

    expected_windows: dict[str, tuple[str, str, int]] = {}
    for window in windows:
        event_id = str(window.get("event_id"))
        entry_at = str(window.get("entry_at"))
        settled_at = str(window.get("settled_at"))
        horizon = _int(window.get("horizon_minutes"), -1)
        expected_windows[event_id] = (entry_at, settled_at, horizon)
        try:
            cutoff = ensure_utc_aware(
                "information_cutoff_at", str(window.get("information_cutoff_at"))
            )
            entry = ensure_utc_aware("entry_at", entry_at)
            settled = ensure_utc_aware("settled_at", settled_at)
        except (TypeError, ValueError):
            violations.append("SELECTION_MANIFEST_EXECUTION_WINDOW_TIMESTAMP_INVALID")
            continue
        if not cutoff < entry < settled:
            violations.append("SELECTION_MANIFEST_EXECUTION_WINDOW_CHRONOLOGY_INVALID")
        if horizon <= 0 or settled - entry != timedelta(minutes=horizon):
            violations.append("SELECTION_MANIFEST_EXECUTION_WINDOW_HORIZON_MISMATCH")

    tournament_windows = _mapping(_summary(tournament_rows).get("execution_windows"))
    actual_tournament_windows = {
        str(event_id): (
            str(_mapping(window).get("entry_at")),
            str(_mapping(window).get("settled_at")),
            _int(_mapping(window).get("horizon_minutes"), -1),
        )
        for event_id, window in tournament_windows.items()
    }
    if actual_tournament_windows != expected_windows:
        violations.append("TOURNAMENT_ROWS_EXECUTION_WINDOWS_MISMATCH")

    signal_windows = {
        str(row.get("event_id")): (
            str(row.get("entry_at")),
            _int(row.get("outcome_horizon_minutes"), -1),
        )
        for row in signal_rows
    }
    expected_signal_windows = {
        event_id: (entry_at, horizon)
        for event_id, (entry_at, _, horizon) in expected_windows.items()
    }
    if signal_windows != expected_signal_windows:
        violations.append("SIGNAL_ROWS_EXECUTION_WINDOWS_MISMATCH")

    consumers = {
        "SIGNAL_ROWS": signal_rows,
        "BACKTEST_RESULTS": [
            row for row in _sequence(backtest.get("results")) if isinstance(row, Mapping)
        ],
        "STRESS_RESULTS": [
            row for row in _sequence(stress.get("results")) if isinstance(row, Mapping)
        ],
    }
    expected = sorted(expected_pairs)
    for name, rows in consumers.items():
        actual = sorted((str(row.get("event_id")), str(row.get("outcome_id"))) for row in rows)
        if actual != expected:
            violations.append(f"{name}_EVENT_OUTCOME_PAIR_MISMATCH")
    return violations


def _artifact_lineage_violations(
    *,
    selection_manifest: Mapping[str, Any],
    decision: Mapping[str, Any],
    tournament_rows: Mapping[str, Any],
    bias_guard: Mapping[str, Any],
    data_availability: Mapping[str, Any],
    signal_rows: Sequence[Mapping[str, Any]],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    rolling_stability: Mapping[str, Any],
    gate: Mapping[str, Any],
    kill_report: Mapping[str, Any],
    leaderboard: Mapping[str, Any],
    selection_manifest_path: Path,
    decision_path: Path,
    tournament_rows_path: Path,
    bias_guard_path: Path,
    data_availability_path: Path,
    signal_rows_path: Path,
    backtest_path: Path,
    stress_path: Path,
    rolling_stability_path: Path,
    gate_path: Path,
    kill_report_path: Path,
) -> list[str]:
    violations: list[str] = []
    expected_schemas = [
        (selection_manifest, "SELECTION_MANIFEST", "crypto_perp_real_market_no_cash_sample.v1"),
        (decision, "DECISION", "crypto_perp_backtest_candidate_pack.v1"),
        (tournament_rows, "TOURNAMENT_ROWS", "crypto_perp_tournament_rows.v2"),
        (bias_guard, "BIAS_GUARD", "crypto_perp_bias_guard.v1"),
        (
            data_availability,
            "DATA_AVAILABILITY",
            "crypto_perp_backtest_data_availability_ledger.v1",
        ),
        (backtest, "BACKTEST", "crypto_perp_backtest_result.v1"),
        (stress, "STRESS", "crypto_perp_backtest_stress_result.v1"),
        (
            rolling_stability,
            "ROLLING_STABILITY",
            "crypto_perp_backtest_rolling_stability_result.v1",
        ),
        (gate, "GATE", "crypto_perp_no_cash_backtest_gate.v1"),
        (kill_report, "KILL_REPORT", "crypto_perp_no_trade_kill_report.v1"),
        (leaderboard, "LEADERBOARD", "crypto_perp_candidate_leaderboard.v1"),
    ]
    for payload, name, expected_schema in expected_schemas:
        if str(payload.get("schema_version", "")) != expected_schema:
            violations.append(f"{name}_SCHEMA_VERSION_MISMATCH")

    source_requirements = [
        (
            decision,
            "DECISION",
            "SELECTION_MANIFEST",
            selection_manifest_path,
            "crypto_perp_real_market_no_cash_sample.v1",
        ),
        (
            bias_guard,
            "BIAS_GUARD",
            "TOURNAMENT_ROWS",
            tournament_rows_path,
            "crypto_perp_tournament_rows.v2",
        ),
        (gate, "GATE", "DECISION", decision_path, None),
        (gate, "GATE", "DATA_AVAILABILITY", data_availability_path, None),
        (gate, "GATE", "BACKTEST", backtest_path, None),
        (gate, "GATE", "STRESS", stress_path, None),
        (gate, "GATE", "ROLLING_STABILITY", rolling_stability_path, None),
        (kill_report, "KILL_REPORT", "SIGNAL_ROWS", signal_rows_path, None),
        (kill_report, "KILL_REPORT", "BACKTEST", backtest_path, None),
        (kill_report, "KILL_REPORT", "STRESS", stress_path, None),
        (kill_report, "KILL_REPORT", "TOURNAMENT_ROWS", tournament_rows_path, None),
        (kill_report, "KILL_REPORT", "GATE", gate_path, None),
        (leaderboard, "LEADERBOARD", "DECISION", decision_path, None),
        (leaderboard, "LEADERBOARD", "BACKTEST", backtest_path, None),
        (leaderboard, "LEADERBOARD", "STRESS", stress_path, None),
        (leaderboard, "LEADERBOARD", "GATE", gate_path, None),
        (leaderboard, "LEADERBOARD", "KILL_REPORT", kill_report_path, None),
        (leaderboard, "LEADERBOARD", "SIGNAL_ROWS", signal_rows_path, None),
    ]
    for payload, consumer, source, source_path, schema_version in source_requirements:
        if not _source_ref_matches(payload, source_path, schema_version):
            violations.append(f"{consumer}_{source}_SOURCE_REF_MISMATCH")

    component_requirements = [
        ("signal_rows.jsonl", signal_rows_path, None),
        (
            "data_availability_ledger.json",
            data_availability_path,
            "crypto_perp_backtest_data_availability_ledger.v1",
        ),
        (
            "tournament_rows_v2.json",
            tournament_rows_path,
            "crypto_perp_tournament_rows.v2",
        ),
        ("bias_guard.json", bias_guard_path, "crypto_perp_bias_guard.v1"),
        ("backtest_result.json", backtest_path, "crypto_perp_backtest_result.v1"),
        ("stress_result.json", stress_path, "crypto_perp_backtest_stress_result.v1"),
        (
            "rolling_stability_result.json",
            rolling_stability_path,
            "crypto_perp_backtest_rolling_stability_result.v1",
        ),
    ]
    for name, component_path, schema_version in component_requirements:
        if not _component_ref_matches(decision, name, component_path, schema_version):
            violations.append(f"DECISION_{name.upper().replace('.', '_')}_REF_MISMATCH")

    artifact_paths = _mapping(decision.get("artifact_paths"))
    artifact_path_requirements = {
        "signal_rows.jsonl": signal_rows_path,
        "data_availability_ledger.json": data_availability_path,
        "tournament_rows_v2.json": tournament_rows_path,
        "bias_guard.json": bias_guard_path,
        "backtest_result.json": backtest_path,
        "stress_result.json": stress_path,
        "rolling_stability_result.json": rolling_stability_path,
    }
    for name, component_path in artifact_path_requirements.items():
        if str(artifact_paths.get(name, "")) != component_path.as_posix():
            violations.append(f"DECISION_{name.upper().replace('.', '_')}_PATH_MISMATCH")

    manifest_event_set = sorted(
        str(value) for value in _sequence(selection_manifest.get("event_set"))
    )
    row_event_set = sorted(str(value) for value in _sequence(tournament_rows.get("event_set")))
    guard_event_set = sorted(str(value) for value in _sequence(bias_guard.get("event_set")))
    if not manifest_event_set or manifest_event_set != row_event_set:
        violations.append("SELECTION_MANIFEST_EVENT_SET_MISMATCH")
    if not row_event_set or row_event_set != guard_event_set:
        violations.append("BIAS_GUARD_EVENT_SET_MISMATCH")
    availability_rows = [
        row for row in _sequence(data_availability.get("rows")) if isinstance(row, Mapping)
    ]
    availability_event_set = sorted({str(row.get("event_id")) for row in availability_rows})
    signal_event_set = sorted(
        str(row.get("event_id")) for row in signal_rows if isinstance(row, Mapping)
    )
    backtest_event_set = sorted(
        str(row.get("event_id"))
        for row in _sequence(backtest.get("results"))
        if isinstance(row, Mapping)
    )
    stress_event_set = sorted(
        str(row.get("event_id"))
        for row in _sequence(stress.get("results"))
        if isinstance(row, Mapping)
    )
    rolling_event_set = sorted(
        str(row.get("event_id"))
        for row in _sequence(rolling_stability.get("points"))
        if isinstance(row, Mapping)
    )
    for name, actual_event_set in (
        ("DATA_AVAILABILITY", availability_event_set),
        ("SIGNAL_ROWS", signal_event_set),
        ("BACKTEST_RESULTS", backtest_event_set),
        ("STRESS_RESULTS", stress_event_set),
        ("ROLLING_STABILITY_POINTS", rolling_event_set),
    ):
        if actual_event_set != row_event_set:
            violations.append(f"{name}_EVENT_SET_MISMATCH")

    event_counts = {
        _int(selection_manifest.get("event_count"), -1),
        _int(decision.get("event_count"), -1),
        _int(bias_guard.get("event_count"), -1),
        _int(_summary(data_availability).get("event_count"), -1),
        _int(_summary(backtest).get("event_count"), -1),
        _int(_summary(stress).get("event_count"), -1),
        _int(_summary(rolling_stability).get("event_count"), -1),
        _int(_summary(gate).get("event_count"), -1),
        len(row_event_set),
    }
    if len(event_counts) != 1 or next(iter(event_counts)) != len(row_event_set):
        violations.append("EVENT_COUNT_MISMATCH")
    if _int(data_availability.get("summary", {}).get("row_count"), -1) != len(availability_rows):
        violations.append("DATA_AVAILABILITY_ROW_COUNT_MISMATCH")
    if _int(bias_guard.get("event_count"), -1) != len(guard_event_set):
        violations.append("BIAS_GUARD_EVENT_COUNT_MISMATCH")

    window_event_set = sorted(
        str(window.get("event_id"))
        for window in _sequence(selection_manifest.get("execution_windows"))
        if isinstance(window, Mapping)
    )
    if window_event_set != row_event_set:
        violations.append("SELECTION_MANIFEST_EXECUTION_WINDOW_EVENT_SET_MISMATCH")
    violations.extend(
        _event_outcome_pair_violations(
            selection_manifest=selection_manifest,
            tournament_rows=tournament_rows,
            signal_rows=signal_rows,
            backtest=backtest,
            stress=stress,
        )
    )

    manifest_outcome_set = sorted(
        str(value) for value in _sequence(selection_manifest.get("outcome_set"))
    )
    manifest_outcome_id_set = sorted(
        str(window.get("outcome_id"))
        for window in _sequence(selection_manifest.get("execution_windows"))
        if isinstance(window, Mapping)
    )
    signal_outcome_set = sorted(
        str(row.get("outcome_id")) for row in signal_rows if isinstance(row, Mapping)
    )
    backtest_outcome_set = sorted(
        str(row.get("outcome_id"))
        for row in _sequence(backtest.get("results"))
        if isinstance(row, Mapping)
    )
    stress_outcome_set = sorted(
        str(row.get("outcome_id"))
        for row in _sequence(stress.get("results"))
        if isinstance(row, Mapping)
    )
    if (
        not manifest_outcome_set
        or not manifest_outcome_id_set
        or len(manifest_outcome_set) != len(manifest_outcome_id_set)
        or any(
            outcome_set != manifest_outcome_id_set
            for outcome_set in (signal_outcome_set, backtest_outcome_set, stress_outcome_set)
        )
    ):
        violations.append("OUTCOME_SET_MISMATCH")
    outcome_counts = {
        _int(selection_manifest.get("outcome_count"), -1),
        _int(decision.get("outcome_count"), -1),
        _int(_summary(gate).get("outcome_count"), -1),
        len(manifest_outcome_set),
    }
    if len(outcome_counts) != 1 or next(iter(outcome_counts)) != len(manifest_outcome_set):
        violations.append("OUTCOME_COUNT_MISMATCH")

    decision_summary = _summary(decision)
    guard_status = str(bias_guard.get("guard_status", "missing"))
    if guard_status != str(decision_summary.get("bias_guard_status", "missing")):
        violations.append("BIAS_GUARD_DECISION_STATUS_MISMATCH")
    guard_stops = sorted(str(value) for value in _sequence(bias_guard.get("stop_reasons")))
    decision_stops = sorted(
        str(value) for value in _sequence(decision_summary.get("bias_guard_stop_reasons"))
    )
    if guard_stops != decision_stops:
        violations.append("BIAS_GUARD_DECISION_STOP_REASONS_MISMATCH")
    if _warning_codes(bias_guard) != sorted(
        str(value) for value in _sequence(decision_summary.get("bias_guard_warning_codes"))
    ):
        violations.append("BIAS_GUARD_DECISION_WARNING_CODES_MISMATCH")
    guard_pbo = str(bias_guard.get("pbo_status", "missing"))
    decision_pbo = str(decision_summary.get("pbo_status", "missing"))
    gate_pbo = str(_summary(gate).get("pbo_status", "missing"))
    if len({guard_pbo, decision_pbo, gate_pbo}) != 1:
        violations.append("PBO_STATUS_MISMATCH")
    if _mapping(decision_summary.get("backtest")) != _summary(backtest):
        violations.append("DECISION_BACKTEST_SUMMARY_MISMATCH")
    if _mapping(decision_summary.get("stress")) != _summary(stress):
        violations.append("DECISION_STRESS_SUMMARY_MISMATCH")

    gate_decision = str(gate.get("gate_decision", "UNKNOWN"))
    if str(kill_report.get("upstream_gate_decision", "UNKNOWN")) != gate_decision:
        violations.append("KILL_REPORT_GATE_DECISION_MISMATCH")
    rows = _sequence(leaderboard.get("rows"))
    top = _mapping(rows[0]) if rows else {}
    if str(top.get("gate_decision", "UNKNOWN")) != gate_decision:
        violations.append("LEADERBOARD_GATE_DECISION_MISMATCH")
    if str(top.get("kill_decision", "UNKNOWN")) != str(kill_report.get("kill_decision", "UNKNOWN")):
        violations.append("LEADERBOARD_KILL_DECISION_MISMATCH")
    return list(dict.fromkeys(violations))
