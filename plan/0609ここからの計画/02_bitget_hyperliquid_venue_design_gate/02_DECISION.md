<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Decision

## Decision

Proceed with a design gate named:

```text
Bitget / Hyperliquid Venue Capability Gate
```

This gate prepares future support but does not perform live integration.

## Venue Naming

Use separate names:

- `bitget_demo`: existing demo/local fixture paper surface
- `bitget_futures`: future production or credentialed futures venue, catalog-only for now
- `hyperliquid_perp`: future direct Hyperliquid perp venue, catalog-only for now
- `trade_xyz`: existing Trade[XYZ] / Hyperliquid-derived proxy/research surface

Do not use `bitget_demo` as a production Bitget venue.

Do not use `trade_xyz` as a generic Hyperliquid direct-perp venue.

## Promotion Order

1. Current catalog-only entries remain disabled.
2. Add a venue capability contract and fixture-only tests.
3. Add read-only capability artifacts with no external network by default.
4. Add opt-in credentialed read-only smoke only after a separate plan.
5. Widen `VenueId` and schemas only after capability artifacts and tests exist.
6. Add paper-only path only after schema widening and fee/cost contract are
   covered.
7. Live order remains out of scope until a separate operator-approved live gate.

## Decision Status

Ready for planning and docs. Not ready for live implementation.
