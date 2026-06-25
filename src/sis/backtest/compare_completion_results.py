from __future__ import annotations

from typing import Any

__all__ = ["completion_artifact"]


def completion_artifact(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    summary = payload.get("summary")
    return {
        "schema_version": payload.get("schema_version"),
        "status": payload.get("status"),
        "summary": summary if isinstance(summary, dict) else {},
        "dependency_added": payload.get("dependency_added"),
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "live_conversion_allowed": payload.get("live_conversion_allowed"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }
