from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sis.strategy_idea_seeds.common.canonical_json import canonical_json


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_text(canonical_json(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def stable_id(prefix: str, value: Any, *, length: int = 24) -> str:
    digest = canonical_hash(value).removeprefix("sha256:")
    return f"{prefix}-{digest[:length]}"
