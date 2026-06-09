<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Code Truth And Risk Review

## Current Code Truth

- `src/sis/venues/ids.py`
  - `VenueId = Literal["trade_xyz", "bitget_demo"]`
  - `VENUE_IDS = ("trade_xyz", "bitget_demo")`
- `src/sis/venues/capabilities.py`
  - catalog keys: `trade_xyz`, `bitget_demo`, `bitget_futures`,
    `hyperliquid_perp`
  - `bitget_futures` and `hyperliquid_perp` are schema/paper/network/live
    disabled
  - `bitget_demo` is execution-venue-schema enabled but
    `strategy_lab_evaluation_plan_enabled=false`
- `src/sis/venues/suitability.py`
  - same four venue keys
  - future venues are not enabled for operator context
- `schemas/evaluation_plan.mls.v1.schema.json`
  - `target_venue` is still `const: trade_xyz`
- `src/sis/commands/execution.py`
  - existing `bitget-demo-smoke` is local/mock-first and writes summary/report
  - existing `execution-read-only-surfaces` writes a read-only surface report
- `src/sis/execution/bitget_demo_adapter.py`
  - local demo env detection and signing helpers exist
  - default read-only network probe is `not_executed`

## Strongest Source Of Truth

Use this priority:

1. code and tests under `src/sis/` and `tests/`
2. JSON schemas under `schemas/`
3. `uv run sis --help`
4. current docs: `README.md`, `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`,
   `docs/venues/bitget_hyperliquid_capability_gate.md`
5. plan docs

## Risks Found In Additional Review

- The next implementation could add a CLI that sounds like network readiness.
- The artifact could omit `external_api_used=false` or `exchange_write_used=false`.
- The probe could accidentally read credentials from tracked files or print env
  values.
- The future venue artifact could drift from capability/suitability catalog
  keys.
- The plan could under-specify tests and let schema widening slip in.

## Risk Reduction In This Plan

- Add a dedicated artifact contract with explicit false fields.
- Require tests that compare artifact venue ids to capability catalog keys.
- Require tests that schema files and `VenueId` remain unchanged.
- Require CLI wording to use `blocked`, `not_configured`, or `not_executed`,
  never `ready`.
- Require full `./scripts/check` before completion.

