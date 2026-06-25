from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from sis.research.ndx.artifacts import read_json, sha256_file, sha256_json, utc_now_iso, write_json
from sis.research.strategy_lifecycle.paper_observation_sessions import (
    dict_field as _dict_field,
    latest_normal_requirement_gaps as _latest_normal_requirement_gaps,
    latest_session as _latest_session,
    session_decision as _session_decision,
    session_id as _session_id,
    session_sort_key as _session_sort_key,
    string_field as _string_field,
    string_list as _string_list,
)

PASS = "PASS_PAPER_OBSERVATION_REVIEW"
NEEDS_MORE = "NEEDS_MORE_PAPER_OBSERVATION"
STOP = "STOP_PAPER_OBSERVATION"

BOUNDARY_KEYS = {
    "permits_live_order",
    "live_conversion_allowed",
    "live_order_submitted",
    "credentials_used",
    "external_api_used",
    "wallet_used",
    "signing_used",
    "venue_write_used",
    "exchange_write_used",
}


@dataclass(frozen=True)
class StrategyPaperObservationStatusResult:
    status_path: Path
    report_path: Path
    observation_state: str
    next_action: str
    status_id: str


def run_strategy_paper_observation_status(
    *,
    data_dir: Path,
    out_dir: Path,
    reports_dir: Path,
    canonical_review_path: Path | None = None,
    lifecycle_review_path: Path | None = None,
    sessions_root: Path | None = None,
) -> StrategyPaperObservationStatusResult:
    selected_canonical_review_path = canonical_review_path or (
        data_dir / "research/ndx/paper_observation_review_decision.json"
    )
    selected_lifecycle_review_path = lifecycle_review_path or (
        data_dir / "research/strategy_lifecycle/strategy_lifecycle_review.json"
    )
    selected_sessions_root = sessions_root or (data_dir / "paper/observations")

    source_artifacts: list[dict[str, Any]] = []
    incomplete_artifacts: list[dict[str, str]] = []
    stale_artifacts: list[dict[str, str]] = []
    source_payloads: dict[str, Any] = {}

    canonical_review, canonical_artifact = _read_source_artifact(
        "canonical_paper_review",
        selected_canonical_review_path,
        required=True,
    )
    source_artifacts.append(canonical_artifact)
    lifecycle_review, lifecycle_artifact = _read_source_artifact(
        "lifecycle_review",
        selected_lifecycle_review_path,
        required=True,
    )
    source_artifacts.append(lifecycle_artifact)
    for artifact in (canonical_artifact, lifecycle_artifact):
        if artifact["required"] and artifact["status"] != "present":
            incomplete_artifacts.append(
                _artifact_issue(
                    name=str(artifact["name"]),
                    path=str(artifact["path"]),
                    error=str(artifact["error"] or artifact["status"]),
                )
            )

    sessions = _read_sessions(
        sessions_root=selected_sessions_root,
        source_artifacts=source_artifacts,
        incomplete_artifacts=incomplete_artifacts,
        stale_artifacts=stale_artifacts,
        source_payloads=source_payloads,
    )
    sessions_by_manifest = {
        _path_key(Path(str(session["manifest_path"]))): session for session in sessions
    }

    canonical_review_hash = (
        sha256_file(selected_canonical_review_path)
        if selected_canonical_review_path.exists()
        else ""
    )
    canonical_review_decision = _string_field(canonical_review, "decision")
    canonical_manifest_path = _string_field(
        canonical_review,
        "source_paper_observation_session_manifest_path",
    )
    canonical_review_session_id = ""
    canonical_review_session_smoke: bool | None = None
    if canonical_manifest_path:
        canonical_session = sessions_by_manifest.get(_path_key(Path(canonical_manifest_path)))
        if canonical_session is None and Path(canonical_manifest_path).exists():
            canonical_manifest = read_json(Path(canonical_manifest_path))
            canonical_review_session_id = str(canonical_manifest.get("session_id") or "")
            canonical_review_session_smoke = bool(canonical_manifest.get("smoke") is True)
        elif canonical_session is not None:
            canonical_review_session_id = str(canonical_session["session_id"])
            canonical_review_session_smoke = bool(canonical_session["smoke"])
        _check_hash_match(
            name="canonical_session_manifest",
            path=Path(canonical_manifest_path),
            expected_hash=_string_field(
                canonical_review,
                "source_paper_observation_session_manifest_hash",
            ),
            stale_artifacts=stale_artifacts,
        )

    if lifecycle_review is not None:
        lifecycle_source_review_path = _string_field(lifecycle_review, "source_paper_review_path")
        if lifecycle_source_review_path:
            if _path_key(Path(lifecycle_source_review_path)) != _path_key(
                selected_canonical_review_path
            ):
                stale_artifacts.append(
                    _artifact_issue(
                        name="lifecycle_source_paper_review",
                        path=lifecycle_source_review_path,
                        error="lifecycle review points at a different paper review path",
                    )
                )
            _check_hash_match(
                name="lifecycle_source_paper_review",
                path=Path(lifecycle_source_review_path),
                expected_hash=_string_field(lifecycle_review, "source_paper_review_hash"),
                stale_artifacts=stale_artifacts,
            )

    normal_sessions = [session for session in sessions if session["smoke"] is False]
    smoke_sessions = [session for session in sessions if session["smoke"] is True]
    latest_normal = _latest_session(normal_sessions)
    latest_smoke = _latest_session(smoke_sessions)
    latest_normal_decision = _session_decision(latest_normal)
    latest_smoke_decision = _session_decision(latest_smoke)
    latest_normal_session_id = _session_id(latest_normal)
    latest_smoke_session_id = _session_id(latest_smoke)
    normal_thresholds_met = latest_normal_decision == PASS
    latest_normal_requirement_gaps = _latest_normal_requirement_gaps(latest_normal)
    smoke_pass_present = any(_session_decision(session) == PASS for session in smoke_sessions)
    canonical_matches_latest_normal = bool(
        canonical_review_session_id
        and canonical_review_session_id == latest_normal_session_id
        and canonical_review_session_smoke is False
    )

    source_boundary_violations = _source_boundary_violations(
        {
            "canonical_paper_review": canonical_review,
            "lifecycle_review": lifecycle_review,
            **source_payloads,
        }
    )
    observation_state = _observation_state(
        incomplete_artifacts=incomplete_artifacts,
        stale_artifacts=stale_artifacts,
        source_boundary_violations=source_boundary_violations,
        latest_normal_decision=latest_normal_decision,
        smoke_pass_present=smoke_pass_present,
    )
    next_action = _next_action(observation_state)
    stable_payload: dict[str, Any] = {
        "schema_version": "strategy_paper_observation_status.v1",
        "observation_state": observation_state,
        "next_action": next_action,
        "canonical_review_decision": canonical_review_decision,
        "canonical_review_path": selected_canonical_review_path.as_posix(),
        "canonical_review_hash": canonical_review_hash,
        "canonical_review_session_id": canonical_review_session_id,
        "canonical_review_session_smoke": canonical_review_session_smoke,
        "lifecycle_decision": _string_field(lifecycle_review, "decision"),
        "lifecycle_decision_reasons": _string_list(lifecycle_review, "decision_reasons"),
        "normal_session_count": len(normal_sessions),
        "smoke_session_count": len(smoke_sessions),
        "latest_normal_session_id": latest_normal_session_id,
        "latest_normal_decision": latest_normal_decision,
        "latest_smoke_session_id": latest_smoke_session_id,
        "latest_smoke_decision": latest_smoke_decision,
        "normal_thresholds_met": normal_thresholds_met,
        "latest_normal_requirement_gaps": latest_normal_requirement_gaps,
        "smoke_pass_present": smoke_pass_present,
        "smoke_pass_counts_as_normal_pass": False,
        "canonical_matches_latest_normal": canonical_matches_latest_normal,
        "incomplete_artifacts": incomplete_artifacts,
        "stale_artifacts": stale_artifacts,
        "source_boundary_violations": source_boundary_violations,
        "source_artifacts": source_artifacts,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "credentials_used": False,
        "external_api_used": False,
        "wallet_used": False,
        "signing_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
        "sessions": sessions,
    }
    status_id = sha256_json(stable_payload)
    payload = {**stable_payload, "status_id": status_id, "generated_at": utc_now_iso()}
    status_path = write_json(out_dir / "paper_observation_status.json", payload)
    report_path = _write_report(reports_dir / "paper_observation_status.md", payload)
    return StrategyPaperObservationStatusResult(
        status_path=status_path,
        report_path=report_path,
        observation_state=observation_state,
        next_action=next_action,
        status_id=status_id,
    )


def _read_source_artifact(
    name: str,
    path: Path,
    *,
    required: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not path.exists():
        return None, _source_artifact(
            name=name,
            path=path,
            required=required,
            status="missing",
            payload=None,
            error="missing",
        )
    try:
        payload = read_json(path)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return None, _source_artifact(
            name=name,
            path=path,
            required=required,
            status="invalid",
            payload=None,
            error=str(exc),
        )
    return payload, _source_artifact(
        name=name,
        path=path,
        required=required,
        status="present",
        payload=payload,
        error="",
    )


def _source_artifact(
    *,
    name: str,
    path: Path,
    required: bool,
    status: str,
    payload: dict[str, Any] | None,
    error: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "required": required,
        "status": status,
        "path": path.as_posix(),
        "sha256": sha256_file(path) if path.exists() else "",
        "schema_version": _string_field(payload, "schema_version"),
        "error": error,
    }


def _read_sessions(
    *,
    sessions_root: Path,
    source_artifacts: list[dict[str, Any]],
    incomplete_artifacts: list[dict[str, str]],
    stale_artifacts: list[dict[str, str]],
    source_payloads: dict[str, Any],
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for manifest_path in sorted(sessions_root.glob("*/paper_observation_session_manifest.json")):
        manifest, manifest_artifact = _read_source_artifact(
            f"session_manifest:{manifest_path.parent.name}",
            manifest_path,
            required=False,
        )
        source_artifacts.append(manifest_artifact)
        if manifest is None:
            incomplete_artifacts.append(
                _artifact_issue(
                    name=str(manifest_artifact["name"]),
                    path=manifest_path.as_posix(),
                    error=str(manifest_artifact["error"] or manifest_artifact["status"]),
                )
            )
            continue
        source_payloads[f"session_manifest:{manifest_path.parent.name}"] = manifest
        review_path = manifest_path.parent / "paper_observation_review_decision.json"
        review, review_artifact = _read_source_artifact(
            f"session_review:{manifest_path.parent.name}",
            review_path,
            required=False,
        )
        source_artifacts.append(review_artifact)
        if review is None:
            incomplete_artifacts.append(
                _artifact_issue(
                    name=str(review_artifact["name"]),
                    path=review_path.as_posix(),
                    error=str(review_artifact["error"] or review_artifact["status"]),
                )
            )
        else:
            source_payloads[f"session_review:{manifest_path.parent.name}"] = review
        cycle_summary_path = manifest_path.parent / "paper_observation_cycle_summary.json"
        if cycle_summary_path.exists():
            _, cycle_artifact = _read_source_artifact(
                f"cycle_summary:{manifest_path.parent.name}",
                cycle_summary_path,
                required=False,
            )
            source_artifacts.append(cycle_artifact)

        manifest_hash = sha256_file(manifest_path)
        review_hash = sha256_file(review_path) if review_path.exists() else ""
        expected_manifest_hash = _string_field(
            review,
            "source_paper_observation_session_manifest_hash",
        )
        manifest_hash_matches_review = (
            expected_manifest_hash == manifest_hash if expected_manifest_hash else None
        )
        if manifest_hash_matches_review is False:
            stale_artifacts.append(
                _artifact_issue(
                    name=f"session_review_manifest:{manifest_path.parent.name}",
                    path=manifest_path.as_posix(),
                    error="session review source manifest hash mismatch",
                )
            )
        sessions.append(
            {
                "session_id": _string_field(manifest, "session_id") or manifest_path.parent.name,
                "created_at": _string_field(manifest, "created_at"),
                "smoke": bool(manifest.get("smoke") is True),
                "manifest_path": manifest_path.as_posix(),
                "manifest_hash": manifest_hash,
                "review_path": review_path.as_posix(),
                "review_hash": review_hash,
                "review_status": "present" if review is not None else review_artifact["status"],
                "review_decision": _string_field(review, "decision"),
                "thresholds": _dict_field(manifest, "thresholds"),
                "metrics": _dict_field(review, "metrics"),
                "reason_codes": _string_list(review, "reason_codes"),
                "block_reasons": _string_list(review, "block_reasons"),
                "source_manifest_hash_matches_review": manifest_hash_matches_review,
            }
        )
    return sorted(sessions, key=_session_sort_key)


def _check_hash_match(
    *,
    name: str,
    path: Path,
    expected_hash: str,
    stale_artifacts: list[dict[str, str]],
) -> None:
    if not expected_hash:
        return
    if not path.exists():
        stale_artifacts.append(
            _artifact_issue(name=name, path=path.as_posix(), error="source artifact missing")
        )
        return
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        stale_artifacts.append(
            _artifact_issue(
                name=name,
                path=path.as_posix(),
                error=f"hash mismatch: expected {expected_hash} got {actual_hash}",
            )
        )


def _source_boundary_violations(sources: dict[str, Any]) -> list[str]:
    violations: list[str] = []

    def visit(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_prefix = f"{prefix}.{key}" if prefix else key
                if key in BOUNDARY_KEYS and child is not False:
                    violations.append(child_prefix)
                visit(child_prefix, child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(f"{prefix}[{index}]", child)

    for name, payload in sources.items():
        if payload is not None:
            visit(name, payload)
    return sorted(set(violations))


def _observation_state(
    *,
    incomplete_artifacts: list[dict[str, str]],
    stale_artifacts: list[dict[str, str]],
    source_boundary_violations: list[str],
    latest_normal_decision: str,
    smoke_pass_present: bool,
) -> str:
    if incomplete_artifacts:
        return "incomplete_artifacts"
    if stale_artifacts:
        return "stale_or_mismatched_artifacts"
    if source_boundary_violations:
        return "source_boundary_violation"
    if latest_normal_decision == PASS:
        return "normal_observation_passed_not_live_ready"
    if latest_normal_decision == NEEDS_MORE:
        return "needs_more_normal_paper_observation"
    if latest_normal_decision == STOP:
        return "paper_observation_stopped"
    if smoke_pass_present:
        return "smoke_only_not_normal_pass"
    return "manual_review_required"


def _next_action(observation_state: str) -> str:
    if observation_state == "incomplete_artifacts":
        return "no_action_until_artifacts_exist"
    if observation_state in {
        "stale_or_mismatched_artifacts",
        "source_boundary_violation",
        "normal_observation_passed_not_live_ready",
        "manual_review_required",
    }:
        return "manual_review_required"
    if observation_state in {
        "needs_more_normal_paper_observation",
        "smoke_only_not_normal_pass",
    }:
        return "continue_normal_paper_observation"
    if observation_state == "paper_observation_stopped":
        return "review_stop_reason"
    return "manual_review_required"


def _artifact_issue(*, name: str, path: str, error: str) -> dict[str, str]:
    return {"name": name, "path": path, "error": error}


def _path_key(path: Path) -> str:
    return path.resolve(strict=False).as_posix()


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    gaps = payload["latest_normal_requirement_gaps"]
    fills = gaps["fills"]
    trading_days = gaps["trading_days"]
    timestamp_quality = gaps["timestamp_quality"]
    lines = [
        "# Paper Observation Status",
        "",
        f"- observation_state: {payload['observation_state']}",
        f"- next_action: {payload['next_action']}",
        f"- canonical_review_decision: {payload['canonical_review_decision']}",
        f"- lifecycle_decision: {payload['lifecycle_decision']}",
        f"- normal_session_count: {payload['normal_session_count']}",
        f"- smoke_session_count: {payload['smoke_session_count']}",
        f"- latest_normal_session_id: {payload['latest_normal_session_id'] or 'none'}",
        f"- latest_normal_decision: {payload['latest_normal_decision'] or 'none'}",
        f"- latest_smoke_session_id: {payload['latest_smoke_session_id'] or 'none'}",
        f"- latest_smoke_decision: {payload['latest_smoke_decision'] or 'none'}",
        f"- normal_thresholds_met: {str(payload['normal_thresholds_met']).lower()}",
        f"- latest_normal_fills: {fills['observed']}/{fills['required']} (remaining={fills['remaining']})",
        f"- latest_normal_trading_days: {trading_days['observed']}/{trading_days['required']} (remaining={trading_days['remaining']})",
        f"- latest_normal_timestamp_quality: {timestamp_quality['observed'] or 'none'} (required={timestamp_quality['required']})",
        f"- smoke_pass_present: {str(payload['smoke_pass_present']).lower()}",
        "- smoke_pass_counts_as_normal_pass: false",
        "- permits_live_order: false",
        "- live_conversion_allowed: false",
        "",
        "This status artifact is read-only. It does not create paper intents, submit paper orders, or prove live readiness.",
        "",
    ]
    if payload["incomplete_artifacts"]:
        lines.extend(["## Incomplete Artifacts", ""])
        for issue in payload["incomplete_artifacts"]:
            lines.append(f"- {issue['name']}: {issue['path']} ({issue['error']})")
        lines.append("")
    if payload["stale_artifacts"]:
        lines.extend(["## Stale Or Mismatched Artifacts", ""])
        for issue in payload["stale_artifacts"]:
            lines.append(f"- {issue['name']}: {issue['path']} ({issue['error']})")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
