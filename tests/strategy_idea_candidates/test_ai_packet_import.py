from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sis.cli import app

from .test_candidate_cli import _perp_input_files


runner = CliRunner()


def _build_candidate_outputs(tmp_path: Path) -> tuple[Path, Path]:
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
            "1",
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp"),
        ],
    )
    assert result.exit_code == 0, result.stdout
    return (
        tmp_path / "data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json",
        tmp_path / "data/strategy_idea_candidates/btc-perp/search_ledger.jsonl",
    )


def _build_packet(tmp_path: Path) -> Path:
    candidate_set_path, ledger_path = _build_candidate_outputs(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-ai-packet-build",
            "--candidate-set",
            str(candidate_set_path),
            "--ledger",
            str(ledger_path),
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp/ai_packet"),
        ],
    )
    assert result.exit_code == 0, result.stdout
    return tmp_path / "data/strategy_idea_candidates/btc-perp/ai_packet/ai_candidate_packet.json"


def _valid_ai_response(prompt_hash: str) -> dict:
    return {
        "prompt_hash": prompt_hash,
        "provider": "manual-packet",
        "model": "manual-ai",
        "candidates": [
            {
                "candidate_id": "ai-perp-momentum-001",
                "family": "perp_momentum_continuation",
                "title": "BTCUSDT mark-index momentum continuation variation",
                "hypothesis_template": (
                    "BTCUSDT may continue after mark-index spread confirms momentum."
                ),
                "signal_expression": "mark_return_12 > 1.1 * realized_volatility",
                "side_bias": "long",
                "parameter_set": {
                    "side_bias": "long",
                    "lookback": 12,
                    "breakout_z": 1.1,
                    "venue": "bitget",
                    "product_type": "USDT-FUTURES",
                    "margin_mode": "isolated",
                    "margin_coin": "USDT",
                    "leverage": 3,
                    "funding_assumption": "funding paid or received during hold is modeled",
                    "fee_model_ref": "bitget_usdt_futures_taker_fee_estimate",
                    "slippage_model_ref": "bps_stress_model",
                    "liquidation_buffer_bps": 2500,
                    "max_position_notional_usd": 100,
                    "max_daily_loss_usd": 25,
                    "kill_conditions": ["spread_bps_gt_15"],
                },
                "feature_columns_used": ["mark_price", "index_price", "funding_rate"],
            }
        ],
    }


def test_ai_packet_excludes_sensitive_and_exchange_write_fields(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = _build_packet(tmp_path)

    packet_text = packet_path.read_text(encoding="utf-8")
    report_text = packet_path.with_suffix(".md").read_text(encoding="utf-8")
    combined = f"{packet_text}\n{report_text}".lower()
    assert "secret" not in combined
    assert "account" not in combined
    assert "wallet" not in combined
    assert "exchange_write" not in combined
    assert "exchange-write" not in combined


def test_ai_import_records_ai_generated_candidates_and_ledger(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = _build_packet(tmp_path)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    response_path = tmp_path / "ai_response.json"
    response_path.write_text(
        json.dumps(_valid_ai_response(packet["ai_input_hash"])),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-ai-import",
            "--packet",
            str(packet_path),
            "--response",
            str(response_path),
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp/ai_import"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    imported_path = (
        tmp_path
        / "data/strategy_idea_candidates/btc-perp/ai_import/strategy_idea_candidate_set.json"
    )
    ledger_path = tmp_path / "data/strategy_idea_candidates/btc-perp/ai_import/search_ledger.jsonl"
    payload = json.loads(imported_path.read_text(encoding="utf-8"))
    imported = payload["candidate_inventory"][-1]
    assert imported["candidate_status"] == "UNVERIFIED_CANDIDATE"
    assert imported["decision"] == "REJECTED"
    assert imported["raw_validation_metrics"]["source_kind"] == "ai_generated"
    assert imported["raw_validation_metrics"]["prompt_hash"] == packet["ai_input_hash"]

    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["source_kind"] == "ai_generated"
    assert rows[-1]["prompt_hash"] == packet["ai_input_hash"]
    assert rows[-1]["decision"] == "REJECTED"


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda response: response.pop("prompt_hash"), "prompt_hash"),
        (
            lambda response: response["candidates"][0]["parameter_set"].__setitem__(
                "product_type", "SPOT"
            ),
            "USDT-FUTURES",
        ),
        (
            lambda response: response["candidates"][0]["parameter_set"].pop(
                "liquidation_buffer_bps"
            ),
            "liquidation_buffer_bps",
        ),
        (
            lambda response: response["candidates"][0].__setitem__("permits_live_order", True),
            "live permission",
        ),
    ],
)
def test_ai_import_rejects_unsafe_or_malformed_response(
    tmp_path: Path, monkeypatch, mutator, expected: str
) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = _build_packet(tmp_path)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    response = _valid_ai_response(packet["ai_input_hash"])
    mutator(response)
    response_path = tmp_path / "ai_response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-ai-import",
            "--packet",
            str(packet_path),
            "--response",
            str(response_path),
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp/ai_import"),
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert expected in result.stdout


def test_ai_import_rejects_invalid_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = _build_packet(tmp_path)
    response_path = tmp_path / "ai_response.json"
    response_path.write_text("{not json", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-ai-import",
            "--packet",
            str(packet_path),
            "--response",
            str(response_path),
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "invalid JSON" in result.stdout
