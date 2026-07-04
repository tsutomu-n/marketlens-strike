<!--
作成日: 2026-07-04_23:18 JST
更新日: 2026-07-04_23:18 JST
-->

# G3 Ticker Source Plan

## Checkpoint ID

G3-TICKER-SOURCE-2026-07-04

## Purpose

Address one blocker from the 10 event pre-actual-cash real-data-adjacent dogfood:
`TICKER_SOURCE_MISSING_BLOCKS_COST_ADJUSTED_ESTIMATE_AND_EDGE_ACTION`.

The goal is to connect a local ticker source reference into per-event
`crypto_perp_source_availability.v1` artifacts so `ticker` can be available
without claiming actual cash, live readiness, exchange write readiness, or profit proof.

## Current State

The dogfood pack under
`docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/` reports:

- `decision=COLLECT_MORE_SOURCES`
- `event_count=10`
- `outcome_count=10`
- `ticker.missing_event_count=10`
- `can_compute_cost_adjusted_estimate_count=0`
- `selected_action_counts={'UNKNOWN': 10}`

Existing `build_source_availability()` already recognizes ticker-like
`source_refs` through path or schema text containing `ticker`, `tickers`, or
`market_snapshot`. The missing path is passing a validated local ticker source
reference through the per-event profit-readiness run.

## Constraints

- Do not add actual cash, cash ledger, actual-cash rows, actual-cash gates, wallet/signing, exchange writes, tiny-live, or live orders.
- Do not add trades, books, replay expansion, event-definition changes, 30 event expansion, ML/LLM decisions, or bias sample-size changes.
- Do not use future ticker snapshots as event-time ticker evidence.
- Keep the source explicit as local pre-actual-cash evidence, not profit proof.
- Preserve existing behavior when no extra source refs are passed.

## Target Files

- `src/sis/crypto_perp/profit_readiness.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

1. Add a small parser for local extra source refs in the profit-readiness CLI.
2. Add `extra_source_refs` to `build_profit_readiness_run()` and pass them to
   `build_source_availability()`.
3. Rebuild the concrete source/feature/edge artifacts in the CLI using the same
   extra refs as the manifest.
4. Add a focused regression test proving a ticker source ref changes ticker
   availability and cost-adjusted estimate availability without enabling actual cash.
5. Build local ticker proxy artifacts for the 10 existing dogfood event windows
   from the already-local public candle row at or before each event cutoff.
6. Re-run the pack over the same 10 event/outcome pairs and update the tracked
   dogfood summaries.

## Test Plan

- `uv run pytest tests/crypto_perp/test_source_availability.py tests/crypto_perp/test_profit_readiness_local_automation.py`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `uv run sis --help | rg "pre-actual-cash|pre_actual_cash|evidence-pack" || true`
- `./scripts/check` if focused tests pass.

## Completion Conditions

- A per-event run can carry an explicit ticker source ref into
  `source_availability.json`.
- The ticker status is available while actual-cash status remains false.
- Dogfood summaries show `ticker.missing_event_count=0`.
- Dogfood summaries show `can_compute_cost_adjusted_estimate_count > 0`.
- The result still avoids actual cash, tiny-live, live-order, wallet/signing, and
  exchange-write claims.

## Failure Conditions

- A future ticker snapshot is used as event-time evidence.
- A generic source ref silently marks ticker available without an explicit ticker
  path or schema.
- Existing no-extra-source behavior changes.
- The update claims actual cash profit or live readiness.

## Critique Pass 1

Risk: a candle-close ticker proxy is not a true exchange ticker snapshot.
Correction: name it as a local pre-actual-cash ticker proxy artifact and keep
actual cash/live/profit flags false.

Risk: adding a broad CLI option could be abused to mark arbitrary sources.
Correction: the option only passes source refs; source availability still requires
the ref text to match the target source id and does not change row counts or actual
cash status by itself.

## Critique Pass 2

Risk: updating only docs without a durable code path would make the dogfood hard
to reproduce. Correction: add a tested API/CLI path for explicit local source refs.

Risk: fixing ticker may expose funding semantics as the next blocker. Correction:
record that separately; do not broaden this checkpoint into funding.

## Branch

`ai/g3-ticker-source-20260704-2318`

## Destructive Change

No destructive operation is planned.
