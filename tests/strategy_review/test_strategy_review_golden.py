from __future__ import annotations

import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_review.manifest import StrategyReviewManifest
from sis.strategy_review.service import build_strategy_review


CREATED_AT = "2026-06-16T09:00:00Z"
FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures/strategy_review"


def _copy_fixture_tree(name: str, tmp_path: Path) -> Path:
    source = FIXTURES_ROOT / name
    target = tmp_path / name
    shutil.copytree(source, target)
    return target


def _schema() -> dict:
    return json.loads(
        (
            Path(__file__).resolve().parents[2] / "schemas/strategy_review_manifest.v1.schema.json"
        ).read_text(encoding="utf-8")
    )


def test_strategy_review_complete_golden_packet(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_dir = _copy_fixture_tree("complete", tmp_path)

    result = build_strategy_review(
        review_id="golden-complete",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=fixture_dir / "strategy_backtest_pack.json",
        validation_path=fixture_dir / "strategy_backtest_pack_validation.json",
        lifecycle_review_path=fixture_dir / "strategy_lifecycle_review.json",
        created_at=CREATED_AT,
    )

    manifest_payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(manifest_payload)
    manifest = StrategyReviewManifest.model_validate(manifest_payload)
    assert manifest.review_status.value == "READY_FOR_HUMAN_REVIEW"
    assert manifest.source_safety.status.value == "PASS"
    assert manifest.summary.missing_required_count == 0
    assert manifest.summary.invalid_required_count == 0
    assert manifest.summary.boundary_violation_count == 0

    artifacts = {
        artifact["artifact_key"]: artifact for artifact in manifest_payload["source_artifacts"]
    }
    assert artifacts["pack"]["status"] == "present"
    assert (
        artifacts["pack"]["bytes"] == (fixture_dir / "strategy_backtest_pack.json").stat().st_size
    )
    assert artifacts["pack"]["detected_schema_version"] == "strategy_backtest_pack.v1"
    assert artifacts["authoring_spec"]["status"] == "present"
    assert artifacts["authoring_spec"]["detected_schema_version"] == "strategy_authoring_spec.v1"
    assert artifacts["lifecycle_review"]["status"] == "present"
    assert (
        artifacts["lifecycle_review"]["detected_schema_version"] == "strategy_lifecycle_review.v1"
    )

    markdown = result.review_markdown_path.read_text(encoding="utf-8")
    expected_fragments = (
        "# Strategy Review: golden-complete",
        "## 1. Summary",
        "review_status: `READY_FOR_HUMAN_REVIEW`",
        "## 2. Readiness Disclaimer",
        "alpha、paper readiness、live readinessを証明しません",
        "## 3. Source Artifact Status",
        "| artifact | required | status | path | error |",
        "## 4. Backtest Pack / Validation Summary",
        "## 5. Strategy Definition",
        "strategy_id: `trend_pullback_test_v1`",
        "## 6. Lifecycle Summary",
        "Lifecycle decision は paper / live 実行許可ではありません",
        "decision: `CONTINUE_PAPER_OBSERVATION`",
        "## 7. Safety Boundary",
        "## 8. Missing / Invalid / Blocked Details",
        "`framework_run`: missing",
        "## 9. Source Hash Table",
        "| path | status | bytes | sha256 | detected_schema_version |",
        "## 10. Next Human Review Checklist",
        "別の operator review artifact と既存 paper revalidation を通す",
    )
    for fragment in expected_fragments:
        assert fragment in markdown


def test_strategy_review_problem_golden_packets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    complete_dir = _copy_fixture_tree("complete", tmp_path)
    blocked_dir = _copy_fixture_tree("blocked", tmp_path)
    invalid_dir = _copy_fixture_tree("invalid", tmp_path)

    missing = build_strategy_review(
        review_id="golden-missing",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=tmp_path / "missing_pack.json",
        validation_path=tmp_path / "missing_validation.json",
        strict=True,
        created_at=CREATED_AT,
    )
    blocked = build_strategy_review(
        review_id="golden-blocked",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=blocked_dir / "strategy_backtest_pack.json",
        validation_path=complete_dir / "strategy_backtest_pack_validation.json",
        created_at=CREATED_AT,
    )
    invalid = build_strategy_review(
        review_id="golden-invalid",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=invalid_dir / "invalid_json.json",
        validation_path=complete_dir / "strategy_backtest_pack_validation.json",
        created_at=CREATED_AT,
    )

    cases = (
        (missing, "INCOMPLETE_ARTIFACTS", "UNKNOWN", "missing"),
        (blocked, "BLOCKED_BOUNDARY_VIOLATION", "BLOCKED", "blocked: source boundary violation"),
        (invalid, "INVALID_INPUT", "UNKNOWN", "invalid:"),
    )
    for result, expected_review_status, expected_safety_status, expected_detail in cases:
        payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        Draft202012Validator(_schema()).validate(payload)
        StrategyReviewManifest.model_validate(payload)
        markdown = result.review_markdown_path.read_text(encoding="utf-8")

        assert f"review_status: `{expected_review_status}`" in markdown
        assert f"source_safety.status: `{expected_safety_status}`" in markdown
        assert "## 8. Missing / Invalid / Blocked Details" in markdown
        assert expected_detail in markdown
        assert "## 9. Source Hash Table" in markdown
