<!--
作成日: 2026-06-15_19:09 JST
更新日: 2026-06-15_19:09 JST
-->

# Backtest User Guide And Current Capabilities

## 結論

この repo の backtest system は、local data と Strategy Authoring spec から paper-only の研究用 backtest pack を作り、複数手法、外部 benchmark 比較、stress、regime split、rolling stability、data availability、baseline、no-lookahead、execution simulation、assumption ledger、trial ledger をまとめて確認できる状態です。

現在できることは、戦略候補を local fixture / local artifact で検証し、`PASS_BACKTEST_ACCEPTANCE` まで進め、paper observation 継続判断へ渡すことです。

現在できないことは、backtest だけで alpha、paper pass、live readiness、market impact、wallet / signing / exchange write の許可を主張することです。現行 artifact 上の Strategy Lifecycle は `CONTINUE_PAPER_OBSERVATION` であり、live へ進む状態ではありません。

## 誰向けか

この文書は、コードを読まずに backtest system を使いたい人向けです。

- まず何を実行すればよいか知りたい。
- 出力 artifact の意味を知りたい。
- `PASS` と出た時に、何が許可されたのかを誤読したくない。
- paper observation や live readiness との境界を確認したい。

実装者向けの詳細や責務分離は、`docs/backtest/README.md` から個別 plan / design docs を見ます。

## まず使う最短手順

標準の backtest pack を作り、検査し、主要 field を表示する最短手順です。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

この手順は local fixture と local CSV を使います。外部 API fetch、live order、wallet、signing、exchange write は行いません。

## 現在の代表的な状態

2026-06-15_19:09 JST 時点で、現在の artifact summary は次の状態です。

| 項目 | 現在値 | 意味 |
|---|---:|---|
| pack path | `data/research/backtest_pack/strategy_backtest_pack.json` | 標準 pack artifact |
| pack schema | `strategy_backtest_pack.v1` | 現行 pack schema |
| pack validation | `PASS` | pack integrity と no-live 境界の検査に通過 |
| validation checks | `198` checks / `0` failed | pack validation の確認数 |
| suite methods | `5` | 標準 backtest suite の手法数 |
| suite runs | `5` | 標準 suite の run 数 |
| standard engine | `strategy_authoring_native` | 標準 backtest engine |
| completion line | `complete_without_locked_external_dependency` | 外部 framework 必須なしで完成扱い |
| paper only | `true` | paper-only artifact |
| permits live order | `false` | live order は許可しない |
| wallet / exchange write | `false` / `false` | wallet / exchange write は使わない |
| backtest acceptance | `PASS_BACKTEST_ACCEPTANCE` | Strategy Lifecycle 用の backtest acceptance は通過 |
| lifecycle decision | `CONTINUE_PAPER_OBSERVATION` | 次は paper observation 継続 |

## 何ができるか

### 1. Strategy Authoring spec を検証して backtest する

YAML spec を validation し、signal 生成から backtest まで進められます。

```bash
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

主な出力:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/reports/strategy_backtest_report.md`

### 2. Backtest acceptance を出す

Strategy Lifecycle に渡せる backtest acceptance decision を作れます。

```bash
uv run sis strategy-backtest-acceptance \
  --metrics-path data/research/strategy_backtest_metrics.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

主な出力:

- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/reports/strategy_backtest_acceptance_report.md`

現在の artifact では `decision=PASS_BACKTEST_ACCEPTANCE` です。ただし、これは paper pass や live readiness ではありません。

### 3. 複数手法の backtest suite を回す

標準例では次の 5 手法を 1 command で回せます。

- `single_window`
- `walk_forward:trading_day`
- `purged_walk_forward:trading_day`
- `purged_walk_forward:trading_day+return_bootstrap`
- `purged_walk_forward:trading_day+block_bootstrap`

```bash
uv run sis strategy-backtest-suite --suite docs/strategy_research_lab/examples/backtest_suite.yaml
```

主な出力:

- `data/research/backtest_suite/strategy_backtest_suite_result.json`
- `data/reports/strategy_backtest_suite_report.md`

### 4. 外部 benchmark と比較する

local CSV の benchmark return series と strategy return を比較できます。

```bash
uv run sis strategy-backtest-benchmark-relative \
  --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
```

現在の代表値:

- strategy total return: `0.0046531202609065075`
- benchmark total return: `0.004920882894421784`
- active total return: `-0.00026776263351527654`
- information ratio: `-0.08156554737966769`

これは過去 artifact の診断値であり、将来収益の主張ではありません。

### 5. Robustness と弱点を見る

backtest 結果に対して、追加 cost / slippage stress、regime split、rolling stability を確認できます。

```bash
uv run sis strategy-backtest-stress
uv run sis strategy-backtest-regime-split
uv run sis strategy-backtest-rolling-stability
```

現在の代表値:

- worst stress scenario: `severe`
- worst stressed total return: `-0.012846879739093493`
- weakest regime dimension: `ts_hour`
- worst rolling window size: `3`

これらは「弱点を見つけるための診断」です。market impact proof ではありません。

### 6. Data availability を確認する

local source の hash、row count、timestamp range、gap / duplicate count と、将来候補の provider 行を確認できます。

```bash
uv run sis strategy-backtest-data-availability
```

現在の代表値:

- status: `pass`
- total gap count: `0`
- future candidate count: `3`
- external API called: `false`
- network used: `false`
- schema widening required: `false`

Bitget direct、Hyperliquid direct、Coinalyze は future candidate のままです。現行 backtest system はこれらの collector や direct schema widening を実装しません。

### 7. Baseline と比較する

cash / no-trade と、実行済み return series 由来の simple momentum / simple mean reversion / random throttle control を比較できます。

```bash
uv run sis strategy-backtest-baseline-compare
```

注意: ここでの simple momentum などは return-series control です。別 engine で再実行した独立 baseline ではありません。

### 8. No-lookahead と execution simulation を確認する

未来側 feature rows を変異させて cutoff 以前の結果が変わらないか、paper-only の order intent / fill event simulation がどうなるかを artifact 化できます。

```bash
uv run sis strategy-backtest-no-lookahead-diff
uv run sis strategy-backtest-execution-sim
```

現在の代表値:

- no-lookahead status: `pass`
- execution simulation status: `pass`
- unknown critical assumptions: `0`

execution simulation は live execution ではありません。rate limit、cancel/modify、unknown order state、market impact などは仮定として記録します。

### 9. Assumption ledger と trial ledger を残す

仮定と試行履歴を artifact として残せます。

```bash
uv run sis strategy-backtest-assumption-ledger
uv run sis strategy-backtest-trial-ledger
```

目的:

- 成功結果だけを残す reporting を避ける。
- measured / configured / assumed / unknown を分ける。
- 何を試し、何が available / missing だったかを追跡する。

### 10. まとめ pack を作る

個別 command をまとめ、標準 artifact chain を一括生成します。

```bash
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

主な出力:

- `data/research/backtest_pack/strategy_backtest_pack.json`
- `data/research/backtest_pack/strategy_backtest_pack_validation.json`
- `data/reports/strategy_backtest_pack_report.md`
- `data/reports/strategy_backtest_pack_validation_report.md`

`strategy-backtest-artifact-summary` は artifact を生成せず、既存 artifact の主要 field を JSON で表示します。欠損 artifact は `exists=false` として表示します。

## Optional extras でできること

標準完成線は native primary です。外部 framework は必須ではありません。

lockfile 上の optional extras:

| Extra | Package | 用途 |
|---|---|---|
| `vectorbt` | `vectorbt==1.0.0` | vectorbt runner / framework run |
| `bt` | `bt==1.2.0` | portfolio allocation comparison |
| `metrics` | `empyrical-reloaded==0.5.12` | metrics extension |
| `reports` | `quantstats==0.0.81` | HTML report / tear sheet |

例:

```bash
uv sync --dev --extra bt --extra metrics --extra reports --locked
uv run --extra bt --extra metrics --extra reports sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run --extra bt --extra metrics --extra reports sis strategy-backtest-pack-validate
uv run --extra bt --extra metrics --extra reports sis strategy-backtest-artifact-summary
```

pack manifest の hash と実ファイルをずらさないため、optional extra の artifact を使う場合は pack 自体を extras 環境で再実行します。

## Paper observation との関係

backtest system は paper observation の前段です。

現在の artifact chain は次の状態です。

```text
PASS_BACKTEST_ACCEPTANCE
-> promote / promote_to_paper_observation
-> NEEDS_MORE_PAPER_OBSERVATION
-> CONTINUE_PAPER_OBSERVATION
```

つまり、現時点の次 action は live ではなく paper observation 継続です。

関連 command:

```bash
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision promote
uv run sis strategy-paper-observation-cycle --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
uv run sis strategy-lifecycle-review --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
```

`strategy-paper-observation-cycle --smoke` は local verification 用です。production paper pass evidence ではありません。

## できないこと

この backtest system は次をしません。

- live order を出す。
- wallet、signing、exchange write を使う。
- backtest 結果だけで alpha を主張する。
- backtest 結果だけで paper pass を主張する。
- backtest 結果だけで live readiness を主張する。
- replay-style simulation から market impact を主張する。
- Bitget / Hyperliquid direct schema widening を行う。
- Coinalyze collector を作る。
- NautilusTrader / HftBacktest / Tardis / PyBroker / Qlib / FinRL / skfolio を採用する。

## 出力の読み方

| Field | 読み方 |
|---|---|
| `pack_validation.decision=PASS` | pack artifact の整合性と no-live boundary に通った |
| `failed_count=0` | validation finding の失敗がない |
| `paper_only=true` | research / paper-only artifact である |
| `permits_live_order=false` | live order は許可しない |
| `wallet_used=false` | wallet は使っていない |
| `exchange_write_used=false` | exchange write は使っていない |
| `PASS_BACKTEST_ACCEPTANCE` | lifecycle に渡せる backtest acceptance は通った |
| `CONTINUE_PAPER_OBSERVATION` | paper observation を続ける状態 |
| `ELIGIBLE_FOR_LIVE_CANARY_PLAN` | live order 許可ではなく、別計画を書いてよい候補 |

## よく使う確認 command

```bash
uv run sis strategy-backtest-artifact-summary
jq '.decision, .summary.failed_count' data/research/backtest_pack/strategy_backtest_pack_validation.json
jq '.decision, .summary_checks, .boundary_flags' data/research/strategy_lifecycle/backtest_acceptance_decision.json
jq '.decision, .decision_reasons, .next_actions' data/research/strategy_lifecycle/strategy_lifecycle_review.json
```

docs / metadata / links を確認する場合:

```bash
uv run python scripts/check_current_docs.py
```

repo 全体の通常 gate:

```bash
./scripts/check
```

## 読む順番

1. この文書
2. `docs/backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md`
3. `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md`
4. `docs/strategy_lifecycle/README.md`
5. `docs/backtest/BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md`

## まとめ

現行 backtest system は、戦略候補を local data で検証し、pack と validation artifact を残し、Strategy Lifecycle へ渡すところまで実用できます。

実務上の使い方は、まず `strategy-backtest-pack`、`strategy-backtest-pack-validate`、`strategy-backtest-artifact-summary` で pack を確認し、その後 `strategy-backtest-acceptance` と paper observation route に進めることです。

ただし、backtest は live 許可装置ではありません。現在の次 action は paper observation 継続です。
