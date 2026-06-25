from __future__ import annotations

from typing import Any

__all__ = ["adapter_spike", "external_results", "framework_run"]


def adapter_spike(spike_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if spike_payload is None:
        return None
    candidates = [
        {
            "framework_id": candidate.get("framework_id"),
            "adapter_role": candidate.get("adapter_role"),
            "status": candidate.get("status"),
            "version": candidate.get("version"),
            "adoption_status": candidate.get("adoption_status"),
            "adoption_blockers": candidate.get("adoption_blockers") or [],
            "dependency_added": candidate.get("dependency_added"),
            "engine_run": candidate.get("engine_run"),
            "permits_live_order": candidate.get("permits_live_order"),
            "wallet_used": candidate.get("wallet_used"),
            "exchange_write_used": candidate.get("exchange_write_used"),
        }
        for candidate in spike_payload.get("candidates") or []
        if isinstance(candidate, dict)
    ]
    return {
        "schema_version": spike_payload.get("schema_version"),
        "created_at": spike_payload.get("created_at"),
        "dependency_added": spike_payload.get("dependency_added"),
        "external_engine_run": spike_payload.get("external_engine_run"),
        "permits_live_order": spike_payload.get("permits_live_order"),
        "live_conversion_allowed": spike_payload.get("live_conversion_allowed"),
        "wallet_used": spike_payload.get("wallet_used"),
        "exchange_write_used": spike_payload.get("exchange_write_used"),
        "decision": spike_payload.get("decision") or {},
        "candidates": candidates,
    }


def external_results(external_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if external_payload is None:
        return []
    return [
        {
            "framework_id": result.get("framework_id"),
            "adapter_role": result.get("adapter_role"),
            "status": result.get("status"),
            "framework_version": result.get("framework_version"),
            "runner_mode": result.get("runner_mode"),
            "run_status": result.get("run_status"),
            "reason_codes": result.get("reason_codes") or [],
            "dependency_added": result.get("dependency_added"),
            "engine_run": result.get("engine_run"),
            "permits_live_order": result.get("permits_live_order"),
            "wallet_used": result.get("wallet_used"),
            "exchange_write_used": result.get("exchange_write_used"),
            "metrics": result.get("metrics") or {},
        }
        for result in external_payload.get("results") or []
        if isinstance(result, dict)
    ]


def framework_run(framework_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if framework_payload is None:
        return None
    summary = framework_payload.get("summary")
    runs = [
        {
            "framework_id": run.get("framework_id"),
            "surface_type": run.get("surface_type"),
            "status": run.get("status"),
            "run_status": run.get("run_status"),
            "reason_codes": run.get("reason_codes") or [],
            "dependency_source": run.get("dependency_source"),
            "artifact": run.get("artifact") if isinstance(run.get("artifact"), dict) else None,
            "report": run.get("report") if isinstance(run.get("report"), dict) else None,
            "boundary": run.get("boundary") if isinstance(run.get("boundary"), dict) else {},
        }
        for run in framework_payload.get("runs") or []
        if isinstance(run, dict)
    ]
    return {
        "schema_version": framework_payload.get("schema_version"),
        "created_at": framework_payload.get("created_at"),
        "selected_frameworks": framework_payload.get("selected_frameworks") or [],
        "summary": summary if isinstance(summary, dict) else {},
        "dependency_added": framework_payload.get("dependency_added"),
        "permits_live_order": framework_payload.get("permits_live_order"),
        "live_conversion_allowed": framework_payload.get("live_conversion_allowed"),
        "wallet_used": framework_payload.get("wallet_used"),
        "exchange_write_used": framework_payload.get("exchange_write_used"),
        "runs": runs,
    }
