from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from typer.testing import CliRunner

from sis.cli import app
from sis.edge_candidates.protocol import CandidateProtocolManifest


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def valid_protocol_payload() -> dict:
    return {
        "schema_version": "candidate_protocol_manifest.v1",
        "protocol_id": "btc-perp-verification-001",
        "mode": "verification_throughput",
        "created_at": "2026-06-30T11:36:00Z",
        "target_market": "crypto_perp",
        "target_venue_family": "bitget_usdt_futures",
        "families": [
            {
                "family_id": "intraday_breakout",
                "hypothesis": "Breakout continuation after liquidity event.",
                "generator_type": "classical_rule",
            }
        ],
        "parameter_spaces": {
            "intraday_breakout": {
                "lookback_minutes": [15, 30],
                "threshold_bps": [10, 20],
            }
        },
        "objective": {
            "primary": "after_cost_edge_over_no_trade",
            "benchmark": "NO_TRADE",
        },
        "exclusion_rules": ["no arbitrary Python eval", "no live order"],
        "sealed_holdout_definition": {
            "window_id": "holdout-2026-q3",
            "start": "2026-07-01T00:00:00Z",
            "end": "2026-09-30T23:59:59Z",
            "peek_policy": "winner-only once",
        },
        "family_event_count_policy": {
            "intraday_breakout": {
                "min_event_count_default": 100,
                "insufficient_data_state": "INCONCLUSIVE_DATA",
            }
        },
        "source_requirements": [
            {
                "source_id": "btc_15m_features",
                "schema_version": "crypto_perp_feature_pack.v1",
                "required": True,
            }
        ],
        "venue_execution_constraints": {
            "max_leverage": 3,
            "margin_mode": "isolated",
            "reduce_only_close_required": True,
        },
        "llm_policy": {
            "role": "adversarial_finding_only",
            "approval_allowed": False,
        },
        "permits_actual_cash": False,
        "permits_live_order": False,
    }


def test_protocol_manifest_accepts_default_mode_and_fixed_false_boundaries() -> None:
    manifest = CandidateProtocolManifest.model_validate(valid_protocol_payload())

    assert manifest.mode == "verification_throughput"
    assert manifest.permits_actual_cash is False
    assert manifest.permits_live_order is False
    assert manifest.boundary["actual_cash"] is False
    assert manifest.boundary["live_order_submitted"] is False


def test_protocol_manifest_rejects_missing_sealed_holdout() -> None:
    payload = valid_protocol_payload()
    payload.pop("sealed_holdout_definition")

    with pytest.raises(ValidationError, match="sealed_holdout_definition"):
        CandidateProtocolManifest.model_validate(payload)


def test_protocol_manifest_requires_risk_taker_sprint_isolation() -> None:
    payload = valid_protocol_payload()
    payload["mode"] = "risk_taker_sprint"

    with pytest.raises(ValidationError, match="mode_isolation"):
        CandidateProtocolManifest.model_validate(payload)

    payload["mode_isolation"] = True
    manifest = CandidateProtocolManifest.model_validate(payload)
    assert manifest.mode == "risk_taker_sprint"
    assert manifest.mode_isolation is True


def test_protocol_manifest_rejects_actual_cash_or_live_permission() -> None:
    payload = valid_protocol_payload()
    payload["permits_actual_cash"] = True

    with pytest.raises(ValidationError, match="permits_actual_cash"):
        CandidateProtocolManifest.model_validate(payload)

    payload = valid_protocol_payload()
    payload["permits_live_order"] = True

    with pytest.raises(ValidationError, match="permits_live_order"):
        CandidateProtocolManifest.model_validate(payload)


def test_protocol_manifest_schema_and_cli_validation(tmp_path: Path) -> None:
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(valid_protocol_payload()), encoding="utf-8")

    result = runner.invoke(
        app, ["edge-candidate-protocol-validate", "--protocol", str(protocol_path)]
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "mode=verification_throughput" in result.stdout
    assert "permits_actual_cash=false" in result.stdout
    assert "permits_live_order=false" in result.stdout

    schema = json.loads(
        (REPO_ROOT / "schemas/candidate_protocol_manifest.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(protocol_path.read_text(encoding="utf-8")))
