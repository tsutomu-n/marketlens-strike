from sis.models import Decision
from sis.reports.go_no_go_trade_xyz import (
    build_trade_xyz_go_no_go_report,
    has_trade_xyz_artifacts,
    latest_trade_xyz_quote,
    trade_xyz_summary_row_count,
)
from sis.storage.jsonl_store import write_json


def test_trade_xyz_artifact_helpers_detect_local_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    assert not has_trade_xyz_artifacts(data_dir)
    assert latest_trade_xyz_quote(data_dir) is None
    assert (
        trade_xyz_summary_row_count(data_dir / "ops/trade_xyz_quote_collection_summary.json") == 0
    )

    write_json(
        data_dir / "registry/trade_xyz_instrument_registry.json",
        [{"venue": "trade_xyz", "canonical_symbol": "NVDA"}],
    )
    quotes_dir = data_dir / "raw/quotes/trade_xyz"
    quotes_dir.mkdir(parents=True)
    old_quote = quotes_dir / "2026-05-26.jsonl"
    latest_quote = quotes_dir / "2026-05-27.jsonl"
    old_quote.write_text('{"canonical_symbol":"AAPL"}\n', encoding="utf-8")
    latest_quote.write_text('{"canonical_symbol":"NVDA"}\n', encoding="utf-8")
    write_json(
        data_dir / "ops/trade_xyz_quote_collection_summary.json",
        {"venue": "trade_xyz", "row_count": "3"},
    )

    assert has_trade_xyz_artifacts(data_dir)
    assert latest_trade_xyz_quote(data_dir) == latest_quote
    assert (
        trade_xyz_summary_row_count(data_dir / "ops/trade_xyz_quote_collection_summary.json") == 3
    )


def test_build_trade_xyz_go_no_go_report_reports_go_when_artifacts_exist(tmp_path) -> None:
    data_dir = tmp_path / "data"
    write_json(
        data_dir / "registry/trade_xyz_instrument_registry.json",
        [{"venue": "trade_xyz", "canonical_symbol": "NVDA"}],
    )
    (data_dir / "raw/quotes/trade_xyz").mkdir(parents=True)
    (data_dir / "raw/quotes/trade_xyz/2026-05-27.jsonl").write_text(
        '{"venue":"trade_xyz","canonical_symbol":"NVDA"}\n',
        encoding="utf-8",
    )
    write_json(
        data_dir / "ops/trade_xyz_quote_collection_summary.json",
        {"venue": "trade_xyz", "row_count": 1},
    )
    (data_dir / "normalized").mkdir(parents=True)
    (data_dir / "normalized/quotes.parquet").write_bytes(b"placeholder")
    write_json(
        data_dir / "ops/phase_gate_review_summary.json",
        {"phase_gate_decision": "READ_ONLY_GO"},
    )

    report = build_trade_xyz_go_no_go_report(data_dir)

    assert report.decision == Decision.GO
    assert report.blockers == []
    assert [item.venue for item in report.venue_decisions] == ["trade_xyz"]
    assert report.next_actions == []


def test_build_trade_xyz_go_no_go_report_lists_missing_artifact_actions(tmp_path) -> None:
    data_dir = tmp_path / "data"
    report = build_trade_xyz_go_no_go_report(data_dir)

    assert report.decision == Decision.NO_GO
    assert report.venue_decisions[0].main_blocker == "Trade[XYZ] registry generated"
    assert "Trade[XYZ] registry generated" in report.blockers
    assert "Run `uv run sis probe trade-xyz`." in report.next_actions
    assert (
        "Run `uv run sis collect-trade-xyz-quotes --write-summary --write-report`."
        in report.next_actions
    )
