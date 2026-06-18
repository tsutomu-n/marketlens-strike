from __future__ import annotations

from pathlib import Path

from .test_strategy_review_build import (
    CREATED_AT,
    _write_authoring_spec,
    _write_input_contract,
    _write_lifecycle_review,
    _write_required_artifacts,
    _write_strategy_idea,
)
from sis.strategy_review.service import build_strategy_review


def test_strategy_review_markdown_contains_boundary_notices(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = build_strategy_review(
        review_id="render-smoke",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )
    text = result.review_markdown_path.read_text(encoding="utf-8")

    assert "このreviewは人間の戦略レビュー用artifactです。" in text
    assert "alpha、paper readiness、live readinessを証明しません" in text
    assert "戦略の収益性、paper移行可否、live実行可否は証明されません" in text
    assert "source_safety.status: `PASS`" in text
    assert "| artifact | required | status | path | error |" in text
    assert "| path | status | bytes | sha256 | detected_schema_version |" in text
    assert "detected_schema_version" in text
    assert CREATED_AT in text


def test_strategy_review_markdown_orders_strategy_before_backtest_summary(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    spec_path = tmp_path / "spec.yaml"
    lifecycle_path = tmp_path / "lifecycle.json"
    _write_authoring_spec(spec_path)
    _write_lifecycle_review(lifecycle_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = build_strategy_review(
        review_id="render-sections",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        authoring_spec_path=spec_path,
        lifecycle_review_path=lifecycle_path,
        created_at=CREATED_AT,
    )
    text = result.review_markdown_path.read_text(encoding="utf-8")

    assert text.index("## 1. Summary") < text.index("## 2. Readiness Disclaimer")
    assert text.index("## 3. Source Artifact Status") < text.index(
        "## 4. Backtest Pack / Validation Summary"
    )
    assert text.index("## 4. Backtest Pack / Validation Summary") < text.index(
        "## 5. Strategy Definition"
    )
    assert text.index("## 5. Strategy Definition") < text.index("## 6. Lifecycle Summary")
    assert text.index("## 6. Lifecycle Summary") < text.index("## 7. Safety Boundary")
    assert text.index("## 8. Missing / Invalid / Blocked Details") < text.index(
        "## 9. Source Hash Table"
    )
    assert "decision: `CONTINUE_PAPER_OBSERVATION`" in text
    assert "next_actions: `Continue paper observation until thresholds are met.`" in text
    assert "pack_validation_pass_is_readiness_proof: `false`" in text
    assert "Lifecycle decision は paper / live 実行許可ではありません" in text


def test_strategy_review_markdown_inserts_optional_input_sections(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    input_contract_path = tmp_path / "configs/strategy_inputs/inputs.yaml"
    strategy_idea_path = tmp_path / "configs/strategy_ideas/idea.yaml"
    _write_input_contract(input_contract_path)
    _write_strategy_idea(strategy_idea_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = build_strategy_review(
        review_id="render-input-sections",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        input_contract_path=input_contract_path,
        strategy_idea_path=strategy_idea_path,
        created_at=CREATED_AT,
    )
    text = result.review_markdown_path.read_text(encoding="utf-8")

    assert text.index("## 5. Strategy Definition") < text.index("## 6. Input Contract Summary")
    assert text.index("## 6. Input Contract Summary") < text.index("## 7. Idea Intake Summary")
    assert text.index("## 7. Idea Intake Summary") < text.index("## 8. Lifecycle Summary")
    assert "contract_id: `ndx-breakout-inputs-001`" in text
    assert "baseline_name: `cash_or_no_trade`" in text
