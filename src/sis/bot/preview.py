from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.storage.jsonl_store import read_json, write_json

SCHEMA_VERSION = "bot_preview.v1"


@dataclass(frozen=True)
class BotPreviewResult:
    decision_path: Path
    report_path: Path
    decision: str
    reason_codes: list[str]
    ready_artifact_reasons: list[str]

    @property
    def ready_for_bot_logic(self) -> bool:
        return not self.ready_artifact_reasons


def _safe_read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_quote_path(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))
    return paths[-1] if paths else None


def _int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _symbols_from_summary(summary: dict[str, Any]) -> list[str]:
    for key in ("collected_symbols", "requested_symbols"):
        value = summary.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
    per_symbol = summary.get("per_symbol")
    if isinstance(per_symbol, dict):
        return [str(item) for item in per_symbol.keys()]
    return []


def _next_actions(reason_codes: list[str]) -> list[str]:
    actions: list[str] = []
    if "MISSING_PHASE_GATE_SUMMARY" in reason_codes:
        actions.append("Run `uv run sis phase-gate-review`.")
    if "PHASE_GATE_NOT_READ_ONLY_GO" in reason_codes:
        actions.append("Clear phase gate blockers, then rerun `uv run sis phase-gate-review`.")
    if "MISSING_TRADE_XYZ_QUOTE_SUMMARY" in reason_codes or "EMPTY_TRADE_XYZ_QUOTE_SUMMARY" in reason_codes:
        actions.append("Run `uv run sis collect-trade-xyz-quotes --write-summary --write-report`.")
    if "MISSING_TRADE_XYZ_QUOTE_WINDOW" in reason_codes:
        actions.append("Collect a Trade[XYZ] quote window before building bot preview.")
    if "BOT_ORDER_LOGIC_NOT_IMPLEMENTED" in reason_codes:
        actions.append("Implement explicit order selection logic before producing order candidates.")
    return list(dict.fromkeys(actions))


def _build_report(decision_payload: dict[str, Any]) -> str:
    reasons = decision_payload["reason_codes"]
    actions = decision_payload["next_actions"]
    artifacts = decision_payload["read_only_artifacts"]
    lines = [
        "# Bot Orders Preview",
        "",
        "## Decision",
        "",
        f"- decision: {decision_payload['decision']}",
        "- live_order_submitted: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "## Reason Codes",
        "",
    ]
    lines.extend(f"- {item}" for item in reasons)
    lines.extend(
        [
            "",
            "## Phase Gate",
            "",
            f"- phase_gate_decision: {decision_payload.get('phase_gate_decision') or ''}",
            f"- phase2_entry_allowed: {decision_payload.get('phase2_entry_allowed')}",
            "",
            "## Trade[XYZ] Artifacts",
            "",
            f"- quote_summary_path: {artifacts.get('quote_summary_path') or ''}",
            f"- raw_quote_path: {artifacts.get('raw_quote_path') or ''}",
            f"- quote_row_count: {artifacts.get('quote_row_count')}",
            f"- symbols_checked: {', '.join(decision_payload['symbols_checked'])}",
            "",
            "## Order Preview",
            "",
            "No order candidates are produced in bot-preview v1.",
            "",
            "## Next Actions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in actions)
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This command is read-only. It does not use wallet secrets, signing, or exchange write APIs.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_bot_preview(data_dir: Path) -> BotPreviewResult:
    phase_summary_path = data_dir / "ops/phase_gate_review_summary.json"
    quote_summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
    raw_quote_path = _latest_quote_path(data_dir)
    phase_summary = _safe_read_json_dict(phase_summary_path)
    quote_summary = _safe_read_json_dict(quote_summary_path)

    phase_gate_decision = str(
        phase_summary.get("phase_gate_decision") or phase_summary.get("decision") or ""
    )
    row_count = _int_value(quote_summary.get("row_count"))
    reason_codes: list[str] = []
    ready_artifact_reasons: list[str] = []

    if not phase_summary_path.exists():
        ready_artifact_reasons.append("MISSING_PHASE_GATE_SUMMARY")
    elif phase_gate_decision != "READ_ONLY_GO":
        ready_artifact_reasons.append("PHASE_GATE_NOT_READ_ONLY_GO")
    if not quote_summary_path.exists():
        ready_artifact_reasons.append("MISSING_TRADE_XYZ_QUOTE_SUMMARY")
    elif row_count <= 0:
        ready_artifact_reasons.append("EMPTY_TRADE_XYZ_QUOTE_SUMMARY")
    if raw_quote_path is None:
        ready_artifact_reasons.append("MISSING_TRADE_XYZ_QUOTE_WINDOW")

    reason_codes.extend(ready_artifact_reasons)
    reason_codes.append("BOT_ORDER_LOGIC_NOT_IMPLEMENTED")

    decision_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "venue": "trade_xyz",
        "decision": "HOLD",
        "reason_codes": reason_codes,
        "phase_gate_decision": phase_gate_decision or None,
        "phase2_entry_allowed": phase_summary.get("phase2_entry_allowed"),
        "read_only_artifacts": {
            "phase_gate_summary_path": str(phase_summary_path) if phase_summary_path.exists() else None,
            "quote_summary_path": str(quote_summary_path) if quote_summary_path.exists() else None,
            "raw_quote_path": str(raw_quote_path) if raw_quote_path is not None else None,
            "quote_row_count": row_count,
        },
        "symbols_checked": _symbols_from_summary(quote_summary),
        "next_actions": _next_actions(reason_codes),
        "live_order_submitted": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }

    decision_path = data_dir / "bot/bot_decision.json"
    report_path = data_dir / "reports/bot_orders_preview.md"
    write_json(decision_path, decision_payload)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_build_report(decision_payload), encoding="utf-8")
    return BotPreviewResult(
        decision_path=decision_path,
        report_path=report_path,
        decision="HOLD",
        reason_codes=reason_codes,
        ready_artifact_reasons=ready_artifact_reasons,
    )
