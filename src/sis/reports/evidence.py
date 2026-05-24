from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sis.reports.go_no_go import build_go_no_go_report
from sis.reports.summary_normalizers import (
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    phase_gate_flat_fields,
    normalize_phase_gate_summary,
    readiness_flat_fields,
    normalize_readiness_summary,
)
from sis.storage.jsonl_store import write_json
from sis.venues.ostium.positions import latest_positions_sidecar


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sha256_tree(root: Path) -> str | None:
    if not root.exists():
        return None
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        return None
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def build_evidence_card(
    data_dir: Path,
    out_dir: Path,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
) -> Path:
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S")
    report = build_go_no_go_report(data_dir)
    ostium_positions = latest_positions_sidecar(data_dir / "raw/sidecar/ostium")
    normalized_phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    phase_gate_flat = phase_gate_flat_fields(normalized_phase_gate_summary)
    readiness_flat = readiness_flat_fields(normalized_readiness_summary)
    execution_drift_flat = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    card = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "scope": {
            "venues": ["gtrade", "ostium"],
            "symbols": ["SPY", "QQQ", "XAU"],
            "timeframes": ["4h", "1d", "3d"],
            "scalping_policy": "prohibited_by_default",
        },
        "data": {
            "raw_quote_digest": sha256_tree(data_dir / "raw/quotes"),
            "gtrade_registry_digest": sha256_file(data_dir / "registry/gtrade_instrument_registry.json"),
            "ostium_registry_digest": sha256_file(data_dir / "registry/ostium_instrument_registry.json"),
            "ostium_positions_digest": sha256_file(ostium_positions) if ostium_positions else None,
            "normalized_quote_digest": sha256_file(data_dir / "normalized/quotes.parquet"),
            "cost_matrix_digest": sha256_file(data_dir / "research/venue_cost_matrix.csv"),
            "research_signals_digest": sha256_file(data_dir / "research/signals.csv"),
            "backtest_report_digest": sha256_file(data_dir / "research/backtest_report.md"),
            "decision_summary_digest": sha256_file(data_dir / "research/decision_summary.json"),
            "go_no_go_report_digest": sha256_file(data_dir / "research/go_no_go_report.md"),
            "decision_logs_digest": sha256_tree(data_dir / "evidence/decision_logs"),
        },
        "decision": report.decision.value,
        "venue_decisions": [item.model_dump(mode="json") for item in report.venue_decisions],
        "criteria": [item.model_dump(mode="json") for item in report.criteria],
        "blockers": report.blockers,
        "next_actions": report.next_actions,
        "audit_summary": audit_summary if isinstance(audit_summary, dict) else {},
        "phase_gate_summary": normalized_phase_gate_summary,
        **phase_gate_flat,
        "readiness_summary": normalized_readiness_summary,
        **readiness_flat,
        "execution_summary": execution_summary if isinstance(execution_summary, dict) else {},
        "execution_comparison_summary": (
            execution_comparison_summary if isinstance(execution_comparison_summary, dict) else {}
        ),
        "execution_diagnostics_summary": (
            execution_diagnostics_summary if isinstance(execution_diagnostics_summary, dict) else {}
        ),
        "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
        **execution_drift_flat,
    }
    out_path = out_dir / f"evidence_card_{run_id}.json"
    write_json(out_path, card)
    return out_path
