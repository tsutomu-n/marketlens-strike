from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.edge_candidates.external_venue_adapter import (
    ExternalVenueAdapterRunError,
    ProfitCoreExternalVenueAdapterStatus,
    build_and_write_external_venue_adapter_run,
    build_external_venue_adapter_run,
)
from sis.strategy_inputs.io import write_json_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64
runner = CliRunner()


def _write_virtual_gate(tmp_path: Path, *, gate_state: str = "LOCAL_MOCK_VERIFIED") -> Path:
    path = tmp_path / "virtual_execution_gate.json"
    blocker_codes = []
    if gate_state != "LOCAL_MOCK_VERIFIED":
        blocker_codes = ["backtest_gate_not_shortlist_for_virtual"]
    write_json_artifact(
        path,
        {
            "schema_version": "virtual_execution_gate.v1",
            "gate_id": "idea-cand-001-virtual-gate",
            "evaluated_at": "2026-07-01T06:50:00Z",
            "candidate_id": "idea-cand-001",
            "mode": "verification_throughput",
            "gate_state": gate_state,
            "blocker_codes": blocker_codes,
            "lifecycle_events": [
                {"event_type": "SUBMIT_ACK", "order_id": "virtual-order-001"},
                {
                    "event_type": "PARTIAL_FILL",
                    "order_id": "virtual-order-001",
                    "filled_quantity": 0.5,
                    "position_after": 0.5,
                },
                {"event_type": "CANCEL_ACK", "order_id": "virtual-order-001"},
                {
                    "event_type": "RECONCILED_FLAT",
                    "order_id": "virtual-order-001",
                    "position_after": 0.0,
                },
            ],
            "cash_metric_basis": "virtual_exchange",
            "evidence_basis": "virtual_exchange",
            "actual_cash": False,
            "permits_live_order": False,
            "permits_paper_order": False,
            "permits_actual_cash": False,
            "production_exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "virtual_pnl_evaluated": False,
            "artifact_refs": {
                "candidate_set_path": "candidate_set.json",
                "candidate_set_sha256": SHA256_A,
                "factory_summary_path": "edge_candidate_factory_summary.json",
                "factory_summary_sha256": SHA256_A,
                "multiplicity_account_path": "trial_multiplicity_account.json",
                "multiplicity_account_sha256": SHA256_A,
                "backtest_kill_gate_path": "backtest_kill_gate.json",
                "backtest_kill_gate_sha256": SHA256_A,
            },
            "summary": {
                "submit_ack_checked": True,
                "partial_fill_checked": True,
                "cancel_checked": True,
                "duplicate_prevention_checked": True,
                "flat_reconciliation_checked": True,
                "candidate_decision": "SHORTLISTED",
                "backtest_gate_state": "SHORTLIST_FOR_VIRTUAL",
                "multiplicity_success_only_reporting": False,
                "multiplicity_sealed_test_used_for_selection": False,
                "unexecutable_reason_count": 0,
                "blocker_count": len(blocker_codes),
                "profit_evidence": False,
            },
        },
    )
    return path


def _write_adapter_plan(
    tmp_path: Path,
    *,
    network_opt_in: bool = True,
    include_recorded_http: bool = True,
    include_all_docs: bool = True,
    secret_header: bool = False,
) -> Path:
    path = tmp_path / "external_adapter_plan.json"
    payload = _adapter_plan_payload(
        network_opt_in=network_opt_in,
        include_recorded_http=include_recorded_http,
        include_all_docs=include_all_docs,
        secret_header=secret_header,
    )
    write_json_artifact(path, payload)
    return path


def _adapter_plan_payload(
    *,
    network_opt_in: bool,
    include_recorded_http: bool,
    include_all_docs: bool,
    secret_header: bool,
) -> dict:
    docs = [
        {
            "doc_id": "bitget_demo_rest_api",
            "url": "https://www.bitget.com/api-doc/common/demotrading/restapi",
            "verified_at_jst": "2026-07-01_16:38 JST",
            "finding_summary": "Demo API requires Demo API Key and paptrading: 1 header.",
        },
        {
            "doc_id": "bitget_request_interaction_rate_limit",
            "url": "https://www.bitget.com/api-doc/common/signature-samaple/interaction",
            "verified_at_jst": "2026-07-01_16:38 JST",
            "finding_summary": "Public market information interface rate limit is max 20 req/sec.",
        },
    ]
    if include_all_docs:
        docs.append(
            {
                "doc_id": "bitget_terms_of_use",
                "url": "https://www.bitget.com/support/articles/360014944032-terms-of-use",
                "verified_at_jst": "2026-07-01_16:38 JST",
                "finding_summary": "Terms last updated June 16, 2026; jurisdiction must be rechecked.",
            }
        )
    headers = {"accept": "application/json"}
    if secret_header:
        headers["ACCESS-KEY"] = "raw-key"
    recorded_http = []
    if include_recorded_http:
        recorded_http = [
            {
                "record_id": "bitget-contracts-recorded",
                "endpoint_id": "bitget.mix.market.contracts",
                "method": "GET",
                "url": "https://api.bitget.com/api/v2/mix/market/contracts",
                "request_headers": headers,
                "request_params": {"productType": "USDT-FUTURES"},
                "status_code": 200,
                "response_body_sha256": SHA256_A,
                "recorded_at": "2026-07-01T07:38:00Z",
                "source_kind": "manual_recorded_response",
                "raw_response_body_stored": False,
            }
        ]
    return {
        "run_id": "p10-bitget-public-read-only",
        "venue": "bitget",
        "adapter_mode": "public_read_only",
        "network_opt_in": network_opt_in,
        "official_doc_refs": docs,
        "recorded_http": recorded_http,
        "rate_limit_policy": {
            "max_requests_per_second": 20,
            "source_doc_id": "bitget_request_interaction_rate_limit",
        },
        "operator_jurisdiction_recheck_required": True,
        "credential_policy": {
            "credentials_required": False,
            "credentials_used": False,
            "credential_values_redacted": True,
        },
    }


def test_external_venue_adapter_records_bitget_read_only_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_and_write_external_venue_adapter_run(
        virtual_gate_path=_write_virtual_gate(tmp_path),
        adapter_plan_path=_write_adapter_plan(tmp_path),
        out_dir=tmp_path / "external_adapter",
    )

    run = result.run

    assert run.schema_version == "profit_core_external_venue_adapter_run.v1"
    assert run.venue == "bitget"
    assert run.adapter_mode == "public_read_only"
    assert run.candidate_id == "idea-cand-001"
    assert (
        run.adapter_status
        == ProfitCoreExternalVenueAdapterStatus.RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW
    )
    assert run.blockers == []
    assert run.network_opt_in is True
    assert run.network_attempted is False
    assert run.credentials_used is False
    assert run.credential_values_redacted is True
    assert run.external_write_used is False
    assert run.exchange_write_allowed is False
    assert run.order_submit_allowed is False
    assert run.actual_cash is False
    assert run.demo_or_testnet_result_is_actual_cash is False
    assert run.profit_evidence is False
    assert run.recorded_http[0].request_headers == {"accept": "application/json"}
    assert result.run_path.exists()


def test_external_venue_adapter_schema_validates_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    result = build_and_write_external_venue_adapter_run(
        virtual_gate_path=_write_virtual_gate(tmp_path),
        adapter_plan_path=_write_adapter_plan(tmp_path),
        out_dir=tmp_path / "external_adapter",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_external_venue_adapter_run.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.run.model_dump(mode="json"))


def test_external_venue_adapter_blocks_without_network_opt_in(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    run = build_external_venue_adapter_run(
        virtual_gate_path=_write_virtual_gate(tmp_path),
        adapter_plan_path=_write_adapter_plan(tmp_path, network_opt_in=False),
    )

    assert run.adapter_status == ProfitCoreExternalVenueAdapterStatus.BLOCKED_NETWORK_OPT_IN
    assert {blocker.blocker_code for blocker in run.blockers} == {"NETWORK_OPT_IN_REQUIRED"}
    assert run.network_attempted is False
    assert run.order_submit_allowed is False


def test_external_venue_adapter_blocks_missing_recorded_response(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    run = build_external_venue_adapter_run(
        virtual_gate_path=_write_virtual_gate(tmp_path),
        adapter_plan_path=_write_adapter_plan(tmp_path, include_recorded_http=False),
    )

    assert (
        run.adapter_status == ProfitCoreExternalVenueAdapterStatus.BLOCKED_RECORDED_RESPONSE_MISSING
    )
    assert {blocker.blocker_code for blocker in run.blockers} == {
        "RECORDED_REQUEST_RESPONSE_REQUIRED"
    }
    assert run.actual_cash is False


def test_external_venue_adapter_blocks_missing_official_doc_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    run = build_external_venue_adapter_run(
        virtual_gate_path=_write_virtual_gate(tmp_path),
        adapter_plan_path=_write_adapter_plan(tmp_path, include_all_docs=False),
    )

    assert (
        run.adapter_status
        == ProfitCoreExternalVenueAdapterStatus.BLOCKED_OFFICIAL_DOCS_VERIFICATION
    )
    assert {blocker.blocker_code for blocker in run.blockers} == {
        "OFFICIAL_DOC_VERIFICATION_INCOMPLETE"
    }
    assert run.external_write_used is False


def test_external_venue_adapter_blocks_unverified_local_virtual_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    run = build_external_venue_adapter_run(
        virtual_gate_path=_write_virtual_gate(tmp_path, gate_state="BLOCKED_BY_BACKTEST_GATE"),
        adapter_plan_path=_write_adapter_plan(tmp_path),
    )

    assert run.adapter_status == ProfitCoreExternalVenueAdapterStatus.BLOCKED_LOCAL_VIRTUAL_GATE
    assert {blocker.blocker_code for blocker in run.blockers} == {"LOCAL_VIRTUAL_GATE_NOT_VERIFIED"}
    assert run.network_attempted is False


def test_external_venue_adapter_rejects_secret_like_recorded_http(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ExternalVenueAdapterRunError, match="secret-like"):
        build_external_venue_adapter_run(
            virtual_gate_path=_write_virtual_gate(tmp_path),
            adapter_plan_path=_write_adapter_plan(tmp_path, secret_header=True),
        )


def test_external_venue_adapter_cli_writes_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "external_adapter_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-external-venue-adapter-record",
            "--virtual-gate",
            str(_write_virtual_gate(tmp_path)),
            "--adapter-plan",
            str(_write_adapter_plan(tmp_path)),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "credentials_used=false" in result.stdout
    assert "external_write_used=false" in result.stdout
    assert "order_submit_allowed=false" in result.stdout
    assert "actual_cash=false" in result.stdout
    assert "status=pass" in result.stdout
    assert "adapter_status=RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW" in result.stdout
    assert (out_dir / "profit_core_external_venue_adapter_run.json").exists()
