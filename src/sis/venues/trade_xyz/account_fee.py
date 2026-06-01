from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re
from typing import Any

from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.client import TradeXyzClient

_HEX_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _rate_to_bps(value: Any) -> float | None:
    rate = _decimal_or_none(value)
    if rate is None:
        return None
    return float(rate * Decimal("10000"))


def _discount_value(value: Any) -> float | None:
    discount = _decimal_or_none(value)
    if discount is None:
        return None
    return float(discount)


def _active_staking_discount(payload: dict[str, Any]) -> dict[str, Any] | None:
    value = payload.get("activeStakingDiscount")
    return value if isinstance(value, dict) else None


def collect_trade_xyz_account_fee_snapshot(
    *,
    data_dir: Path,
    user_address: str,
    client: TradeXyzClient,
    snapshot_ts: datetime | None = None,
) -> dict[str, Any]:
    if not _HEX_ADDRESS_RE.fullmatch(user_address.strip()):
        raise ValueError("user_address must be a 42-character 0x-prefixed hexadecimal address")

    effective_snapshot_ts = snapshot_ts or _utc_now()
    user_address_normalized = user_address.strip().lower()
    user_address_sha256 = _sha256_text(user_address_normalized)
    payload = client.user_fees(user_address_normalized)
    raw_artifact_path = (
        data_dir
        / "raw/fees/trade_xyz_account"
        / f"{effective_snapshot_ts.date()}_{user_address_sha256[:12]}.json"
    )
    raw_artifact = {
        "schema_version": "trade_xyz_account_fee_raw.v1",
        "generated_at": effective_snapshot_ts.isoformat(),
        "source": "hyperliquid_info_userFees",
        "user_address_sha256": user_address_sha256,
        "payload": payload,
    }
    write_json(raw_artifact_path, raw_artifact)

    active_staking = _active_staking_discount(payload)
    available_fields = [
        field
        for field, value in {
            "userCrossRate": payload.get("userCrossRate"),
            "userAddRate": payload.get("userAddRate"),
            "activeReferralDiscount": payload.get("activeReferralDiscount"),
            "activeStakingDiscount": active_staking,
            "feeSchedule": payload.get("feeSchedule"),
        }.items()
        if value is not None
    ]
    missing_fields = [
        field
        for field in (
            "userCrossRate",
            "userAddRate",
            "activeReferralDiscount",
            "activeStakingDiscount",
            "feeSchedule",
        )
        if field not in available_fields
    ]
    manifest = {
        "schema_version": "trade_xyz_account_fee_manifest.v1",
        "generated_at": effective_snapshot_ts.isoformat(),
        "status": "pass"
        if payload.get("userCrossRate") is not None and payload.get("userAddRate") is not None
        else "partial",
        "data_dir": str(data_dir),
        "source": "hyperliquid_info_userFees",
        "source_doc": "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint",
        "raw_artifact_path": str(raw_artifact_path),
        "user_address_sha256": user_address_sha256,
        "payload_field_keys": sorted(str(key) for key in payload.keys()),
        "available_fields": available_fields,
        "missing_fields": missing_fields,
        "parsed": {
            "user_cross_rate": str(payload.get("userCrossRate"))
            if payload.get("userCrossRate") is not None
            else None,
            "user_add_rate": str(payload.get("userAddRate"))
            if payload.get("userAddRate") is not None
            else None,
            "user_taker_fee_bps": _rate_to_bps(payload.get("userCrossRate")),
            "user_maker_fee_bps": _rate_to_bps(payload.get("userAddRate")),
            "active_referral_discount": _discount_value(payload.get("activeReferralDiscount")),
            "active_staking_discount": _discount_value(active_staking.get("discount"))
            if active_staking is not None
            else None,
            "active_staking_bps_of_max_supply": _discount_value(
                active_staking.get("bpsOfMaxSupply")
            )
            if active_staking is not None
            else None,
            "daily_user_volume_count": len(payload.get("dailyUserVlm") or [])
            if isinstance(payload.get("dailyUserVlm"), list)
            else None,
        },
        "not_collected_fields": {
            "builder_fee_bps": "requires a specific builder address and maxBuilderFee query",
            "account_growth_mode": "growth mode is HIP-3 asset/deployer state, not returned by userFees",
            "fee_tier": "userFees returns effective rates and schedule; explicit tier label is not returned",
        },
        "notes": [
            "This is a read-only /info userFees snapshot; it does not require wallet signing.",
            "The user address is stored only as sha256 in manifest and raw artifact metadata.",
            "Use user_taker_fee_bps and user_maker_fee_bps as the observed account-specific fee rates.",
        ],
    }
    write_json(data_dir / "manifests/trade_xyz_account_fee_manifest.json", manifest)
    return manifest
