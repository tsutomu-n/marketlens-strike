from __future__ import annotations

from pathlib import Path

from .test_strategy_review_build import (
    CREATED_AT,
    _write_authoring_spec,
    _write_lifecycle_review,
    _write_required_artifacts,
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
    assert "| artifact | required | status | path | sha256 |" in text
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

    assert text.index("## 2. 戦略定義") < text.index("## 3. 入力artifact")
    assert text.index("## 3. 入力artifact") < text.index("## 4. Backtest Pack Summary")
    assert text.index("## 4. Backtest Pack Summary") < text.index("## 5. Lifecycle Summary")
    assert "decision: `CONTINUE_PAPER_OBSERVATION`" in text
    assert "next_actions: `Continue paper observation until thresholds are met.`" in text
    assert "pack_validation_pass_is_readiness_proof: `false`" in text
