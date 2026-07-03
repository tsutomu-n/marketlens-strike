<!--
作成日: 2026-07-03_12:44 JST
更新日: 2026-07-03_12:49 JST
-->

# Profit Core Reality Check Source Blocker Priority Plan

## Checkpoint ID

RC3-SOURCE-BLOCKER-PRIORITY

## Purpose

`profit-core-reality-check` の `NEXT_BLOCKER_PRIORITY` から `NO_SYMBOL_DATA_DOMINATES` と `MISSING_SOURCE_COLUMNS_DOMINATES` が抜けている不一致を直す。

この2つは hard blocker と taxonomy / next action mapping には存在する。だが priority に無いため、source blocker が存在しても `BRIDGED_TECHNICAL_ONLY` など後続の blocker に隠れるリスクがある。

## Current Facts

- `HARD_BLOCKERS` には `NO_SYMBOL_DATA_DOMINATES` と `MISSING_SOURCE_COLUMNS_DOMINATES` がある。
- bridge summary は `BLOCKED_NO_SYMBOL_DATA` と `BLOCKED_MISSING_SOURCE_COLUMNS` を集計し、dominant なら stage blocker に追加している。
- `NEXT_BLOCKER_PRIORITY` にはこの2つが無い。
- `docs/plans/2026-07-03-profit-core-reality-check/05_BLOCKER_TAXONOMY.md` の next action mapping にはこの2つがある。
- RC2 dogfood では `MISSING_SOURCE_COLUMNS_DOMINATES` が発生したが、top blockers では `BRIDGED_TECHNICAL_ONLY` より下に隠れ得る状態だった。

## Constraints

- blocker name、public schema、CLI surface は変えない。
- actual cash rows、gate、demo/testnet、external API は触らない。
- source不足を estimate で埋めない。
- current dogfood の `UNSUPPORTED_SIDE_BIAS_DOMINATES` を無理に消さない。

## Target Files

- `src/sis/profit_core_reality_check/summarize.py`
- `tests/profit_core_reality_check/test_profit_core_reality_check.py`
- `docs/plans/2026-07-03-profit-core-reality-check/02_EXISTING_PIPELINE_TRACE.md`
- `docs/final-summary.md`

## Implementation Approach

1. `NEXT_BLOCKER_PRIORITY` に `NO_SYMBOL_DATA_DOMINATES` と `MISSING_SOURCE_COLUMNS_DOMINATES` を追加する。
2. 位置は C9 bridge structural blockers と `BRIDGED_TECHNICAL_ONLY` の間に置く。
3. Focused test を追加し、missing source columns がある場合に `BRIDGED_TECHNICAL_ONLY` より先に選ばれることを固定する。
4. docs の priority list をコードと合わせる。
5. RC2 dogfoodを再評価し、`top_blockers` に `MISSING_SOURCE_COLUMNS_DOMINATES` が表示されることを確認する。

## Test Plan

```bash
uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q
uv run sis profit-core-reality-check \
  --candidate-set data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/candidates/strategy_idea_candidate_set.json \
  --search-ledger data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/candidates/search_ledger.jsonl \
  --export-manifest data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/candidates/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json \
  --authoring-bridge data/profit_core_reality_check/dogfood/c9-reversal-fail-closed/authoring_bridge/strategy_idea_candidate_authoring_bridge_manifest.json \
  --profit-readiness-inventory data/profit_core_reality_check/dogfood/c9-btcusdt-realdata-20260628T045945Z/profit_readiness_inventory/inventory.json \
  --out data/profit_core_reality_check/dogfood/c9-source-priority/summary
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- Source blockers appear in deterministic next-blocker priority before `BRIDGED_TECHNICAL_ONLY`.
- Existing unsupported family and side-bias behavior remains deterministic.
- Focused tests pass.
- RC2 dogfood report includes `MISSING_SOURCE_COLUMNS_DOMINATES` in top blockers.
- Full verification passes.

## Verification Record

- `uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q` -> 7 passed.
- Dogfood `profit-core-reality-check` -> `next_single_blocker_to_fix=UNSUPPORTED_SIDE_BIAS_DOMINATES`.
- Dogfood top blockers -> `UNSUPPORTED_SIDE_BIAS_DOMINATES`, `MISSING_SOURCE_COLUMNS_DOMINATES`, `BRIDGED_TECHNICAL_ONLY`, `BLOCKED_MISSING_EVENT_OR_OUTCOME`, `ACTUAL_CASH_SOURCE_MISSING`.
- `uv run python scripts/check_current_docs.py` -> checked 198 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2865 passed`.

## Failure Conditions

- The change makes `BRIDGED_TECHNICAL_ONLY` hide source blockers.
- The change removes or renames blocker values.
- The change claims source availability or profit evidence.
- The change changes CLI/schema output shape.

## Critique Pass 1

Risk: Reordering blockers could change current dogfood `next_single_blocker_to_fix` and make the report look inconsistent with the latest pushed RC2 summary.

Correction: Add missing source blockers after `UNSUPPORTED_SIDE_BIAS_DOMINATES`, not before it. Current dogfood can still choose side-bias first, while source blockers stop being hidden in source-only cases.

## Critique Pass 2

Risk: This may look like progress on actual source availability. It is not. It only fixes reporting priority.

Correction: Keep verification focused on blocker ordering and state clearly that liquidation source support remains unimplemented.
