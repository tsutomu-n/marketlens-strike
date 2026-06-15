<!--
作成日: 2026-06-16_06:46 JST
更新日: 2026-06-16_06:46 JST
-->

# 大学生向け: 現行 Backtest Capability Guide

## 結論

この repo の backtest は、過去データで戦略候補を評価し、その評価がどの入力、期間、仮定、外部検算、失敗条件に基づくかを artifact として残す仕組みである。

中心は `strategy_authoring_native` である。外部 OSS は標準 engine の置き換えではなく、検算、metrics、report、採用前 readiness 判定に使う。

## まず何ができるか

最短では次を実行する。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

これで、単発 backtest、suite、benchmark 比較、stress、regime split、rolling stability、data availability、baseline、no-lookahead、execution simulation、assumption ledger、trial ledger、comparison、pack validation をまとめて確認できる。

## 標準 Engine と外部 OSS の関係

標準 engine:

- `strategy_authoring_native`

optional OSS:

- `vectorbt`: signal runner / external check
- `bt`: portfolio allocation / rebalance comparison
- `empyrical-reloaded`: metrics normalization
- `quantstats`: report / tear sheet

reference-only / 採用前 contract:

- `HftBacktest`: L2/L3/tick/latency/queue input readiness
- `qstrader`: local input contract
- `skfolio` / `Riskfolio-Lib`: portfolio validation / optimization reference
- `PyBroker`: local DataFrame input / point-in-time feature provenance

外部 OSS の結果は native result を上書きしない。別の測定器で検算するイメージで読む。

## 見るべき artifact

| Artifact | 意味 |
|---|---|
| `strategy_backtest_metrics.json` | native backtest の主要数値 |
| `strategy_backtest_suite_result.json` | 複数手法・複数 case の比較 |
| `strategy_backtest_framework_run.json` | optional OSS matrix の結果 |
| `strategy_backtest_benchmark_relative.json` | benchmark series との相対比較 |
| `strategy_backtest_no_lookahead_diff.json` | 未来データを見ていないかの検査 |
| `strategy_backtest_pack_validation.json` | pack integrity と no-live boundary の検査 |

`strategy-backtest-artifact-summary` はこれらの主要 field をまとめて stdout に出す。

## 誤解してはいけないこと

pack validation の `PASS` は、artifact が壊れていないことと no-live boundary を守っていることを示す。収益性、paper pass、live readiness の証明ではない。

この backtest は次を許可しない。

- live order
- wallet
- signing
- exchange write
- broker / exchange credential の使用
- backtest 結果だけによる alpha claim
- backtest 結果だけによる live readiness claim
- HFT / market impact 対応済みという主張

## 次に読む文書

- [BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](BACKTEST_CURRENT_TECHNICAL_REFERENCE.md)
- [BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md](BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md)
- [OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md](OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md)
- [BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md](BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md)
