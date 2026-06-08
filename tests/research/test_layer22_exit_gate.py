from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.helpers import CONFIG_DIR
from support.cli import invoke_cli
from sis.research.dag.exit_gate import run_exit_gate
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


def _normalized_review(pack: ReviewPackResult, fixture_name: str) -> Path:
    result_path = pack.input_path.parent / "llm_review_result.json"
    result_path.write_text(
        json.dumps(_fixture_payload(fixture_name, pack.pack_hash), indent=2) + "\n",
        encoding="utf-8",
    )
    return import_review_result(pack_path=pack.input_path, result_path=result_path).normalized_path


def _write_resolutions(pack: ReviewPackResult, *decision_ids: str) -> Path:
    path = pack.input_path.parent / "layer_2_2_human_resolutions.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "layer_2_2_human_resolutions.v1",
                "dag_id": "HYP-NDX-001",
                "pack_hash": pack.pack_hash,
                "resolutions": [
                    {
                        "decision_id": decision_id,
                        "selected_option": "accept_risk",
                        "reason": "Accepted as a tracked Layer 2.2 review risk.",
                        "resolved_by": "human",
                        "resolved_at": "2026-06-07T21:35:00+09:00",
                    }
                    for decision_id in decision_ids
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_exit_gate_approves_clean_review_and_writes_freeze_manifest(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _normalized_review(pack, "valid_approve.json")

    result = run_exit_gate(
        root=CONFIG_DIR,
        pack_path=pack.input_path,
        review_path=review_path,
        out_dir=pack.input_path.parent,
    )

    assert result.decision.decision == "APPROVE_2_3"
    assert result.decision_path.exists()
    assert result.freeze_manifest_path is not None
    assert result.freeze_manifest_path.exists()


def test_exit_gate_revises_for_blocker_and_does_not_write_freeze_manifest(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _normalized_review(pack, "blocker_temporal_leakage.json")

    result = run_exit_gate(
        root=CONFIG_DIR,
        pack_path=pack.input_path,
        review_path=review_path,
        out_dir=pack.input_path.parent,
    )

    assert result.decision.decision == "REVISE_2_2"
    assert result.decision.blocker_count == 1
    assert result.freeze_manifest_path is None


def test_exit_gate_revises_for_unresolved_required_human_decision(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _normalized_review(pack, "valid_warn_requires_resolution.json")

    result = run_exit_gate(
        root=CONFIG_DIR,
        pack_path=pack.input_path,
        review_path=review_path,
        out_dir=pack.input_path.parent,
    )

    assert result.decision.decision == "REVISE_2_2"
    assert result.decision.unresolved_human_decisions == ["HD001"]
    assert result.decision.second_review_required is True


def test_exit_gate_rejects_seed_when_operator_confirms_rejection(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _normalized_review(pack, "reject_seed.json")
    resolutions_path = _write_resolutions(pack, "HD_REJECT")

    result = run_exit_gate(
        root=CONFIG_DIR,
        pack_path=pack.input_path,
        review_path=review_path,
        out_dir=pack.input_path.parent,
        human_resolutions_path=resolutions_path,
    )

    assert result.decision.decision == "REJECT_SEED"
    assert result.freeze_manifest_path is None


def test_exit_gate_operator_second_review_flag_revises(tmp_path) -> None:
    pack = _export_and_pack(tmp_path)
    review_path = _normalized_review(pack, "valid_approve.json")

    result = run_exit_gate(
        root=CONFIG_DIR,
        pack_path=pack.input_path,
        review_path=review_path,
        out_dir=pack.input_path.parent,
        require_second_review=True,
    )

    assert result.decision.decision == "REVISE_2_2"
    assert result.decision.second_review_required is True
