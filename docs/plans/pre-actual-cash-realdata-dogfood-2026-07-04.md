<!--
作成日: 2026-07-04_22:52 JST
更新日: 2026-07-04_22:52 JST
-->

# Pre Actual Cash Real Data Dogfood Plan

## Checkpoint ID

PAC-REALDATA-DOGFOOD-2026-07-04

## Purpose

Use the existing internal `write_pre_actual_cash_evidence_pack()` with 10 real-data-adjacent BTCUSDT public-candle event / outcome pairs. This is not a profit search. The goal is to verify whether the current writer can read existing local artifacts, emit the 11 pack artifacts, classify the candidate into the existing 4-choice decision, and expose one next blocker.

## Current State

The previous varied dogfood proved structure: 10 distinct event ids, outcome ids, timestamps, and synthetic regime proxies. That is useful as a writer test, but it is still not evidence-rich. The current repo has a validated BTCUSDT public 5m candle CSV at:

`data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/input/BTCUSDT_5m_input.csv`

The CSV has 200 rows from `2026-06-27T12:20:00Z` through `2026-06-28T04:55:00Z`. Existing `crypto-perp-event-record` and `crypto-perp-outcome-record` surfaces can represent historical public-candle event/outcome inputs without network, credentials, exchange write, or live orders. Existing `build_profit_readiness_run()` can create per-event local source/replay/feature/edge artifacts for the writer to read as `artifact_origin=existing`.

## Constraints

- Use existing `write_pre_actual_cash_evidence_pack()`.
- Do not add a new public CLI.
- Do not add actual cash source, cash ledger, actual-cash rows, actual-cash gate, tiny-live behavior, live order, exchange write, wallet/signing, production deploy, credential changes, external API calls, or ML/LLM trade decisions.
- Do not claim profit proof, actual cash readiness, tiny-live readiness, or live trading readiness.
- Keep source addition out of this checkpoint. G3 must be chosen after reading this dogfood's blocker.
- Treat `NO_TRADE` as a valid action, not a nuisance.

## Target Files

- `docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/decision.json`
- `docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/decision.md`
- `docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/blocker.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

Runtime-only generated inputs and per-event run artifacts go under:

`data/crypto_perp/pre_actual_cash_realdata_dogfood_20260704/`

## Implementation Approach

Use 10 hourly market windows with a 360-minute future outcome horizon:

- `2026-06-27T13:50:00Z`
- `2026-06-27T14:50:00Z`
- `2026-06-27T15:50:00Z`
- `2026-06-27T16:50:00Z`
- `2026-06-27T17:50:00Z`
- `2026-06-27T18:50:00Z`
- `2026-06-27T19:50:00Z`
- `2026-06-27T20:50:00Z`
- `2026-06-27T21:50:00Z`
- `2026-06-27T22:50:00Z`

For each cutoff:

1. Build a `market_window_v1` event from rows available at or before the cutoff.
2. Build a matured outcome from the next 360 minutes of public candles.
3. Build a local profit-readiness run for that event/outcome pair, so per-event source/replay/feature/edge artifacts exist under the writer `data_dir`.
4. Run `write_pre_actual_cash_evidence_pack()` over the resulting 10-pair directory.
5. Copy the generated pack summaries and decision artifacts into `docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/`.
6. Add a blocker note that selects exactly one next blocker from the generated decision and source gaps.

## Test Plan

- Validate generated `decision.json` against `crypto_perp_pre_actual_cash_decision.v1.schema.json`.
- Confirm 11 pack artifacts are generated.
- Confirm `event_count=10` and `outcome_count=10`.
- Confirm source/replay/feature/edge artifact origin counts are `existing: 10`.
- Confirm decision is one of `KILL`, `REVISE_EVENT_DEFINITION`, `COLLECT_MORE_SOURCES`, or `HOLD_FOR_FUTURE_ACTUAL_CASH`.
- Confirm all `non_goal_flags` are `false`.
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `uv run sis --help | rg "pre-actual-cash|pre_actual_cash|evidence-pack" || true`
- `./scripts/check`

## Completion Conditions

- 10 real-data-adjacent event/outcome pairs are generated from the existing validated BTCUSDT 5m CSV.
- Existing per-event run artifacts are created and read by the writer.
- The writer emits 11 artifacts.
- `decision.json` is schema-valid.
- `decision.md` records event count, outcome count, source gaps, selected action counts, leader action, leader beats no trade, bias guard status, PBO status, decision, and reason codes.
- One next blocker is selected and recorded.
- No out-of-scope public CLI, actual cash, tiny-live, live order, exchange write, wallet/signing, or ML/LLM decision behavior is added.

## Failure Conditions

- The dogfood silently falls back to synthetic or cloned fixtures.
- The writer recomputes per-event source/replay/feature/edge artifacts instead of reading existing artifacts.
- The result claims profit proof or readiness.
- More than one blocker is selected for the next step.
- The selected blocker is chosen before reading the generated decision and source gaps.

## Critique Pass 1

Risk: public 5m candles are still not actual cash or full market microstructure. Correction: call the run real-data-adjacent, not real profit evidence; preserve the no-profit/no-readiness boundary in `decision.md`, `blocker.md`, and final summary.

Risk: all events will have `event_family=market_window_v1`, so the earlier synthetic `event_family` regime proxy no longer applies. Correction: use data-derived window regime proxies outside the event schema: 60m direction, 60m range, turnover, time-of-day, and 360m outcome. Do not pretend this is a schema regime field.

Risk: running only the pack over event/outcome files would make source gaps look recomputed by writer. Correction: build per-event run-local artifacts first, then verify source/replay/feature/edge origin counts are `existing: 10`.

## Critique Pass 2

Risk: selecting `ACTUAL_CASH_SOURCE_MISSING` as the next blocker would jump beyond the user's requested pre-actual-cash source triage. Correction: choose one pre-actual-cash blocker from `selected_action=UNKNOWN`, `can_compute_cost_adjusted_estimate=false`, optional features missing, depth missing, NO_TRADE, or bias sample insufficiency.

Risk: trying to fix the blocker in the same pass would inflate scope. Correction: this checkpoint only identifies one blocker. It does not add ticker/funding/trades/books/replay.

Risk: generated runtime artifacts under `data/` are ignored. Correction: copy the decision, summaries, and blocker note into tracked docs; keep the heavy raw/runtime chain under `data/`.

## Open Issues

None requiring user action.

## Destructive Change

No destructive operation is planned.

## Branch

`ai/pre-actual-cash-realdata-dogfood-20260704-2252`

## Migration

No migration is required.
