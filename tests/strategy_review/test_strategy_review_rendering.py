from __future__ import annotations

from pathlib import Path

from .test_strategy_review_build import (
    CREATED_AT,
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

    assert "この review は人間の戦略レビュー用 artifact" in text
    assert "alpha、paper readiness、live readiness を証明しません" in text
    assert "pack validation PASS でも収益性、paper移行可否、live実行可否は証明しません" in text
    assert "| artifact | required | status | path | sha256 |" in text
    assert CREATED_AT in text
