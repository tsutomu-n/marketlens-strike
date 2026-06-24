from __future__ import annotations


def load_stale_thresholds() -> dict[str, int]:
    try:
        from sis.risk.halt_policy import load_halt_policy

        policy = load_halt_policy()
        stale_policy = policy.get("halt_policy", policy).get("stale_price", {})
    except FileNotFoundError:
        stale_policy = {}
    return {
        "gtrade": int(stale_policy.get("gtrade_max_age_ms", 3000)),
        "ostium": int(stale_policy.get("ostium_max_age_ms", 5000)),
        "trade_xyz": int(stale_policy.get("trade_xyz_max_age_ms", 5000)),
    }


def load_spread_thresholds() -> dict[str, float]:
    try:
        from sis.risk.halt_policy import load_halt_policy

        policy = load_halt_policy()
        spread_policy = (
            policy.get("halt_policy", policy).get("spread", {}).get("max_spread_bps", {})
        )
    except FileNotFoundError:
        spread_policy = {}
    if not isinstance(spread_policy, dict):
        spread_policy = {}
    return {
        str(key): float(value)
        for key, value in spread_policy.items()
        if isinstance(value, (int, float))
    }


def spread_threshold_for_symbol(symbol: str, thresholds: dict[str, float]) -> float:
    if symbol in thresholds:
        return thresholds[symbol]
    if symbol in {"SP500", "XYZ100", "SPY", "QQQ"}:
        return thresholds.get("default_index", 12.0)
    return thresholds.get("default_equity", 25.0)


def trade_xyz_diagnostic_healthy(
    entry: dict, symbol: str, spread_thresholds: dict[str, float]
) -> bool:
    spread_p90 = entry.get("spread_p90_bps")
    return (
        entry.get("missing_mark_price_rate") == 0
        and entry.get("missing_oracle_price_rate") == 0
        and entry.get("missing_funding_rate") == 0
        and entry.get("missing_open_interest_rate") == 0
        and entry.get("stale_rate") == 0
        and entry.get("l2_only_rate") == 0
        and entry.get("fee_mode_unknown_rate") == 0
        and isinstance(spread_p90, (int, float))
        and spread_p90 <= spread_threshold_for_symbol(symbol, spread_thresholds)
    )


def trade_xyz_diagnostic_blockers(
    diagnostics: list[dict], spread_thresholds: dict[str, float]
) -> list[str]:
    blockers: list[str] = []
    for item in diagnostics:
        symbol = str(item.get("symbol") or "")
        entries = item.get("items")
        if not item.get("available") or not isinstance(entries, list) or not entries:
            blockers.append(f"{symbol}:diagnostics_unavailable")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                blockers.append(f"{symbol}:diagnostics_malformed")
                continue
            spread_p90 = entry.get("spread_p90_bps")
            spread_limit = spread_threshold_for_symbol(symbol, spread_thresholds)
            checks = {
                "missing_mark_price_rate": entry.get("missing_mark_price_rate"),
                "missing_oracle_price_rate": entry.get("missing_oracle_price_rate"),
                "missing_funding_rate": entry.get("missing_funding_rate"),
                "missing_open_interest_rate": entry.get("missing_open_interest_rate"),
                "stale_rate": entry.get("stale_rate"),
                "l2_only_rate": entry.get("l2_only_rate"),
                "fee_mode_unknown_rate": entry.get("fee_mode_unknown_rate"),
            }
            for name, value in checks.items():
                if value != 0:
                    blockers.append(f"{symbol}:{name}={value}")
            if not isinstance(spread_p90, (int, float)):
                blockers.append(f"{symbol}:spread_p90_bps_missing")
            elif spread_p90 > spread_limit:
                blockers.append(f"{symbol}:spread_p90_bps={spread_p90}>limit={spread_limit}")
    return blockers
