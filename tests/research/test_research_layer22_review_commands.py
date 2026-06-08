from __future__ import annotations

import json
from pathlib import Path

from research.helpers import CONFIG_DIR
from support.cli import invoke_cli
from support.cli import normalized_stdout


FIXTURE_DIR = Path("tests/fixtures/research_layer_2_2/reviews")


def _export_layer22(tmp_path: Path) -> Path:
    out_dir = tmp_path / "data/research/ndx"
    result = invoke_cli(
        [
            "research-layer22-export",
            "--root",
            str(CONFIG_DIR),
            "--out",
            str(out_dir),
        ]
    )
    assert result.exit_code == 0, result.stdout
    return out_dir


def _write_review_result(review_dir: Path, fixture_name: str) -> Path:
    pack = json.loads((review_dir / "llm_review_input.json").read_text(encoding="utf-8"))
    text = (FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")
    payload = json.loads(text.replace("sha256:PACK_HASH_PLACEHOLDER", pack["pack_hash"]))
    result_path = review_dir / "llm_review_result.json"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return result_path


def test_research_layer22_review_pack_cli_writes_expected_files(tmp_path) -> None:
    data_dir = _export_layer22(tmp_path)
    review_dir = data_dir / "review"

    result = invoke_cli(
        ["research-layer22-review-pack", "--root", str(CONFIG_DIR), "--out", str(review_dir)]
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in normalized_stdout(result)
    assert (review_dir / "llm_review_pack.md").exists()
    assert (review_dir / "llm_review_input.json").exists()
    assert (review_dir / "llm_review_prompt.md").exists()


def test_research_layer22_review_import_cli_writes_normalized_json(tmp_path) -> None:
    data_dir = _export_layer22(tmp_path)
    review_dir = data_dir / "review"
    pack_result = invoke_cli(
        ["research-layer22-review-pack", "--root", str(CONFIG_DIR), "--out", str(review_dir)]
    )
    assert pack_result.exit_code == 0, pack_result.stdout
    result_path = _write_review_result(review_dir, "valid_approve.json")

    result = invoke_cli(
        [
            "research-layer22-review-import",
            "--pack",
            str(review_dir / "llm_review_input.json"),
            "--result",
            str(result_path),
        ]
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in normalized_stdout(result)
    assert (review_dir / "normalized_review.json").exists()


def test_research_layer22_exit_gate_cli_writes_decision_and_report(tmp_path) -> None:
    data_dir = _export_layer22(tmp_path)
    review_dir = data_dir / "review"
    assert (
        invoke_cli(
            ["research-layer22-review-pack", "--root", str(CONFIG_DIR), "--out", str(review_dir)]
        ).exit_code
        == 0
    )
    result_path = _write_review_result(review_dir, "valid_approve.json")
    assert (
        invoke_cli(
            [
                "research-layer22-review-import",
                "--pack",
                str(review_dir / "llm_review_input.json"),
                "--result",
                str(result_path),
            ]
        ).exit_code
        == 0
    )

    result = invoke_cli(
        [
            "research-layer22-exit-gate",
            "--root",
            str(CONFIG_DIR),
            "--pack",
            str(review_dir / "llm_review_input.json"),
            "--review",
            str(review_dir / "normalized_review.json"),
            "--out",
            str(review_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    assert "decision=APPROVE_2_3" in normalized_stdout(result)
    assert (review_dir / "layer_2_2_exit_decision.json").exists()
    assert (review_dir / "layer_2_2_freeze_manifest.json").exists()
    assert (tmp_path / "data/reports/ndx_layer_2_2_exit_gate_report.md").exists()


def test_research_layer22_exit_gate_cli_uses_revise_exit_code(tmp_path) -> None:
    data_dir = _export_layer22(tmp_path)
    review_dir = data_dir / "review"
    assert (
        invoke_cli(
            ["research-layer22-review-pack", "--root", str(CONFIG_DIR), "--out", str(review_dir)]
        ).exit_code
        == 0
    )
    result_path = _write_review_result(review_dir, "blocker_temporal_leakage.json")
    assert (
        invoke_cli(
            [
                "research-layer22-review-import",
                "--pack",
                str(review_dir / "llm_review_input.json"),
                "--result",
                str(result_path),
            ]
        ).exit_code
        == 0
    )

    result = invoke_cli(
        [
            "research-layer22-exit-gate",
            "--root",
            str(CONFIG_DIR),
            "--pack",
            str(review_dir / "llm_review_input.json"),
            "--review",
            str(review_dir / "normalized_review.json"),
            "--out",
            str(review_dir),
        ]
    )

    assert result.exit_code == 3
    assert "decision=REVISE_2_2" in normalized_stdout(result)
