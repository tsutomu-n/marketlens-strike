from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bitget.client import (
    BitgetHTTPResult,
    BitgetPublicClient,
    BitgetPublicClientConfig,
    BitgetResponseError,
)
from sis.crypto_perp.bitget.normalizers import (
    normalize_candles,
    normalize_funding_history,
    normalize_instruments,
    normalize_open_interest,
    normalize_tickers,
)
from sis.crypto_perp.bitget.public_api import BitgetPublicAPI
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.config import CryptoPerpLabConfig
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.raw_store import RawSnapshotRef, write_raw_snapshot


PROBE_SCHEMA_VERSION = "crypto_perp_provider_probe.v1"
DEFAULT_PROBE_SYMBOL = "BTCUSDT"


class ProviderProbeSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    schema_version: str


class ProviderProbeEndpointResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_id: str
    method: Literal["GET"]
    path: str
    params_redacted: dict[str, str]
    status_code: int
    latency_ms: int
    response_shape_hash: str | None
    row_count: int
    observed_page_limit: int | None
    pagination_behavior: str
    rate_limit_headers: dict[str, str]
    error_class: str | None = None
    error_excerpt: str | None = None


class ProviderProbeCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruments: bool = False
    tickers: bool = False
    candle_1m: bool = False
    candle_15m: bool = False
    mark_candle: bool = False
    index_candle: bool = False
    funding_history: bool = False
    open_interest: bool = False
    public_trade_ws: bool = False
    books1_ws: bool = False
    books15_ws: bool = False


class ProviderProbeArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_provider_probe.v1"] = PROBE_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[ProviderProbeSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    probe_id: str
    provider_id: Literal["bitget"]
    base_url: str
    started_at: datetime
    finished_at: datetime
    network_attempted: bool
    credentials_used: Literal[False] = False
    clock_offset_ms: int | None = None
    endpoint_results: list[ProviderProbeEndpointResult]
    capabilities: ProviderProbeCapabilities
    documentation_anomalies: list[str]

    @field_validator("created_at", "started_at", "finished_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "started_at", "finished_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class ProviderProbeRunResult:
    probe: ProviderProbeArtifact
    probe_path: Path
    report_path: Path


type EndpointCall = Callable[[], Awaitable[BitgetHTTPResult]]
type Normalizer = Callable[[Mapping[str, Any]], list[dict[str, str]]]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _shape(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        if not value:
            return []
        return [_shape(value[0])]
    return type(value).__name__


def _shape_hash(payload: Mapping[str, Any]) -> str:
    return stable_hash(["bitget-response-shape", _shape(payload)])


def _rate_limit_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in sorted(headers.items())
        if "limit" in key.lower() or "remaining" in key.lower() or "reset" in key.lower()
    }


def _error_excerpt(payload: Mapping[str, Any]) -> str:
    code = str(payload.get("code", ""))
    msg = str(payload.get("msg", ""))
    text = " ".join(part for part in [code, msg] if part).strip()
    return text[:240]


async def _probe_endpoint(
    *,
    provider_id: str,
    raw_root: Path,
    endpoint_id: str,
    call: EndpointCall,
    normalize: Normalizer,
    observed_page_limit: int | None,
) -> tuple[ProviderProbeEndpointResult, RawSnapshotRef | None, bool]:
    try:
        result = await call()
        raw_ref = write_raw_snapshot(result=result, raw_root=raw_root, provider_id=provider_id)
        rows = normalize(result.payload) if result.status_code < 400 else []
        success = 200 <= result.status_code < 300 and result.payload.get("code") == "00000"
        endpoint_result = ProviderProbeEndpointResult(
            endpoint_id=endpoint_id,
            method="GET",
            path=result.path,
            params_redacted=result.params_redacted,
            status_code=result.status_code,
            latency_ms=result.latency_ms,
            response_shape_hash=_shape_hash(result.payload),
            row_count=len(rows),
            observed_page_limit=observed_page_limit,
            pagination_behavior="single_page_probe",
            rate_limit_headers=_rate_limit_headers(result.headers),
            error_class=None if success else "BitgetHTTPError",
            error_excerpt=None if success else _error_excerpt(result.payload),
        )
        return endpoint_result, raw_ref, success
    except (BitgetResponseError, ValueError) as exc:
        endpoint_result = ProviderProbeEndpointResult(
            endpoint_id=endpoint_id,
            method="GET",
            path="",
            params_redacted={},
            status_code=0,
            latency_ms=0,
            response_shape_hash=None,
            row_count=0,
            observed_page_limit=observed_page_limit,
            pagination_behavior="single_page_probe",
            rate_limit_headers={},
            error_class=exc.__class__.__name__,
            error_excerpt=str(exc)[:240],
        )
        return endpoint_result, None, False


def _build_capabilities(success: dict[str, bool]) -> ProviderProbeCapabilities:
    candle_ok = success.get("candles", False)
    return ProviderProbeCapabilities(
        instruments=success.get("instruments", False),
        tickers=success.get("tickers", False),
        candle_1m=candle_ok,
        candle_15m=candle_ok,
        mark_candle=candle_ok,
        index_candle=candle_ok,
        funding_history=success.get("funding_history", False),
        open_interest=success.get("open_interest", False),
    )


def _documentation_anomalies() -> list[str]:
    return [
        (
            "bitget_uta_candle_limit_doc_conflict: candle_limit docs mention up to "
            "1,000 candlesticks while the limit parameter table says maximum 100"
        ),
        (
            "bitget_uta_instruments_path_doc_conflict: official pages disagree between "
            "/api/v3/market/instruments and /api/v3/public/instruments"
        ),
    ]


def _source_refs(raw_refs: list[RawSnapshotRef]) -> list[ProviderProbeSourceRef]:
    return [ProviderProbeSourceRef.model_validate(ref.__dict__) for ref in raw_refs]


def _provider_report(probe: ProviderProbeArtifact) -> str:
    lines = [
        "# Crypto Perp Provider Probe",
        "",
        f"- provider_id: `{probe.provider_id}`",
        f"- network_attempted: `{str(probe.network_attempted).lower()}`",
        f"- credentials_used: `{str(probe.credentials_used).lower()}`",
        f"- endpoint_count: `{len(probe.endpoint_results)}`",
        "",
        "## Endpoints",
        "",
        "| endpoint | status | rows | error |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in probe.endpoint_results:
        error = item.error_class or ""
        lines.append(f"| `{item.endpoint_id}` | {item.status_code} | {item.row_count} | {error} |")
    if probe.documentation_anomalies:
        lines.extend(["", "## Documentation Anomalies", ""])
        lines.extend(f"- {item}" for item in probe.documentation_anomalies)
    return "\n".join(lines)


async def _run_provider_probe_async(
    *,
    config: CryptoPerpLabConfig,
    out_dir: Path,
    raw_root: Path,
    transport: httpx.AsyncBaseTransport | None,
    network_attempted: bool,
    started_at: datetime,
) -> ProviderProbeRunResult:
    client = BitgetPublicClient(
        BitgetPublicClientConfig(
            base_url=config.provider.base_url,
            transport=transport,
        )
    )
    api = BitgetPublicAPI(client, category=config.provider.product_type)
    endpoint_specs: list[tuple[str, EndpointCall, Normalizer, int | None]] = [
        ("instruments", api.instruments, normalize_instruments, None),
        ("tickers", api.tickers, normalize_tickers, None),
        (
            "candles",
            lambda: api.candles(symbol=DEFAULT_PROBE_SYMBOL, interval="15m", limit=100),
            lambda payload: normalize_candles(payload, candle_type="market", interval="15m"),
            100,
        ),
        (
            "open_interest",
            lambda: api.open_interest(symbol=DEFAULT_PROBE_SYMBOL),
            normalize_open_interest,
            None,
        ),
        (
            "funding_history",
            lambda: api.funding_history(symbol=DEFAULT_PROBE_SYMBOL, limit=100),
            normalize_funding_history,
            100,
        ),
    ]

    endpoint_results: list[ProviderProbeEndpointResult] = []
    raw_refs: list[RawSnapshotRef] = []
    endpoint_success: dict[str, bool] = {}
    for endpoint_id, call, normalize, observed_page_limit in endpoint_specs:
        endpoint_result, raw_ref, success = await _probe_endpoint(
            provider_id=config.provider.provider_id,
            raw_root=raw_root,
            endpoint_id=endpoint_id,
            call=call,
            normalize=normalize,
            observed_page_limit=observed_page_limit,
        )
        endpoint_results.append(endpoint_result)
        endpoint_success[endpoint_id] = success
        if raw_ref is not None:
            raw_refs.append(raw_ref)

    finished_at = _utc_now()
    probe_id = stable_hash(
        [
            "crypto-perp-provider-probe",
            config.provider.provider_id,
            serialize_utc_z(started_at),
            [item.model_dump(mode="json") for item in endpoint_results],
        ]
    )
    artifact_id = stable_hash(["crypto-perp-provider-probe-artifact", probe_id])
    probe = ProviderProbeArtifact(
        artifact_id=artifact_id,
        created_at=finished_at,
        producer=CryptoPerpProducer(command="crypto-perp-probe"),
        source_refs=_source_refs(raw_refs),
        probe_id=probe_id,
        provider_id=config.provider.provider_id,
        base_url=config.provider.base_url,
        started_at=started_at,
        finished_at=finished_at,
        network_attempted=network_attempted,
        credentials_used=False,
        clock_offset_ms=None,
        endpoint_results=endpoint_results,
        capabilities=_build_capabilities(endpoint_success),
        documentation_anomalies=_documentation_anomalies(),
    )
    probe_path = out_dir / "provider_probe.json"
    report_path = out_dir / "provider_probe.md"
    write_json_artifact(probe_path, probe.model_dump(mode="json"))
    write_text_artifact(report_path, _provider_report(probe))
    return ProviderProbeRunResult(probe=probe, probe_path=probe_path, report_path=report_path)


def run_provider_probe(
    *,
    config: CryptoPerpLabConfig,
    out_dir: Path,
    raw_root: Path,
    transport: httpx.AsyncBaseTransport | None = None,
    network_attempted: bool,
    started_at: datetime | str | None = None,
) -> ProviderProbeRunResult:
    started = ensure_utc_aware("started_at", started_at or _utc_now())
    return asyncio.run(
        _run_provider_probe_async(
            config=config,
            out_dir=out_dir,
            raw_root=raw_root,
            transport=transport,
            network_attempted=network_attempted,
            started_at=started,
        )
    )
