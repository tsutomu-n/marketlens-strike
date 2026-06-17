<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Bitget / Hyperliquid Venue Design Gate

This is a design-gate plan, not an implementation plan for live trading.

Goal: decide the minimum safe path for future Bitget and Hyperliquid support
without weakening the existing NDX/QQQ paper-path block, widening schemas
prematurely, or mixing demo, read-only, paper, and live responsibilities.

Read in order:

1. `01_RESEARCH_FINDINGS.md`
2. `02_DECISION.md`
3. `03_SCOPE_AND_BOUNDARIES.md`
4. `04_TARGET_FILE_MAP.md`
5. `05_IMPLEMENTATION_TASKS.md`
6. `06_SCHEMA_AND_ARTIFACT_CONTRACT.md`
7. `07_TEST_PLAN.md`
8. `08_ACCEPTANCE.md`
9. `09_STOP_CONDITIONS.md`
10. `10_CODER_HANDOFF_PROMPT.md`

Current decision:

- Do not add `bitget_futures` or `hyperliquid_perp` to `VenueId` yet.
- Do not add production Bitget live order or Hyperliquid live order paths in
  this slice.
- First implement a fixture-first venue design gate and read-only capability
  contract.
- Treat Bitget demo, Bitget futures, Hyperliquid direct perp, and Trade[XYZ] as
  separate venue concepts.
