<!--
作成日: 2026-07-03_13:41 JST
更新日: 2026-07-03_13:46 JST
-->

# Profit Core Input Collection Report Plan

## Checkpoint ID

RC9-INPUT-COLLECTION-REPORT

## Purpose

`profit-core-reality-check.md` に、`next_action=COLLECT_INPUTS` の時だけ読む入力収集 section を追加する。

現在の停止点はコード修正ではなく real `crypto_perp_event.v1` / matured `crypto_perp_outcome.v1` 入力不足です。report が次に集める artifact と、代用してはいけない artifact を明示すれば、C9 bridge / dogfood / viewer を profit evidence と誤読しにくくなる。

## Current Facts

- Current dogfood: `next_single_blocker_to_fix=BLOCKED_MISSING_EVENT_OR_OUTCOME`。
- Current dogfood: `next_action=COLLECT_INPUTS`。
- `data/crypto_perp` has dogfood/status/viewer artifacts only.
- Existing report shows blockers but does not spell out required input artifacts or rejected substitutes.

## Constraints

- No JSON schema change.
- No public CLI option change.
- Do not create event/outcome/actual-cash artifacts.
- Do not run actual-cash rows, gate, demo/testnet, external LLM API, or live measurement.
- Keep `BRIDGED_TECHNICAL_ONLY` visible.

## Target Files

- `src/sis/profit_core_reality_check/rendering.py`
- `tests/profit_core_reality_check/test_profit_core_reality_check.py`
- `docs/final-summary.md`

## Implementation Approach

1. Add an `Input Collection` section to the Markdown renderer when `summary.next_action == COLLECT_INPUTS`.
2. For `BLOCKED_MISSING_EVENT_OR_OUTCOME`, list required `crypto_perp_event.v1` and matured `crypto_perp_outcome.v1`.
3. For `ACTUAL_CASH_SOURCE_MISSING`, list cash ledger / live measurement requirement.
4. Always list rejected substitutes: C9 bridge/backtest pack, dogfood/status/viewer artifacts, preview/estimate rows.
5. Add a focused renderer assertion to existing profit-core tests.

## Test Plan

```bash
uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q
uv run sis profit-core-reality-check ...
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- Report includes `## Input Collection` for `COLLECT_INPUTS`.
- Report names required event/outcome inputs for the current blocker.
- Report says C9 bridge/backtest and dogfood/status/viewer artifacts are not substitutes.
- JSON schema and CLI remain unchanged.

## Verification Record

- `uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q` -> 8 passed.
- Re-ran `profit-core-reality-check` on the RC6 dogfood candidate/bridge artifacts.
- Dogfood Markdown now contains `## Input Collection`.
- Dogfood Markdown lists real `crypto_perp_event.v1`, matured `crypto_perp_outcome.v1`, and cash source requirements.
- Dogfood Markdown rejects C9 bridge/backtest, dogfood/status/viewer, preview, estimate, virtual, and before-cost proxy rows as substitutes.
- `uv run python scripts/check_current_docs.py` -> checked 204 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2869 passed`.

## Failure Conditions

- Report implies event/outcome can be generated from C9 bridge output.
- Report hides the technical-only bridge boundary.
- Report says actual cash rows or gates should run before actual cash source exists.

## Critique Pass 1

Risk: This looks like documentation instead of progress.

Correction: At this stage, clear operator-facing input requirements are the safe next progress. Generating fake event/outcome artifacts would be worse.

## Critique Pass 2

Risk: A renderer-only section could drift from machine-readable JSON.

Correction: The source of truth remains `next_action`, `next_single_blocker_to_fix`, `blocker_counts`, and existing summaries. The section is a deterministic rendering of those existing fields, not a new hidden state.
