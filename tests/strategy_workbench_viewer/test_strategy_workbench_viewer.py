from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_workbench_viewer.service import build_strategy_workbench_viewer


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _stage_decision(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_stage_decision.v1",
            "decision_id": "stage-001",
            "strategy_id": "ndx-breakout-001",
            "decision_status": "READY_FOR_PAPER_SMOKE_PLAN",
            "recommended_action": "BUILD_PAPER_SMOKE_PLAN",
            "live_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    )


def _unsafe_review(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Review <script>alert(1)</script>\n\n"
        "This markdown contains <img src=x onerror=alert(1)> and must be escaped.\n",
        encoding="utf-8",
    )
    return path


def test_strategy_workbench_viewer_builds_schema_valid_static_html(tmp_path: Path) -> None:
    result = build_strategy_workbench_viewer(
        artifacts=[
            _stage_decision(tmp_path / "data/strategy_stage/stage.json"),
            _unsafe_review(tmp_path / "data/strategy_reviews/review.md"),
        ],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)

    assert payload["schema_version"] == "strategy_workbench_viewer.v1"
    assert payload["artifact_count"] == 2
    assert payload["paper_execution_allowed"] is False
    assert payload["live_allowed"] is False
    assert payload["source_artifacts"][0]["status"] == "READY_FOR_PAPER_SMOKE_PLAN"

    html = result.html_path.read_text(encoding="utf-8")
    HTMLParser().feed(html)
    assert "Strategy Workbench Viewer" in html
    assert "paper / live 実行許可ではありません" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_strategy_workbench_viewer_scans_data_dir(tmp_path: Path) -> None:
    _stage_decision(tmp_path / "data/a/stage.json")
    _unsafe_review(tmp_path / "data/b/review.md")

    result = build_strategy_workbench_viewer(
        artifacts=None,
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    assert result.manifest.artifact_count == 2
    assert result.html_path.exists()
