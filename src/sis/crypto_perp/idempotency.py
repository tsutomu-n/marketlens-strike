from __future__ import annotations

import re

from sis.crypto_perp.models import stable_hash


CLIENT_OID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def build_client_oid(
    *,
    event_id: str,
    decision_id: str,
    symbol: str,
    side: str,
    position_side: str,
) -> str:
    digest = stable_hash(
        ["crypto-perp-client-oid", event_id, decision_id, symbol, side, position_side]
    )
    client_oid = f"mls-{digest[:28]}"
    if not CLIENT_OID_PATTERN.fullmatch(client_oid):
        raise ValueError("generated clientOid is invalid")
    return client_oid
