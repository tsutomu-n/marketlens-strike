<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-17_11:38 JST
-->

# Venue Read-Only Capability Probe Plan

This is the next implementation plan after
`02_bitget_hyperliquid_venue_design_gate`.

Current implementation source for this plan:

1. `11_PR_VENUE_PROBE_00_FINAL_PLAN.md`
2. `12_PR_VENUE_PROBE_01_DOGFOOD_AND_DECISION.md`
3. `13_PR_VENUE_PROBE_01_DECISION.md`
4. older split plan files below for background and cross-checks

Goal: add a fixture-first read-only capability probe surface for future
`bitget_futures` and `hyperliquid_perp` without widening `VenueId`, enabling
Strategy Lab artifacts, calling external APIs by default, using credentials,
or adding any order path.

Read historical split files in order only after the final plan:

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

Current decision:

- `PR-VENUE-PROBE-01` selected `NO_ACTION` after local dogfood.
- The dogfood does not prove credentialed read-only network readiness, paper
  readiness, live readiness, wallet readiness, signing readiness, or
  exchange-write readiness.
- Additional work requires a new explicit plan.

Assumptions:

- This slice is local/fixture-first only.
- Default CLI and tests must not touch external networks.
- `bitget_futures` and `hyperliquid_perp` remain disabled for schemas, paper,
  evaluation plans, and live execution.
- A later explicit approval is required before credentialed network probes,
  paper execution, schema widening, or live execution.
