<!--
作成日: 2026-06-13_09:53 JST
更新日: 2026-06-13_20:23 JST
-->

# Current Backtest Detail And Framework Options

## 結論

現行 repo の backtest は、専用 OSS backtesting framework を依存として使っていない。中核は repo 内の自前実装で、`polars`, `pydantic`, `pyarrow`, `duckdb`, `typer` などの Python data / CLI stack の上に作られている。

いま実務で使う主入口は `Strategy Authoring fixed-horizon backtest` である。YAML で戦略を記述し、`strategy-author-run --through backtest` で signal 生成から paper-only backtest metrics まで出す。これは live readiness ではなく、研究用の backtest artifact である。

今後「様々な手法で backtest する」機能を広げる場合、最初に外部 OSS を中核へ入れるのではなく、現行の artifact / safety boundary を維持したまま、adapter として比較導入するのが安全である。候補は `vectorbt`, `bt`, `backtesting.py`, `zipline-reloaded`, `backtrader`, `quantstats`, `empyrical-reloaded`, `pyfolio-reloaded`, `qstrader` だが、現時点で正式採用している外部 framework はない。`vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` は一時 `uv --with ...` で実行確認済みだが、依存追加前に Python 3.13 / uv lock / license / artifact contract の review が必要である。

## 現行 Backtest Surface

| Surface | Entry | 実装状態 | 主な用途 | 現在の制約 |
|---|---|---:|---|---|
| Strategy Authoring fixed-horizon backtest | `uv run sis strategy-author-run --spec <spec> --through backtest` | 実装済み / public CLI | YAML 戦略の paper-only 研究評価 | live order なし、wallet なし、固定 horizon が主軸 |
| Strategy Backtest Acceptance | `uv run sis strategy-backtest-acceptance` | 実装済み / public CLI | backtest artifact の pass/fail と境界判定 | backtest を live 許可へ昇格しない |
| Trade[XYZ] pure backtest v0.1 | `sis.backtest.engine.runner.run_backtest()` | 実装済み / CLI 未公開 | Trade[XYZ] 単一銘柄 long-only の詳細 engine | venue 専用、public CLI なし、portfolio 不十分 |
| Legacy backtest bridge | `uv run sis build-backtest` | 互換維持 | historical bridge 系の簡易評価 | 新規主経路ではない |

## いま行える Backtest

### 1. Strategy Authoring Fixed-Horizon Backtest

最短手順:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
```

主な入力:

- `strategy_authoring_spec.v1` YAML
- `feature_panel_path`
- `quote_data_path`
- `cost_model_path`
- symbol binding
- rule DSL
- backtest section

主な出力:

- `data/research/strategy_authoring_run.json`
- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/reports/strategy_backtest_report.md`
- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/reports/strategy_backtest_acceptance_report.md`
- `data/research/backtest_compare/strategy_backtest_comparison.json`
- `data/research/backtest_suite/strategy_backtest_suite_result.json`
- `data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json`
- `data/research/backtest_framework_smoke/strategy_backtest_framework_smoke.json`
- `data/research/backtest_adapter_selection/strategy_backtest_adapter_selection.json`
- `data/research/backtest_adapter_contract/strategy_backtest_adapter_contract.json`
- `data/research/backtest_metric_extension/strategy_backtest_metric_extension.json`
- `data/research/backtest_metric_extension/strategy_backtest_returns.jsonl`
- `data/research/backtest_report_extension/strategy_backtest_report_extension.json`
- `data/research/backtest_report_extension/strategy_backtest_report_returns.jsonl`
- `data/research/backtest_report_extension/strategy_backtest_quantstats_report.html`
- `data/research/backtest_stress/strategy_backtest_stress.json`
- `data/research/backtest_regime_split/strategy_backtest_regime_split.json`
- `data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json`
- `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json`
- `data/reports/strategy_backtest_comparison_report.md`
- `data/reports/strategy_backtest_suite_report.md`
- `data/reports/strategy_backtest_adapter_spike_report.md`
- `data/reports/strategy_backtest_framework_smoke_report.md`
- `data/reports/strategy_backtest_adapter_selection_report.md`
- `data/reports/strategy_backtest_adapter_contract_report.md`
- `data/reports/strategy_backtest_metric_extension_report.md`
- `data/reports/strategy_backtest_report_extension_report.md`
- `data/reports/strategy_backtest_stress_report.md`
- `data/reports/strategy_backtest_regime_split_report.md`
- `data/reports/strategy_backtest_rolling_stability_report.md`
- `data/reports/strategy_backtest_benchmark_relative_report.md`

現在できること:

- long / short / hold / close / reduce / add / rebalance signal
- fixed horizon exit
- stop loss / take profit / trailing stop / partial take profit
- min / max holding time
- explicit close / reduce / add / rebalance marker
- market / limit / stop-market entry constraint
- GTC / GTD / IOC / FOK 風の paper entry constraint
- post-only / reduce-only marker
- spread / depth / latency / queue position / borrow / tax drag / turnover / capacity / crowding / fee-edge gate
- notional / position weight / volatility target
- equal weight / score proportional / inverse volatility / dollar neutral / beta neutral / group neutral allocation
- multi-leg group metrics
- parameter sweep
- `single_window`, `walk_forward`, `purged_walk_forward`
- suite case の `return_bootstrap`, `block_bootstrap` resampling
- cost / slippage bps stress scenario
- side / timeframe / exit_reason / timestamp bucket split
- rolling window return / drawdown stability
- benchmark-relative active return / tracking error / information ratio
- pass thresholds
- executed signal summary
- strategy scorecard
- bundle-level comparison

現在できないこと:

- real live order
- wallet / signing / exchange write
- broker queue replay
- full L2 order book event replay
- production slippage calibration
- true portfolio accounting across independent strategies as a live book
- external model execution / arbitrary Python strategy code
- profitability guarantee

境界:

- `strategy_authoring_backtest_result.v1` は `paper_only=true` と `live_order_submitted=false` を要求する。
- `strategy_backtest_comparison.v1` は comparison artifact でも `permits_live_order=false`, `live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false` を要求する。
- `strategy_backtest_stress.v1` は既存 backtest metrics の returns を入力にした paper-only robustness artifact で、`dependency_added=false`, `live_order_submitted=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を要求する。
- `strategy_backtest_regime_split.v1` は既存 backtest metrics の returns を dimension 別に集計する paper-only robustness artifact で、`dependency_added=false`, `live_order_submitted=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を要求する。
- `strategy_backtest_rolling_stability.v1` は既存 backtest metrics の returns を rolling window 別に集計する paper-only robustness artifact で、`dependency_added=false`, `live_order_submitted=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を要求する。
- `strategy_backtest_benchmark_relative.v1` は既存 backtest metrics の returns を benchmark return と比較する paper-only robustness artifact で、`dependency_added=false`, `live_order_submitted=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を要求する。
- `strategy-backtest-acceptance` は `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。
- backtest pass は paper observation や live canary 許可ではない。現行 Strategy Lifecycle では backtest acceptance の後に paper observation review が必要である。

### 2. Trade[XYZ] Pure Backtest v0.1

入口:

```python
from sis.backtest.engine.runner import run_backtest
```

正本コード:

- `src/sis/backtest/engine/config.py`
- `src/sis/backtest/engine/runner.py`
- `src/sis/backtest/trade_xyz/schema.py`
- `src/sis/backtest/trade_xyz/cost_model.py`
- `src/sis/backtest/trade_xyz/gates.py`
- `tests/backtest/`

現在できること:

- Trade[XYZ] 専用
- single-symbol
- long-only
- fixed notional sizing
- market-like taker fill
- next-row fill
- fee / slippage / nullable funding
- optional external funding events
- entry / exit gate
- forced close on end
- breakout parameter grid
- scenario results
- train/test split results
- benchmark results
- data quality artifact
- markdown / HTML / SVG / JSON chart output

主な出力:

- `backtest_run.json`
- `config.json`
- `data_manifest.json`
- `data_quality.json`
- `orders.parquet`
- `fills.parquet`
- `trades.parquet`
- `blocked_events.parquet`
- `equity_curve.parquet`
- `metrics.json`
- `benchmark_results.json`
- `scenario_results.parquet`
- `parameter_results.parquet`
- `candidate_result.json`
- `backtest_report.md`
- `backtest_report.html`

現在できないこと:

- public CLI
- Strategy Authoring の汎用 backtest engine として直接利用
- short
- multi-symbol portfolio
- multi-strategy book
- limit / stop / partial fill の詳細再現
- L2 order book replay
- MT5 / IC Markets / CFD
- live order / wallet / signing / exchange write

### 3. Legacy Backtest Bridge

入口:

```bash
uv run sis build-backtest
```

これは互換維持の bridge であり、新規 backtest 機能拡張の主入口ではない。現行の主入口は `strategy-author-run --through backtest` である。

## 現行の内部 Framework

現行 repo は「外部 backtesting framework を入れて strategy を載せる」形ではなく、次の内部 contract で構成されている。

| 層 | 役割 | 主なファイル |
|---|---|---|
| Strategy Authoring DSL | YAML から signal / derived feature / exit / sizing / portfolio rule を定義 | `src/sis/research/strategy_lab/authoring/` |
| Backtest bridge | Strategy Lab signal を `ResearchSignal` として評価 | `src/sis/backtest/bridge.py` |
| Trade[XYZ] pure engine | venue 専用の fill / gate / fee / artifact engine | `src/sis/backtest/engine/`, `src/sis/backtest/trade_xyz/` |
| Lifecycle gate | backtest pass を paper observation 以降へ接続 | `src/sis/research/strategy_lifecycle/` |
| Artifact schemas | paper-only / no-live 境界を固定 | `schemas/strategy_authoring_backtest_result.v1.schema.json`, `schemas/strategy_backtest_acceptance_decision.v1.schema.json`, `schemas/strategy_backtest_comparison.v1.schema.json`, `schemas/strategy_backtest_stress.v1.schema.json`, `schemas/strategy_backtest_regime_split.v1.schema.json`, `schemas/strategy_backtest_rolling_stability.v1.schema.json`, `schemas/strategy_backtest_benchmark_relative.v1.schema.json` |

## Backtest Comparison Artifact

`strategy-backtest-compare` は、現行 `strategy_backtest_metrics.json` を比較用の canonical artifact に正規化する。既定の `data/research/backtest_suite/strategy_backtest_suite_result.json` が存在する場合は suite 結果を `suite_results` として、既定の `data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json` が存在する場合は adapter spike 結果を `adapter_spike` として、既定の `data/research/backtest_external/strategy_backtest_external_result.json` が存在する場合は外部 framework result を `external_results` として、既定の `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json` が存在する場合は `portfolio_comparison` として、既定の `data/research/backtest_metric_extension/strategy_backtest_metric_extension.json` が存在する場合は `metric_extension` として、既定の `data/research/backtest_report_extension/strategy_backtest_report_extension.json` が存在する場合は `report_extension` として、既定の `data/research/backtest_stress/strategy_backtest_stress.json` が存在する場合は `stress` として、既定の `data/research/backtest_regime_split/strategy_backtest_regime_split.json` が存在する場合は `regime_split` として、既定の `data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json` が存在する場合は `rolling_stability` として、既定の `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json` が存在する場合は `benchmark_relative` として同じ artifact に取り込む。

```bash
uv run sis strategy-backtest-compare
```

出力:

- `data/research/backtest_compare/strategy_backtest_comparison.json`
- `data/reports/strategy_backtest_comparison_report.md`

現時点では外部 framework dependency を追加しない。`framework_adapters` には optional framework の installed / not installed 状態、候補 role、license 注意を記録する。`adapter_spike` には `strategy-backtest-adapter-spike` が作った dependency 追加なしの import / metadata / license risk / adoption blocker を取り込む。`external_results` には `strategy-backtest-external-run` が作った外部 framework 実行用 artifact を取り込む。`portfolio_comparison` には `strategy-backtest-portfolio-compare` が作った `bt` 用 portfolio allocation / rebalance comparison artifact を取り込む。`metric_extension` には `strategy-backtest-metric-extension` が作った `empyrical-reloaded` 用 metrics normalization artifact を取り込む。`report_extension` には `strategy-backtest-report-extension` が作った `quantstats` 用 report / tear sheet artifact を取り込む。`stress` には `strategy-backtest-stress` が作った cost / slippage robustness artifact を取り込む。`regime_split` には `strategy-backtest-regime-split` が作った dimension 別 robustness artifact を取り込む。`rolling_stability` には `strategy-backtest-rolling-stability` が作った rolling window return / drawdown robustness artifact を取り込む。`benchmark_relative` には `strategy-backtest-benchmark-relative` が作った benchmark-relative active return artifact を取り込む。現環境で framework が未インストールなら `run_status=skipped`, `metric_status=skipped`, `report_status=skipped`, `reason_codes=["not_installed_in_current_env"]`, `runner_mode=not_installed_in_current_env` として記録する。`vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` の一時実行結果は `framework_version` と `runner_mode=temporary_or_optional_import` も比較 artifact に保持する。これは今後の adapter 比較の土台であり、外部 dependency 採用や live 許可ではない。

`method_results` には現行 native engine で実行済みの比較軸を正規化して記録する。現在の対応は `strategy_authoring_native_overall`、`strategy_authoring_walk_forward`、`strategy_authoring_optimizer_sweep` で、`summary.walk_forward_eras` と `summary.optimizer` が metrics に存在する場合は era 別結果と parameter sweep の best variant / variants も同じ comparison artifact で読める。`suite_results` には suite 単位の aggregate、best run、run 別 metrics、`method_matrix` を正規化する。`adapter_spike` には候補 framework ごとの `dependency_added=false`, `engine_run=false`, `permits_live_order=false` を含める。`comparison_diagnostics` には threshold failure、weakest era、suite best run、suite failed run、diagnostic notes を記録し、Markdown report にも Diagnostics section と Adapter Spike section を出す。

## Backtest Suite Runner

`strategy-backtest-suite` は `strategy_backtest_suite.v1` YAML を読み、複数specと複数backtest case を1コマンドで走らせる。

```bash
uv run sis strategy-backtest-suite --suite docs/strategy_research_lab/examples/backtest_suite.yaml
```

出力:

- `data/research/backtest_suite/strategy_backtest_suite_result.json`
- `data/reports/strategy_backtest_suite_report.md`

suite result は `paper_only=true`, `live_order_submitted=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を持つ。run には `method_id` / `method_type` が入り、suite 全体には `method_matrix` が出る。標準例は `single_window`、`walk_forward:trading_day`、`purged_walk_forward:trading_day`、`purged_walk_forward:trading_day+return_bootstrap`、`purged_walk_forward:trading_day+block_bootstrap` の5手法を同じ suite で実行し、手法別 run 数、pass 数、case id を JSON と report で確認できる。resampling case は実行済み signal return から deterministic bootstrap 分布を作り、`summary.resampling` に total return の p05 / p50 / p95、min / max、positive rate を残す。現時点では既存 Strategy Authoring native engine を使い、外部 framework engine や live order path は呼び出さない。

## Backtest Adapter Spike

`strategy-backtest-adapter-spike` は、外部 backtest framework 候補を repo dependency に入れる前の metadata spike artifact を作る。

```bash
uv run sis strategy-backtest-adapter-spike
```

出力:

- `data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json`
- `data/reports/strategy_backtest_adapter_spike_report.md`

この command は `pyproject.toml` / `uv.lock` を変更しない。外部 framework engine を実行せず、`vectorbt`, `bt`, `backtesting.py`, `zipline-reloaded`, `backtrader`, `quantstats`, `empyrical-reloaded`, `pyfolio-reloaded`, `qstrader` の import 可否、installed metadata、license classifier、adoption blocker、次の review step を記録する。`dependency_added=false`, `external_engine_run=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を artifact で固定する。

## Backtest Framework Temporary Import Smoke

`strategy-backtest-framework-smoke` は、外部 OSS を repo dependency に追加する前に、一時環境で import できるかを artifact 化する。

```bash
uv run sis strategy-backtest-framework-smoke
```

出力:

- `data/research/backtest_framework_smoke/strategy_backtest_framework_smoke.json`
- `data/reports/strategy_backtest_framework_smoke_report.md`

既定 target は `vectorbt`, `bt`, `quantstats`, `empyrical-reloaded` である。通常環境では未インストールなら `not_installed` として記録する。実際の一時 import smoke は次で行う。

```bash
uv run --with vectorbt --with bt --with quantstats --with empyrical-reloaded sis strategy-backtest-framework-smoke
```

2026-06-13_16:50 JST 時点の一時 smoke では4件すべて `import_status=imported` だった。artifact は `vectorbt=1.0.0`, `bt=1.2.0`, `quantstats=0.0.81`, `empyrical-reloaded=0.5.12`、Requires-Python はそれぞれ `>=3.10`, `>=3.9`, `>=3.10`, `>=3.9` を記録した。採用分類は `vectorbt` と `bt` が `optional_extra_candidate`、`quantstats` と `empyrical-reloaded` が `report_only_candidate` である。

この command は `pyproject.toml` / `uv.lock` を変更しない。外部 engine は実行せず、`dependency_added=false`, `external_engine_run=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を artifact で固定する。

## Backtest Adapter Selection

`strategy-backtest-adapter-selection` は、adapter spike と framework smoke の artifact から Phase C の初期選定を作る。

```bash
uv run sis strategy-backtest-adapter-selection
```

出力:

- `data/research/backtest_adapter_selection/strategy_backtest_adapter_selection.json`
- `data/reports/strategy_backtest_adapter_selection_report.md`

2026-06-13_19:23 JST 時点では、`vectorbt` を `high_speed_signal_runner`、`bt` を `portfolio_allocation_rebalance`、`empyrical-reloaded` を `metrics_normalization`、`quantstats` を `report_tearsheet` として selected にした。`backtesting.py`, `zipline-reloaded`, `backtrader`, `pyfolio-reloaded`, `qstrader` は license / build / maturity / no-live isolation などの理由で deferred にした。

この command は `pyproject.toml` / `uv.lock` を変更しない。外部 engine は実行せず、`dependency_added=false`, `external_engine_run=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を artifact で固定する。

## Backtest Adapter Contract

`strategy-backtest-adapter-contract` は、Phase C selected adapter の入力、出力、provenance、受入条件を dependency-free artifact として作る。

```bash
uv run sis strategy-backtest-adapter-contract
```

出力:

- `data/research/backtest_adapter_contract/strategy_backtest_adapter_contract.json`
- `data/reports/strategy_backtest_adapter_contract_report.md`

2026-06-13_19:23 JST 時点では、次の4 contract を作る。

| Framework | Role | Input | Output |
|---|---|---|---|
| `vectorbt` | `high_speed_signal_runner` | `strategy_signals_and_quotes` | `strategy_backtest_external_result.v1.result` |
| `bt` | `portfolio_allocation_rebalance` | `strategy_authoring_bundle_or_weight_series` | `strategy_backtest_portfolio_comparison.v1` |
| `empyrical-reloaded` | `metrics_normalization` | `returns_series` | `strategy_backtest_metric_extension.v1` |
| `quantstats` | `report_tearsheet` | `returns_series` | `strategy_backtest_report_extension.v1` |

この command は `pyproject.toml` / `uv.lock` を変更しない。外部 engine は実行せず、`dependency_added=false`, `external_engine_run=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を artifact で固定する。

## Backtest External Framework Result

`strategy-backtest-external-run` は外部 framework 候補の実行結果用 artifact を作る。

```bash
uv run sis strategy-backtest-external-run
```

出力:

- `data/research/backtest_external/strategy_backtest_external_result.json`
- `data/reports/strategy_backtest_external_report.md`

この command も `pyproject.toml` / `uv.lock` を変更しない。既定では `data/research/strategy_signals.parquet` と `data/research/strategy_authoring_baseline_quotes.parquet` を読み、`--label-horizon-minutes` で external framework 用の exit を作る。artifact には `source_metrics_path/hash`, `source_signals_path/hash`, `source_quotes_path/hash`, `label_horizon_minutes` を記録する。framework ごとの result には `framework_version` と `runner_mode` も入る。`vectorbt` がインストール済みなら `src/sis/backtest/vectorbt_adapter.py` が `vectorbt.Portfolio.from_signals` を呼び、`trade_count`, `total_return`, `max_drawdown`, `cost_drag_bps` を `strategy_backtest_external_result.v1` に記録する。現環境で `vectorbt`, `bt`, `backtesting.py`, `zipline-reloaded`, `backtrader`, `quantstats`, `empyrical-reloaded`, `pyfolio-reloaded`, `qstrader` が未インストールなら、各 candidate を `run_status=skipped`, `reason_codes=["not_installed_in_current_env"]`, `runner_mode=not_installed_in_current_env` で記録する。artifact は `dependency_added=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を固定し、外部 engine 実行が無い場合は `external_engine_run=false` になる。

一時環境で `vectorbt` を使う場合:

```bash
uv run --with vectorbt sis strategy-backtest-external-run
uv run sis strategy-backtest-compare
```

2026-06-13_18:25 JST 時点の smoke では、`uv run --with vectorbt` で `vectorbt_version=1.0.0` を import でき、`strategy-backtest-external-run` は `vectorbt` result を `framework_version=1.0.0`, `runner_mode=temporary_or_optional_import`, `run_status=completed`, `engine_run=true`, `trade_count=7`, `total_return=0.005833333333333431`, `max_drawdown=0.0`, `cost_drag_bps=0.0` として記録した。この smoke は repo dependency / lockfile 採用ではない。

## Backtest Portfolio Comparison

`strategy-backtest-portfolio-compare` は、Phase C selected adapter の `bt` contract に対応する portfolio allocation / rebalance comparison artifact を作る。

```bash
uv run sis strategy-backtest-portfolio-compare
```

出力:

- `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json`
- `data/reports/strategy_backtest_portfolio_comparison_report.md`

既定では `data/research/strategy_authoring_bundle_result.json` と `data/research/strategy_authoring_baseline_quotes.parquet` を読む。通常 locked env で `bt` が未インストールなら `run_status=skipped`, `reason_codes=["not_installed_in_current_env"]`, `runner_mode=not_installed_in_current_env`, `engine_run=false` を記録する。`bt` がインストール済みなら `src/sis/backtest/portfolio_comparison.py` が `bt.Strategy`, `bt.Backtest`, `bt.run()` を呼び、`portfolio_return`, `max_drawdown`, `turnover`, `rebalance_count` を `strategy_backtest_portfolio_comparison.v1` に記録する。artifact は `source_bundle_hash`, `price_frame_hash`, `dependency_added=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を固定する。

一時環境で `bt` を使う場合:

```bash
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
uv run --with bt sis strategy-backtest-portfolio-compare
uv run sis strategy-backtest-compare
```

2026-06-13_18:40 JST 時点の smoke では、`uv run --with bt` で `bt=1.2.0` を import でき、`strategy-backtest-portfolio-compare` は `bt` result を `framework_version=1.2.0`, `runner_mode=temporary_or_optional_import`, `run_status=completed`, `engine_run=true`, `portfolio_return=0.005833333333333801`, `max_drawdown=0.0`, `turnover=1.0`, `rebalance_count=1` として記録した。この smoke は repo dependency / lockfile 採用ではない。

## Backtest Metric Extension

`strategy-backtest-metric-extension` は、Phase C selected adapter の `empyrical-reloaded` contract に対応する metrics normalization artifact を作る。

```bash
uv run sis strategy-backtest-metric-extension
```

出力:

- `data/research/backtest_metric_extension/strategy_backtest_metric_extension.json`
- `data/research/backtest_metric_extension/strategy_backtest_returns.jsonl`
- `data/reports/strategy_backtest_metric_extension_report.md`

既定では `data/research/strategy_backtest_metrics.json` を読み、`summary.executed_signal_results[].signal_return` から returns series JSONL を作る。通常 locked env で `empyrical` が未インストールなら `metric_status=skipped`, `reason_codes=["not_installed_in_current_env"]`, `runner_mode=not_installed_in_current_env`, `engine_run=false` を記録する。`empyrical` がインストール済みなら `src/sis/backtest/metric_extension.py` が `empyrical` の Sharpe / Sortino / max drawdown / annual return / annual volatility / Calmar / Omega 系 metric を呼び、`strategy_backtest_metric_extension.v1` に記録する。artifact は `source_backtest_metrics_hash`, `returns_series_hash`, `dependency_added=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を固定する。

一時環境で `empyrical-reloaded` を使う場合:

```bash
uv run --with empyrical-reloaded sis strategy-backtest-metric-extension
uv run sis strategy-backtest-compare
```

2026-06-13_18:57 JST 時点の smoke では、`uv run --with empyrical-reloaded` で `empyrical-reloaded=0.5.12` を import でき、`strategy-backtest-metric-extension` は `framework_version=0.5.12`, `runner_mode=temporary_or_optional_import`, `metric_status=completed`, `engine_run=true`, `return_count=7`, `sharpe_ratio=7684.451501905242`, `max_drawdown=0.0`, `annual_return=0.18229407031297362`, `annual_volatility=0.000021798866106592272` として記録した。現行サンプル return では `sortino_ratio`, `calmar_ratio`, `omega_ratio` は null になり得る。この smoke は repo dependency / lockfile 採用ではない。

## Backtest Report Extension

`strategy-backtest-report-extension` は、Phase C selected adapter の `quantstats` contract に対応する report / tear sheet artifact を作る。

```bash
uv run sis strategy-backtest-report-extension
```

出力:

- `data/research/backtest_report_extension/strategy_backtest_report_extension.json`
- `data/research/backtest_report_extension/strategy_backtest_report_returns.jsonl`
- `data/research/backtest_report_extension/strategy_backtest_quantstats_report.html`
- `data/reports/strategy_backtest_report_extension_report.md`

既定では `data/research/strategy_backtest_metrics.json` を読み、`summary.executed_signal_results[].signal_return` から report 用 returns series JSONL を作る。通常 locked env で `quantstats` が未インストールなら `report_status=skipped`, `reason_codes=["not_installed_in_current_env"]`, `runner_mode=not_installed_in_current_env`, `engine_run=false` を記録する。`quantstats` がインストール済みなら `src/sis/backtest/report_extension.py` が `quantstats.reports.html` と `quantstats.reports.metrics` を呼び、HTML report path/hash と metrics table row count を `strategy_backtest_report_extension.v1` に記録する。artifact は `source_backtest_metrics_hash`, `returns_series_hash`, `quantstats_html_hash`, `dependency_added=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を固定する。

一時環境で `quantstats` を使う場合:

```bash
uv run --with quantstats sis strategy-backtest-report-extension
uv run sis strategy-backtest-compare
```

2026-06-13_19:23 JST 時点の smoke では、`uv run --with quantstats` で `quantstats=0.0.81` を import でき、`strategy-backtest-report-extension` は `framework_version=0.0.81`, `runner_mode=temporary_or_optional_import`, `report_status=completed`, `engine_run=true`, `return_count=7`, `metrics_table_row_count=38` として記録し、HTML report を生成した。この smoke は repo dependency / lockfile 採用ではない。

## Backtest Cost / Slippage Stress

`strategy-backtest-stress` は、既存 `strategy_backtest_metrics.json` の `summary.executed_signal_results[].signal_return` に追加 cost / slippage bps を掛け、scenario 別の robustness artifact を作る。

```bash
uv run sis strategy-backtest-stress
```

出力:

- `data/research/backtest_stress/strategy_backtest_stress.json`
- `data/reports/strategy_backtest_stress_report.md`

既定 scenario は `base:0:0,mild:1:4,moderate:2:8,severe:5:20` で、`--scenario-csv id:additional_cost_bps:additional_slippage_bps,...` で変更できる。artifact は source backtest metrics の path / hash、scenario count、base summary、scenario 別 stressed total return、delta、positive rate、max drawdown、stressed cost drag bps を記録する。これは既存 returns に対する paper-only stress であり、外部 framework、dependency 追加、live order、wallet、exchange write は使わない。

## Backtest Regime Split

`strategy-backtest-regime-split` は、既存 `strategy_backtest_metrics.json` の `summary.executed_signal_results[]` を dimension 別に集計し、弱い bucket を確認する artifact を作る。

```bash
uv run sis strategy-backtest-regime-split
```

出力:

- `data/research/backtest_regime_split/strategy_backtest_regime_split.json`
- `data/reports/strategy_backtest_regime_split_report.md`

既定 dimension は `side,timeframe,exit_reason,ts_weekday,ts_hour` で、`--dimension-csv side,timeframe,exit_reason,ts_date,ts_weekday,ts_hour,...` のように変更できる。dimension は executed signal row の既存 field か、`ts_signal` から派生する `ts_date`, `ts_weekday`, `ts_hour` を使う。artifact は source backtest metrics の path / hash、dimension count、bucket count、bucket 別 total return / average return / positive rate / max drawdown / cost drag / notional を記録する。現時点の baseline artifact には明示的な `market_regime` 列はないため、まず timestamp bucket と既存 row field の分割を使う。これは paper-only 分析であり、外部 framework、dependency 追加、live order、wallet、exchange write は使わない。

## Backtest Rolling Stability

`strategy-backtest-rolling-stability` は、既存 `strategy_backtest_metrics.json` の `summary.executed_signal_results[].signal_return` を rolling window 別に集計し、窓幅ごとの弱い期間を確認する artifact を作る。

```bash
uv run sis strategy-backtest-rolling-stability
```

出力:

- `data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json`
- `data/reports/strategy_backtest_rolling_stability_report.md`

既定 window は `3,5` で、`--window-csv 3,5,10` のように変更できる。artifact は source backtest metrics の path / hash、window count、window size 別の min / max / average total return、positive rate、worst window の start / end index、worst total return、max drawdown、source row indices を記録する。これは既存 returns に対する paper-only stability 分析であり、外部 framework、dependency 追加、live order、wallet、exchange write は使わない。

## Backtest Benchmark Relative

`strategy-backtest-benchmark-relative` は、既存 `strategy_backtest_metrics.json` の `summary.executed_signal_results[].signal_return` を benchmark return と比較し、active return を確認する artifact を作る。

```bash
uv run sis strategy-backtest-benchmark-relative
```

出力:

- `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json`
- `data/reports/strategy_backtest_benchmark_relative_report.md`

既定では `benchmark_return` 列が executed signal row にあればそれを使い、無ければ `data/research/strategy_authoring_baseline_quotes.parquet` の `mid_price` から `--horizon-minutes` の benchmark return を計算する。標準 pack では spec の `quote_data_path` と `backtest.label_horizon_minutes` を使う。artifact は strategy total return、benchmark total return、active total return、tracking error、information ratio、row-level active return を記録する。これは paper-only 比較であり、外部 framework、dependency 追加、live order、wallet、exchange write は使わない。

## Backtest Pack

標準の local backtest artifact chain を一括で作る場合は `strategy-backtest-pack` を使う。

```bash
uv run sis strategy-backtest-pack
```

この command は、単発 Strategy Authoring backtest metrics、5手法 suite、Strategy Authoring bundle result、adapter spike、external result、portfolio comparison、metric extension、report extension、cost / slippage stress、regime split、rolling stability、benchmark relative、comparison、pack manifest/report を順番に生成する。pack manifest は `strategy_backtest_pack.v1` で、artifact path / hash、suite run count、suite method count、external engine 実行有無、comparison id、外部 framework 方針を記録する。既定出力は次である。

- `data/research/backtest_pack/strategy_backtest_pack.json`
- `data/reports/strategy_backtest_pack_report.md`

pack も `paper_only=true`, `live_order_submitted=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を固定する。外部 framework dependency は追加せず、通常 locked env では外部 framework が未インストールなら `external_results`、`portfolio_comparison`、`metric_extension`、`report_extension` は skipped として comparison に残る。`external_framework_policy.policy_id` は `native_primary_external_evaluation_only.v1` で、標準 engine は `strategy_authoring_native`、標準完成線は `complete_without_locked_external_dependency`、`locked_dependency_added=false`、`external_adapters_required_for_completion=false` である。一時実行許可は `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` に限定する。外部 OSS を正式採用する場合は、license、Python 3.13 / uv lock、CI、schema boundary review を先に通す。

生成済み pack を検査する場合は `strategy-backtest-pack-validate` を使う。

```bash
uv run sis strategy-backtest-pack-validate
```

この command は `strategy_backtest_pack.v1` の artifact path / hash、標準5手法、paper-only / no-live boundary、外部 framework 方針を検査し、`strategy_backtest_pack_validation.v1` を作る。`decision=PASS` の場合だけ exit code 0 で、`FAIL` の場合は validation artifact / report を残して exit code 2 で止まる。

現行依存:

- `polars`: DataFrame 処理と backtest 入出力
- `pyarrow`: parquet artifact
- `duckdb`: data / report 系の集計に使う基盤
- `pydantic`: config / model validation
- `jsonschema`: JSON schema validation
- `typer`: CLI
- `exchange-calendars`: market calendar 系
- `yfinance`, `yahooquery`, `fredapi`, `pandas-datareader`: research data source

専用 backtest OSS は `pyproject.toml` に入っていない。

## OSS / Framework 候補

### 評価軸

今後の導入候補は、単に有名かではなく、次の条件で見る。

- Python 3.13 と `uv lock` で再現可能か
- repo の `paper_only=true`, `live_order_submitted=false`, `wallet_used=false`, `exchange_write_used=false` 境界を壊さないか
- Polars / parquet artifact と接続しやすいか
- Strategy Authoring YAML から adapter で呼べるか
- multi-asset / portfolio / parameter sweep / walk-forward に強いか
- broker/live 機能が混ざっても安全に無効化できるか
- license が commercial / internal use に問題ないか
- output を現行 `strategy_backtest_metrics.json` / lifecycle artifact に正規化できるか

### 候補一覧

| 候補 | 公式情報ベースの特徴 | repo への向き | 注意点 | 位置づけ |
|---|---|---|---|---|
| `vectorbt` | pandas / NumPy ベースの高速 backtesting / quantitative analysis。Numba / Rust による高速化も説明されている。 | 大量 parameter sweep、vectorized research、factor scan に向く | Polars 中心の現行 artifact とは変換層が必要。Python 3.13 / optional deps は導入 spike 必須 | 研究探索 adapter 候補 |
| `backtesting.py` | historical data 上で trading strategy viability を見る Python framework。PyPI では Python `>=3.9`。 | 単純な OHLC strategy prototype に向く | AGPLv3+ 表示があるため license review 必須。複雑な portfolio / artifact contract は adapter が必要 | 小型 prototype 候補 |
| `backtrader` | backtesting と trading の feature-rich Python framework。strategy / indicators / analyzers を書く設計。 | event-driven / indicator-heavy な検証に向く | live trading 機能も含むため、repo の no-live boundary と強く分離が必要。依存と保守状態の spike 必須 | event-driven comparison 候補 |
| `zipline-reloaded` | Pythonic event-driven backtester。PyPI は Python `>=3.9` と NumFOCUS library 互換を説明している。 | equity-style pipeline / calendar / event-driven 検証に向く | 導入が重くなりやすい。現行 Strategy Authoring YAML との対応が薄い。Python 3.13 での実導入確認が必要 | 大型 framework 候補 |

### 2026-06-13 Import / License Smoke

repo の `pyproject.toml` / `uv.lock` は変更せず、`uv run --with ... python` で一時環境の import smoke を行った。

| 候補 | import smoke | observed version | observed metadata | 判断 |
|---|---:|---|---|---|
| `vectorbt` | pass | `1.0.0` | `Requires-Python >=3.10`; wheel metadata 上の `License` / license classifier は空 | 技術 spike は可能。ただし license metadata が弱いため採用前に project license を別途確認する |
| `backtesting` | pass | `0.6.5` | `Requires-Python >=3.9`; `License=AGPL-3.0`; classifier `AGPLv3+` | 技術的には軽いが、AGPL のため repo dependency 追加は license review 後 |
| `backtrader` | pass | `1.9.78.123` | `License=GPLv3+`; classifier `GPLv3+`; import 時に Python 3.13 warning あり | GPL のため repo dependency 追加は license review 後。event-driven 比較は別環境 adapter が無難 |
| `zipline-reloaded` | fail | `3.1.1` resolution attempted | `bcolz-zipline==1.13.0` wheel build failed; `Python.h` missing during build | 現環境で即採用不可。大型 dependency なので候補順位を下げる |

実行した確認:

```bash
uv run --with vectorbt python -c 'import vectorbt'
uv run --with backtesting python -c 'import backtesting'
uv run --with backtrader python -c 'import backtrader'
uv run --with zipline-reloaded python -c 'import zipline'
uv run --with vectorbt --with backtesting --with backtrader python - <<'PY'
from importlib.metadata import metadata, version
for dist in ['vectorbt', 'backtesting', 'backtrader']:
    m = metadata(dist)
    print(dist, version(dist), m.get('License'), m.get('Requires-Python'))
PY
```

この smoke は「依存追加してよい」証明ではない。`uv.lock`、CI、license、artifact normalization、no-live boundary test を通すまでは採用しない。

参照:

- vectorbt docs: https://vectorbt.dev/
- vectorbt installation: https://vectorbt.dev/getting-started/installation/
- backtesting.py docs: https://kernc.github.io/backtesting.py/
- backtesting.py PyPI: https://pypi.org/project/backtesting/
- Backtrader docs: https://www.backtrader.com/
- Backtrader installation: https://www.backtrader.com/docu/installation/
- zipline-reloaded PyPI: https://pypi.org/project/zipline-reloaded/
- Zipline installation docs: https://zipline.ml4trading.io/install.html

## 採用方針

現時点の推奨は **core は現行自前 engine を維持し、外部 OSS は adapter として比較導入する** である。

理由:

- 現行 repo は backtest 結果を Strategy Lifecycle / paper observation / safety boundary に接続している。
- 外部 framework の出力をそのまま正本にすると、`paper_only`, `no_live`, source hash, lifecycle decision の contract が壊れやすい。
- Strategy Authoring YAML は既に多くの entry / exit / sizing / portfolio / execution gate を持つため、外部 framework へ全面移行すると既存機能の再実装コストが高い。
- 一方で、parameter sweep、portfolio research、event-driven comparison は外部 framework で補える可能性がある。

## 次に作るべき Scope

「様々な手法で backtest する」ための次 scope は、live ではなく backtest expansion として切る。

推奨 scope:

```text
Backtest Expansion Scope 1: Framework Adapter Spike

目的:
- 現行 Strategy Authoring backtest を正本にしたまま、外部 backtest framework を比較 adapter として試せるようにする。

対象:
- vectorized research adapter
- simple OHLC prototype adapter
- event-driven comparison adapter

やらない:
- dependency 追加を即決しない
- live order / wallet / signing / exchange write に触れない
- Strategy Authoring YAML contract を壊さない
- 既存 backtest artifact を置き換えない

完了条件:
- 候補 framework ごとの導入可否表
- Python 3.13 / uv lock / license / import smoke 結果
- 現行 `strategy_backtest_metrics.json` へ正規化できる最小 adapter 方針
- 採用候補を 1 つ、または「当面自前拡張」の判断を記録
```

その次の実装候補:

1. `strategy-backtest-compare` command を追加し、現行 engine と adapter result を同じ report に並べる。
2. 最初の adapter は repo 依存を増やさず、現行 output を比較用 canonical shape に正規化する internal adapter にする。
3. 外部 framework は、license review 後に optional extra または別環境 runner として扱う。
4. `strategy_authoring_spec.v1` の `backtest.engine` を追加する前に、内部設定だけで adapter を選ぶ spike を行う。
5. 採用する場合だけ `pyproject.toml` / `uv.lock` を更新する。

## 抜け、漏れ、誤謬リスク

- 外部 OSS の Python 3.13 実互換は未検証。公式 PyPI の `Requires-Python` は導入成功や全テスト成功を保証しない。
- `vectorbt` / `bt` / `backtesting.py` / `zipline-reloaded` / `backtrader` / `quantstats` / `empyrical-reloaded` / `pyfolio-reloaded` / `qstrader` は現行 lockfile に入っていない。採用には依存追加と CI 検証が必要。
- `backtesting.py` は PyPI 上で AGPLv3+ と表示されるため、利用形態によっては license review が必要。
- external framework が持つ live trading 機能は、採用しても repo では無効化・隔離する必要がある。
- 現行 NDX Layer 2.5 は `permits_backtest=false` の research-only export であり、NDX residual validation 自体が backtest 許可を出しているわけではない。
- Strategy Lifecycle 上は backtest acceptance は通過済みでも、paper observation はまだ不足している。backtest expansion と paper observation continuation は別 scope として扱う。
