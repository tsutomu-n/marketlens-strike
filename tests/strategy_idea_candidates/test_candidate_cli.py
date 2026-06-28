from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sis.backtest.artifact_io import sha256_file
from sis.cli import app
from sis.strategy_inputs.io import write_json_artifact
from support.cli import normalized_stdout

from .fixtures import valid_input_contract_payload, valid_input_validation_payload


runner = CliRunner()


def _perp_input_files(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "data/research/crypto_perp/source/BTCUSDT_15m.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,mark,index,spread_bps\n2026-06-17T21:00:00Z,100,99,2\n", encoding="utf-8")
    source_hash = sha256_file(source)

    contract_payload = valid_input_contract_payload(sha256=source_hash)
    contract_payload["contract_id"] = "btc-perp-inputs-001"
    contract_payload["strategy_scope"]["strategy_family"] = "crypto_perp_hypothesis"
    contract_payload["strategy_scope"]["instruments"] = ["BTCUSDT"]
    contract_payload["strategy_scope"]["timeframe"] = "15m"
    contract_payload["sources"][0]["source_id"] = "btc_usdt_perp_features"
    contract_payload["sources"][0]["path"] = "data/research/crypto_perp/source/BTCUSDT_15m.csv"
    contract_payload["sources"][0]["schema_version"] = "crypto_perp_feature_pack.v1"
    contract_payload["known_gaps"] = ["fixture_source_only"]

    validation_payload = valid_input_validation_payload()
    validation_payload["contract_id"] = "btc-perp-inputs-001"
    validation_payload["source_results"][0]["source_id"] = "btc_usdt_perp_features"
    validation_payload["source_results"][0]["path"] = (
        "data/research/crypto_perp/source/BTCUSDT_15m.csv"
    )
    validation_payload["source_results"][0]["actual_sha256"] = source_hash
    validation_payload["source_results"][0]["declared_sha256"] = source_hash

    contract_path = tmp_path / "data/strategy_inputs/btc_perp/strategy_input_contract.json"
    validation_path = (
        tmp_path / "data/strategy_inputs/btc_perp/strategy_input_contract_validation.json"
    )
    write_json_artifact(contract_path, contract_payload)
    write_json_artifact(validation_path, validation_payload)
    return contract_path, validation_path


def test_strategy_idea_candidates_build_help() -> None:
    result = runner.invoke(app, ["strategy-idea-candidates-build", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--profile" in stdout
    assert "perp-risk-taker" in stdout
    assert "--candidate-cap" in stdout
    assert "shortlist" in stdout


def test_strategy_idea_candidates_ai_commands_help() -> None:
    packet = runner.invoke(app, ["strategy-idea-candidates-ai-packet-build", "--help"])
    imported = runner.invoke(app, ["strategy-idea-candidates-ai-import", "--help"])

    assert packet.exit_code == 0
    assert "--candidate-set" in normalized_stdout(packet)
    assert "--ledger" in normalized_stdout(packet)
    assert imported.exit_code == 0
    assert "--prompt-hash" not in normalized_stdout(imported)
    assert "--response" in normalized_stdout(imported)


def test_strategy_idea_candidates_build_crypto_perp_happy_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    contract_path, validation_path = _perp_input_files(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-build",
            "--contract",
            str(contract_path),
            "--validation",
            str(validation_path),
            "--profile",
            "crypto-perp-risk-taker",
            "--candidate-cap",
            "3",
            "--shortlist-count",
            "2",
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "profile=crypto-perp-risk-taker" in result.stdout
    candidate_set_path = (
        tmp_path / "data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json"
    )
    ledger_path = tmp_path / "data/strategy_idea_candidates/btc-perp/search_ledger.jsonl"
    export_manifest_path = (
        tmp_path
        / "data/strategy_idea_candidates/btc-perp/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json"
    )
    assert candidate_set_path.exists()
    assert ledger_path.exists()
    assert export_manifest_path.exists()

    candidate_set = json.loads(candidate_set_path.read_text(encoding="utf-8"))
    assert candidate_set["producer"]["command"] == "strategy-idea-candidates-build"
    assert candidate_set["search_ledger_summary"]["candidate_cap"] == 3
    assert candidate_set["search_ledger_summary"]["candidate_count_shortlisted"] == 2
    assert candidate_set["search_ledger_summary"]["cap_rejection_count"] > 0
    assert any(
        candidate["rejection_reason"] == "candidate cap exceeded before shortlist"
        for candidate in candidate_set["candidate_inventory"]
        if candidate["decision"] == "REJECTED"
    )
    shortlisted = [
        candidate
        for candidate in candidate_set["candidate_inventory"]
        if candidate["decision"] == "SHORTLISTED"
    ]
    assert shortlisted
    for candidate in shortlisted:
        parameter_set = candidate["parameter_set"]
        assert parameter_set["venue"] == "bitget"
        assert parameter_set["product_type"] == "USDT-FUTURES"
        assert parameter_set["margin_mode"] == "isolated"
        assert parameter_set["margin_coin"] == "USDT"
        assert parameter_set["leverage"] <= 3
        assert parameter_set["funding_assumption"]
        assert parameter_set["fee_model_ref"]
        assert parameter_set["slippage_model_ref"]
        assert parameter_set["liquidation_buffer_bps"] > 0

    ledger_rows = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(ledger_rows) == len(candidate_set["candidate_inventory"])
    assert {row["source_kind"] for row in ledger_rows} == {"deterministic_generator"}
    assert {row["uses_sealed_test_for_selection"] for row in ledger_rows} == {False}
    assert any(row["decision"] == "REJECTED" for row in ledger_rows)
