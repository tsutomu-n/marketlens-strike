<!--
作成日: 2026-06-16_06:46 JST
更新日: 2026-06-16_06:46 JST
-->

# Backtest Current Technical Reference

## 結論

この文書は、現行コードを正とした backtest 技術リファレンスである。過去の計画、採用前調査、実行ログは `docs/archive/backtest/` に移した。

標準 backtest engine は `strategy_authoring_native` のままである。外部 OSS は標準 engine を置き換えず、optional execution、analytics、reference-only contract、Constraint Breaker decision に分けて扱う。

## 標準入口

最短の標準 pack:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

単体 Strategy Authoring backtest:

```bash
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

## Backtest Surface

| Surface | Entry | Status | 用途 |
|---|---|---|---|
| Strategy Authoring native backtest | `strategy-author-run --through backtest` | 標準 | YAML strategy の paper-only 研究評価 |
| Backtest pack | `strategy-backtest-pack` | 標準 | suite、benchmark、stress、data availability、baseline、no-lookahead、comparison を一括生成 |
| Backtest suite | `strategy-backtest-suite` | 標準 | 複数 case / walk-forward / purged walk-forward / bootstrap を比較 |
| Framework run matrix | `strategy-backtest-framework-run` | optional | `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` を同一 artifact で扱う |
| Reference-only contracts | `strategy-backtest-*-contract`, `strategy-backtest-microstructure-readiness` | 採用前判定 | HftBacktest / qstrader / portfolio validation / PyBroker の readiness を記録 |
| Trade[XYZ] pure backtest v0.1 | `sis.backtest.engine.runner.run_backtest()` | Python API only | Trade[XYZ] 単一銘柄 long-only の isolated surface |
| Legacy bridge | `uv run sis build-backtest` | 互換維持 | historical Strategy Lab bridge |

## Artifact Chain

`strategy-backtest-pack` は主に次を生成する。

- signals parquet / jsonl / manifest
- native backtest metrics / report
- suite result / report
- adapter spike
- framework run matrix
- external result
- portfolio comparison
- metric extension
- report extension
- stress
- regime split
- rolling stability
- benchmark relative
- data availability
- baseline comparison
- no-lookahead diff
- execution simulation
- assumption ledger
- trial ledger
- comparison
- pack manifest / validation

`strategy-backtest-pack-validate` は artifact path / hash、paper-only / no-live boundary、completion artifact、external framework policy を検査する。

## Optional Extras

`pyproject.toml` / `uv.lock` の optional extras:

| Extra | Package | 用途 | 標準 engine か |
|---|---|---|---|
| `vectorbt` | `vectorbt==1.0.0` | signal runner / external check | no |
| `bt` | `bt==1.2.0` | portfolio allocation / rebalance comparison | no |
| `metrics` | `empyrical-reloaded==0.5.12` | metrics normalization | no |
| `reports` | `quantstats==0.0.81` | report / tear sheet | no |

通常 env で optional extra が無い場合、framework run matrix は `skipped/not_installed_in_current_env` として記録される。これは pack 失敗ではない。

optional extras 付きで検算する場合:

```bash
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-framework-run --framework vectorbt --framework bt --framework metrics --framework reports
```

pack manifest と生成 artifact の hash を揃える場合は、pack 自体も同じ extras env で再実行する。

## Reference-Only / 採用前 Contract

次は dependency 追加や engine 実行ではなく、採用前の readiness / contract を artifact 化する。

| Command | 対象 | 目的 |
|---|---|---|
| `strategy-backtest-microstructure-readiness` | HftBacktest など | L2/L3/tick/latency/queue input が足りるかを判定 |
| `strategy-backtest-qstrader-contract` | qstrader | local input contract を記録 |
| `strategy-backtest-portfolio-validation-contract` | skfolio / Riskfolio-Lib | portfolio validation / optimization reference として可用性を記録 |
| `strategy-backtest-pybroker-contract` | PyBroker | local DataFrame input / point-in-time feature provenance を判定 |
| `strategy-backtest-constraint-breaker-decision` | 制約破壊候補 | dependency 追加や標準 engine 変更の前に scorecard decision を残す |

これらは `dependency_added=false`, `engine_run=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。

## Safety Boundary

backtest artifact が許可しないこと:

- live order
- wallet
- signing
- exchange write
- broker / exchange credential の使用
- backtest 結果だけによる alpha claim
- backtest 結果だけによる paper pass claim
- backtest 結果だけによる live readiness claim
- market replay からの market impact claim

pack validation の `PASS` は artifact integrity と no-live boundary の検査結果であり、収益性や live readiness の証明ではない。

## Current Docs と Archive

現在の利用者・実装者向け入口:

- [BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md](BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md)
- [OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md](OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md)
- [BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md](BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md)
- [OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md](OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md)
- [VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md](VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md)
- [TRADE_XYZ_PURE_BACKTEST_V0_1.md](TRADE_XYZ_PURE_BACKTEST_V0_1.md)

履歴・採用前調査・完了済み計画は `docs/archive/backtest/` に置く。archive は判断履歴として残すが、current truth ではない。
