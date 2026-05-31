import json
from datetime import UTC, datetime, timedelta

from typer.testing import CliRunner

from sis.cli import app
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.coverage import build_trade_xyz_quote_coverage_manifest


def _quote_row(ts: datetime, *, raw_payload_ref: str | None = "fixture://row") -> dict:
    return {
        "ts_client": ts.isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "SP500",
        "venue_symbol": "SP500",
        "source": "test",
        "raw_payload_sha256": f"hash-{int(ts.timestamp())}",
        "recv_ts_ms": int(ts.timestamp() * 1000),
        "source_ts_ms": int(ts.timestamp() * 1000),
        "best_bid": 99.9,
        "best_ask": 100.1,
        "exec_buy_price": 100.1,
        "exec_sell_price": 99.9,
        "oracle_ts_ms": int(ts.timestamp() * 1000),
        "funding_rate": 0.0,
        "taker_fee_bps": 9.0,
        "maker_fee_bps": 3.0,
        "raw_payload_ref": raw_payload_ref,
    }


def _write_quotes(path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_trade_xyz_quote_coverage_manifest_passes_for_sufficient_span(tmp_path) -> None:
    data_dir = tmp_path / "data"
    start = datetime(2026, 5, 1, tzinfo=UTC)
    rows = [_quote_row(start + timedelta(days=offset)) for offset in range(31)]
    _write_quotes(data_dir / "raw/quotes/trade_xyz/2026-05.jsonl", rows)

    manifest = build_trade_xyz_quote_coverage_manifest(
        data_dir=data_dir,
        min_days=30.0,
        max_gap_minutes=24 * 60,
    )

    assert manifest["coverage_passed"] is True
    assert manifest["per_symbol"]["SP500"]["coverage_status"] == "pass"
    assert manifest["per_symbol"]["SP500"]["distinct_utc_date_count"] == 31
    assert (data_dir / "manifests/trade_xyz_quote_coverage_manifest.json").exists()


def test_trade_xyz_quote_coverage_manifest_excludes_untraceable_rows_by_default(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    start = datetime(2026, 5, 1, tzinfo=UTC)
    rows = [
        _quote_row(start, raw_payload_ref=None),
        _quote_row(start + timedelta(minutes=30)),
    ]
    _write_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-01.jsonl", rows)

    manifest = build_trade_xyz_quote_coverage_manifest(
        data_dir=data_dir,
        min_days=30.0,
        max_gap_minutes=10.0,
    )

    item = manifest["per_symbol"]["SP500"]
    assert manifest["coverage_passed"] is False
    assert manifest["traceable_only"] is True
    assert manifest["raw_row_count"] == 2
    assert manifest["row_count"] == 1
    assert manifest["excluded_missing_raw_payload_ref_count"] == 1
    assert manifest["excluded_missing_raw_payload_ref_by_symbol"] == {"SP500": 1}
    assert item["coverage_status"] == "insufficient"
    assert item["insufficient_reasons"] == [
        "span_days_below_min",
        "single_or_missing_gap_basis",
    ]
    assert item["missing_rates"]["raw_payload_ref"] == 0.0
    assert item["excluded_missing_raw_payload_ref_count"] == 1


def test_trade_xyz_quote_coverage_manifest_can_include_untraceable_rows(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    start = datetime(2026, 5, 1, tzinfo=UTC)
    rows = [
        _quote_row(start, raw_payload_ref=None),
        _quote_row(start + timedelta(minutes=30)),
    ]
    _write_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-01.jsonl", rows)

    manifest = build_trade_xyz_quote_coverage_manifest(
        data_dir=data_dir,
        min_days=30.0,
        max_gap_minutes=10.0,
        traceable_only=False,
    )

    item = manifest["per_symbol"]["SP500"]
    assert manifest["coverage_passed"] is False
    assert manifest["traceable_only"] is False
    assert manifest["raw_row_count"] == 2
    assert manifest["row_count"] == 2
    assert manifest["excluded_missing_raw_payload_ref_count"] == 0
    assert item["insufficient_reasons"] == [
        "span_days_below_min",
        "single_or_missing_gap_basis",
        "raw_payload_ref_missing",
    ]
    assert item["observed_max_gap_seconds"] == 1800.0
    assert item["gap_segment_count"] == 2
    assert item["selected_gap_segment_row_count"] == 1
    assert item["missing_rates"]["raw_payload_ref"] == 0.5


def test_trade_xyz_quote_coverage_manifest_uses_latest_contiguous_segment(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    start = datetime(2026, 5, 1, tzinfo=UTC)
    rows = [
        _quote_row(start),
        _quote_row(start + timedelta(minutes=30)),
        _quote_row(start + timedelta(minutes=31)),
        _quote_row(start + timedelta(minutes=32)),
    ]
    _write_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-01.jsonl", rows)

    manifest = build_trade_xyz_quote_coverage_manifest(
        data_dir=data_dir,
        min_days=30.0,
        max_gap_minutes=10.0,
    )

    item = manifest["per_symbol"]["SP500"]
    assert item["row_count"] == 4
    assert item["gap_segment_count"] == 2
    assert item["selected_gap_segment_row_count"] == 3
    assert item["observed_max_gap_seconds"] == 1800.0
    assert item["max_gap_seconds"] == 60.0
    assert item["insufficient_reasons"] == ["span_days_below_min"]


def test_trade_xyz_quote_coverage_manifest_reports_no_traceable_rows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    start = datetime(2026, 5, 1, tzinfo=UTC)
    rows = [_quote_row(start, raw_payload_ref=None)]
    _write_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-01.jsonl", rows)

    manifest = build_trade_xyz_quote_coverage_manifest(
        data_dir=data_dir,
        min_days=30.0,
        max_gap_minutes=10.0,
    )

    item = manifest["per_symbol"]["SP500"]
    assert manifest["coverage_passed"] is False
    assert manifest["row_count"] == 0
    assert manifest["raw_row_count"] == 1
    assert item["row_count"] == 0
    assert item["raw_row_count"] == 1
    assert item["insufficient_reasons"] == ["no_traceable_rows"]


def test_trade_xyz_quote_coverage_cli_writes_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    start = datetime(2026, 5, 1, tzinfo=UTC)
    _write_quotes(data_dir / "raw/quotes/trade_xyz/2026-05-01.jsonl", [_quote_row(start)])

    result = CliRunner().invoke(
        app,
        [
            "build-trade-xyz-quote-coverage",
            "--symbols",
            "SP500",
            "--min-days",
            "30",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "manifest_path=" in result.stdout
    assert "coverage_passed=False" in result.stdout
    assert "traceable_only=True" in result.stdout
    assert "excluded_missing_raw_payload_ref_count=0" in result.stdout
    payload = read_json(data_dir / "manifests/trade_xyz_quote_coverage_manifest.json")
    assert payload["per_symbol"]["SP500"]["coverage_status"] == "insufficient"
