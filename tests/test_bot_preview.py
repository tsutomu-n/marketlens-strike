from sis.bot.preview import build_bot_preview
from sis.storage.jsonl_store import read_json, write_json


def _write_ready_artifacts(data_dir):
    write_json(
        data_dir / "ops/phase_gate_review_summary.json",
        {"phase_gate_decision": "READ_ONLY_GO", "phase2_entry_allowed": True},
    )
    write_json(
        data_dir / "ops/trade_xyz_quote_collection_summary.json",
        {
            "venue": "trade_xyz",
            "row_count": 1,
            "requested_symbols": ["SP500"],
            "collected_symbols": ["SP500"],
        },
    )
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-27.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text('{"venue":"trade_xyz","canonical_symbol":"SP500"}\n', encoding="utf-8")


def test_bot_preview_holds_even_when_read_only_gate_is_ready(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_ready_artifacts(data_dir)

    result = build_bot_preview(data_dir)

    assert result.decision == "HOLD"
    assert result.ready_for_bot_logic is True
    assert result.reason_codes == ["BOT_ORDER_LOGIC_NOT_IMPLEMENTED"]
    payload = read_json(result.decision_path)
    assert payload["schema_version"] == "bot_preview.v1"
    assert payload["decision"] == "HOLD"
    assert payload["venue"] == "trade_xyz"
    assert payload["symbols_checked"] == ["SP500"]
    assert payload["live_order_submitted"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    report = result.report_path.read_text(encoding="utf-8")
    assert "No order candidates are produced in bot-preview v1." in report


def test_bot_preview_records_missing_artifact_reasons(tmp_path) -> None:
    data_dir = tmp_path / "data"

    result = build_bot_preview(data_dir)

    assert result.ready_for_bot_logic is False
    assert "MISSING_PHASE_GATE_SUMMARY" in result.reason_codes
    assert "MISSING_TRADE_XYZ_QUOTE_SUMMARY" in result.reason_codes
    assert "MISSING_TRADE_XYZ_QUOTE_WINDOW" in result.reason_codes
    payload = read_json(result.decision_path)
    assert "Run `uv run sis phase-gate-review`." in payload["next_actions"]
    assert (
        "Run `uv run sis collect-trade-xyz-quotes --write-summary --write-report`."
        in payload["next_actions"]
    )


def test_bot_preview_records_phase_gate_not_ready(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_ready_artifacts(data_dir)
    write_json(
        data_dir / "ops/phase_gate_review_summary.json",
        {"phase_gate_decision": "NO_GO", "phase2_entry_allowed": False},
    )

    result = build_bot_preview(data_dir)

    assert result.ready_for_bot_logic is False
    payload = read_json(result.decision_path)
    assert "PHASE_GATE_NOT_READ_ONLY_GO" in payload["reason_codes"]
    assert payload["phase_gate_decision"] == "NO_GO"
