from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.strategy_idea_seeds.common.errors import SeedInputError
from sis.strategy_idea_seeds.common.ids import canonical_hash, sha256_file
from sis.strategy_idea_seeds.source.models import (
    SOURCE_KEYS,
    SourceCapability,
    SourceCapabilityClass,
    SourceCapabilitySnapshot,
    SourceUsableFor,
)


_SOURCE_PATTERNS = {
    "candles_5m": ("data/candles_5m/date=*/candles.parquet",),
    "funding_rows": ("data/funding_rows/exchange=*/symbol=*/date=*/funding_rows.parquet",),
    "ticker_rows": ("data/ticker_rows/exchange=*/symbol=*/date=*/ticker_rows.parquet",),
    "mark_index_history": ("data/mark_index_history/**/*.parquet",),
    "open_interest_history": ("data/open_interest_history/**/*.parquet",),
    "trade_tape_history": (
        "data/trade_tape_history/**/*.parquet",
        "data/trades/**/*.parquet",
    ),
    "order_book_history": (
        "data/order_book_history/**/*.parquet",
        "data/books/**/*.parquet",
    ),
    "liquidation_history": ("data/liquidation_history/**/*.parquet",),
}

_REQUIRED_COLUMNS = {
    "candles_5m": {"symbol", "ts", "open", "high", "low", "close"},
    "funding_rows": {
        "symbol_canonical",
        "funding_time_ms",
        "available_at_ms",
        "funding_rate",
    },
    "ticker_rows": {
        "symbol_canonical",
        "ts_exchange_ms",
        "ts_received_ms",
        "is_snapshot",
    },
}

_MANIFEST_PATHS = {
    "funding_rows": "data/funding_manifest.json",
    "ticker_rows": "data/ticker_manifest.json",
}


def probe_source_root(source_root: Path) -> SourceCapabilitySnapshot:
    root = source_root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SeedInputError(f"source root missing or not a directory: {source_root}")
    capabilities = [_probe_source(root, source_key) for source_key in SOURCE_KEYS]
    source_root_hash = canonical_hash(
        [
            {
                "source_key": item.source_key,
                "capability": item.capability,
                "row_count": item.row_count,
                "fields_present": item.fields_present,
                "artifact_paths": item.artifact_paths,
                "artifact_hashes": item.artifact_hashes,
                "reason_codes": item.reason_codes,
            }
            for item in capabilities
        ]
    )
    return SourceCapabilitySnapshot(
        source_root=root.as_posix(),
        source_root_hash=source_root_hash,
        capabilities=capabilities,
    )


def _probe_source(root: Path, source_key: str) -> SourceCapability:
    paths = _matching_paths(root, source_key)
    manifest_path = root / _MANIFEST_PATHS[source_key] if source_key in _MANIFEST_PATHS else None
    manifest, manifest_error = _read_manifest(manifest_path)
    relative_paths = [path.relative_to(root).as_posix() for path in paths]
    hashes = [sha256_file(path) for path in paths]

    if manifest_error is not None:
        return _capability(
            source_key,
            SourceCapabilityClass.INVALID,
            paths=relative_paths,
            hashes=hashes,
            manifest_path=manifest_path,
            reason_codes=["SOURCE_MANIFEST_INVALID"],
        )

    if not paths:
        if _manifest_claims_rows(manifest):
            return _capability(
                source_key,
                SourceCapabilityClass.INVALID,
                paths=[],
                hashes=[],
                manifest_path=manifest_path,
                reason_codes=["SOURCE_MANIFEST_INVALID", "SOURCE_HISTORY_MISSING"],
            )
        if _source_directory_exists(root, source_key):
            return _capability(
                source_key,
                SourceCapabilityClass.UNKNOWN,
                paths=[],
                hashes=[],
                manifest_path=manifest_path,
                reason_codes=["TIMESTAMP_SEMANTICS_UNKNOWN"],
            )
        return _capability(
            source_key,
            SourceCapabilityClass.MISSING,
            paths=[],
            hashes=[],
            manifest_path=manifest_path,
            reason_codes=["SOURCE_HISTORY_MISSING"],
        )

    try:
        frames = [pl.read_parquet(path) for path in paths]
    except Exception:
        return _capability(
            source_key,
            SourceCapabilityClass.INVALID,
            paths=relative_paths,
            hashes=hashes,
            manifest_path=manifest_path,
            reason_codes=["SOURCE_MANIFEST_INVALID"],
        )
    row_count = sum(frame.height for frame in frames)
    fields = sorted({column for frame in frames for column in frame.columns})
    missing_columns = sorted(_REQUIRED_COLUMNS.get(source_key, set()).difference(fields))
    if row_count <= 0 or missing_columns:
        return _capability(
            source_key,
            SourceCapabilityClass.INVALID,
            row_count=row_count,
            fields=fields,
            paths=relative_paths,
            hashes=hashes,
            manifest_path=manifest_path,
            reason_codes=["SOURCE_MANIFEST_INVALID"],
        )
    if _manifest_row_count(manifest) not in {None, row_count}:
        return _capability(
            source_key,
            SourceCapabilityClass.INVALID,
            row_count=row_count,
            fields=fields,
            paths=relative_paths,
            hashes=hashes,
            manifest_path=manifest_path,
            reason_codes=["SOURCE_MANIFEST_INVALID"],
        )

    if source_key == "ticker_rows":
        capability = _ticker_capability(frames)
        reason = (
            "SOURCE_FORWARD_ONLY"
            if capability is SourceCapabilityClass.FORWARD_ONLY
            else "SOURCE_SNAPSHOT_ONLY"
        )
        return _capability(
            source_key,
            capability,
            row_count=row_count,
            fields=fields,
            paths=relative_paths,
            hashes=hashes,
            manifest_path=manifest_path,
            reason_codes=[reason],
        )
    if source_key in {"candles_5m", "funding_rows"}:
        capability = SourceCapabilityClass.HISTORICAL
        reasons: list[str] = []
    else:
        capability, reasons = _generic_history_capability(frames, fields)
    return _capability(
        source_key,
        capability,
        row_count=row_count,
        fields=fields,
        paths=relative_paths,
        hashes=hashes,
        manifest_path=manifest_path,
        reason_codes=reasons,
    )


def _matching_paths(root: Path, source_key: str) -> list[Path]:
    paths = {
        path.resolve()
        for pattern in _SOURCE_PATTERNS[source_key]
        for path in root.glob(pattern)
        if path.is_file()
    }
    return sorted(paths)


def _source_directory_exists(root: Path, source_key: str) -> bool:
    return (root / "data" / source_key).exists()


def _read_manifest(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None or not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "manifest must be an object"
    for field in ("credentials_used", "exchange_write_used", "live_order_submitted"):
        if field in payload and payload[field] is not False:
            return None, f"{field} must be false"
    return payload, None


def _manifest_row_count(manifest: dict[str, Any] | None) -> int | None:
    if manifest is None:
        return None
    value = manifest.get("row_count_after_dedupe", manifest.get("row_count_total"))
    return value if isinstance(value, int) and value >= 0 else None


def _manifest_claims_rows(manifest: dict[str, Any] | None) -> bool:
    count = _manifest_row_count(manifest)
    return count is not None and count > 0


def _ticker_capability(frames: list[pl.DataFrame]) -> SourceCapabilityClass:
    rows = pl.concat(frames, how="vertical_relaxed")
    if rows.filter(pl.col("is_snapshot") != True).height:  # noqa: E712
        return SourceCapabilityClass.UNKNOWN
    grouped = rows.group_by("symbol_canonical").len()
    max_count = int(grouped.select(pl.col("len").max()).item() or 0)
    return (
        SourceCapabilityClass.FORWARD_ONLY if max_count > 1 else SourceCapabilityClass.SNAPSHOT_ONLY
    )


def _generic_history_capability(
    frames: list[pl.DataFrame], fields: list[str]
) -> tuple[SourceCapabilityClass, list[str]]:
    timestamp_fields = {
        "ts",
        "timestamp",
        "ts_ms",
        "event_time_ms",
        "available_at_ms",
        "funding_time_ms",
    }
    if not timestamp_fields.intersection(fields):
        return SourceCapabilityClass.UNKNOWN, ["TIMESTAMP_SEMANTICS_UNKNOWN"]
    if any("is_snapshot" in frame.columns for frame in frames):
        rows = pl.concat(frames, how="vertical_relaxed")
        if rows.filter(pl.col("is_snapshot") == True).height:  # noqa: E712
            return SourceCapabilityClass.FORWARD_ONLY, ["SOURCE_FORWARD_ONLY"]
    return SourceCapabilityClass.HISTORICAL, []


def _capability(
    source_key: str,
    capability: SourceCapabilityClass,
    *,
    row_count: int = 0,
    fields: list[str] | None = None,
    paths: list[str],
    hashes: list[str],
    manifest_path: Path | None,
    reason_codes: list[str],
) -> SourceCapability:
    historical = capability is SourceCapabilityClass.HISTORICAL
    contextual = capability not in {
        SourceCapabilityClass.INVALID,
        SourceCapabilityClass.UNKNOWN,
    }
    return SourceCapability(
        source_key=source_key,
        capability=capability,
        row_count=row_count,
        fields_present=fields or [],
        artifact_paths=paths,
        artifact_hashes=hashes,
        manifest_path=manifest_path.as_posix()
        if manifest_path and manifest_path.exists()
        else None,
        reason_codes=reason_codes,
        usable_for=SourceUsableFor(
            technical_concept_generation=True,
            ml_historical_feature=historical,
            llm_context=contextual,
        ),
    )
