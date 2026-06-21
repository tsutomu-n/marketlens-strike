from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.crypto_perp.bitget.client import BitgetHTTPResult
from sis.crypto_perp.clock import serialize_utc_z


RAW_SNAPSHOT_SCHEMA_VERSION = "crypto_perp_raw_snapshot.v1"


@dataclass(frozen=True)
class RawSnapshotRef:
    path: str
    sha256: str
    schema_version: str = RAW_SNAPSHOT_SCHEMA_VERSION


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _date_partition(value: datetime) -> str:
    return value.date().isoformat()


def write_raw_snapshot(
    *,
    result: BitgetHTTPResult,
    raw_root: Path,
    provider_id: str,
) -> RawSnapshotRef:
    raw_sha = sha256_text(result.raw_text)
    snapshot = {
        "schema_version": RAW_SNAPSHOT_SCHEMA_VERSION,
        "provider_id": provider_id,
        "endpoint_id": result.endpoint_id,
        "method": result.method,
        "path": result.path,
        "params_redacted": result.params_redacted,
        "status_code": result.status_code,
        "headers": result.headers,
        "received_at": serialize_utc_z(result.received_at),
        "latency_ms": result.latency_ms,
        "raw_sha256": raw_sha,
        "body": result.payload,
    }
    snapshot_sha = sha256_json(snapshot)
    path = (
        raw_root
        / f"provider={provider_id}"
        / f"date={_date_partition(result.received_at)}"
        / f"channel={result.endpoint_id}"
        / f"{snapshot_sha}.json"
    )
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(path)
    return RawSnapshotRef(path=path.as_posix(), sha256=snapshot_sha)
