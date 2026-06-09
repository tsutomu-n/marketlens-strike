<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Scope And Boundaries

## In Scope

- Add a local probe model for read-only venue capability status.
- Add fixture-first probe builders for:
  - `bitget_futures`
  - `hyperliquid_perp`
  - existing venues already in capability catalog
- Add a minimal CLI that writes a JSON summary and Markdown report.
- Add schema validation for the new probe artifact.
- Add tests that prove the default path is non-network, non-credentialed, and
  non-writing.
- Update docs so the new artifact is discoverable.

## Out Of Scope

- Network requests to Bitget or Hyperliquid.
- New dependencies.
- New credential names.
- Reading real account balance, positions, fills, or order status.
- Paper or live execution.
- Any Strategy Lab artifact enablement for `bitget_futures` or
  `hyperliquid_perp`.
- Any change to:
  - `src/sis/venues/ids.py`
  - `schemas/strategy_signal.v1.schema.json`
  - `schemas/trade_candidate.v1.schema.json`
  - `schemas/paper_intent_preview.v1.schema.json`
  - `schemas/evaluation_plan.mls.v1.schema.json`
  - `pyproject.toml`
  - `uv.lock`

## Required Semantics

- "Probe" means local capability inspection, not exchange communication.
- "Read-only" means no write endpoints, no order paths, no cancel paths, no
  wallet/signing use, and no live conversion.
- "Credential status" in this slice means `not_required` or `not_checked`, not
  account readiness.
- "Configured" must not be used for `bitget_futures` or `hyperliquid_perp`
  unless a later network-probe slice defines what configured means.

## Failure Modes To Prevent

- `APPROVE`-style wording that implies trading readiness.
- `bitget_demo` re-used as production Bitget.
- `trade_xyz` re-used as generic direct Hyperliquid.
- A passing fixture probe being interpreted as account readiness.
- Future venue names entering Strategy Lab schemas by accident.

