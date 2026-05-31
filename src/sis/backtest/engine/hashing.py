from __future__ import annotations

import hashlib
import json

import polars as pl
from pydantic import BaseModel


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def config_hash(config: BaseModel | dict) -> str:
    payload = config.model_dump(mode="json") if isinstance(config, BaseModel) else config
    return _sha256_json(payload)


def input_schema_hash(frame: pl.DataFrame) -> str:
    payload = [
        {"name": name, "dtype": str(dtype)}
        for name, dtype in sorted(frame.schema.items(), key=lambda item: item[0])
    ]
    return _sha256_json(payload)


def frame_sha256(frame: pl.DataFrame) -> str:
    rows = frame.sort(frame.columns).to_dicts() if frame.columns else frame.to_dicts()
    schema = [
        {"name": name, "dtype": str(dtype)}
        for name, dtype in sorted(frame.schema.items(), key=lambda item: item[0])
    ]
    return _sha256_json({"schema": schema, "rows": rows})
