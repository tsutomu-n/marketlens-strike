<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Acceptance

The design gate is complete when:

- the plan package exists under this directory
- `src/sis/venues/capabilities.py` exists and is tested, if implementation is requested
- `bitget_futures` and `hyperliquid_perp` remain disabled unless a later
  explicit schema-widening slice is approved
- `VenueId` remains unchanged in this design-gate slice
- Strategy Lab schemas remain unchanged in this design-gate slice
- `evaluation_plan.mls.v1` fixed `target_venue=trade_xyz` is documented as a
  blocker for venue widening
- Bitget demo is clearly separated from production Bitget futures
- Hyperliquid direct perp is clearly separated from Trade[XYZ]
- NDX/QQQ paper-path blocking remains intact
- no credentials, external API calls, dependency additions, paper orders, live
  orders, wallet operations, or exchange writes are introduced
- focused tests and `./scripts/check` pass after any implementation
