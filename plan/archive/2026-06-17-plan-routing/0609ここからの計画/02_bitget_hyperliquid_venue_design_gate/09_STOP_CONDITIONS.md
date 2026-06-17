<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Stop Conditions

Stop and revise the plan if any of these happen:

- A change requires production Bitget credentials.
- A change requires Hyperliquid wallet credentials or signing.
- A default test would call an external API.
- A change widens `VenueId` without updating Strategy Lab schemas and
  `evaluation_plan.mls.v1` together.
- A change enables `live_execution_enabled=true`.
- A change submits, cancels, or closes a real order.
- A change treats `bitget_demo` as production Bitget.
- A change treats Trade[XYZ] as generic `hyperliquid_perp`.
- A change allows NDX/QQQ family through paper candidate or paper intent.
- A change requires dependency additions.
- A change requires storing secrets in tracked files.
