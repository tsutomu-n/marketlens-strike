from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.edge_candidate_factory.adversarial_review import (
    build_adversarial_packet,
    import_adversarial_review,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TS = datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc)


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_adversarial_packet_records_missing_source(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    missing = tmp_path / "missing.json"
    source.write_text('{"schema_version":"smart_candidate_prior_report.v1"}\n', encoding="utf-8")

    result = build_adversarial_packet(
        packet_id="adversarial-packet-001",
        created_at=TS,
        source_paths=[source, missing],
        out_dir=tmp_path / "packet",
    )

    assert result.packet["network_attempted"] is False
    assert [item["exists"] for item in result.packet["sources"]] == [True, False]
    assert result.packet["sources"][1]["sha256"] == "sha256:" + "0" * 64
    assert result.packet_path.exists()


def test_adversarial_import_ignores_approval_and_flags_missing_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.json"
    missing = tmp_path / "missing.json"
    source.write_text('{"schema_version":"smart_candidate_prior_report.v1"}\n', encoding="utf-8")
    packet = build_adversarial_packet(
        packet_id="adversarial-packet-001",
        created_at=TS,
        source_paths=[source, missing],
        out_dir=tmp_path / "packet",
    )
    response_path = tmp_path / "manual_response.json"
    response_path.write_text(
        json.dumps(
            {
                "approval": "approved for live trading",
                "review_status": "OVERCLAIM_FLAG",
                "findings": [
                    {
                        "finding_id": "finding-overclaim-001",
                        "finding_type": "OVERCLAIM_FLAG",
                        "severity": "soft",
                        "source_ref": "manual_response",
                        "claim_text": "candidate is safe for actual cash",
                        "problem": "actual cash evidence is not present",
                        "required_fix": "collect actual cash rows before claiming readiness",
                        "machine_checkable": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = import_adversarial_review(
        review_id="llm-adversarial-001",
        created_at=TS,
        packet_path=packet.packet_path,
        response_path=response_path,
        out_dir=tmp_path / "review",
    )

    review = result.review
    assert review.review_status == "MISSING_ARTIFACT"
    assert review.hard_blocker_count == 1
    assert review.soft_warning_count == 1
    assert review.llm_approval_ignored is True
    assert review.paper_execution_allowed is False
    assert review.live_allowed is False
    assert review.actual_cash_decision_allowed is False
    assert review.gate_override_allowed is False
    assert any(finding.finding_type == "MISSING_ARTIFACT" for finding in review.findings)
    Draft202012Validator(_schema("llm_adversarial_evidence_review.v1.schema.json")).validate(
        review.model_dump(mode="json")
    )
