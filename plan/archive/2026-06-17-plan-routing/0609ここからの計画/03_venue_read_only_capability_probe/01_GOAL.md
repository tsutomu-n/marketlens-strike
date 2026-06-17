<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Goal

## Purpose

Implement the smallest safe next step for Bitget Futures and Hyperliquid
support: a fixture-first read-only capability probe that records what is known,
blocked, and not attempted.

The probe must reduce these residual risks:

- future venues exist in capability/suitability catalogs but have no
  standardized probe artifact
- operators may confuse "known venue" with "readiness"
- `bitget_demo` may be mistaken for production Bitget Futures
- Trade[XYZ] proxy may be mistaken for direct `hyperliquid_perp`
- a future implementation may widen schemas before read-only boundaries are
  explicit

## Non-Goal

This slice is not a trading implementation.

Do not implement:

- `VenueId` widening
- Strategy Lab schema widening
- `evaluation_plan.mls.v1` target widening
- Strategy Lab export for future venues
- paper candidate or `PaperIntentPreview` enablement for future venues
- external API calls in default tests or default CLI
- credentialed account, balance, position, order, or fill reads
- signing, wallet operations, order submit, order cancel, close position, live
  trading, or dependency additions

## Expected Outcome

After this slice, the repo can produce local artifacts saying:

- `bitget_futures`: known future venue, read-only probe not configured, no
  external API used, no credentials used, no exchange write used
- `hyperliquid_perp`: known future venue, read-only probe not configured, no
  external API used, no credentials used, no exchange write used
- `bitget_demo`: remains separate and demo-only
- `trade_xyz`: remains separate proxy/read-only surface

