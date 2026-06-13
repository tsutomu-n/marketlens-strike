<!--
作成日: 2026-05-31_17:20 JST
更新日: 2026-06-13_20:36 JST
-->

# Backtest Docs

この directory は、現行 repo の backtest surface をコード基準で分けて読む入口です。

## 結論

現行 repo には、用途が違う backtest surface が複数あります。

| Surface | Entry | Status | 用途 |
|---|---|---|---|
| Trade[XYZ] pure backtest v0.1 | `sis.backtest.engine.runner.run_backtest()` | 実装済み、CLI未公開 | Trade[XYZ] 単一銘柄 long-only の純粋BT |
| Strategy Authoring fixed-horizon backtest | `uv run sis strategy-author-run --through backtest` | 実装済み、baseline seedあり | YAML戦略のpaper-only研究評価 |
| Legacy backtest bridge | `uv run sis build-backtest` | 互換維持 | Strategy Lab / historical bridge系の簡易評価 |

現行 backtest の詳細、現在できること、専用 backtesting OSS / framework の候補整理は
[CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md](CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md)
を見ます。
`vectorbt` 以外も含めた OSS backtest framework の評価計画は
[OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md](OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md)
を見ます。
`vectorbt` を一時 smoke から optional extra 採用へ進める場合の計画は
[VECTORBT_ADOPTION_PLAN_2026-06-13.md](VECTORBT_ADOPTION_PLAN_2026-06-13.md)
を見ます。
正式 optional dependency としてどの OSS を先に採用するかの review は
[OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md](OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md)
を見ます。
`strategy-backtest-suite` は `strategy_backtest_suite.v1` YAML を読み、複数specと複数backtest条件を1コマンドで実行して suite result / report に集約します。標準例は `single_window`、`walk_forward:trading_day`、`purged_walk_forward:trading_day`、`purged_walk_forward:trading_day+return_bootstrap`、`purged_walk_forward:trading_day+block_bootstrap` の5手法を走らせ、suite result の `method_matrix` で手法別 run 数を確認できます。
`strategy-backtest-adapter-spike` は9件の外部 backtest / metrics / report OSS 候補の import / metadata / license risk を artifact 化します。依存追加、外部engine実行、live order は行いません。
`strategy-backtest-framework-smoke` は一時 `uv --with ...` 環境で `vectorbt`, `bt`, `quantstats`, `empyrical-reloaded` などの import 結果、version、license metadata、Requires-Python、採用分類を artifact 化します。repo dependency は追加しません。
`strategy-backtest-adapter-selection` は adapter spike と framework smoke の artifact から Phase C の初期選定を artifact 化します。現時点では `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` を selected、`backtesting.py`, `zipline-reloaded`, `backtrader`, `pyfolio-reloaded`, `qstrader` を deferred とします。repo dependency は追加しません。
`strategy-backtest-adapter-contract` は selected adapter の入力、出力、provenance、受入条件を artifact 化します。`vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` の contract を作りますが、repo dependency は追加しません。
`strategy-backtest-external-run` は外部 framework 候補の実行結果用 artifact を作ります。`vectorbt` がインストール済みで signals / quotes 入力がある場合は `src/sis/backtest/vectorbt_adapter.py` 経由で `vectorbt.Portfolio.from_signals` を呼び、未インストールなら `skipped/not_installed_in_current_env` として記録します。artifact には metrics / signals / quotes の source path と hash、`label_horizon_minutes`、framework ごとの `framework_version` と `runner_mode` を残します。依存追加や live order は行いません。
`strategy-backtest-portfolio-compare` は `bt` 用の portfolio allocation / rebalance comparison artifact を作ります。通常環境で `bt` が未インストールなら `skipped/not_installed_in_current_env`、一時 `uv --with bt` 環境では `bt.run()` の結果を `strategy_backtest_portfolio_comparison.v1` に記録します。依存追加や live order は行いません。
`strategy-backtest-metric-extension` は `empyrical-reloaded` 用の metrics normalization artifact を作ります。通常環境で `empyrical` が未インストールなら `skipped/not_installed_in_current_env`、一時 `uv --with empyrical-reloaded` 環境では `empyrical` の Sharpe / drawdown / annual return / annual volatility 系 metric を `strategy_backtest_metric_extension.v1` に記録します。依存追加や live order は行いません。
`strategy-backtest-report-extension` は `quantstats` 用の report / tear sheet artifact を作ります。通常環境で `quantstats` が未インストールなら `skipped/not_installed_in_current_env`、一時 `uv --with quantstats` 環境では `quantstats.reports.html` と `quantstats.reports.metrics` を呼び、`strategy_backtest_report_extension.v1` と HTML report path/hash を記録します。依存追加や live order は行いません。
`strategy-backtest-stress` は既存 `strategy_backtest_metrics.json` の executed signal return に追加 cost / slippage bps を掛け、`strategy_backtest_stress.v1` に scenario 別の耐性結果を記録します。既定 scenario は `base`, `mild`, `moderate`, `severe` です。依存追加や live order は行いません。
`strategy-backtest-regime-split` は既存 `strategy_backtest_metrics.json` の executed signal return を `side`, `timeframe`, `exit_reason`, `ts_weekday`, `ts_hour` などの dimension 別に集計し、弱い bucket を確認できる `strategy_backtest_regime_split.v1` を作ります。依存追加や live order は行いません。
`strategy-backtest-rolling-stability` は既存 `strategy_backtest_metrics.json` の executed signal return を rolling window 別に集計し、窓幅ごとの worst return / drawdown を確認できる `strategy_backtest_rolling_stability.v1` を作ります。既定 window は `3,5` です。依存追加や live order は行いません。
`strategy-backtest-benchmark-relative` は既存 `strategy_backtest_metrics.json` の executed signal return を row-level benchmark return または quote frame 由来の benchmark return と比較し、active return / tracking error / information ratio を確認できる `strategy_backtest_benchmark_relative.v1` を作ります。依存追加や live order は行いません。
`strategy-backtest-compare` は `strategy_backtest_metrics.json` から overall / walk-forward era / optimizer sweep を `method_results` に正規化し、既定の suite result があれば `suite_results`、既定の adapter spike があれば `adapter_spike`、既定の external result があれば `external_results`、既定の portfolio comparison があれば `portfolio_comparison`、既定の metric extension があれば `metric_extension`、既定の report extension があれば `report_extension`、既定の stress result があれば `stress`、既定の regime split result があれば `regime_split`、既定の rolling stability result があれば `rolling_stability`、既定の benchmark relative result があれば `benchmark_relative` として取り込みます。`comparison_diagnostics` では threshold failure、weakest era、suite best run も確認できます。
`strategy-backtest-pack` は単発 Strategy Authoring backtest、5手法 suite、bundle result、adapter spike、external result、portfolio comparison、metric extension、report extension、cost / slippage stress、regime split、rolling stability、benchmark relative、comparison、pack manifest を一括生成します。pack manifest は `external_framework_policy` で、標準 engine を `strategy_authoring_native`、完成線を `complete_without_locked_external_dependency` として固定します。
`strategy-backtest-pack-validate` は pack manifest の artifact path / hash、5手法、paper-only / no-live boundary、外部 framework 方針を検査し、PASS / FAIL artifact を出します。

バックテストへ最短で入る入口は Strategy Authoring baseline です。
Trade[XYZ] を当面の注文口にせず、バックテスト優先へ切り替える計画は
[BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md](BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md)
を見ます。

## Backtest-First Baseline

外部 API や Trade[XYZ] 30日 quote coverage を待たず、まずこの local fixture で Strategy Authoring backtest を通します。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
uv run sis strategy-backtest-suite --suite docs/strategy_research_lab/examples/backtest_suite.yaml
uv run sis strategy-backtest-adapter-spike
uv run sis strategy-backtest-framework-smoke
uv run sis strategy-backtest-adapter-selection
uv run sis strategy-backtest-adapter-contract
uv run sis strategy-backtest-external-run
uv run sis strategy-backtest-portfolio-compare
uv run sis strategy-backtest-metric-extension
uv run sis strategy-backtest-report-extension
uv run sis strategy-backtest-stress
uv run sis strategy-backtest-regime-split
uv run sis strategy-backtest-rolling-stability
uv run sis strategy-backtest-benchmark-relative
uv run sis strategy-backtest-compare
uv run sis strategy-backtest-pack
uv run sis strategy-backtest-pack-validate
```

Tier 1 / report 候補を repo dependency に入れず一時 import smoke する場合:

```bash
uv run --with vectorbt --with bt --with quantstats --with empyrical-reloaded sis strategy-backtest-framework-smoke
```

`vectorbt` を repo dependency に入れず一時環境で external-run smoke する場合:

```bash
uv run --with vectorbt sis strategy-backtest-external-run
uv run sis strategy-backtest-compare
```

`bt` を repo dependency に入れず一時環境で portfolio comparison smoke する場合:

```bash
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
uv run --with bt sis strategy-backtest-portfolio-compare
uv run sis strategy-backtest-compare
```

`empyrical-reloaded` を repo dependency に入れず一時環境で metric extension smoke する場合:

```bash
uv run --with empyrical-reloaded sis strategy-backtest-metric-extension
uv run sis strategy-backtest-compare
```

`quantstats` を repo dependency に入れず一時環境で report extension smoke する場合:

```bash
uv run --with quantstats sis strategy-backtest-report-extension
uv run sis strategy-backtest-compare
```

この一時 smoke では `pyproject.toml` / `uv.lock` を変更しません。

主な出力:

- `data/research/strategy_authoring_baseline_feature_panel.parquet`
- `data/research/strategy_authoring_baseline_quotes.parquet`
- `data/research/strategy_authoring_baseline_venue_cost_matrix.csv`
- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/research/backtest_compare/strategy_backtest_comparison.json`
- `data/research/backtest_suite/strategy_backtest_suite_result.json`
- `data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json`
- `data/research/backtest_framework_smoke/strategy_backtest_framework_smoke.json`
- `data/research/backtest_adapter_selection/strategy_backtest_adapter_selection.json`
- `data/research/backtest_adapter_contract/strategy_backtest_adapter_contract.json`
- `data/research/backtest_external/strategy_backtest_external_result.json`
- `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json`
- `data/research/backtest_metric_extension/strategy_backtest_metric_extension.json`
- `data/research/backtest_metric_extension/strategy_backtest_returns.jsonl`
- `data/research/backtest_report_extension/strategy_backtest_report_extension.json`
- `data/research/backtest_report_extension/strategy_backtest_report_returns.jsonl`
- `data/research/backtest_report_extension/strategy_backtest_quantstats_report.html`
- `data/research/backtest_stress/strategy_backtest_stress.json`
- `data/research/backtest_regime_split/strategy_backtest_regime_split.json`
- `data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json`
- `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json`
- `data/research/backtest_pack/strategy_backtest_pack.json`
- `data/research/backtest_pack/strategy_backtest_pack_validation.json`
- `data/reports/strategy_backtest_report.md`
- `data/reports/strategy_backtest_acceptance_report.md`
- `data/reports/strategy_backtest_comparison_report.md`
- `data/reports/strategy_backtest_suite_report.md`
- `data/reports/strategy_backtest_adapter_spike_report.md`
- `data/reports/strategy_backtest_framework_smoke_report.md`
- `data/reports/strategy_backtest_adapter_selection_report.md`
- `data/reports/strategy_backtest_adapter_contract_report.md`
- `data/reports/strategy_backtest_external_report.md`
- `data/reports/strategy_backtest_portfolio_comparison_report.md`
- `data/reports/strategy_backtest_metric_extension_report.md`
- `data/reports/strategy_backtest_report_extension_report.md`
- `data/reports/strategy_backtest_stress_report.md`
- `data/reports/strategy_backtest_regime_split_report.md`
- `data/reports/strategy_backtest_rolling_stability_report.md`
- `data/reports/strategy_backtest_benchmark_relative_report.md`
- `data/reports/strategy_backtest_pack_report.md`
- `data/reports/strategy_backtest_pack_validation_report.md`

これは Strategy Authoring の paper-only 研究評価です。`strategy-backtest-acceptance` は backtest artifact の pass/fail/boundary 判定を固定しますが、Trade[XYZ] `backtest_data_ready=true`、Bitget 接続、demo order submit、live readiness の証明ではありません。

## Trade[XYZ] Pure Backtest v0.1

正本コード:

- `src/sis/backtest/engine/`
- `src/sis/backtest/trade_xyz/`
- `tests/backtest/`

現在できること:

- Trade[XYZ]専用
- single-symbol
- long-only
- market-like taker fill
- next-row fill
- fixed notional sizing
- fee / slippage / nullable funding v0
- entry gate / exit gate
- data quality report
- metrics / report / artifact出力

現在できないこと:

- public CLI
- live order
- wallet / signing / exchange write
- short
- multi-symbol portfolio
- limit / stop / partial fill
- L2 order book replay
- MT5 / IC Markets / CFD

## Boundary

`uv run sis build-backtest` は既存 bridge 系の command です。Trade[XYZ] pure backtest v0.1 の入口ではありません。

`strategy-author-run --through backtest` は Strategy Authoring の fixed-horizon paper-only 評価です。Trade[XYZ] pure backtest v0.1 の会計・約定・artifact契約とは別物です。

## Verification

current verification は固定の pass count ではなく、作業時点で次を再実行して確認する:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run pytest -q tests/backtest
uv run python scripts/check_current_docs.py
```
