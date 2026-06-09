<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Venue Read-Only Capability Probe Plan

This is the next implementation plan after
`02_bitget_hyperliquid_venue_design_gate`.

Goal: add a fixture-first read-only capability probe surface for future
`bitget_futures` and `hyperliquid_perp` without widening `VenueId`, enabling
Strategy Lab artifacts, calling external APIs by default, using credentials,
or adding any order path.

Read in order:

1. `01_GOAL.md`
2. `02_SCOPE_AND_BOUNDARIES.md`
3. `03_CODE_TRUTH_AND_RISK_REVIEW.md`
4. `04_TARGET_FILE_MAP.md`
5. `05_ARTIFACT_CONTRACT.md`
6. `06_IMPLEMENTATION_TASKS.md`
7. `07_TEST_PLAN.md`
8. `08_ACCEPTANCE.md`
9. `09_STOP_CONDITIONS.md`
10. `10_CODER_HANDOFF_PROMPT.md`

Readiness verdict: ready with assumptions.

Assumptions:

- This slice is local/fixture-first only.
- Default CLI and tests must not touch external networks.
- `bitget_futures` and `hyperliquid_perp` remain disabled for schemas, paper,
  evaluation plans, and live execution.
- A later explicit approval is required before credentialed network probes,
  paper execution, schema widening, or live execution.

