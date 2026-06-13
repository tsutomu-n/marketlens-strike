from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sis.backtest.frameworks import framework_adapter_status


@dataclass(frozen=True)
class BacktestAdapterSpikeResult:
    spike_path: Path
    report_path: Path
    payload: dict[str, Any]


def _license_text(candidate: dict[str, Any]) -> str:
    parts = [str(candidate.get("license") or "")]
    parts.extend(str(item) for item in candidate.get("license_classifiers") or [])
    parts.append(str(candidate.get("adoption_note") or ""))
    return " ".join(parts).lower()


def _adoption_blockers(candidate: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    license_text = _license_text(candidate)
    if "agpl" in license_text:
        blockers.append("license_review_required_agpl")
    elif "gpl" in license_text:
        blockers.append("license_review_required_gpl")
    if candidate.get("status") != "installed":
        blockers.append("not_installed_in_current_env")
    if candidate.get("framework_id") == "zipline_reloaded":
        blockers.append("temporary_install_failed_in_prior_spike")
    return blockers


def _adoption_status(blockers: list[str]) -> str:
    if any(item.startswith("license_review_required") for item in blockers):
        return "blocked_pending_license_review"
    if "temporary_install_failed_in_prior_spike" in blockers:
        return "blocked_pending_install_spike"
    if "not_installed_in_current_env" in blockers:
        return "requires_temporary_install_spike"
    return "metadata_review_required"


def _spike_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    blockers = _adoption_blockers(candidate)
    return {
        "framework_id": candidate["framework_id"],
        "module": candidate["module"],
        "distribution": candidate["distribution"],
        "adapter_role": candidate["adapter_role"],
        "status": candidate["status"],
        "version": candidate.get("version"),
        "license": candidate.get("license"),
        "requires_python": candidate.get("requires_python"),
        "license_classifiers": candidate.get("license_classifiers") or [],
        "adoption_note": candidate["adoption_note"],
        "adoption_status": _adoption_status(blockers),
        "adoption_blockers": blockers,
        "dependency_added": False,
        "engine_run": False,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def _decision(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = sorted(
        {
            blocker
            for candidate in candidates
            for blocker in candidate.get("adoption_blockers") or []
        }
    )
    return {
        "selected_for_dependency_adoption": None,
        "reason_codes": blockers or ["metadata_review_required"],
        "recommended_next_step": (
            "Run isolated temporary install and license review before dependency adoption."
        ),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Adapter Spike",
        "",
        f"- created_at: {payload['created_at']}",
        "- dependency_added: false",
        "- external_engine_run: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        f"- selected_for_dependency_adoption: {payload['decision']['selected_for_dependency_adoption']}",
        "",
        "## Candidates",
        "",
        "| Framework | Status | Version | Adoption Status | Blockers |",
        "|---|---:|---|---|---|",
    ]
    for candidate in payload["candidates"]:
        lines.append(
            "| {framework_id} | {status} | {version} | {adoption_status} | {blockers} |".format(
                framework_id=candidate["framework_id"],
                status=candidate["status"],
                version=candidate.get("version") or "",
                adoption_status=candidate["adoption_status"],
                blockers=", ".join(candidate["adoption_blockers"]) or "none",
            )
        )
    lines.extend(
        [
            "",
            "This spike does not add dependencies, run external framework engines, or permit live orders.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_backtest_adapter_spike(*, out_dir: Path, reports_dir: Path) -> BacktestAdapterSpikeResult:
    candidates = [_spike_candidate(candidate) for candidate in framework_adapter_status()]
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_adapter_spike.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "candidates": candidates,
        "decision": _decision(candidates),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    spike_path = out_dir / "strategy_backtest_adapter_spike.json"
    spike_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(reports_dir / "strategy_backtest_adapter_spike_report.md", payload)
    return BacktestAdapterSpikeResult(
        spike_path=spike_path, report_path=report_path, payload=payload
    )
