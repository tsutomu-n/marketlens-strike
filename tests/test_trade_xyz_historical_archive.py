from datetime import UTC, date, datetime
import json
from pathlib import Path

import pytest

from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import read_jsonl
from sis.venues.trade_xyz.historical_archive import HistoricalL2ArchiveRequest
from sis.venues.trade_xyz.historical_archive import aws_download_command_status
from sis.venues.trade_xyz.historical_archive import (
    build_hyperliquid_historical_archive_bulk_plan,
)
from sis.venues.trade_xyz.historical_archive import (
    collect_hyperliquid_historical_asset_ctxs_archive,
)
from sis.venues.trade_xyz.historical_archive import collect_hyperliquid_historical_l2_archive
from sis.venues.trade_xyz.historical_archive import execute_hyperliquid_historical_archive_bulk_plan
from sis.venues.trade_xyz.historical_archive import (
    normalize_historical_archive_bulk_to_trade_xyz_quotes,
)
from sis.venues.trade_xyz.historical_archive import normalize_historical_archive_to_trade_xyz_quotes
from sis.venues.trade_xyz.historical_archive import (
    check_hyperliquid_historical_archive_preflight,
)


def test_historical_l2_archive_dry_run_writes_requester_pays_plan(tmp_path) -> None:
    data_dir = tmp_path / "data"

    manifest = collect_hyperliquid_historical_l2_archive(
        data_dir=data_dir,
        request=HistoricalL2ArchiveRequest(coin="xyz:XYZ100", date=date(2026, 5, 1), hour=9),
        dry_run=True,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["status"] == "planned"
    assert manifest["dry_run"] is True
    assert manifest["s3_uri"] == (
        "s3://hyperliquid-archive/market_data/20260501/9/l2Book/xyz:XYZ100.lz4"
    )
    assert manifest["download_command"][-2:] == ["--request-payer", "requester"]
    persisted = read_json(data_dir / "manifests/trade_xyz_historical_l2_archive_manifest.json")
    assert persisted["raw_lz4_path"].endswith(
        "raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.lz4"
    )


def test_historical_archive_download_command_can_use_configured_aws_command(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SIS_AWS_COMMAND", "custom-aws --profile trade")

    manifest = collect_hyperliquid_historical_l2_archive(
        data_dir=tmp_path / "data",
        request=HistoricalL2ArchiveRequest(coin="xyz:XYZ100", date=date(2026, 5, 1), hour=9),
        dry_run=True,
    )

    assert aws_download_command_status()["source"] == "SIS_AWS_COMMAND"
    assert manifest["aws_command_source"] == "SIS_AWS_COMMAND"
    assert manifest["download_command"][:3] == ["custom-aws", "--profile", "trade"]
    assert manifest["download_command"][-2:] == ["--request-payer", "requester"]


def test_historical_archive_preflight_records_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SIS_AWS_COMMAND", "custom-aws")

    def fake_runner(command: list[str]) -> tuple[int, str, str]:
        assert command == ["custom-aws", "sts", "get-caller-identity"]
        return 255, "", "Unable to locate credentials"

    manifest = check_hyperliquid_historical_archive_preflight(
        data_dir=tmp_path / "data",
        command_runner=fake_runner,
    )

    assert manifest["status"] == "fail"
    assert manifest["return_code"] == 255
    assert manifest["stderr"] == "Unable to locate credentials"
    persisted = read_json(
        tmp_path / "data/manifests/trade_xyz_historical_archive_preflight_manifest.json"
    )
    assert persisted["aws_command_source"] == "SIS_AWS_COMMAND"


def test_historical_l2_archive_execute_requires_passing_preflight(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SIS_AWS_COMMAND", "custom-aws")

    check_hyperliquid_historical_archive_preflight(
        data_dir=tmp_path / "data",
        command_runner=lambda command: (255, "", "Unable to locate credentials"),
    )

    with pytest.raises(RuntimeError, match="preflight has not passed"):
        collect_hyperliquid_historical_l2_archive(
            data_dir=tmp_path / "data",
            request=HistoricalL2ArchiveRequest(coin="SP500", date=date(2026, 5, 1), hour=9),
            dry_run=False,
            acknowledge_requester_pays=True,
        )

    manifest = read_json(tmp_path / "data/manifests/trade_xyz_historical_l2_archive_manifest.json")
    assert manifest["status"] == "blocked_preflight_failed"
    assert manifest["preflight"]["status"] == "fail"


def test_historical_l2_archive_execute_requires_requester_pays_ack(tmp_path) -> None:
    with pytest.raises(ValueError, match="requester-pays"):
        collect_hyperliquid_historical_l2_archive(
            data_dir=tmp_path / "data",
            request=HistoricalL2ArchiveRequest(coin="SP500", date=date(2026, 5, 1), hour=9),
            dry_run=False,
            acknowledge_requester_pays=False,
        )

    manifest = read_json(tmp_path / "data/manifests/trade_xyz_historical_l2_archive_manifest.json")
    assert manifest["status"] == "blocked_requires_requester_pays_ack"


def test_historical_asset_ctxs_archive_dry_run_writes_requester_pays_plan(tmp_path) -> None:
    data_dir = tmp_path / "data"

    manifest = collect_hyperliquid_historical_asset_ctxs_archive(
        data_dir=data_dir,
        archive_date=date(2026, 5, 1),
        dry_run=True,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["status"] == "planned"
    assert manifest["s3_uri"] == "s3://hyperliquid-archive/asset_ctxs/20260501.csv.lz4"
    assert manifest["download_command"][-2:] == ["--request-payer", "requester"]
    persisted = read_json(
        data_dir / "manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json"
    )
    assert persisted["decompressed_path"].endswith(
        "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    )


def test_historical_archive_bulk_plan_counts_l2_and_asset_ctx_objects(tmp_path) -> None:
    data_dir = tmp_path / "data"

    manifest = build_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        coins=["xyz:XYZ100", "xyz:SP500"],
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        hours=[0, 12],
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["date_count"] == 2
    assert manifest["estimated_l2_object_count"] == 8
    assert manifest["estimated_asset_ctx_object_count"] == 2
    assert manifest["estimated_total_object_count"] == 10
    assert manifest["l2_objects"][0]["download_command"][-2:] == [
        "--request-payer",
        "requester",
    ]
    persisted = read_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json"
    )
    assert persisted["requester_pays_ack_required"] is True


def test_historical_archive_bulk_execution_dry_run_selects_limited_objects(tmp_path) -> None:
    data_dir = tmp_path / "data"
    build_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        coins=["xyz:XYZ100", "xyz:SP500"],
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        hours=[0, 12],
    )

    manifest = execute_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        dry_run=True,
        max_objects=3,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert manifest["status"] == "planned"
    assert manifest["selected_object_count"] == 3
    assert manifest["downloaded_object_count"] == 0
    assert manifest["selected_objects"][0]["kind"] == "asset_ctxs"


def test_historical_archive_bulk_execution_requires_requester_pays_ack(tmp_path) -> None:
    data_dir = tmp_path / "data"
    build_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        coins=["xyz:XYZ100"],
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
        hours=[0],
    )

    with pytest.raises(ValueError, match="requester-pays"):
        execute_hyperliquid_historical_archive_bulk_plan(
            data_dir=data_dir,
            dry_run=False,
            acknowledge_requester_pays=False,
        )


def test_historical_archive_bulk_execution_requires_passing_preflight(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SIS_AWS_COMMAND", "custom-aws")
    data_dir = tmp_path / "data"
    build_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        coins=["xyz:XYZ100"],
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
        hours=[0],
        include_asset_ctxs=False,
    )
    check_hyperliquid_historical_archive_preflight(
        data_dir=data_dir,
        command_runner=lambda command: (255, "", "Unable to locate credentials"),
    )

    with pytest.raises(RuntimeError, match="preflight has not passed"):
        execute_hyperliquid_historical_archive_bulk_plan(
            data_dir=data_dir,
            dry_run=False,
            acknowledge_requester_pays=True,
            max_objects=1,
            decompress=False,
        )

    manifest = read_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_execution_manifest.json"
    )
    assert manifest["status"] == "blocked_preflight_failed"
    assert manifest["preflight"]["status"] == "fail"
    assert manifest["downloaded_object_count"] == 0


def test_historical_archive_bulk_execution_can_use_injected_runner(tmp_path) -> None:
    data_dir = tmp_path / "data"
    build_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        coins=["xyz:XYZ100"],
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
        hours=[0],
        include_asset_ctxs=False,
    )
    commands: list[list[str]] = []

    def fake_runner(command: list[str]) -> None:
        commands.append(command)
        Path(command[4]).parent.mkdir(parents=True, exist_ok=True)
        Path(command[4]).write_bytes(b"fixture")

    manifest = execute_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        dry_run=False,
        acknowledge_requester_pays=True,
        max_objects=1,
        decompress=False,
        command_runner=fake_runner,
    )

    assert manifest["status"] == "completed"
    assert manifest["downloaded_object_count"] == 1
    assert commands[0][-2:] == ["--request-payer", "requester"]


def _write_registry(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "venue": "trade_xyz",
                    "canonical_symbol": "XYZ100",
                    "venue_symbol": "XYZ100",
                    "asset_class": "basket_index",
                    "dex": "xyz",
                    "coin": "xyz:XYZ100",
                    "asset_id": 100,
                    "real_market_symbol": "^XYZ100",
                    "fee_mode": "standard",
                    "taker_fee_bps": 9.0,
                    "maker_fee_bps": 3.0,
                    "active": True,
                }
            ]
        ),
        encoding="utf-8",
    )


def _write_l2_archive(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "coin": "xyz:XYZ100",
                        "time": 1770000000000,
                        "levels": [
                            [{"px": "99.9", "sz": "10"}],
                            [{"px": "100.1", "sz": "12"}],
                        ],
                    }
                ),
                json.dumps(
                    {
                        "coin": "xyz:XYZ100",
                        "time": 1770000060000,
                        "levels": [
                            [{"px": "100.0", "sz": "9"}],
                            [{"px": "100.2", "sz": "11"}],
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_normalize_historical_archive_to_trade_xyz_quotes_with_asset_ctxs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    l2_path = data_dir / "raw/historical_archive/hyperliquid/example.jsonl"
    ctx_path = data_dir / "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    _write_registry(registry_path)
    _write_l2_archive(l2_path)
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(
        "coin,markPx,oraclePx,midPx,funding,openInterest,oracleTs\n"
        "xyz:XYZ100,100.2,100.1,100.15,-0.00001,1234,1770000000000\n",
        encoding="utf-8",
    )

    manifest = normalize_historical_archive_to_trade_xyz_quotes(
        data_dir=data_dir,
        l2_jsonl_path=l2_path,
        asset_ctxs_path=ctx_path,
        registry_path=registry_path,
        coin="xyz:XYZ100",
    )

    assert manifest["rows_written"] == 2
    assert manifest["asset_ctx_matched"] is True
    rows = list(read_jsonl(data_dir / manifest["raw_quote_output_path"]))
    assert rows[0]["source"] == "hyperliquid_archive.l2Book+asset_ctxs"
    assert rows[0]["ts_client"] == "2026-02-02T02:40:00Z"
    assert rows[0]["mark_price"] == 100.2
    assert rows[0]["oracle_price"] == 100.1
    assert rows[0]["funding_rate"] == -0.00001
    assert rows[0]["taker_fee_bps"] == 9.0
    assert rows[0]["raw_payload_ref"].endswith("#row=0")


def test_normalize_historical_archive_marks_missing_asset_ctx_not_tradable(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    l2_path = data_dir / "raw/historical_archive/hyperliquid/example.jsonl"
    _write_registry(registry_path)
    _write_l2_archive(l2_path)

    manifest = normalize_historical_archive_to_trade_xyz_quotes(
        data_dir=data_dir,
        l2_jsonl_path=l2_path,
        registry_path=registry_path,
        coin="xyz:XYZ100",
    )

    rows = list(read_jsonl(data_dir / manifest["raw_quote_output_path"]))
    assert manifest["asset_ctx_matched"] is False
    assert manifest["missing_asset_ctx_count"] == 2
    assert rows[0]["is_tradable"] is False
    assert "BLOCK_HISTORICAL_ASSET_CTX_MISSING" in rows[0]["block_reasons"]


def test_normalize_historical_archive_bulk_writes_flat_quote_files(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    l2_path = (
        data_dir
        / "raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.jsonl"
    )
    ctx_path = data_dir / "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    _write_registry(registry_path)
    _write_l2_archive(l2_path)
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(
        "coin,markPx,oraclePx,midPx,funding,openInterest,oracleTs\n"
        "xyz:XYZ100,100.2,100.1,100.15,-0.00001,1234,1770000000000\n",
        encoding="utf-8",
    )
    build_hyperliquid_historical_archive_bulk_plan(
        data_dir=data_dir,
        coins=["xyz:XYZ100"],
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
        hours=[9],
    )

    manifest = normalize_historical_archive_bulk_to_trade_xyz_quotes(
        data_dir=data_dir,
        registry_path=registry_path,
        normalize=True,
    )

    assert manifest["status"] == "completed"
    assert manifest["normalized_file_count"] == 1
    assert manifest["rows_written"] == 2
    assert manifest["normalized_row_count"] == 2
    output_path = data_dir / "raw/quotes/trade_xyz/historical_archive_20260501_9_xyz_XYZ100.jsonl"
    assert output_path.exists()
    rows = list(read_jsonl(output_path))
    assert rows[0]["raw_payload_ref"].startswith(str(output_path))
    assert (data_dir / "normalized/quotes.parquet").exists()
