from __future__ import annotations

from enum import StrEnum


class CryptoPerpReasonCode(StrEnum):
    PUBLIC_NETWORK_OPT_IN_REQUIRED = "public_network_opt_in_required"
    CREDENTIALED_READ_OPT_IN_REQUIRED = "credentialed_read_opt_in_required"
    TINY_LIVE_OPT_IN_REQUIRED = "tiny_live_opt_in_required"
    PROVIDER_PROBE_NOT_IMPLEMENTED_M02 = "provider_probe_not_implemented_m02"
    MARKET_REFRESH_NOT_IMPLEMENTED_M02 = "market_refresh_not_implemented_m02"
    EVENT_REFRESH_NOT_IMPLEMENTED_M04 = "event_refresh_not_implemented_m04"
    WATCHDECK_NOT_IMPLEMENTED_M04 = "watchdeck_not_implemented_m04"
