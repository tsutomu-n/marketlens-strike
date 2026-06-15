<!--
作成日: 2026-06-13_21:35 JST
更新日: 2026-06-15_21:08 JST
-->

# Operator Backtest Pack Recipe

## 結論

外部 benchmark series を明示して標準 backtest pack を作る場合は、次の 3 command を使う。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

これは local fixture と local CSV だけを読む paper-only 手順である。live order、wallet、signing、exchange write、外部 benchmark fetching は行わない。

## 入力

- Strategy Authoring spec: `docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml`
- Strategy Backtest Suite: `docs/strategy_research_lab/examples/backtest_suite.yaml`
- Strategy Authoring bundle: `docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml`
- external benchmark series: `docs/strategy_research_lab/examples/external_benchmark_series.csv`

external benchmark series は次の列を持つ。

- `source_row_index`
- `signal_id`
- `ts_signal`
- `venue`
- `canonical_symbol`
- `benchmark_return`

対応付けは `source_row_index`、`signal_id`、`ts_signal + venue + canonical_symbol` の順に使える。`benchmark_return` 以外の列名を使う場合は `--benchmark-series-return-column <column>` を渡す。

## 出力

pack と validation:

- `data/research/backtest_pack/strategy_backtest_pack.json`
- `data/research/backtest_pack/strategy_backtest_pack_validation.json`
- `data/reports/strategy_backtest_pack_report.md`
- `data/reports/strategy_backtest_pack_validation_report.md`

benchmark-relative artifact:

- `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json`
- `data/reports/strategy_backtest_benchmark_relative_report.md`

framework run matrix:

- `data/research/backtest_framework_run/strategy_backtest_framework_run.json`
- `data/reports/strategy_backtest_framework_run_report.md`

## 確認する field

`strategy_backtest_pack.json`:

- `artifacts.benchmark_relative.exists`
- `artifacts.framework_run.exists`
- `artifacts.benchmark_relative.sha256`
- `artifacts.framework_run.sha256`
- `external_framework_policy.standard_engine`
- `external_framework_policy.completion_line`
- `external_framework_policy.locked_dependency_added`
- `paper_only`
- `live_order_submitted`
- `permits_live_order`
- `wallet_used`
- `exchange_write_used`

`strategy_backtest_benchmark_relative.json`:

- `source_benchmark_series_path`
- `source_benchmark_series_hash`
- `benchmark_series_return_column`
- `summary.strategy_total_return`
- `summary.benchmark_total_return`
- `summary.active_total_return`
- `summary.tracking_error`
- `summary.information_ratio`
- `comparisons[].benchmark_source`
- `comparisons[].active_return`

`strategy_backtest_pack_validation.json`:

- `decision`
- `summary.failed_count`
- `findings[].passed`
- `findings[].check_id`

`decision=PASS` の場合だけ `strategy-backtest-pack-validate` は exit code 0 で終わる。`decision=FAIL` の場合は validation artifact と report を残して exit code 2 で止まる。

主要 field だけを JSON で確認する場合は、次を使う。

```bash
uv run sis strategy-backtest-artifact-summary
```

この command は pack、pack validation、benchmark relative、framework run、metric extension、report extension、stress、regime split、rolling stability、comparison diagnostics を読み、欠損 artifact は `exists=false` として表示する。

## optional extras

通常 locked env で `vectorbt`、`bt`、`empyrical-reloaded`、`quantstats` が入っていない場合、該当 framework run は `skipped/not_installed_in_current_env` として comparison / pack に残る。これは標準 pack の失敗ではない。

optional extra を明示して追加検証する場合は、pack manifest の artifact hash と実ファイルをずらさないため、pack 自体を extras 環境で再実行する。

```bash
uv sync --dev --extra vectorbt --extra bt --extra metrics --extra reports --locked
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-pack-validate
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-artifact-summary
```

確認 field:

- `pack.artifacts.portfolio_comparison.sha256`
- `pack.artifacts.framework_run.sha256`
- `framework_run.summary.executed_count`
- `framework_run.runs[].dependency_source`
- `pack.artifacts.metric_extension.sha256`
- `pack.artifacts.report_extension.sha256`
- `metric_extension.dependency_source`
- `metric_extension.metric_status`
- `report_extension.dependency_source`
- `report_extension.report_status`
- `report_extension.framework_warning_count`
- `pack_validation.decision`

`vectorbt` は 2026-06-14_11:00 JST の owner 承認により、`vectorbt==1.0.0` を optional extra / lockfile に正式採用済みである。標準 pack の完成線は native-primary のままなので、`vectorbt` を明示して使う場合は `uv run --extra vectorbt sis strategy-backtest-framework-run --framework vectorbt` を使う。

## reference-only contract

次の command は dependency 追加や engine 実行ではなく、採用前の readiness / contract を artifact 化する。

```bash
uv run sis strategy-backtest-microstructure-readiness
uv run sis strategy-backtest-qstrader-contract
uv run sis strategy-backtest-portfolio-validation-contract
uv run sis strategy-backtest-pybroker-contract
```

これらの output は `decision` と `reason_codes` を読む。`NOT_READY_*` は通常 pack の破損ではなく、当該 OSS runner をまだ採用できない理由の記録である。
