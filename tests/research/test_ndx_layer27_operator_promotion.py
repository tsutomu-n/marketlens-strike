from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.paper.runner import run_paper_from_intents
from support.cli import invoke_cli
from research.test_ndx_layer26_paper_observation_gate import (
    _layer25_export,
    _write_xyz_quote,
)
from research.test_ndx_layer25_strategy_lab_export import _validate_json_artifact


def test_layer27_promotion_unlocks_ndx_paper_observation_only(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _layer25_export(tmp_path)
    quotes_path = _write_xyz_quote(data_dir)
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))

    assert invoke_cli(["evaluate-strategy-lab"]).exit_code == 0
    assert invoke_cli(["build-paper-candidate-pack"]).exit_code == 0
    blocked_pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert blocked_pack["selected_candidate_ids"] == []

    gate = invoke_cli(
        [
            "research-ndx-paper-observation-gate",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--quotes-path",
            str(quotes_path),
        ]
    )
    assert gate.exit_code == 0, gate.stdout
    promotion = invoke_cli(
        [
            "research-ndx-operator-promotion",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--decision",
            "promote_to_paper_observation",
            "--reviewer",
            "local_operator",
            "--approval-reason",
            "paper_observation_gate_reviewed",
        ]
    )
    assert promotion.exit_code == 0, promotion.stdout
    promotion_path = artifact_dir / "operator_promotion_decision.json"
    promotion_payload = json.loads(promotion_path.read_text(encoding="utf-8"))
    assert promotion_payload["permits_paper_candidate"] is True
    assert promotion_payload["permits_paper_intent_preview"] is True
    assert promotion_payload["permits_paper_observation"] is True
    assert promotion_payload["permits_live_order"] is False
    assert promotion_payload["live_conversion_allowed"] is False
    assert promotion_payload["wallet_used"] is False
    assert promotion_payload["venue_write_used"] is False
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_operator_promotion_decision.v1.schema.json"),
        artifact_path=promotion_path,
    )

    assert invoke_cli(["build-paper-candidate-pack"]).exit_code == 0
    pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert pack["selected_candidate_ids"]
    assert pack["candidates"][0]["status"] == "candidate"
    assert pack["candidates"][0]["block_reasons"] == []
    assert pack["operator_promotion_path"] == promotion_path.as_posix()

    assert invoke_cli(["promotion-decision", "--decision", "promote"]).exit_code == 0
    assert invoke_cli(["build-paper-intent-preview"]).exit_code == 0
    intents = json.loads((data_dir / "bot/paper_intent_preview.json").read_text())
    assert len(intents) == 1
    assert intents[0]["paper_only"] is True
    assert intents[0]["live_conversion_allowed"] is False
    assert intents[0]["wallet_used"] is False
    assert intents[0]["exchange_write_used"] is False
    assert intents[0]["operator_promotion_path"] == promotion_path.as_posix()

    summary = run_paper_from_intents(
        data_dir, intents_path=data_dir / "bot/paper_intent_preview.json"
    )
    assert summary.orders_count == 1
    assert summary.fills_count == 1
    assert summary.blocked_count == 0
    assert '"exchange_write_used": false' in summary.observation_ledger_path.read_text(
        encoding="utf-8"
    )


def test_layer27_rejects_promotion_without_approved_gate(tmp_path) -> None:
    data_dir, artifact_dir, _reports_dir = _layer25_export(tmp_path)

    result = invoke_cli(
        [
            "research-ndx-operator-promotion",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--decision",
            "promote_to_paper_observation",
            "--reviewer",
            "local_operator",
            "--approval-reason",
            "paper_observation_gate_reviewed",
        ]
    )

    assert result.exit_code == 2
    assert not (artifact_dir / "operator_promotion_decision.json").exists()


def test_layer27_rejects_promotion_when_layer25_source_hash_changes(tmp_path) -> None:
    data_dir, artifact_dir, reports_dir = _layer25_export(tmp_path)
    quotes_path = _write_xyz_quote(data_dir)
    gate = invoke_cli(
        [
            "research-ndx-paper-observation-gate",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--quotes-path",
            str(quotes_path),
        ]
    )
    assert gate.exit_code == 0, gate.stdout
    export_path = artifact_dir / "strategy_lab_research_export_manifest.json"
    export_payload = json.loads(export_path.read_text(encoding="utf-8"))
    export_payload["stale_marker"] = True
    export_path.write_text(json.dumps(export_payload, indent=2) + "\n", encoding="utf-8")

    result = invoke_cli(
        [
            "research-ndx-operator-promotion",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--decision",
            "promote_to_paper_observation",
            "--reviewer",
            "local_operator",
            "--approval-reason",
            "paper_observation_gate_reviewed",
        ]
    )

    assert result.exit_code == 2
    assert "hash mismatch" in result.stdout


def test_layer27_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        json.loads(
            Path("schemas/ndx_operator_promotion_decision.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
    )
