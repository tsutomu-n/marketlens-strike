<!--
作成日: 2026-06-28_07:21 JST
更新日: 2026-06-28_07:21 JST
-->

# Cash Metric Legacy Migration Plan

## Checkpoint

I1b: `actual_cash_result_usd` の旧互換を残しつつ、非actual cashの正の数値を `cash_metric_value_usd` に移す。

## Purpose

before-cost proxy / estimate / mixed basis を `actual_cash_result_usd` field で表現し続ける誤読リスクを下げる。生成物は `cash_metric_value_usd` を必ず出し、`actual_cash_result_usd` は actual cash basis の時だけ値を持つ legacy alias にする。

## Current State

- `TournamentEventResult.actual_cash_result_usd` が score 計算の入力値でもあり、preview rows では before-cost proxy が入る。
- I1a で `cash_metric_basis`、`actual_cash`、`primary_metric_display_name` は追加済み。
- CLI report は `cash_metric_basis != actual_cash` rows を拒否する。
- `crypto_perp_tournament_report.v1` は v1 のまま optional field 追加で互換を維持している。

## Constraints

- 旧 `actual_cash_result_usd` rows は読み続ける。
- `crypto-perp-tournament-report` の actual-cash-only input guard は緩めない。
- preview / proxy rows を report input に昇格しない。
- schema version は v1 のまま、optional追加で既存artifact互換を優先する。
- public network、credential、exchange write、live order、dependency changeは行わない。

## Target Files

- `src/sis/crypto_perp/tournament.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `src/sis/strategy_workbench_viewer/summary_fields.py`
- `schemas/crypto_perp_tournament_report.v1.schema.json`
- `schemas/crypto_perp_tournament_rows_preview.v1.schema.json`
- `schemas/strategy_workbench_viewer.v1.schema.json`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `tests/crypto_perp/test_workbench_bridge.py`
- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/final-summary.md`

## Implementation Steps

1. Add `cash_metric_value_usd` to row and score models.
2. Accept legacy input where `cash_metric_value_usd` is absent by copying `actual_cash_result_usd`.
3. Serialize `actual_cash_result_usd` as `null` for non-actual rows and reports, while keeping it populated for actual cash rows.
4. Move scoring and leader summaries to `cash_metric_value_usd`.
5. Update preview rows and Markdown to use `cash_metric_value_usd` / `before_cost_proxy_usd`.
6. Update schemas with optional `cash_metric_value_usd` and nullable legacy `actual_cash_result_usd`.
7. Update Workbench compact summary and docs.

## Test Plan

- Preview rows emit `cash_metric_value_usd` and `actual_cash_result_usd=null`.
- Actual cash rows generated from old inputs still pass report CLI.
- Non-actual rows remain rejected by report CLI.
- Proxy basis report built via Python API has leader value but no leader actual cash alias.
- Schema validation accepts generated v1 artifacts.
- Workbench summary shows `leader_cash_metric_value_usd` and does not require legacy actual-cash alias for non-actual artifacts.

## Completion Conditions

- Focused Crypto Perp and Workbench tests pass.
- `check_current_docs.py`, `check_cli_catalog.py`, and `git diff --check` pass.
- Docs explain that `cash_metric_value_usd` is the value column and `actual_cash_result_usd` is actual-cash-only legacy alias.

## Failure Conditions

- Existing actual-cash JSONL without `cash_metric_value_usd` stops working.
- Preview rows can feed `crypto-perp-tournament-report`.
- Non-actual rows populate `actual_cash_result_usd` in generated artifacts.
- Gate or Workbench starts treating non-actual basis as fills/slippage evidence.

## Rollback

Revert this checkpoint's row/model/schema/test/docs changes. I1a remains a valid intermediate state.
