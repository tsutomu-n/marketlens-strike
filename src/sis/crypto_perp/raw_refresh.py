from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sis.crypto_perp.bars import build_candle_bars
from sis.crypto_perp.bitget.normalizers import (
    normalize_candles,
    normalize_instruments,
    normalize_tickers,
)
from sis.crypto_perp.bitget.probe import ProviderProbeArtifact
from sis.crypto_perp.events import CryptoPerpEvent, detect_event
from sis.crypto_perp.features import EventDetectorConfig
from sis.crypto_perp.heartbeat import build_market_snapshot
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.probe_audit import CryptoPerpProbeAudit
from sis.crypto_perp.quality import validate_candle_series
from sis.crypto_perp.raw_store import RAW_SNAPSHOT_SCHEMA_VERSION
from sis.crypto_perp.universe import build_universe_snapshot


class RawRefreshSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    schema_version: str


class CryptoPerpRawRefreshArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_raw_refresh.v1"] = "crypto_perp_raw_refresh.v1"
    artifact_id: str
    producer: CryptoPerpProducer
    source_refs: list[RawRefreshSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    probe_id: str
    probe_audit_status: Literal["READY_FOR_EVENT_REFRESH"]
    universe_snapshot_path: str
    market_snapshot_path: str
    quality_report_path: str
    event_paths: list[str]
    event_count: int
    known_gaps: list[str]
    summary: dict[str, Any]


class RawRefreshResult(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    artifact: CryptoPerpRawRefreshArtifact
    universe_payload: dict[str, Any]
    market_payload: dict[str, Any]
    quality_payload: dict[str, Any]
    event_payloads: list[dict[str, Any]]


def _raw_snapshots_by_endpoint(
    probe: ProviderProbeArtifact,
) -> dict[str, tuple[dict[str, Any], str]]:
    snapshots: dict[str, tuple[dict[str, Any], str]] = {}
    for ref in probe.source_refs:
        payload = json.loads(Path(ref.path).read_text(encoding="utf-8"))
        endpoint_id = str(payload.get("endpoint_id", ""))
        body = payload.get("body")
        if not endpoint_id or not isinstance(body, dict):
            raise ValueError(f"invalid raw snapshot: {ref.path}")
        snapshots[endpoint_id] = (payload, ref.sha256)
    return snapshots


def _source_ref(path: str, sha256: str) -> dict[str, str]:
    return {
        "path": path,
        "sha256": sha256,
        "schema_version": RAW_SNAPSHOT_SCHEMA_VERSION,
    }


def build_raw_refresh(
    *,
    probe: ProviderProbeArtifact,
    audit: CryptoPerpProbeAudit,
    out_dir: Path,
    detector_config: EventDetectorConfig | None = None,
) -> RawRefreshResult:
    if audit.probe_id != probe.probe_id:
        raise ValueError("probe audit does not match provider probe")
    if audit.audit_status != "READY_FOR_EVENT_REFRESH":
        raise ValueError("probe audit must be READY_FOR_EVENT_REFRESH")

    detector = detector_config or EventDetectorConfig()
    raw_by_endpoint = _raw_snapshots_by_endpoint(probe)
    required = {"instruments", "tickers", "candles"}
    missing = sorted(endpoint for endpoint in required if endpoint not in raw_by_endpoint)
    if missing:
        raise ValueError("missing raw snapshots: " + ",".join(missing))

    instruments_raw, instruments_sha = raw_by_endpoint["instruments"]
    tickers_raw, tickers_sha = raw_by_endpoint["tickers"]
    candles_raw, candles_sha = raw_by_endpoint["candles"]
    observed_at = probe.finished_at

    instruments_ref = _source_ref(instruments_raw["path"], instruments_sha)
    tickers_ref = _source_ref(tickers_raw["path"], tickers_sha)
    candles_ref = _source_ref(candles_raw["path"], candles_sha)

    universe = build_universe_snapshot(
        provider_id="bitget",
        product_type="USDT-FUTURES",
        observed_at=observed_at,
        instruments=normalize_instruments(instruments_raw["body"]),
        source_refs=[instruments_ref],
    )
    ticker_rows = normalize_tickers(tickers_raw["body"])
    market = build_market_snapshot(
        provider_id="bitget",
        observed_at=observed_at,
        ticker_rows=ticker_rows,
        source_payload_sha256=tickers_sha,
        source_refs=[tickers_ref],
    )
    candle_rows = normalize_candles(candles_raw["body"], candle_type="market", interval="15m")
    raw_symbol = str(candles_raw.get("params_redacted", {}).get("symbol", "UNKNOWN"))
    native_symbol = raw_symbol if candle_rows else "UNKNOWN"
    bars = build_candle_bars(
        provider_id="bitget",
        native_symbol=native_symbol,
        candle_rows=candle_rows,
        ts_ingested=observed_at,
        source_payload_sha256=candles_sha,
        now_ms=int(observed_at.timestamp() * 1000),
    )
    quality = validate_candle_series(bars, interval="15m", checked_at=observed_at)
    ticker = next((item for item in market.tickers if item.native_symbol == native_symbol), None)
    event: CryptoPerpEvent | None = None
    if ticker is not None:
        event = detect_event(
            provider_id="bitget",
            native_symbol=native_symbol,
            canonical_symbol=native_symbol,
            bars=bars,
            ticker=ticker,
            quality_report=quality,
            universe_snapshot_id=universe.snapshot_id,
            market_snapshot_id=market.snapshot_id,
            detector_config=detector,
            source_refs=[candles_ref, tickers_ref],
        )
    known_gaps = list(quality.reason_codes)
    if ticker is None:
        known_gaps.append("TICKER_NOT_FOUND_FOR_CANDLE_SYMBOL")
    if not event:
        known_gaps.append("NO_EVENT_DETECTED")
    known_gaps = list(dict.fromkeys(known_gaps))

    universe_path = out_dir / "universe_snapshot.json"
    market_path = out_dir / "market_snapshot.json"
    quality_path = out_dir / "candle_quality.json"
    event_paths = [str(out_dir / "events" / f"{event.event_id}.json")] if event else []
    summary = {
        "probe_id": probe.probe_id,
        "event_count": len(event_paths),
        "known_gap_count": len(known_gaps),
        "universe_instrument_count": len(universe.instruments),
        "market_ticker_count": len(market.tickers),
        "candle_bar_count": len(bars),
    }
    artifact = CryptoPerpRawRefreshArtifact(
        artifact_id=stable_hash(["crypto-perp-raw-refresh", probe.probe_id, summary]),
        producer=CryptoPerpProducer(command="crypto-perp-raw-refresh"),
        source_refs=[
            RawRefreshSourceRef.model_validate(instruments_ref),
            RawRefreshSourceRef.model_validate(tickers_ref),
            RawRefreshSourceRef.model_validate(candles_ref),
        ],
        probe_id=probe.probe_id,
        probe_audit_status="READY_FOR_EVENT_REFRESH",
        universe_snapshot_path=universe_path.as_posix(),
        market_snapshot_path=market_path.as_posix(),
        quality_report_path=quality_path.as_posix(),
        event_paths=event_paths,
        event_count=len(event_paths),
        known_gaps=known_gaps,
        summary=summary,
    )
    return RawRefreshResult(
        artifact=artifact,
        universe_payload=universe.model_dump(mode="json"),
        market_payload=market.model_dump(mode="json"),
        quality_payload=quality.model_dump(mode="json"),
        event_payloads=[event.model_dump(mode="json")] if event else [],
    )
