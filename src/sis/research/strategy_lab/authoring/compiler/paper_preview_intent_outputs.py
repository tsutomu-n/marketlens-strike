from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _write_empty_paper_intent_preview_outputs(
    *,
    data_dir: Path,
    decision: str,
    scorecard_summary: dict[str, Any],
) -> dict[str, Path]:
    preview_path = data_dir / "bot/paper_intent_preview.json"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(json.dumps([], indent=2), encoding="utf-8")

    report_path = data_dir / "reports/paper_intent_preview.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Paper Intent Preview\n\n"
        "- source: strategy_authoring\n"
        f"- decision: {decision}\n"
        "- intents: 0\n"
        f"- scorecard_schema_version: {scorecard_summary.get('schema_version')}\n"
        f"- scorecard_failed_thresholds: {scorecard_summary.get('failed_thresholds', [])}\n"
        "- paper_only: true\n",
        encoding="utf-8",
    )
    return {
        "paper_intent_preview": preview_path,
        "paper_intent_preview_report": report_path,
    }
