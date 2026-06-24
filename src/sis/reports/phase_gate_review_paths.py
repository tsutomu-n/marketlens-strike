from __future__ import annotations

from pathlib import Path


def reports_dir(data_dir: Path) -> Path:
    return data_dir / "reports"


def quick_navigation(summary: dict[str, object], data_dir: Path) -> dict[str, str]:
    report_dir = reports_dir(data_dir)
    items = (
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        ("current_state_index_report", str(report_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(report_dir / "readiness_snapshot.md")),
        ("remediation_scoreboard_report", str(report_dir / "remediation_scoreboard.md")),
        ("paper_operations_runbook_report", str(report_dir / "paper_operations_runbook.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def related_reports(summary: dict[str, object], data_dir: Path) -> dict[str, str]:
    report_dir = reports_dir(data_dir)
    items = (
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        ("operations_dashboard_report", str(report_dir / "operations_dashboard.md")),
        ("current_state_index_report", str(report_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(report_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(report_dir / "paper_operations_runbook.md")),
        ("remediation_scoreboard_report", str(report_dir / "remediation_scoreboard.md")),
        ("go_no_go_report", str(data_dir / "research" / "go_no_go_report.md")),
        (
            "paper_vs_backtest_comparison_report",
            str(report_dir / "paper_vs_backtest_comparison.md"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def latest_path(pattern_root: Path, glob_pattern: str) -> Path | None:
    paths = sorted(pattern_root.glob(glob_pattern))
    return paths[-1] if paths else None


def read_only_collector_gate(data_dir: Path) -> dict[str, object]:
    trade_registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    trade_summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
    trade_quote_path = latest_path(data_dir / "raw/quotes/trade_xyz", "*.jsonl")
    blockers: list[str] = []
    if not trade_registry_path.exists():
        blockers.append("missing_trade_xyz_registry")
    if not trade_quote_path:
        blockers.append("missing_trade_xyz_quote_window")
    if not trade_summary_path.exists():
        blockers.append("missing_trade_xyz_quote_collection_summary")
    return {
        "read_only_collector_gate_passed": not blockers,
        "read_only_collector_blockers": blockers,
        "latest_trade_xyz_registry_path": str(trade_registry_path)
        if trade_registry_path.exists()
        else None,
        "latest_trade_xyz_quote_path": str(trade_quote_path) if trade_quote_path else None,
        "latest_trade_xyz_summary_path": str(trade_summary_path)
        if trade_summary_path.exists()
        else None,
        "latest_gtrade_backend_manifest_path": None,
        "latest_gtrade_backend_status": None,
        "latest_gtrade_backend_event_count": None,
        "latest_gtrade_backend_reconnect_count": None,
        "latest_gtrade_backend_deep_reorg_detected": None,
        "latest_ostium_constraint_path": None,
        "latest_ostium_constraint_status": None,
        "latest_ostium_constraint_failures": [],
        "latest_ostium_python_sdk_status": None,
        "latest_ostium_builder_prices_artifact_path": None,
    }


def required_artifact_paths(summary: dict[str, object]) -> dict[str, str | None]:
    artifact_keys = (
        "latest_trade_xyz_registry_path",
        "latest_trade_xyz_quote_path",
        "latest_trade_xyz_summary_path",
    )
    paths: dict[str, str | None] = {}
    for key in artifact_keys:
        value = summary.get(key)
        paths[key] = value if isinstance(value, str) else None
    return paths
