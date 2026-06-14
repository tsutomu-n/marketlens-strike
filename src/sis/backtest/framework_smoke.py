from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
from importlib import metadata
import json
from pathlib import Path
from typing import Any, Sequence

from sis.backtest.frameworks import FRAMEWORK_CANDIDATES


DEFAULT_SMOKE_FRAMEWORKS = (
    "vectorbt",
    "bt",
    "quantstats",
    "empyrical_reloaded",
)

ADOPTION_CLASSIFICATIONS = {
    "vectorbt": "optional_extra_candidate",
    "bt": "optional_extra_candidate",
    "quantstats": "report_only_candidate",
    "empyrical_reloaded": "report_only_candidate",
    "pyfolio_reloaded": "report_only_candidate",
    "backtesting": "separate_runner_candidate",
    "zipline_reloaded": "separate_runner_candidate",
    "backtrader": "separate_runner_candidate",
    "qstrader": "separate_runner_candidate",
}


@dataclass(frozen=True)
class BacktestFrameworkSmokeResult:
    smoke_path: Path
    report_path: Path
    payload: dict[str, Any]


def _candidate_by_id() -> dict[str, dict[str, Any]]:
    return {str(candidate["framework_id"]): dict(candidate) for candidate in FRAMEWORK_CANDIDATES}


def _metadata_for(distribution: str) -> dict[str, Any]:
    try:
        package_metadata = metadata.metadata(distribution)
        classifiers = package_metadata.get_all("Classifier") or []
        return {
            "version": metadata.version(distribution),
            "license": package_metadata.get("License"),
            "requires_python": package_metadata.get("Requires-Python"),
            "license_classifiers": [item for item in classifiers if item.startswith("License ::")],
            "python_classifiers": [
                item for item in classifiers if item.startswith("Programming Language :: Python ::")
            ],
        }
    except metadata.PackageNotFoundError:
        return {
            "version": None,
            "license": None,
            "requires_python": None,
            "license_classifiers": [],
            "python_classifiers": [],
        }


def _license_text(result: dict[str, Any]) -> str:
    parts = [str(result.get("license") or "")]
    parts.extend(str(item) for item in result.get("license_classifiers") or [])
    parts.append(str(result.get("adoption_note") or ""))
    return " ".join(parts).lower()


def _adoption_blockers(result: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    license_text = _license_text(result)
    if "agpl" in license_text:
        blockers.append("license_review_required_agpl")
    elif "gpl" in license_text:
        blockers.append("license_review_required_gpl")
    if result["import_status"] == "not_installed":
        blockers.append("not_installed_in_temporary_env")
    if result["import_status"] == "import_failed":
        blockers.append("temporary_import_failed")
    if result["framework_id"] == "zipline_reloaded":
        blockers.append("build_smoke_required_before_optional_extra")
    if result["framework_id"] in {"backtesting", "backtrader"}:
        blockers.append("license_review_required_before_lock")
    return blockers


def _import_status(module: str) -> tuple[str, str | None, str | None]:
    try:
        importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name == module:
            return "not_installed", type(exc).__name__, str(exc)
        return "import_failed", type(exc).__name__, str(exc)
    except Exception as exc:  # pragma: no cover - framework-specific import failures vary.
        return "import_failed", type(exc).__name__, str(exc)
    return "imported", None, None


def _smoke_result(candidate: dict[str, Any]) -> dict[str, Any]:
    framework_id = str(candidate["framework_id"])
    distribution = str(candidate["distribution"])
    import_status, error_type, error_message = _import_status(str(candidate["module"]))
    package_metadata = _metadata_for(distribution)
    result: dict[str, Any] = {
        "framework_id": framework_id,
        "module": candidate["module"],
        "distribution": distribution,
        "adapter_role": candidate["adapter_role"],
        "import_status": import_status,
        **package_metadata,
        "adoption_classification": ADOPTION_CLASSIFICATIONS[framework_id],
        "adoption_note": candidate["adoption_note"],
        "adoption_blockers": [],
        "import_error_type": error_type,
        "import_error_message": error_message,
        "dependency_added": False,
        "engine_run": False,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    result["adoption_blockers"] = _adoption_blockers(result)
    return result


def _summary(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "target_count": len(results),
        "imported_count": sum(1 for item in results if item["import_status"] == "imported"),
        "not_installed_count": sum(
            1 for item in results if item["import_status"] == "not_installed"
        ),
        "import_failed_count": sum(
            1 for item in results if item["import_status"] == "import_failed"
        ),
        "optional_extra_candidate_count": sum(
            1 for item in results if item["adoption_classification"] == "optional_extra_candidate"
        ),
        "separate_runner_candidate_count": sum(
            1 for item in results if item["adoption_classification"] == "separate_runner_candidate"
        ),
        "report_only_candidate_count": sum(
            1 for item in results if item["adoption_classification"] == "report_only_candidate"
        ),
    }


def _decision(results: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = sorted(
        {blocker for result in results for blocker in result.get("adoption_blockers") or []}
    )
    if any(result["import_status"] != "imported" for result in results):
        reason_codes = blockers or ["temporary_import_smoke_incomplete"]
    else:
        reason_codes = blockers or ["metadata_review_required_before_dependency_adoption"]
    return {
        "selected_for_dependency_adoption": None,
        "reason_codes": reason_codes,
        "recommended_next_step": (
            "Review license, Requires-Python, uv lock stability, and CI before adding optional extras."
        ),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Framework Smoke",
        "",
        f"- created_at: {payload['created_at']}",
        "- runner_mode: temporary_import_smoke",
        "- dependency_added: false",
        "- external_engine_run: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        f"- imported_count: {payload['summary']['imported_count']}",
        f"- not_installed_count: {payload['summary']['not_installed_count']}",
        f"- import_failed_count: {payload['summary']['import_failed_count']}",
        "",
        "## Results",
        "",
        "| Framework | Import Status | Version | Requires Python | Classification | Blockers |",
        "|---|---:|---|---|---|---|",
    ]
    for result in payload["results"]:
        lines.append(
            "| {framework_id} | {import_status} | {version} | {requires_python} | {classification} | {blockers} |".format(
                framework_id=result["framework_id"],
                import_status=result["import_status"],
                version=result.get("version") or "",
                requires_python=result.get("requires_python") or "",
                classification=result["adoption_classification"],
                blockers=", ".join(result["adoption_blockers"]) or "none",
            )
        )
    lines.extend(
        [
            "",
            "This smoke records temporary import status only. It does not add dependencies, run external engines, or permit live orders.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_backtest_framework_smoke(
    *,
    out_dir: Path,
    reports_dir: Path,
    target_frameworks: Sequence[str] | None = None,
) -> BacktestFrameworkSmokeResult:
    candidates = _candidate_by_id()
    targets = list(target_frameworks or DEFAULT_SMOKE_FRAMEWORKS)
    unknown = sorted(set(targets) - set(candidates))
    if unknown:
        raise ValueError(f"unknown framework target(s): {', '.join(unknown)}")
    results = [_smoke_result(candidates[target]) for target in targets]
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_framework_smoke.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "runner_mode": "temporary_import_smoke",
        "target_frameworks": targets,
        "results": results,
        "summary": _summary(results),
        "decision": _decision(results),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    smoke_path = out_dir / "strategy_backtest_framework_smoke.json"
    smoke_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_framework_smoke_report.md", payload
    )
    return BacktestFrameworkSmokeResult(
        smoke_path=smoke_path, report_path=report_path, payload=payload
    )
