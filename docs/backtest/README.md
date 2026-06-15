<!--
作成日: 2026-05-31_17:20 JST
更新日: 2026-06-15_20:13 JST
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
ユーザー向けに、backtest system で今できること、最短手順、出力の読み方、paper observation / live boundary をまとめた文書は
[BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md](BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md)
を見ます。
高校生にも分かるように専門語を減らした別版は
[BACKTEST_HIGH_SCHOOL_GUIDE_2026-06-15.md](BACKTEST_HIGH_SCHOOL_GUIDE_2026-06-15.md)
を見ます。
プレースホルダーデータで、backtest 実行後にどのような端末出力、JSON、Markdown report が見えるかのサンプルは
[BACKTEST_PLACEHOLDER_OUTPUT_SAMPLE_2026-06-15.md](BACKTEST_PLACEHOLDER_OUTPUT_SAMPLE_2026-06-15.md)
を見ます。
現在の backtest 方針、外部 framework の責務分担、PyBroker / NautilusTrader / LEAN / Freqtrade まで含めた現実的な採用位置は
[CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md](CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md)
を見ます。
現在の completion scope では実装しないが将来候補として残す Bitget / Hyperliquid schema widening、Coinalyze collector、live / wallet / signing、NautilusTrader / HftBacktest / Tardis / PyBroker / Qlib / FinRL / skfolio 採用、market impact / alpha / live readiness claim の扱いは
[BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md](BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md)
を見ます。
OSS を使って backtest capability を現実的に増やすための最終実装計画は
[OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md](OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md)
を見ます。既存 optional extras の実行レーン強化、lookahead 検査強化、HftBacktest / qstrader / skfolio の dependency 追加前 contract を、目的・制約・対象ファイル・テスト方針・完了条件つきで定義しています。
backtest system completion の目的、制約、対象ファイル、テスト方針、完了条件は
[BACKTEST_SYSTEM_COMPLETION_PLAN_2026-06-14.md](BACKTEST_SYSTEM_COMPLETION_PLAN_2026-06-14.md)
を見ます。
backtest system completion 後に、機能追加ではなく責務分離で保守性とカスタマイズ性を上げる実装計画は
[BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md](BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md)
を見ます。責務分離後のコード入口は `src/sis/backtest/artifact_io.py`, `src/sis/backtest/boundary.py`, `src/sis/backtest/reporting.py`, `src/sis/backtest/pack_contract.py`, `src/sis/backtest/pack_runner.py`, `src/sis/backtest/pack_validation.py`, `src/sis/backtest/artifact_summary_registry.py` です。
完成済み backtest pack を既存 Strategy Lifecycle / paper observation route にどう接続するかの現実的な計画は
[BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md](BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md)
を見ます。これは新しい paper observation gate を作る計画ではなく、既存 CLI / schema / artifact に足りるかを先に確認する bridge audit 計画です。BP0 の追加調査結果と evidence map は
[BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md](BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md)
を見ます。
`vectorbt` 以外も含めた OSS backtest framework の評価計画は
[OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md](OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md)
を見ます。
`vectorbt` を一時 smoke から optional extra 採用へ進める場合の計画は
[VECTORBT_ADOPTION_PLAN_2026-06-13.md](VECTORBT_ADOPTION_PLAN_2026-06-13.md)
を見ます。
`vectorbt` の license 採用判断は
[VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md](VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md)
を見ます。2026-06-14_11:00 JST に owner 承認済みとして、`vectorbt==1.0.0` を optional extra / lockfile に正式採用済みです。
正式 optional dependency としてどの OSS を先に採用するかの review は
[OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md](OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md)
を見ます。
`empyrical-reloaded` / `quantstats` の optional extra 採用判断は
[METRICS_REPORT_OPTIONAL_EXTRAS_DECISION_2026-06-13.md](METRICS_REPORT_OPTIONAL_EXTRAS_DECISION_2026-06-13.md)
を見ます。現時点では `vectorbt = ["vectorbt==1.0.0"]`, `metrics = ["empyrical-reloaded==0.5.12"]`, `reports = ["quantstats==0.0.81"]` を分けて採用済みです。
external benchmark series を明示して標準 pack を実行する operator 手順は
[OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md](OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md)
を見ます。
`strategy-backtest-suite` は `strategy_backtest_suite.v1` YAML を読み、複数specと複数backtest条件を1コマンドで実行して suite result / report に集約します。標準例は `single_window`、`walk_forward:trading_day`、`purged_walk_forward:trading_day`、`purged_walk_forward:trading_day+return_bootstrap`、`purged_walk_forward:trading_day+block_bootstrap` の5手法を走らせ、suite result の `method_matrix` で手法別 run 数を確認できます。
`strategy-backtest-adapter-spike` は9件の外部 backtest / metrics / report OSS 候補の import / metadata / license risk を artifact 化します。依存追加、外部engine実行、live order は行いません。
`strategy-backtest-framework-smoke` は一時 `uv --with ...` 環境で `vectorbt`, `bt`, `quantstats`, `empyrical-reloaded` などの import 結果、version、license metadata、Requires-Python、採用分類を artifact 化します。この command 自体は repo dependency を変更しません。
`strategy-backtest-adapter-selection` は adapter spike と framework smoke の artifact から Phase C の初期選定を artifact 化します。通常は `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` を selected、`backtesting.py`, `zipline-reloaded`, `backtrader`, `pyfolio-reloaded`, `qstrader` を deferred とします。明示 smoke で `qstrader` が imported、fatal blocker なし、MIT license signal ありの場合だけ、`qstrader` を selected `separate_runner_research` として local-input isolated runner contract 候補に昇格します。この command 自体は repo dependency を変更しません。
`strategy-backtest-adapter-contract` は selected adapter の入力、出力、provenance、受入条件を artifact 化します。`vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` の contract を作りますが、この command 自体は repo dependency を変更しません。
`strategy-backtest-external-run` は外部 framework 候補の実行結果用 artifact を作ります。`vectorbt` がインストール済みで signals / quotes 入力がある場合は `src/sis/backtest/vectorbt_adapter.py` 経由で `vectorbt.Portfolio.from_signals` を呼び、未インストールなら `skipped/not_installed_in_current_env` として記録します。artifact には metrics / signals / quotes の source path と hash、`label_horizon_minutes`、framework ごとの `framework_version` と `runner_mode` を残します。依存追加や live order は行いません。
`strategy-backtest-portfolio-compare` は `bt` 用の portfolio allocation / rebalance comparison artifact を作ります。通常環境で `bt` が未インストールなら `skipped/not_installed_in_current_env`、`uv run --extra bt` 環境では `bt.run()` の結果を `strategy_backtest_portfolio_comparison.v1` に記録します。live order は行いません。
`strategy-backtest-metric-extension` は `empyrical-reloaded` 用の metrics normalization artifact を作ります。通常環境で `empyrical` が未インストールなら `skipped/not_installed_in_current_env`、一時 `uv --with empyrical-reloaded` 環境では `empyrical` の Sharpe / drawdown / annual return / annual volatility 系 metric を `strategy_backtest_metric_extension.v1` に記録します。依存追加や live order は行いません。
`strategy-backtest-report-extension` は `quantstats` 用の report / tear sheet artifact を作ります。通常環境で `quantstats` が未インストールなら `skipped/not_installed_in_current_env`、一時 `uv --with quantstats` 環境では `quantstats.reports.html` と `quantstats.reports.metrics` を呼び、`strategy_backtest_report_extension.v1` と HTML report path/hash、`framework_warning_count`、`framework_warnings` を記録します。既定では optional framework warning を捕捉して表示を抑え、表示したい場合は `--show-framework-warnings` を使います。依存追加や live order は行いません。
`strategy-backtest-stress` は既存 `strategy_backtest_metrics.json` の executed signal return に追加 cost / slippage bps を掛け、`strategy_backtest_stress.v1` に scenario 別の耐性結果を記録します。既定 scenario は `base`, `mild`, `moderate`, `severe` です。依存追加や live order は行いません。
`strategy-backtest-regime-split` は既存 `strategy_backtest_metrics.json` の executed signal return を `side`, `timeframe`, `exit_reason`, `ts_weekday`, `ts_hour` などの dimension 別に集計し、弱い bucket を確認できる `strategy_backtest_regime_split.v1` を作ります。依存追加や live order は行いません。
`strategy-backtest-rolling-stability` は既存 `strategy_backtest_metrics.json` の executed signal return を rolling window 別に集計し、窓幅ごとの worst return / drawdown を確認できる `strategy_backtest_rolling_stability.v1` を作ります。既定 window は `3,5` です。依存追加や live order は行いません。
`strategy-backtest-benchmark-relative` は既存 `strategy_backtest_metrics.json` の executed signal return を row-level benchmark return、明示 external benchmark series、または quote frame 由来の benchmark return と比較し、active return / tracking error / information ratio を確認できる `strategy_backtest_benchmark_relative.v1` を作ります。コピー用 CSV は [external_benchmark_series.csv](../strategy_research_lab/examples/external_benchmark_series.csv) です。依存追加や live order は行いません。
`strategy-backtest-data-availability` は metrics / signals / quotes の local source hash、parquet row count、timestamp range、symbol/venue group 単位の gap / duplicate count と、Bitget / Hyperliquid / Coinalyze future candidate 行を `backtest_data_availability_ledger.v1` に残します。外部 API は呼びません。
`strategy-backtest-baseline-compare` は cash/no-trade と、実行済み return series 由来の simple momentum / simple mean reversion / random throttle control を `strategy_backtest_baseline_comparison.v1` に残します。単純 leverage は戦略リターン由来の diagnostic stress であり、strongest / weakness 判定には含めません。これらの return-series control は、別 engine で再実行した独立 baseline ではありません。
`strategy-backtest-no-lookahead-diff` は spec が渡された場合、未来側 feature rows を一時 parquet で変異させて Strategy Authoring を再実行し、cutoff 以前の signals / executed backtest rows が変わらないことを `strategy_backtest_no_lookahead_diff.v1` に残します。4 timestamp 未満の小さい入力では runtime replay は not applicable として記録します。
`strategy-backtest-execution-sim` は既存 Strategy Authoring metrics から paper-only order intents / fill events を作り、fill status の根拠と rate-limit / cancel-modify / unknown order state / market impact の未モデル仮定を `strategy_backtest_execution_simulation.v1` に残します。
`strategy-backtest-assumption-ledger` は data availability、baseline、no-lookahead、execution simulation の仮定レベルを `measured`, `configured`, `assumed`, `unknown` に分けて `strategy_backtest_assumption_ledger.v1` に残します。
`strategy-backtest-trial-ledger` は試した artifact と missing / available 状態を `strategy_backtest_trial_ledger.v1` に残します。成功結果だけを report に残す運用を避けるための台帳です。
`strategy-backtest-compare` は `strategy_backtest_metrics.json` から overall / walk-forward era / optimizer sweep を `method_results` に正規化し、既定の suite result があれば `suite_results`、既定の adapter spike があれば `adapter_spike`、既定の external result があれば `external_results`、既定の portfolio comparison があれば `portfolio_comparison`、既定の metric extension があれば `metric_extension`、既定の report extension があれば `report_extension`、既定の stress result があれば `stress`、既定の regime split result があれば `regime_split`、既定の rolling stability result があれば `rolling_stability`、既定の benchmark relative result があれば `benchmark_relative`、completion artifact があれば `data_availability` / `baseline_comparison` / `trial_ledger` / `assumption_ledger` / `no_lookahead_diff` / `execution_simulation` として取り込みます。`comparison_diagnostics` では threshold failure、weakest era、suite best run も確認できます。
`strategy-backtest-pack` は単発 Strategy Authoring backtest、5手法 suite、bundle result、adapter spike、external result、portfolio comparison、metric extension、report extension、cost / slippage stress、regime split、rolling stability、benchmark relative、data availability、baseline comparison、no-lookahead diff、execution simulation、assumption ledger、trial ledger、comparison、pack manifest を一括生成します。`--benchmark-series-path` を渡すと pack 内の benchmark relative でも明示 external benchmark series を使います。pack manifest は `external_framework_policy` で、標準 engine を `strategy_authoring_native`、完成線を `complete_without_locked_external_dependency` として固定します。
`strategy-backtest-pack-validate` は pack manifest の artifact path / hash、5手法、paper-only / no-live boundary、外部 framework 方針、completion artifact の存在を検査し、PASS / FAIL artifact を出します。
`strategy-backtest-artifact-summary` は pack、pack validation、benchmark relative、metric extension、report extension、stress、regime split、rolling stability、data availability、baseline comparison、trial ledger、assumption ledger、no-lookahead diff、execution simulation、comparison diagnostics の主要 field を読み、JSON で stdout に出します。artifact を生成せず、欠損 artifact は `exists=false` として表示します。

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
uv run sis strategy-backtest-data-availability
uv run sis strategy-backtest-baseline-compare
uv run sis strategy-backtest-no-lookahead-diff
uv run sis strategy-backtest-execution-sim
uv run sis strategy-backtest-assumption-ledger
uv run sis strategy-backtest-trial-ledger
uv run sis strategy-backtest-compare
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

外部 benchmark series 付きの最短 pack 手順と確認 field は
[OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md](OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md)
にまとめています。

Tier 1 / report 候補を repo dependency に入れず一時 import smoke する場合:

```bash
uv run --with vectorbt --with bt --with quantstats --with empyrical-reloaded sis strategy-backtest-framework-smoke
```

`vectorbt` を repo dependency に入れず一時環境で external-run smoke する場合:

```bash
uv run --with vectorbt sis strategy-backtest-external-run
uv run sis strategy-backtest-compare
```

`bt` optional extra で portfolio comparison smoke する場合:

```bash
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
uv run --extra bt sis strategy-backtest-portfolio-compare
uv run sis strategy-backtest-compare
```

`empyrical-reloaded` を repo dependency に入れず一時環境で metric extension smoke する場合:

```bash
uv run --with empyrical-reloaded sis strategy-backtest-metric-extension
uv run sis strategy-backtest-compare
```

`metrics` optional extra で metric extension を実行する場合:

```bash
uv sync --dev --extra metrics --locked
uv run --extra metrics sis strategy-backtest-metric-extension
uv run sis strategy-backtest-compare
```

`quantstats` を repo dependency に入れず一時環境で report extension smoke する場合:

```bash
uv run --with quantstats sis strategy-backtest-report-extension
uv run sis strategy-backtest-compare
```

`reports` optional extra で report extension を実行する場合:

```bash
uv sync --dev --extra reports --locked
uv run --extra reports sis strategy-backtest-report-extension
uv run sis strategy-backtest-compare
```

pack manifest の artifact hash と optional extra で生成した artifact を揃える場合は、個別 extension を後から上書きせず、pack 自体を extras 環境で再実行します。

```bash
uv sync --dev --extra bt --extra metrics --extra reports --locked
uv run --extra bt --extra metrics --extra reports sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run --extra bt --extra metrics --extra reports sis strategy-backtest-pack-validate
uv run --extra bt --extra metrics --extra reports sis strategy-backtest-artifact-summary
```

一時 `uv --with ...` smoke では `pyproject.toml` / `uv.lock` を変更しません。`--extra metrics` / `--extra reports` は locked optional extra を使う経路です。

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
- `data/research/backtest_data_availability/backtest_data_availability_ledger.json`
- `data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json`
- `data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json`
- `data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json`
- `data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json`
- `data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json`
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
- `data/reports/backtest_data_availability_report.md`
- `data/reports/strategy_backtest_baseline_comparison_report.md`
- `data/reports/strategy_backtest_no_lookahead_diff_report.md`
- `data/reports/strategy_backtest_execution_simulation_report.md`
- `data/reports/strategy_backtest_assumption_ledger_report.md`
- `data/reports/strategy_backtest_trial_ledger_report.md`
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
