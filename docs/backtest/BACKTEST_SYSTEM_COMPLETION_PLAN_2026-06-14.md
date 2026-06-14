<!--
作成日: 2026-06-14_20:12 JST
更新日: 2026-06-14_20:29 JST
-->

# Backtest System Completion Plan

## 目的

MarketLens Strike の backtest system を、local artifact、source hash、paper-only / no-live boundary、baseline / negative control、data availability、trial ledger、assumption ledger、no-lookahead differential、execution-aware order/fill events、pack validation まで一貫して再生成できる状態にする。

標準 engine は `strategy_authoring_native` で固定する。`vectorbt`, `bt`, `metrics`, `reports` は optional surface であり、標準 engine を置き換えない。

## 制約

- live order、wallet、signing、exchange write は禁止。
- Bitget / Hyperliquid direct schema widening と Coinalyze collector は current scope に入れない。
- NautilusTrader / HftBacktest / Tardis / PyBroker / Qlib / FinRL / skfolio は current dependency に入れない。
- replay-style simulation から market impact を主張しない。
- backtest artifact から alpha / live readiness を主張しない。
- すべての completion artifact は source path / hash と paper-only boundary を持つ。

Future scope は [BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md](BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md) に分ける。

## 対象ファイル

実装済み:

- `src/sis/backtest/data_availability.py`
- `src/sis/backtest/baselines.py`
- `src/sis/backtest/no_lookahead.py`
- `src/sis/backtest/execution_simulation.py`
- `src/sis/backtest/assumptions.py`
- `src/sis/backtest/trial_ledger.py`
- `src/sis/backtest/compare.py`
- `src/sis/backtest/pack.py`
- `src/sis/backtest/artifact_summary.py`
- `src/sis/commands/strategy_authoring.py`
- `schemas/backtest_data_availability_ledger.v1.schema.json`
- `schemas/strategy_backtest_baseline_comparison.v1.schema.json`
- `schemas/strategy_backtest_no_lookahead_diff.v1.schema.json`
- `schemas/strategy_backtest_execution_simulation.v1.schema.json`
- `schemas/strategy_backtest_assumption_ledger.v1.schema.json`
- `schemas/strategy_backtest_trial_ledger.v1.schema.json`
- `tests/backtest/test_completion_artifacts.py`
- `tests/strategy_authoring/test_cli_bundle.py`

Docs:

- `docs/backtest/README.md`
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`
- `docs/backtest/BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md`

## 実装済み Completion Artifacts

| Artifact | CLI | Schema | 役割 |
|---|---|---|---|
| Data availability ledger | `strategy-backtest-data-availability` | `backtest_data_availability_ledger.v1` | local metrics / signals / quotes の source hash、parquet row count、timestamp range、gap / duplicate、future candidate provider を記録 |
| Baseline comparison | `strategy-backtest-baseline-compare` | `strategy_backtest_baseline_comparison.v1` | cash/no-trade、単純手法、random throttle、leverage との比較 |
| No-lookahead diff v1 | `strategy-backtest-no-lookahead-diff` | `strategy_backtest_no_lookahead_diff.v1` | 未来側 feature rows を変異させて再実行し、cutoff 以前の signals / executed backtest rows が不変か検査 |
| Execution simulation v1 | `strategy-backtest-execution-sim` | `strategy_backtest_execution_simulation.v1` | native metrics から paper-only order intents / fill events を作り、未モデル venue realism を明示 |
| Assumption ledger | `strategy-backtest-assumption-ledger` | `strategy_backtest_assumption_ledger.v1` | measured / configured / assumed / unknown を分離 |
| Trial ledger | `strategy-backtest-trial-ledger` | `strategy_backtest_trial_ledger.v1` | 成功・missing を含む trial / artifact 台帳 |

## Pack Integration

`strategy-backtest-pack` は次を標準 chain で生成する。

1. single Strategy Authoring backtest
2. 5-method suite
3. bundle / portfolio comparison
4. adapter spike / external result / metric / report extension
5. stress / regime split / rolling stability / benchmark relative
6. data availability
7. baseline comparison
8. no-lookahead diff
9. execution simulation
10. assumption ledger
11. trial ledger
12. comparison
13. pack manifest
14. pack validation

`strategy-backtest-pack-validate` は completion artifact の存在、hash、boundary を検査する。

## テスト方針

最小検証:

```bash
uv run pytest tests/backtest/test_completion_artifacts.py tests/strategy_authoring/test_backtest_pack_validation.py tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain
uv run python scripts/check_current_docs.py
```

標準 fixture での動作確認:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

フル検証:

```bash
./scripts/check
```

## 完了条件

次をすべて満たすこと。

- `strategy-backtest-pack` が local fixture から completion artifact を含む pack を生成する。
- `strategy-backtest-pack-validate` が `decision=PASS` を返す。
- `strategy-backtest-artifact-summary` に `data_availability`, `baseline_comparison`, `no_lookahead_diff`, `execution_simulation`, `assumption_ledger`, `trial_ledger` が表示される。
- completion artifact が schema-valid である。
- completion artifact が `paper_only=true`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を持つ。
- docs current checker が通る。
- `./scripts/check` が通る。

## 残る強化タスク

現在の v0 で完成線に入れたが、将来強化すべき点:

- `strategy-backtest-no-lookahead-diff` を feature mutation だけでなく、将来は signal rows / quote rows mutation replay にも広げる。
- `strategy-backtest-execution-sim` を paper-only order intent / fill event から、将来は cancel race / modify / unknown state の venue-specific event model へ進める。
- `trial_ledger` を artifact-level から parameter / framework / candidate-level ledger へ広げる。
- `baseline_comparison` に buy-and-hold と funding carry を、入力データが揃った場合だけ実計算で追加する。

これらは v0 完了後の quality improvement であり、current scope に live / direct venue / external data provider adoption を混ぜる理由にはしない。
