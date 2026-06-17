<!--
作成日: 2026-06-09_15:07 JST
更新日: 2026-06-09_16:13 JST
-->

# NDX/QQQ Venue Suitability Gate

This plan adds a fail-closed venue suitability gate for NDX/QQQ routing. It
also records the implemented hardening that blocks NDX/QQQ family rows from
raw `paper-from-intents` JSON and the legacy `paper-step` order-generation path.

It is not a Bitget or Hyperliquid integration plan. `bitget_futures` and
`hyperliquid_perp` are catalog-only future candidates and must not be added to
`VenueId` or Strategy Lab artifact schemas in this slice.

Read in order:

1. `01_GOAL.md`
2. `02_CONSTRAINTS.md`
3. `03_TARGET_FILES.md`
4. `04_IMPLEMENTATION_TASKS.md`
5. `05_TEST_PLAN.md`
6. `06_ACCEPTANCE.md`
7. `07_CODER_HANDOFF_PROMPT.md`

Code, tests, schemas, CLI help, and generated manifests remain the source of
truth after implementation.

Current implementation status:

- implemented and verified at HEAD `428ed16`
- `VenueId` and Strategy Lab schemas remain `trade_xyz` / `bitget_demo`
- `bitget_futures` and `hyperliquid_perp` remain suitability-catalog-only
- NDX/QQQ family rows remain usable as research/backtest records but cannot
  advance through selected candidate, paper intent, raw intent JSON, or legacy
  `paper-step` order generation
