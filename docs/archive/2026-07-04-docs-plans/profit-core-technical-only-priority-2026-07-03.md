<!--
作成日: 2026-07-03_13:24 JST
更新日: 2026-07-03_13:30 JST
-->

# Profit Core Technical-Only Priority Plan

## Checkpoint ID

RC7-TECHNICAL-ONLY-PRIORITY

## Purpose

`BRIDGED_TECHNICAL_ONLY` が具体的な profit-readiness / actual-cash input 不足を隠さないようにする。

Technical bridge は重要な境界表示だが、次に直すべき作業ではない。`bridge_success_semantics=technical_only` と `economic_gate_status=NOT_EVALUATED` を残しつつ、`next_single_blocker_to_fix` は real event / matured outcome / actual cash source などの具体的な不足を優先する。

## Current Facts

- RC6 dogfood は bridge 5件すべて `BRIDGED`、bridge blocker 0件。
- Reality check は `next_single_blocker_to_fix=BRIDGED_TECHNICAL_ONLY`。
- 同じ artifact には `BLOCKED_MISSING_EVENT_OR_OUTCOME`、`ACTUAL_CASH_SOURCE_MISSING`、`RISK_REVIEW_MISSING`、`ACTUAL_CASH_ROWS_MISSING` も出ている。
- `BRIDGED_TECHNICAL_ONLY` は hard blocker ではなく、technical bridge を profit proof と読まないための境界表示。

## Constraints

- Public schema / CLI surface は変えない。
- `BRIDGED_TECHNICAL_ONLY` blocker を削除しない。
- `bridge_success_semantics=technical_only`、`economic_gate_status=NOT_EVALUATED`、`actual_cash_result_available=false` は維持する。
- Missing real event / actual cash source を生成しない。
- actual cash rows、actual-cash gate、demo/testnet、external LLM API は実行しない。

## Target Files

- `src/sis/profit_core_reality_check/summarize.py`
- `tests/profit_core_reality_check/test_profit_core_reality_check.py`
- `docs/plans/2026-07-03-profit-core-reality-check/02_EXISTING_PIPELINE_TRACE.md`
- `docs/plans/2026-07-03-profit-core-reality-check/06_NEXT_DECISION_AFTER_DOGFOOD.md`
- `docs/final-summary.md`

## Implementation Approach

1. `NEXT_BLOCKER_PRIORITY` で `BRIDGED_TECHNICAL_ONLY` を concrete economic blockers の後ろへ移動する。
2. Existing test を更新し、bridge-only artifact では `PROFIT_READINESS_INVENTORY_MISSING` が次になることを固定する。
3. New focused test を追加し、inventory が `BLOCKED_MISSING_EVENT_OR_OUTCOME` の場合はそれが `BRIDGED_TECHNICAL_ONLY` より優先されることを固定する。
4. `BRIDGED_TECHNICAL_ONLY` は `blocker_counts` / `top_blockers` に残ることを検査する。
5. Dogfood を再実行して next blocker が concrete missing-input blocker に移ることを確認する。

## Test Plan

```bash
uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q
uv run sis profit-core-reality-check ...
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- `BRIDGED_TECHNICAL_ONLY` remains visible.
- Concrete missing economic input blockers outrank `BRIDGED_TECHNICAL_ONLY`.
- RC6 dogfood next blocker becomes `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- No schema / CLI surface change.
- No runtime artifact is promoted to profit evidence.

## Verification Record

- `uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q` -> 8 passed.
- Re-ran `profit-core-reality-check` on the RC6 dogfood candidate/bridge artifacts.
- Dogfood `next_single_blocker_to_fix` moved from `BRIDGED_TECHNICAL_ONLY` to `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- `BRIDGED_TECHNICAL_ONLY` remains in `blocker_counts` and top blockers.
- Bridge summary still reports `bridge_success_semantics=technical_only`, `economic_gate_status=NOT_EVALUATED`, and `actual_cash_result_available=false`.
- `uv run python scripts/check_current_docs.py` -> checked 202 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2869 passed`.

## Failure Conditions

- `BRIDGED` is treated as pass, profit proof, paper permission, or live permission.
- `BRIDGED_TECHNICAL_ONLY` disappears from the report.
- Missing event/outcome or actual cash inputs are silently generated.

## Critique Pass 1

Risk: Moving `BRIDGED_TECHNICAL_ONLY` lower could hide the technical-only caveat.

Correction: Keep it in `blocker_counts`, `top_blockers`, bridge summary fields, report fields, and known gaps; only stop selecting it as the first actionable blocker while concrete economic inputs are missing.

## Critique Pass 2

Risk: This still does not create profit evidence.

Correction: That is intentional. The next blocker should truthfully point at the missing real event / matured outcome path rather than encouraging more bridge work.
