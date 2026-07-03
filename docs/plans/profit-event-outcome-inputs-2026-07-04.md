<!--
作成日: 2026-07-04_07:34 JST
更新日: 2026-07-04_07:44 JST
-->

# Profit Event Outcome Inputs

## Checkpoint

PEO1: Create real `crypto_perp_event.v1` and matured `crypto_perp_outcome.v1` inputs from existing validated BTCUSDT public 5m candle data.

## Purpose

The Reality Check sprint now stops at `BLOCKED_MISSING_EVENT_OR_OUTCOME`. The repo has a validated C9 dogfood CSV:

`data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/input/BTCUSDT_5m_input.csv`

It is public market data, hash-validated by `strategy_input_contract_validation.v1`, and has no credentials, fills, slippage, wallet, signing, exchange write, or live order evidence. It can support a real market observation event and a matured before-cost outcome, but not actual cash.

## Current State

- `crypto-perp-outcome-record` exists and writes `crypto_perp_outcome.v1`.
- `crypto-perp-outcome-record` currently uses current wall-clock time as `settled_at`; this is wrong for historical matured horizons.
- No public `crypto-perp-event-record` command exists.
- `crypto-perp-raw-refresh` can create events from provider probe/audit artifacts, but those raw probe/audit artifacts are not present in the current local `data/` tree.
- Existing detector event families are `slow_pump_74h_v1`, `fast_pump_1h_v1`, and `near_miss_v1`.
- The BTCUSDT 5m run does not meet the existing fast/near-miss pump thresholds; using those families would be misleading.

## Constraints

- Do not fabricate a detector event.
- Do not label preview, estimate, backtest, or dogfood as actual cash evidence.
- Do not run network, credentials, exchange write, actual cash rows build, actual-cash gate, demo/testnet, or external LLM API.
- Do not grant live permission; every boundary flag remains false.
- Keep the generated event/outcome under `data/` as runtime artifacts, not tracked source of truth.

## Target Files

- `src/sis/crypto_perp/events.py`
- `src/sis/commands/crypto_perp_records.py`
- `schemas/crypto_perp_event.v1.schema.json`
- `tests/crypto_perp/test_events.py`
- `tests/crypto_perp/test_outcomes.py`
- `tests/crypto_perp/test_record_command_registration.py`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md`
- `docs/final-summary.md`
- `.ai-work/state.md`

## Implementation Plan

1. Add `market_window_v1` to the event family enum and schema.
2. Add a helper that builds a `CryptoPerpEvent` from an already validated public candle CSV window.
3. Add `crypto-perp-event-record` CLI:
   - required: `--input-csv`, `--symbol`, `--information-cutoff-at`
   - optional: `--contract`, `--validation`, `--out`, `--lookback-minutes`
   - output: event JSON/Markdown
   - no network or exchange write
4. Make the event helper use only rows with `available_at <= information_cutoff_at`.
5. Compute 15m/60m/window returns from the CSV without pretending that 74h data exists.
6. Record source refs for CSV, contract, and validation.
7. Add `--settled-at` to `crypto-perp-outcome-record` so historical matured outcome timestamps can be explicit.
8. Generate one BTCUSDT event and one matured 360m outcome from the existing CSV.
9. Re-run `crypto-perp-profit-readiness-inventory`, `crypto-perp-profit-readiness-plan`, and `crypto-perp-profit-readiness-run-local`.

## Selected Runtime Input

Use the largest absolute 60m move in the validated CSV that still has a full 360m future horizon:

- event cutoff: `2026-06-27T19:50:00Z`
- reference price: `60150.8`
- horizon: `360` minutes
- settled_at: `2026-06-28T01:50:00Z`

This is an observation window, not alpha proof and not actual cash.

## Test Plan

```bash
uv run pytest tests/crypto_perp/test_events.py tests/crypto_perp/test_outcomes.py tests/crypto_perp/test_record_command_registration.py tests/crypto_perp/test_profit_readiness_local_automation.py -q
uv run sis crypto-perp-event-record --help
uv run sis crypto-perp-outcome-record --help
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- `crypto_perp_event.v1` can be generated from the validated BTCUSDT 5m CSV without network or exchange write.
- `crypto_perp_outcome.v1` can be generated with historical `settled_at`.
- Profit-readiness inventory sees exactly one event and one matured outcome in the selected input directory.
- Profit-readiness plan becomes `READY_FOR_LOCAL_RUN`.
- Profit-readiness run executes locally and blocks on actual-cash/source gaps.
- No actual cash rows/gate/live permission claim is made.

## Failure Conditions

- The implementation labels the observation as a pump detector event.
- The implementation uses future rows for event features.
- The outcome uses wall-clock time instead of horizon settlement time.
- Any generated artifact implies actual cash, live readiness, order permission, wallet/signing, or exchange write.

## Critique Pass 1

Adding an event family is a schema change. The alternative is to force `near_miss_v1`, but that is worse because the data does not meet the threshold. A distinct `market_window_v1` is more honest and easier to reason about.

## Critique Pass 2

This still does not create actual cash evidence. It only moves the system from missing event/outcome inputs to local before-cost/proxy profit-readiness artifacts. The next blocker is expected to be actual cash source / rows / gate, not live readiness.

## Rollback

Revert the event family/schema/CLI additions and remove generated runtime artifacts under `data/`.

## Destructive Change

No.

## Branch

`ai/profit-event-outcome-inputs-20260704-0730`
