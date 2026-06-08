from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from research.helpers import CONFIG_DIR
from support.cli import invoke_cli
from sis.research.dag.review_import import ReviewImportError
from sis.research.dag.review_import import import_review_result
from sis.research.dag.review_pack import ReviewPackResult
from sis.research.dag.review_pack import build_review_pack


FIXTURE_DIR = Path("tests/fixtures/research_layer_2_2/reviews")


def _export_and_pack(tmp_path: Path) -> ReviewPackResult:
    data_dir = tmp_path / "data/research/ndx"
    result = invoke_cli(
        [
            "research-layer22-export",
            "--root",
            str(CONFIG_DIR),
            "--out",
            str(data_dir),
        ]
    )
    assert result.exit_code == 0, result.stdout
    return build_review_pack(root=CONFIG_DIR, out_dir=data_dir / "review")


def _fixture_payload(name: str, pack_hash: str) -> dict[str, Any]:
    text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
    return json.loads(text.replace("sha256:PACK_HASH_PLACEHOLDER", pack_hash))


def _write_review(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_review_import_writes_normalized_review_and_report(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _write_review(
        pack.input_path.parent / "llm_review_result.json",
        _fixture_payload("valid_approve.json", pack.pack_hash),
    )

    result = import_review_result(pack_path=pack.input_path, result_path=review_path)

    assert result.normalized_path.exists()
    assert result.report_path.exists()
    assert result.review.review_id == "review.fixture.approve"


def test_review_import_rejects_pack_hash_mismatch(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _write_review(
        pack.input_path.parent / "llm_review_result.json",
        _fixture_payload("invalid_pack_hash_mismatch.json", pack.pack_hash),
    )

    with pytest.raises(ReviewImportError, match="pack_hash mismatch"):
        import_review_result(pack_path=pack.input_path, result_path=review_path)


def test_review_import_rejects_unknown_evidence_ref(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _write_review(
        pack.input_path.parent / "llm_review_result.json",
        _fixture_payload("invalid_unknown_evidence_ref.json", pack.pack_hash),
    )

    with pytest.raises(ReviewImportError, match="unknown evidence_refs"):
        import_review_result(pack_path=pack.input_path, result_path=review_path)


def test_review_import_rejects_severity_counts_mismatch(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    payload = _fixture_payload("valid_approve.json", pack.pack_hash)
    payload["severity_counts"]["INFO"] = 0
    review_path = _write_review(pack.input_path.parent / "llm_review_result.json", payload)

    with pytest.raises(ReviewImportError, match="severity_counts"):
        import_review_result(pack_path=pack.input_path, result_path=review_path)


def test_review_import_rejects_blocker_with_approve(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    payload = _fixture_payload("valid_approve.json", pack.pack_hash)
    payload["overall_decision"] = "APPROVE"
    payload["findings"][0]["severity"] = "BLOCKER"
    payload["findings"][0]["category"] = "temporal_leakage"
    payload["severity_counts"] = {"BLOCKER": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    review_path = _write_review(pack.input_path.parent / "llm_review_result.json", payload)

    with pytest.raises(ReviewImportError, match="BLOCKER"):
        import_review_result(pack_path=pack.input_path, result_path=review_path)


def test_review_import_rejects_unknown_human_decision_link(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    payload = _fixture_payload("valid_warn_requires_resolution.json", pack.pack_hash)
    payload["findings"][0]["human_decision_id"] = "HD_UNKNOWN"
    review_path = _write_review(pack.input_path.parent / "llm_review_result.json", payload)

    with pytest.raises(ReviewImportError, match="human_decision_id"):
        import_review_result(pack_path=pack.input_path, result_path=review_path)
