from __future__ import annotations

import json
from pathlib import Path
import shutil

import polars as pl

from sis.strategy_idea_seeds.source.models import SourceCapabilityClass
from sis.strategy_idea_seeds.source.probe import probe_source_root


def test_fixture_source_capabilities_do_not_promote_ticker_snapshot(
    fixture_source_root,
) -> None:
    snapshot = probe_source_root(fixture_source_root)
    capabilities = {item.source_key: item for item in snapshot.capabilities}

    assert capabilities["candles_5m"].capability is SourceCapabilityClass.HISTORICAL
    assert capabilities["funding_rows"].capability is SourceCapabilityClass.HISTORICAL
    assert capabilities["ticker_rows"].capability is SourceCapabilityClass.SNAPSHOT_ONLY
    assert capabilities["mark_index_history"].capability is SourceCapabilityClass.MISSING
    assert capabilities["open_interest_history"].capability is SourceCapabilityClass.MISSING
    assert capabilities["ticker_rows"].usable_for.ml_historical_feature is False
    assert capabilities["mark_index_history"].usable_for.ml_historical_feature is False


def test_probe_distinguishes_forward_only_invalid_and_unknown(
    fixture_source_root: Path,
    tmp_path: Path,
) -> None:
    root = tmp_path / "source_root"
    shutil.copytree(fixture_source_root, root)
    ticker_paths = sorted(root.glob("data/ticker_rows/**/ticker_rows.parquet"))
    for path in ticker_paths:
        frame = pl.read_parquet(path)
        second = frame.with_columns(
            pl.col("ts_exchange_ms") + 300_000,
            pl.col("ts_received_ms") + 300_000,
        )
        pl.concat([frame, second]).write_parquet(path)
    manifest_path = root / "data/ticker_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["row_count_total"] = 4
    manifest["row_count_after_dedupe"] = 4
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    unknown_dir = root / "data/order_book_history"
    unknown_dir.mkdir(parents=True)
    (unknown_dir / "README.txt").write_text("timestamp semantics not declared", encoding="utf-8")
    for path in root.glob("data/funding_rows/**/funding_rows.parquet"):
        path.unlink()

    capabilities = {item.source_key: item for item in probe_source_root(root).capabilities}

    assert capabilities["ticker_rows"].capability is SourceCapabilityClass.FORWARD_ONLY
    assert capabilities["funding_rows"].capability is SourceCapabilityClass.INVALID
    assert capabilities["order_book_history"].capability is SourceCapabilityClass.UNKNOWN
