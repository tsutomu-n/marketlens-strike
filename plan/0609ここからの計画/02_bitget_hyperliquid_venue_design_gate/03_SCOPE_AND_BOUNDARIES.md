<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Scope And Boundaries

## In Scope

- Define a fixture-first venue capability contract.
- Add tests that prove future venues remain disabled until explicitly enabled.
- Document when `VenueId` may be widened.
- Document schema surfaces that must change together.
- Document read-only smoke requirements for Bitget and Hyperliquid.
- Preserve the NDX/QQQ paper-path block.

## Out Of Scope

- Production Bitget trading.
- Hyperliquid direct live trading.
- Live order submission.
- Wallet, signing, exchange write, or real funds.
- External API calls in default tests.
- Credentials in tracked files.
- Dependency additions.
- NDX/QQQ direct execution on Bitget or Hyperliquid.
- Strategy Lab export changes.
- Backtest engine changes.

## Required Separation

| Concept | Meaning | Must Not Be Mixed With |
|---|---|---|
| `bitget_demo` | local/demo fixture and paper-only crypto surface | production Bitget futures |
| `bitget_futures` | future Bitget futures venue | demo smoke, current schema enum |
| `hyperliquid_perp` | future direct Hyperliquid perp venue | Trade[XYZ] proxy/index research |
| `trade_xyz` | current proxy/research/read-only surface | generic Hyperliquid direct perp |
| `VenueId` | accepted artifact enum | future catalog wishlist |
| `VENUE_SUITABILITY_CATALOG` | capability registry | proof that schemas accept a venue |

## NDX/QQQ Boundary

NDX/QQQ family remains blocked from paper routing. This plan does not create a
way to trade NDX/QQQ through Bitget or Hyperliquid.
