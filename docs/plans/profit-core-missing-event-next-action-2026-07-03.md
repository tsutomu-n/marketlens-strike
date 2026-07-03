<!--
作成日: 2026-07-03_13:33 JST
更新日: 2026-07-03_13:37 JST
-->

# Profit Core Missing Event Next Action Plan

## Checkpoint ID

RC8-MISSING-EVENT-NEXT-ACTION

## Purpose

`BLOCKED_MISSING_EVENT_OR_OUTCOME` の `next_action` を `FIX_BLOCKER` ではなく `COLLECT_INPUTS` にする。

この blocker はコード修正で消すものではなく、real `crypto_perp_event.v1` と matured `crypto_perp_outcome.v1` を用意する入力不足です。C9 backtest pack、dogfood status、viewer artifact を event/outcome に変換しない。

## Current Facts

- Current dogfood next blocker is `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Current `summary.next_action` is `FIX_BLOCKER`.
- `data/crypto_perp` currently contains dogfood/status/viewer artifacts, not real event or matured outcome artifacts.
- Existing CLI can record decisions/outcomes only when event/outcome source values are supplied; missing values should not be fabricated.

## Constraints

- No schema / public CLI change.
- Do not create fake event/outcome artifacts.
- Do not run actual-cash rows, gate, demo/testnet, external LLM API, or live measurement.
- Keep `overall_status=BLOCKED`.

## Target Files

- `src/sis/profit_core_reality_check/summarize.py`
- `tests/profit_core_reality_check/test_profit_core_reality_check.py`
- `docs/plans/2026-07-03-profit-core-reality-check/05_BLOCKER_TAXONOMY.md`
- `docs/final-summary.md`

## Implementation Approach

1. Update `_next_action()` so `BLOCKED_MISSING_EVENT_OR_OUTCOME` returns `COLLECT_INPUTS`.
2. Extend focused test coverage for the profit-readiness inventory blocker.
3. Re-run the current dogfood reality check and confirm `next_action=COLLECT_INPUTS`.
4. Document that this is an input collection stop, not an implementation success.

## Test Plan

```bash
uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q
uv run sis profit-core-reality-check ...
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- `BLOCKED_MISSING_EVENT_OR_OUTCOME` maps to `COLLECT_INPUTS`.
- Dogfood status remains `blocked`.
- No new event/outcome, actual-cash, gate, demo/testnet, or external API artifacts are generated.
- Docs explain that real event/outcome input is required.

## Verification Record

- `uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q` -> 8 passed.
- Re-ran `profit-core-reality-check` on the RC6 dogfood candidate/bridge artifacts.
- Dogfood remains `overall_status=BLOCKED`.
- Dogfood `next_single_blocker_to_fix=BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Dogfood `next_action=COLLECT_INPUTS`.
- `BRIDGED_TECHNICAL_ONLY` remains present in `blocker_counts`.
- `uv run python scripts/check_current_docs.py` -> checked 203 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2869 passed`.

## Failure Conditions

- C9 bridge/backtest artifacts are treated as real events or outcomes.
- Missing event/outcome is reported as complete or runnable without input.
- Live/paper/tiny-live permission is implied.

## Critique Pass 1

Risk: Changing `next_action` may look like a smaller result than implementing event/outcome generation.

Correction: That is the point. Event/outcome generation without real evidence would be worse than stopping. The practical fix is to label the stop as input collection.

## Critique Pass 2

Risk: This does not move beyond `BLOCKED_MISSING_EVENT_OR_OUTCOME`.

Correction: Moving beyond it requires real market event and matured outcome evidence. The repo should not manufacture that from dogfood artifacts.
