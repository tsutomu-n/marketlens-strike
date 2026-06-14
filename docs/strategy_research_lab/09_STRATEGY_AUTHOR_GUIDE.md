<!--
作成日: 2026-05-30_15:19 JST
更新日: 2026-06-14_17:55 JST
-->

# Strategy Author Guide

この guide は、ユーザーが Strategy Lab で売買ロジックを作るための最短導線です。対象は paper-only research です。ライブ発注、ウォレット操作、取引所書き込みは行いません。

## 1. テンプレートを作る

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

生成される YAML は `strategy_authoring_spec.v1` です。v1 の正式入力は YAML だけです。

## 2. YAML を検証する

```bash
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

検証では次を確認します。

- 必須 section があるか
- `feature_panel_path` が存在するか
- rule と score が参照する feature column が存在するか
- `symbol_bindings.real_market_symbol` の row が feature panel に存在するか
- paper-only 境界から外れる claim を作っていないか

## 3. 人間向け説明レポートを出す

```bash
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

既定出力は `data/reports/strategy_authoring_explain.md` です。売買条件、必要 column、symbol binding、backtest 条件、validation error を一覧できます。

## 4. シグナルを作る

```bash
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through signals
```

出力は既存 Strategy Lab artifact と同じです。

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signals.jsonl`
- `data/research/strategy_signal_manifest.json`
- `data/research/signals.csv`
- `data/research/strategy_authoring_run.json`

`signals.csv` は legacy export です。新しい authoring flow の正本は `strategy_signals.parquet` です。

## 5. バックテストまで実行する

```bash
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

既存 backtest bridge を使い、Strategy Lab signals を直接 `ResearchSignal` に変換して評価します。legacy `signals.csv` を正本にしません。

追加出力は次です。

- `data/research/strategy_backtest_metrics.json`
- `data/reports/strategy_backtest_report.md`

v1 は fixed horizon exit です。`backtest.label_horizon_minutes` で horizon を指定します。

`rules.exit.stop_loss_bps` と `rules.exit.take_profit_bps` を指定した場合は、fixed horizon の手前でも、先に到達した stop loss / take profit quote で仮想 exit します。`min_stop_loss_bps` / `max_stop_loss_bps` / `min_take_profit_bps` / `max_take_profit_bps` と各 `_column` を指定すると、狭すぎる損切、広すぎる損切、狭すぎる利確、広すぎる利確を `stop_loss_bps_too_low` / `stop_loss_bps_too_high` / `take_profit_bps_too_low` / `take_profit_bps_too_high` として見送れます。`rules.exit.min_reward_risk_ratio` または `min_reward_risk_ratio_column` を指定すると、take profit 幅が stop loss 幅に対して小さすぎる候補を `reward_risk_ratio_too_low` で見送れます。`trailing_stop_bps` と `trailing_stop_activation_bps`、`partial_take_profit_bps` / `partial_exit_fraction` も paper backtest に反映できます。`trailing_stop_activation_bps` は、有利方向の含み益が指定 bps に到達するまで trailing stop を発動しない protective threshold です。`rules.bracket.break_even_after_partial_take_profit` を使うと、部分利確後の残り position を break-even stop 待ちへ移せます。`min_holding_minutes` または `min_holding_minutes_column` を指定すると、最低保有時間に到達するまで stop / take / trailing / partial / signal exit / bracket time stop を無視し、早すぎる noise exit を抑えた研究ができます。`max_holding_minutes` または `max_holding_minutes_column` を指定すると、fixed horizon より手前でも指定時間で残り position を time stop として仮想 exit できます。`*_column` は row 値を優先し、空なら固定値へ fallback します。`exit_priority` を指定すると、同じ quote で複数の exit 条件が同時に成立した場合の評価順を paper-only に固定できます。どの exit が使われたかは `strategy_backtest_metrics.json` の `summary.exit_reason_counts` に出ます。実行済み signal の verbose rows は `summary.executed_signal_results` に残り、通常確認用の compact view は `summary.executed_signal_summary` に side / symbol / timeframe / exit reason count、total / average signal return、win rate、cost drag、total notional、notional-weighted signal return として出ます。

`rules.exit.exit_on_opposite_signal: true` を指定すると、同じ execution symbol で反対方向の次シグナルが出た時点でも仮想 exit します。これは reversal、ドテン、close-on-sell / close-on-buy 型の評価用です。実注文は出しません。

`backtest.pass_thresholds` は `strategy_backtest_metrics.json` の `summary.pass_thresholds` と `summary.backtest_passed` に反映されます。`max_drawdown` は `-0.2` 以上なら pass です。`cost_drag_bps`, `stale_rejected_count`, `halt_rejected_count`, `*_cost_bps`, `*_drag_bps`, `*_imbalance`, rejected / blocked / unfilled 系 count、`incomplete_*` は threshold 以下なら pass、それ以外は threshold 以上なら pass です。`multi_leg_group_metrics.complete_group_count`, `multi_leg_group_metrics.total_return`, `multi_leg_group_metrics.incomplete_group_count`, `multi_leg_group_metrics.avg_leg_return_imbalance` のような summary 内の dotted path も指定できます。

## 5.1. 複数条件のバックテスト suite を実行する

```bash
uv run sis strategy-backtest-suite --suite docs/strategy_research_lab/examples/backtest_suite.yaml
```

`strategy_backtest_suite.v1` は `cases` に backtest 条件、`members` に対象 spec を並べます。標準例では1つの spec を `single_window`、`walk_forward:trading_day`、`purged_walk_forward:trading_day`、`purged_walk_forward:trading_day+return_bootstrap`、`purged_walk_forward:trading_day+block_bootstrap` の5手法で試します。複数specを同じ条件で比較する使い方もできます。

出力は次です。

- `data/research/backtest_suite/strategy_backtest_suite_result.json`
- `data/reports/strategy_backtest_suite_report.md`

suite result は paper-only artifact です。live order、wallet、exchange write は行いません。`method_matrix` で `single_window`、`walk_forward:trading_day`、`purged_walk_forward:trading_day`、`purged_walk_forward:trading_day+return_bootstrap`、`purged_walk_forward:trading_day+block_bootstrap` などの手法別 run 数、pass 数、case id を確認できます。`resampling.method` に `return_bootstrap` または `block_bootstrap` を指定した case は、実行済み signal return を deterministic に再標本化し、`summary.resampling` に total return の p05 / p50 / p95、min / max、positive rate を記録します。

外部 framework 候補を repo dependency に入れる前の確認だけを行う場合は、次を使います。

```bash
uv run sis strategy-backtest-adapter-spike
```

これは dependency を追加せず、外部 framework engine も実行せず、candidate metadata / license risk / adoption blocker を `data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json` に記録します。

外部 framework 候補を repo dependency に入れず、一時環境で import できるかを記録する場合は、次を使います。

```bash
uv run --with vectorbt --with bt --with quantstats --with empyrical-reloaded sis strategy-backtest-framework-smoke
```

これは `strategy_backtest_framework_smoke.v1` artifact に import status、version、license metadata、Requires-Python、採用分類を記録します。外部 engine は実行せず、`pyproject.toml` / `uv.lock` も変更しません。

`qstrader` を isolated runner 候補として明示確認する場合は、次を使います。

```bash
uv run --with qstrader sis strategy-backtest-framework-smoke --framework qstrader
```

この smoke が `imported` の場合、次の adapter selection で `qstrader` は selected `separate_runner_research` として記録され、local-input isolated runner contract の設計候補になります。これは dependency 採用でも engine 実行でもありません。

Phase C の初期 adapter 選定を記録する場合は、次を使います。

```bash
uv run sis strategy-backtest-adapter-selection
```

これは `strategy_backtest_adapter_selection.v1` artifact に、`vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` を selected、その他候補を deferred として記録します。明示 smoke で `qstrader` が `imported` の場合だけ、`qstrader` も selected `separate_runner_research` として記録します。外部 engine は実行せず、`pyproject.toml` / `uv.lock` も変更しません。

selected adapter の入力、出力、provenance、受入条件を固定する場合は、次を使います。

```bash
uv run sis strategy-backtest-adapter-contract
```

これは `strategy_backtest_adapter_contract.v1` artifact に `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` の adapter contract を記録します。外部 engine は実行せず、`pyproject.toml` / `uv.lock` も変更しません。

外部 framework result 用 artifact を作る場合は、次を使います。

```bash
uv run sis strategy-backtest-external-run
```

既定では `data/research/strategy_signals.parquet` と `data/research/strategy_authoring_baseline_quotes.parquet` を読み、`--label-horizon-minutes` で外部 framework 用の exit を組み立てます。外部 result artifact には metrics / signals / quotes の source path と hash、`label_horizon_minutes`、framework ごとの `framework_version` と `runner_mode` が入ります。`vectorbt` がインストール済みなら `src/sis/backtest/vectorbt_adapter.py` 経由で `vectorbt.Portfolio.from_signals` を呼びます。現環境で framework が未インストールなら、各候補は `run_status=skipped`, `reason_codes=["not_installed_in_current_env"]`, `runner_mode=not_installed_in_current_env` を持ちます。これは失敗ではなく、依存を追加せずに比較 artifact へ取り込むための境界安全な記録です。

`vectorbt` を repo dependency に入れず一時環境だけで実測する場合は、次を使います。

```bash
uv run --with vectorbt sis strategy-backtest-external-run
```

この場合、`vectorbt` が import でき、入力に entry / exit を作れるなら `vectorbt` の result は `framework_version=1.0.0`, `runner_mode=temporary_or_optional_import`, `run_status=completed`, `engine_run=true` になります。`pyproject.toml` / `uv.lock` は変更しません。

`bt` 用の portfolio allocation / rebalance comparison artifact を作る場合は、次を使います。

```bash
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
uv run sis strategy-backtest-portfolio-compare
```

既定では `data/research/strategy_authoring_bundle_result.json` と `data/research/strategy_authoring_baseline_quotes.parquet` を読みます。通常環境で `bt` が未インストールなら `run_status=skipped`, `runner_mode=not_installed_in_current_env` になります。`bt` を repo dependency に入れず一時環境だけで実測する場合は、次を使います。

```bash
uv run --with bt sis strategy-backtest-portfolio-compare
```

この場合、`bt` が import でき、入力 bundle / price frame を組めるなら `bt` の result は `framework_version=1.2.0`, `runner_mode=temporary_or_optional_import`, `run_status=completed`, `engine_run=true` になります。`pyproject.toml` / `uv.lock` は変更しません。

`empyrical-reloaded` 用の metric extension artifact を作る場合は、次を使います。

```bash
uv run sis strategy-backtest-metric-extension
```

通常環境で `empyrical` が未インストールなら `metric_status=skipped`, `runner_mode=not_installed_in_current_env` になります。`empyrical-reloaded` を repo dependency に入れず一時環境だけで実測する場合は、次を使います。

```bash
uv run --with empyrical-reloaded sis strategy-backtest-metric-extension
```

この場合、`empyrical` が import でき、`strategy_backtest_metrics.json` から returns series を作れるなら `empyrical-reloaded` の result は `framework_version=0.5.12`, `runner_mode=temporary_or_optional_import`, `metric_status=completed`, `engine_run=true` になります。`pyproject.toml` / `uv.lock` は変更しません。

`quantstats` 用の report extension artifact を作る場合は、次を使います。

```bash
uv run sis strategy-backtest-report-extension
```

通常環境で `quantstats` が未インストールなら `report_status=skipped`, `runner_mode=not_installed_in_current_env` になります。`quantstats` を repo dependency に入れず一時環境だけで実測する場合は、次を使います。

```bash
uv run --with quantstats sis strategy-backtest-report-extension
```

この場合、`quantstats` が import でき、`strategy_backtest_metrics.json` から returns series を作れるなら `quantstats` の result は `framework_version=0.0.81`, `runner_mode=temporary_or_optional_import`, `report_status=completed`, `engine_run=true` になり、HTML report path/hash を記録します。`pyproject.toml` / `uv.lock` は変更しません。

cost / slippage bps を追加した robustness scenario を作る場合は、次を使います。

```bash
uv run sis strategy-backtest-stress
```

既定では `data/research/strategy_backtest_metrics.json` を読み、`base:0:0,mild:1:4,moderate:2:8,severe:5:20` の scenario で `data/research/backtest_stress/strategy_backtest_stress.json` と `data/reports/strategy_backtest_stress_report.md` を作ります。`--scenario-csv id:additional_cost_bps:additional_slippage_bps,...` で scenario を変更できます。これは既存 returns への paper-only stress で、live order、wallet、exchange write は許可しません。

executed signal return を dimension 別に分解する場合は、次を使います。

```bash
uv run sis strategy-backtest-regime-split
```

既定では `data/research/strategy_backtest_metrics.json` を読み、`side,timeframe,exit_reason,ts_weekday,ts_hour` で `data/research/backtest_regime_split/strategy_backtest_regime_split.json` と `data/reports/strategy_backtest_regime_split_report.md` を作ります。`--dimension-csv` で executed signal row の field や `ts_signal` から派生する `ts_date`, `ts_weekday`, `ts_hour` を指定できます。これは paper-only 分析で、live order、wallet、exchange write は許可しません。

executed signal return を rolling window 別に確認する場合は、次を使います。

```bash
uv run sis strategy-backtest-rolling-stability
```

既定では `data/research/strategy_backtest_metrics.json` を読み、window `3,5` で `data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json` と `data/reports/strategy_backtest_rolling_stability_report.md` を作ります。`--window-csv` で rolling window size を変更できます。これは paper-only stability 分析で、live order、wallet、exchange write は許可しません。

benchmark relative の active return を確認する場合は、次を使います。

```bash
uv run sis strategy-backtest-benchmark-relative
```

既定では `data/research/strategy_backtest_metrics.json` を読み、executed signal row の `benchmark_return` 列、`--benchmark-series-path` の明示 external benchmark series、または `data/research/strategy_authoring_baseline_quotes.parquet` の `mid_price` から benchmark return を作り、`data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json` と `data/reports/strategy_backtest_benchmark_relative_report.md` を出します。external benchmark series は `source_row_index`、`signal_id`、または `ts_signal + venue + canonical_symbol` で executed signal row と対応付けます。コピー用 CSV は [external_benchmark_series.csv](examples/external_benchmark_series.csv) です。標準 pack では spec の `quote_data_path` と `backtest.label_horizon_minutes` を使います。これは paper-only 比較で、live order、wallet、exchange write は許可しません。

suite、adapter spike、external result、portfolio comparison、metric extension、report extension、stress、regime split、rolling stability、benchmark relative の実行後に `uv run sis strategy-backtest-compare` を実行すると、単発backtest metrics、suite result、外部 framework adapter 候補の状態、adapter spike の採否判断材料、external result、portfolio comparison result、metric extension result、report extension result、cost / slippage stress result、regime split result、rolling stability result、benchmark relative result を `data/research/backtest_compare/strategy_backtest_comparison.json` にまとめられます。既定では `data/research/backtest_suite/strategy_backtest_suite_result.json`、`data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json`、`data/research/backtest_external/strategy_backtest_external_result.json`、`data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json`、`data/research/backtest_metric_extension/strategy_backtest_metric_extension.json`、`data/research/backtest_report_extension/strategy_backtest_report_extension.json`、`data/research/backtest_stress/strategy_backtest_stress.json`、`data/research/backtest_regime_split/strategy_backtest_regime_split.json`、`data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json`、`data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json` が存在する場合だけ取り込みます。comparison artifact は suite の `method_matrix` と run ごとの `method_id` も保持します。`comparison_diagnostics` では threshold failure、weakest era、suite best run を確認できます。

標準の単発backtest、5手法 suite、adapter spike、external result、portfolio comparison、metric extension、report extension、stress、regime split、rolling stability、benchmark relative、comparison、pack manifest を一括生成する場合は、次を使います。

```bash
uv run sis strategy-backtest-pack
```

既定出力は `data/research/backtest_pack/strategy_backtest_pack.json` と `data/reports/strategy_backtest_pack_report.md` です。pack manifest は生成 artifact の path / hash、suite method count、external engine 実行有無、comparison id、`external_framework_policy` を記録します。pack には bundle result、portfolio comparison、metric extension、report extension、stress、regime split、rolling stability、benchmark relative、returns series も入ります。`--benchmark-series-path` を渡すと pack 内の benchmark relative でも明示 external benchmark series を使います。コピー用 CSV を使う operator 手順は [OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md](../backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md) にあります。標準 engine は `strategy_authoring_native` で、完成線は `complete_without_locked_external_dependency` です。これも paper-only artifact で、live order、wallet、exchange write は許可しません。

生成済み pack を検査する場合は次を使います。

```bash
uv run sis strategy-backtest-pack-validate
```

validation は pack manifest の artifact path / hash、標準5手法、paper-only / no-live boundary、外部 framework 方針を検査し、`data/research/backtest_pack/strategy_backtest_pack_validation.json` に `PASS` または `FAIL` を記録します。CLI は `FAIL` の場合 exit code 2 で止まります。

## 6. paper-preview artifact まで出す

```bash
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through paper-preview
```

追加出力は次です。

- `data/research/trial_ledger.jsonl`
- `data/research/paper_candidate_pack.json`
- `data/research/promotion_decision.json`
- `data/bot/paper_intent_preview.json`
- `data/reports/paper_intent_preview.md`

既定の `promotion.default_decision` は `hold` です。そのため `paper_intent_preview.json` は空配列になります。これは意図した安全側 default です。

promotion を `promote` にしても、selected candidate が venue suitability gate で止まる場合は paper intent は作られません。現行では NDX/QQQ family の `trade_xyz` proxy や `bitget_demo` paper intent はこの境界で拒否されます。research/backtest artifact としての保存と、paper routing 可否は分けて読んでください。

## Rule DSL

`rules.entry.all` はすべて満たす条件、`rules.entry.any` は少なくとも 1 つ満たす条件、`rules.entry.none` は 1 つも満たしてはいけない条件です。複数を組み合わせると `all AND any AND none` です。`none` は「イベントでない」「過熱していない」「ニュース blackout でない」のような否定条件に使えます。

```yaml
rules:
  entry:
    all:
      - column: trend_ok
        op: is_true
    any:
      - column: pullback_score
        op: gt
        value: 0.7
      - column: breakout_score
        op: gt
        value: 0.8
    none:
      - column: news_blackout
        op: is_true
      - column: rsi
        op: gt
        value: 80
```

`rules.hold` は同じ DSL で「今は入らない」を記録します。hold 条件に当たった row は `side: none`、`block_reasons: ["hold_rule"]` の Strategy Lab signal として残りますが、backtest の売買対象からは除外されます。

`rules.close` は「新規 entry ではなく既存 paper position を閉じる」ための close signal を作ります。`rules.exit.exit_on_close_signal: true` を entry signal 側に設定すると、同じ execution symbol の次の `side: close` signal で fixed horizon より前に仮想 exit します。close signal 自体は reverse trade を開きません。

`rules.reduce` は「既存 paper position の一部だけを縮小する」ための reduce signal を作ります。`rules.exit.exit_on_reduce_signal: true` と `reduce_fraction` / `reduce_fraction_column` を entry signal 側に設定すると、同じ execution symbol の次の `side: reduce` signal で指定 fraction だけ仮想 exit し、残りは horizon / stop / take profit まで維持します。

`rules.add` は「既存 paper position に追加する」ための add signal を作ります。`rules.exit.exit_on_add_signal: true` と `add_fraction` / `add_fraction_column` を entry signal 側に設定すると、同じ execution symbol の次の `side: add` signal で指定 fraction だけ追加 entry し、元 position と追加分を同じ exit lifecycle で評価します。

`rules.rebalance` は「既存 paper position を目標 exposure へ寄せる」ための rebalance signal を作ります。`rules.exit.exit_on_rebalance_signal: true` と `rebalance_target_fraction` / `rebalance_target_fraction_column` を entry signal 側に設定すると、同じ execution symbol の次の `side: rebalance` signal で paper exposure を target fraction に近づけます。target が現在値より小さい場合は縮小、大きい場合は追加として backtest に反映します。これは paper-only の position resize marker であり、live rebalance order は出しません。

`rules.side: auto` を使うと、同じ YAML から long / short / hold を row ごとに出せます。explicit close は `rules.close` で別に書きます。`rules.side_column` は feature column の値を読み、`long`, `short`, `hold`, `skip`, `flat`, `none` を解釈します。`rules.long_entry` / `rules.short_entry` を使うと、買い専用・売り専用の条件を分けられます。

対応 operator は次です。

- `gt`
- `gte`
- `lt`
- `lte`
- `eq`
- `neq`
- `is_true`
- `is_false`
- `between`
- `in`
- `not_in`

`between` の `value` は 2 要素配列です。

```yaml
- column: vix_level
  op: between
  value: [10, 30]
```

`gt` / `gte` / `lt` / `lte` / `eq` / `neq` は `value` の代わりに `value_column` も使えます。これにより moving average cross、adaptive threshold、pair spread のような「列と列の比較」を直接書けます。

```yaml
- column: fast_ma
  op: gt
  value_column: slow_ma
```

`in` / `not_in` は regime や event category の list 判定に使います。

```yaml
- column: market_regime
  op: in
  value: [bull, neutral]
```

## Derived Features

`rules.derived_features` で、feature panel の既存 column から strategy-local な派生 column を作れます。任意式や Python eval は使わず、許可された演算だけを Polars で実行します。

```yaml
rules:
  derived_features:
    - name: trend_spread
      op: diff
      columns: [fast_ma, slow_ma]
    - name: return_z
      op: rolling_zscore
      columns: [research_return_1d]
      window: 20
      fill_null: 0
  entry:
    all:
      - column: trend_spread
        op: gt
        value: 0
      - column: return_z
        op: gte
        value: 0
```

対応 op は次です。

- row-wise: `add`, `sub`, `mul`, `div`, `ratio`, `diff`, `pct_diff`, `abs`, `neg`, `max`, `min`, `mean`
- OHLC/time-series: `true_range`, `atr`, `bollinger_upper`, `bollinger_lower`, `bollinger_width`, `bollinger_percent_b`, `donchian_upper`, `donchian_lower`, `donchian_mid`, `donchian_width`, `keltner_upper`, `keltner_lower`, `keltner_width`, `ichimoku_conversion`, `ichimoku_base`, `ichimoku_span_a`, `ichimoku_span_b`, `macd_line`, `stochastic_k`, `stochastic_d`, `adx`, `obv`, `volume_zscore`, `ts_weekday`, `ts_hour`, `ts_month`, `ts_day`, `lag`, `ewm_mean`, `rsi`, `rolling_min`, `rolling_max`, `rolling_mean`, `rolling_std`, `rolling_zscore`, `rolling_percentile_rank`, `rolling_skew`, `rolling_kurtosis`, `rolling_corr`, `rolling_beta`, `rolling_spread_zscore`, `tracking_error`, `information_ratio`, `rolling_autocorr`, `kelly_fraction`, `historical_var`, `expected_shortfall`
- flow/carry/liquidity/options-vol/on-chain/sentiment/event/fundamental/factor-ranking/execution-constraint/data-quality/ensemble/capacity: `order_flow_imbalance`, `liquidity_depth_ratio`, `spread_bps`, `funding_bps`, `carry_adjusted_return`, `vol_risk_premium`, `put_call_skew`, `liquidity_stress`, `net_exchange_flow`, `onchain_activity_ratio`, `sentiment_weighted_score`, `event_surprise`, `fundamental_value_gap`, `risk_adjusted_score`, `inverse_volatility_weight`, `cross_sectional_rank`, `cross_sectional_zscore`, `cross_sectional_demean`, `group_cross_sectional_rank`, `group_cross_sectional_zscore`, `group_cross_sectional_demean`, `queue_position_score`, `latency_penalty_bps`, `maker_taker_fee_edge_bps`, `borrow_cost_bps`, `borrow_availability_ratio`, `tax_drag_bps`, `rebalance_drift`, `freshness_score`, `staleness_bps`, `data_quality_blend`, `ensemble_vote_count`, `ensemble_vote_ratio`, `regime_transition_score`, `drawdown_from_peak`, `rolling_max_drawdown`, `drawdown_duration`, `turnover_pressure`, `capacity_usage_ratio`, `correlation_crowding_score`

time-series 系は `canonical_symbol` ごとに `ts` 順で評価します。`fill_null` を指定すると、初期 window やゼロ除算で出る null を指定値で埋めます。例えば breakout は `rolling_max` や `donchian_upper` で channel high を作り、`lag` で prior high にずらしてから現在 price と比較します。EMA crossover は `ewm_mean` で fast / slow EMA を作り、`value_column` で比較します。RSI mean reversion は `rsi` を作って oversold / overbought threshold と比較します。ATR volatility filter は `atr` を high / low / close columns から作って entry、hold、dynamic stop/target columns に使います。Bollinger 系は `window` と標準偏差倍率の `value`、未指定時 2.0 で upper / lower / width / percent_b を作り、band reversal、band breakout、volatility compression の条件に使えます。Keltner 系は close EMA center と ATR envelope を作ります。Ichimoku 系は conversion / base / span A / span B を作り、cloud breakout や trend filter に使えます。MACD は `macd_line` の `window` を fast span、`value` を slow span として作り、必要なら `ewm_mean` で signal line、`diff` で histogram を作れます。Stochastic は `stochastic_k` と `stochastic_d`、trend strength は `adx`、出来高確認は `obv` と `volume_zscore` を使います。Kelly / VaR 系は `kelly_fraction`, `historical_var`, `expected_shortfall` を rolling return column から作り、Kelly sizing、VaR filter、expected shortfall filter に使えます。`rolling_percentile_rank` は現在値が直近 window 内のどの分位にあるかを 0-1 で作り、extreme move / range exhaustion / breakout confirmation に使えます。`rolling_skew` と `rolling_kurtosis` は tail shape を作り、crash-risk filter、tail-risk hedge、non-normal regime filter に使えます。`rolling_max_drawdown` と `drawdown_duration` は equity curve や価格系列から path-dependent な最悪 drawdown と peak からの経過本数を作り、deep drawdown filter、recovery wait、risk-off regime に使えます。Calendar 系は `ts_weekday` を Monday=0、`ts_hour` を 0-23、`ts_month` を 1-12、`ts_day` を 1-31 として作ります。Cross-asset / pair 系は同じ row にある asset return と benchmark return などから `rolling_corr`, `rolling_beta`, `rolling_spread_zscore`, `tracking_error`, `information_ratio` を作り、benchmark confirmation、relative strength、pair spread normalization、active risk budget、information-ratio filter に使えます。`rolling_autocorr` は 1 列の自己相関を作り、trend persistence や mean-reversion regime filter に使えます。Flow / carry / liquidity / options-vol 系は order book size imbalance、depth ratio、quoted spread bps、funding cost bps、carry-adjusted return、implied-realized vol premium、put-call skew、spread/depth stress を作り、order-flow continuation、thin-liquidity exclusion、funding/carry filter、vol risk premium、skew hedge、on-chain flow filter、sentiment confirmation、event surprise、fundamental value gap、factor ranking、cross-sectional standardization、group-aware standardization、queue-position filter、latency-cost filter、maker-taker fee edge、borrow availability and cost、tax drag filter、rebalance drift、data freshness filter、source-quality blend、ensemble vote filter、regime transition filter、rolling drawdown filter / max-drawdown-duration filter、turnover pressure、capacity usage、correlation crowding 条件に使えます。

## Score

`rules.score.weighted_sum` は raw score を作ります。`rank_score` は raw score を `0.0` から `1.0` に clamp した値です。

```yaml
score:
  weighted_sum:
    - column: research_return_1d
      weight: 10
    - column: research_return_4h
      weight: 5
```

`rules.score.model_score` は paper-only の線形モデル adapter です。ここでは学習を実行しません。別途作った係数や手作業の係数を YAML に書き、feature column から score を作るだけです。`weighted_sum` と `model_score` を両方書いた場合は加算します。

```yaml
score:
  model_score:
    model_type: linear
    intercept: 0.1
    activation: sigmoid
    missing_value: 0.0
    coefficients:
      - column: research_return_1d
        weight: 20
      - column: source_confidence
        weight: 0.5
```

- `model_type` は v1 では `linear` だけです。
- `coefficients` は `column * weight` の線形和です。
- `intercept` は切片です。
- `activation` は `identity`, `sigmoid`, `tanh`, `clamp_0_1` に対応します。
- `missing_value` を指定すると、欠損や非数値 feature をその値で補います。未指定ならその係数項は無視します。
- 参照 column は `strategy-author-validate` で feature panel に存在するか確認されます。

線形係数は `strategy-author-train-model` でも作れます。これは feature panel だけを読む paper-only の ordinary least squares / ridge adapter です。外部モデル、pickle、任意 Python、live order は実行しません。

```bash
uv run sis strategy-author-train-model \
  --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml \
  --target-column target_forward_return \
  --feature-column research_return_1d \
  --feature-column source_confidence \
  --ridge-lambda 0.000001 \
  --out-spec data/research/trained_authoring_spec.yaml
```

出力は次です。

- `data/research/strategy_authoring_model_score.json`
- `--out-spec` を指定した場合は、`rules.score.model_score` を埋めた YAML spec

`target_column` は feature panel にある検証用 target column です。未来情報を含む target を使った spec は research/backtest 用に限定し、live 判断へ直接持ち込まないでください。

## Hold / Exit / Stop Loss

```yaml
rules:
  side: long
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: close_above_sma20
        op: is_true
  hold:
    any:
      - column: vix_level
        op: gte
        value: 30
  close:
    all:
      - column: exit_signal
        op: is_true
  reduce:
    all:
      - column: reduce_signal
        op: is_true
  add:
    all:
      - column: add_signal
        op: is_true
  exit:
    exit_on_close_signal: true
    exit_on_reduce_signal: true
    reduce_fraction: 0.5
    exit_on_add_signal: true
    add_fraction: 0.5
    exit_on_opposite_signal: true
    stop_loss_bps: 150
    take_profit_bps: 300
    trailing_stop_bps: 120
    trailing_stop_activation_bps: 0
    partial_take_profit_bps: 200
    partial_exit_fraction: 0.5
    min_holding_minutes: 120
    max_holding_minutes: 480
    exit_priority:
      - break_even_stop
      - stop_loss
      - partial_take_profit
      - take_profit
      - trailing_stop
      - time_stop
    stop_loss_bps_column: atr_stop_bps
    take_profit_bps_column: atr_take_profit_bps
  sizing:
    position_weight: 1.0
    notional_usd: 1000
    volatility_target: 0.20
    volatility_column: realized_vol
    max_volatility_scaled_position_weight: 1.5
  order:
    entry_type: limit
    limit_offset_bps: 25
    time_in_force: gtd
    timeout_minutes: 120
    post_only: true
  bracket:
    enabled: true
    bracket_type: oco
    break_even_after_bps: 100
    time_stop_minutes: 180
  portfolio:
    max_signals_per_timestamp: 3
    max_turnover_weight_per_timestamp: 1.0
    turnover_weight_column: planned_turnover_weight
    allocation_method: score_proportional
    target_total_position_weight: 1.0
    target_total_position_weight_column: target_weight_budget
    allocation_volatility_column: realized_vol
  risk_throttle:
    max_drawdown_column: strategy_drawdown
    max_drawdown_floor: -0.20
    max_drawdown_floor_column: row_drawdown_floor
    daily_loss_column: daily_pnl
    daily_loss_floor: -0.10
    daily_loss_floor_column: row_daily_loss_floor
    loss_streak_column: loss_streak
    max_loss_streak: 3
    max_loss_streak_column: row_max_loss_streak
    cooldown_minutes: 90
  data_guard:
    profile: strict
```

- `side: long` / `side: short` で買い・売りの方向を選べます。
- `side: auto` / `side_column` で、row ごとに long / short / hold を切り替えられます。explicit close は `rules.close` で出します。
- `hold` は「条件が悪いので見送り」を signal artifact に残します。
- `close` は「反対売買を開かずに閉じる」paper close signal を出します。`exit_on_close_signal` が true の entry は、次の close signal で仮想 exit します。
- `reduce` は「反対売買を開かずに一部だけ縮小する」paper reduce signal を出します。`exit_on_reduce_signal` が true の entry は、次の reduce signal で `reduce_fraction` 分を仮想 exit します。
- `add` は「新しい独立 trade ではなく既存 paper position に追加する」paper add signal を出します。`exit_on_add_signal` が true の entry は、次の add signal で `add_fraction` 分を追加入りします。
- `rebalance` は「新しい独立 trade ではなく既存 paper position を目標 exposure に寄せる」paper rebalance signal を出します。`exit_on_rebalance_signal` が true の entry は、次の rebalance signal で `rebalance_target_fraction` へ縮小または追加します。`rebalance_min_delta_fraction` / `rebalance_min_delta_fraction_column` を使うと、target と現在 exposure の差が小さい時は `rebalance_band_skip` として調整を見送れます。
- `stop_loss_bps: 150` は 1.5% 逆行で仮想損切します。
- `take_profit_bps: 300` は 3.0% 有利に動いたら仮想利確します。
- `min_reward_risk_ratio: 2.0` は、`take_profit_bps / stop_loss_bps` が 2.0 未満の候補を `reward_risk_ratio_too_low` として `side: none` に残します。stop / take のどちらかが欠ける場合は `reward_risk_ratio_missing` です。
- `min_reward_risk_ratio_column: required_reward_risk` を使うと、row ごとに必要な reward/risk 下限を変えられます。空なら固定 `min_reward_risk_ratio` へ fallback します。
- `exit_on_opposite_signal` は同じ symbol の反対シグナルで仮想 exit します。
- `exit_on_close_signal` は同じ symbol の explicit close signal で仮想 exit します。
- `exit_on_reduce_signal` は同じ symbol の explicit reduce signal で一部縮小します。`reduce_fraction_column` を使うと row ごとに縮小率を変えられます。
- `exit_on_add_signal` は同じ symbol の explicit add signal で増し玉します。`add_fraction_column` を使うと row ごとに追加率を変えられます。
- `exit_on_rebalance_signal` は同じ symbol の explicit rebalance signal で paper exposure を目標値へ近づけます。`rebalance_target_fraction_column` を使うと row ごとに目標 exposure を変えられます。
- `trailing_stop_bps` は含み益のピークからの戻り幅で仮想 exit します。`trailing_stop_activation_bps` / `trailing_stop_activation_bps_column` を使うと、有利方向の含み益が固定または row ごとの指定 bps に到達するまで trailing stop を発動しません。
- `partial_take_profit_bps` と `partial_exit_fraction` は、一部利確して残りを horizon / stop / trailing に回します。
- `min_holding_minutes` / `min_holding_minutes_column` は、固定または row ごとの指定分数に到達するまで stop / take / trailing / partial / close / reduce / add / rebalance / opposite / bracket time stop を paper-only に遅らせます。
- `exit_priority` は、同じ quote で stop / take / partial / trailing / break-even / time stop が同時に成立した場合の評価順です。既定は `break_even_stop`, `stop_loss`, `partial_take_profit`, `take_profit`, `trailing_stop`, `time_stop` です。
- `max_holding_minutes` / `max_holding_minutes_column` は、fixed horizon より手前でも固定または row ごとの指定分数に到達した最初の quote で残り position を `max_holding_time` として仮想 exit します。
- `bracket.enabled: true` は stop / take profit / time stop / break-even stop を OCO 的に paper 評価します。
- `*_bps_column` を指定すると、ATR やボラティリティから作った feature column で row ごとに損切・利確幅を変えられます。column 値が空の場合は固定値を fallback にします。
- `sizing.position_weight` は backtest return に掛ける paper weight です。`position_weight_column` で row ごとの重みも使えます。
- `sizing.notional_usd` は paper candidate に残す想定 notional です。live order には変換しません。
- `sizing.volatility_target` は `volatility_column` の値に応じて `position_weight` を `target / observed` で拡大縮小します。`max_volatility_scaled_position_weight` があれば上限で cap します。
- `order.entry_type: market` は signal 時刻以降の最初の quote で入る paper 評価です。
- `order.time_in_force` は `gtc`, `gtd`, `ioc`, `fok` から選べます。`gtd` は `timeout_minutes` 必須、`ioc` / `fok` は signal 時点の quote だけで約定判定します。
- `order.post_only: true` は limit entry 専用です。signal 時点で即時約定する marketable limit は `entry_order_post_only_would_cross` として paper-only に未約定扱いへ落とします。
- `portfolio.max_signals_per_timestamp` は同一 timestamp の trade signal を rank score 上位 N 件に絞ります。
- `portfolio.max_total_position_weight` / `max_total_position_weight_column` / `max_long_position_weight` / `max_long_position_weight_column` / `max_short_position_weight` / `max_short_position_weight_column` / `max_abs_net_position_weight` / `max_abs_net_position_weight_column` / `max_symbol_position_weight` / `max_symbol_position_weight_column` / `max_group_position_weight` / `max_group_position_weight_column` / `max_group_abs_net_position_weight` / `max_group_abs_net_position_weight_column` は同一 timestamp の paper exposure を制限します。`*_column` は timestamp ごとの上限です。同一 timestamp 内で非空値が複数あり、値が一致しない場合は validation error にします。空なら同名の固定値へ fallback します。超過候補は `side: none` と `portfolio_*_exposure_limit` の `block_reasons` に残ります。
- `portfolio.max_turnover_weight_per_timestamp` は同一 timestamp の paper turnover 使用量を制限します。`turnover_weight_column` がある場合はその絶対値、無い場合は `position_weight` の絶対値を使い、budget 超過候補は `portfolio_turnover_budget_limit` で見送ります。
- `portfolio.allocation_method: equal_weight` は同一 timestamp の採用候補へ `target_total_position_weight` または `target_total_position_weight_column` を均等配分します。
- `portfolio.allocation_method: score_proportional` は同一 timestamp の採用候補へ正の `raw_score` 比例で `target_total_position_weight` または `target_total_position_weight_column` を配分します。全 score が 0 以下または欠損なら均等配分へ fallback します。
- `portfolio.allocation_method: inverse_volatility` は `allocation_volatility_column` の正の値の逆数で `target_total_position_weight` または `target_total_position_weight_column` を配分します。全 volatility が 0 以下または欠損なら均等配分へ fallback します。
- `portfolio.target_total_position_weight_column` は timestamp ごとの allocation 予算です。同一 timestamp 内で非空値が複数あり、値が一致しない場合は曖昧なので validation error にします。空なら固定 `target_total_position_weight` へ fallback します。
- `portfolio.allocation_method: dollar_neutral` は long / short の gross weight が半分ずつになるように配分します。片側の候補しかない timestamp では、反対側の half target は使わず、その timestamp の exposure は半分に抑えられます。
- `portfolio.allocation_method: beta_neutral` は `allocation_beta_column` を使い、long beta exposure と short beta exposure が釣り合うように配分します。片側の beta が無い、0、または候補が片側だけの場合は dollar-neutral と同じ half target 配分へ fallback します。
- `portfolio.allocation_method: group_neutral` は `group_column` ごとに long / short gross weight が半分ずつになるように配分します。group が欠けた候補は neutral allocation 上は 0 weight になり、group exposure 制限と組み合わせると fail-closed で見送られます。
- `position.allow_pyramiding: false` は、同一 execution symbol の同方向 open state が残っている間の追加 entry を `position_pyramiding_not_allowed` として見送ります。
- `risk_throttle.profile` は `conservative` または `strict` で drawdown、daily loss、loss streak の既定 column と threshold を補完します。明示 field は preset より優先されます。`max_drawdown_floor_column` / `daily_loss_floor_column` / `max_loss_streak_column` を使うと、regime、symbol、strategy state ごとに停止閾値を row 値で変えられます。空なら固定 threshold へ fallback します。`cooldown_minutes` を指定すると、停止発生後の同一 symbol の後続候補も指定時間だけ `risk_throttle_cooldown` で止めます。止めた候補は `side: none` と `risk_throttle_*` の `block_reasons` に残ります。
- `data_guard.profile` は `none`, `fresh_only`, `quality_only`, `strict` から選べる paper-only preset です。`fresh_only` は `feature_age_minutes`、`quality_only` は `source_confidence` / `venue_quality_score`、`strict` は freshness、source/venue quality、`staleness_bps`、`regime_transition_score` を fail-closed に gate します。`max_feature_age_minutes_column` / `min_source_confidence_column` / `min_venue_quality_score_column` / `max_staleness_bps_column` / `max_regime_transition_score_column` を使うと、regime、venue、symbol ごとに data-quality threshold を row 値で変えられます。空なら固定 threshold へ fallback します。
- stop loss / take profit は paper backtest の評価条件です。本番発注の逆指値や利確注文は作りません。

## Regime Overrides

`rules.regime_overrides` で、market regime や volatility regime ごとに risk / sizing / execution parameter を切り替えられます。上から順に評価し、最初に一致した override を signal に反映します。

```yaml
rules:
  regime_overrides:
    - name: high_vol
      when:
        all:
          - column: vix_level
            op: gte
            value: 25
      stop_loss_bps: 90
      take_profit_bps: 180
      position_weight: 0.25
      slippage_bps: 40
      max_fill_fraction: 0.5
      min_fill_fraction: 0.25
```

override できる値:

- exit: `stop_loss_bps`, `take_profit_bps`, `trailing_stop_bps`, `trailing_stop_activation_bps`, `partial_take_profit_bps`, `partial_exit_fraction`
- sizing: `position_weight`, `notional_usd`
- execution: `slippage_bps`, `max_fill_fraction`, `min_fill_fraction`, `min_fill_fraction_column`, `max_spread_bps`, `max_spread_bps_column`, `min_depth_usd`, `min_depth_usd_column`, `depth_participation_rate`

一致した regime は `reason_codes` に `regime:<name>` として残ります。`*_column` がある場合は row の dynamic column 値が優先されます。

## Bracket / OCO Lifecycle

bracket は entry 後に複数の exit 条件を束ねて評価する paper-only lifecycle です。本物の bracket order や OCO order は発注しません。

```yaml
rules:
  exit:
    stop_loss_bps: 150
    take_profit_bps: 300
  bracket:
    enabled: true
    bracket_type: oco
    break_even_after_bps: 100
    break_even_after_bps_column: row_break_even_bps
    break_even_after_partial_take_profit: true
    time_stop_minutes: 180
    time_stop_minutes_column: row_time_stop_minutes
```

- `bracket_type: oco` は v1 で唯一の bracket type です。
- `stop_loss_bps` / `take_profit_bps` は先に到達したほうで exit し、`summary.exit_reason_counts.bracket_stop_loss` または `bracket_take_profit` に出ます。
- `break_even_after_bps` と `break_even_after_bps_column` は含み益が固定または row ごとの指定 bps 以上になった後、return が 0 以下へ戻ったら `bracket_break_even_stop` で exit します。
- `break_even_after_partial_take_profit: true` は、部分利確が成立した後、残り position が entry price 付近へ戻った時に `bracket_break_even_stop` で閉じます。`partial_take_profit_bps` / `partial_take_profit_bps_column` と `partial_exit_fraction` / `partial_exit_fraction_column` の組み合わせが必要です。
- `time_stop_minutes` と `time_stop_minutes_column` は entry quote から固定または row ごとの指定分数後以降の最初の quote で残り position を `bracket_time_stop` として閉じます。
- partial take profit と併用した場合、部分利確後の残り position が bracket stop / take / break-even / time stop の対象です。

## Order Style Entry

entry を成行相当だけでなく、limit / stop-market 相当で評価できます。これは paper-only の約定シミュレーションであり、本物の指値注文・逆指値注文は出しません。

```yaml
rules:
  order:
    entry_type: limit
    entry_type_column: order_type
    limit_offset_bps: 50
    limit_offset_bps_column: limit_offset
    stop_offset_bps_column: stop_offset
    time_in_force: gtd
    time_in_force_column: order_tif
    timeout_minutes: 120
    timeout_minutes_column: order_timeout_minutes
    post_only: true
    post_only_column: order_post_only
    reduce_only_column: reduce_only_order
```

- `entry_type: market` は signal 時刻以降の最初の quote で入ります。
- `entry_type: limit` は long なら基準 entry quote より `limit_offset_bps` だけ安い価格、short なら高い価格に到達した時だけ入ります。
- `entry_type: stop_market` は long なら基準 entry quote より `stop_offset_bps` だけ高い価格、short なら低い価格に到達した時だけ入ります。
- `entry_type_column` / `limit_offset_bps_column` / `stop_offset_bps_column` を使うと、row ごとに market / limit / stop-market と offset を変えられます。空の row は固定 `entry_type` / `limit_offset_bps` / `stop_offset_bps` へ fallback します。
- `time_in_force: gtc` は timeout が無ければ horizon 内の後続 quote まで待ちます。`timeout_minutes` を併用するとその時刻までです。
- `time_in_force: gtd` は `timeout_minutes` 必須で、その時刻までだけ待ちます。
- `time_in_force: ioc` / `fok` は signal 時点の quote だけで判定し、後続 quote を待ちません。quote 粒度の paper simulation なので部分約定数量までは区別しません。
- `time_in_force_column` / `timeout_minutes_column` を使うと、row ごとに GTC / GTD / IOC / FOK と待機期限を変えられます。空の row は固定 `time_in_force` / `timeout_minutes` へ fallback します。
- `post_only: true` は limit 専用です。即時約定する marketable limit は `entry_order_post_only_would_cross` として `summary.entry_order_unfilled_count` と `blocked_reason_counts` に出ます。
- `post_only_column` を使うと、maker-only にしたい row だけ post-only を有効化できます。空の row は固定 `post_only` へ fallback します。
- `reduce_only: true` または `reduce_only_column` が true の row は、新規 entry ではなく反対方向の未期限 open state だけを縮小する `side: reduce` marker に変換します。反対 open が無い場合は `position_reduce_only_without_opposing_open` として `side: none` に残します。
- `timeout_minutes` を過ぎても条件に届かない場合は未約定として `summary.entry_order_unfilled_count` と `blocked_reason_counts.entry_order_unfilled` に出ます。
- 約定した注文種別は `summary.entry_order_type_counts` に出ます。

## Execution Quality

slippage with row cost、partial fill with row fill、min-fill gate with row threshold、spread / depth / latency / queue-position / short borrow / tax drag / turnover / fee edge による venue microstructure 条件も paper-only で評価できます。これは約定品質の仮定を backtest に入れるだけで、実注文には変換しません。

```yaml
rules:
  execution:
    profile: conservative
    slippage_bps: 25
    max_fill_fraction: 0.5
    min_fill_fraction: 0.25
    max_spread_bps: 15
    min_depth_usd: 10000
    depth_column: min_side_depth_10bps_usd
    depth_participation_rate: 0.25
    max_latency_ms: 100
    latency_column: observed_latency_ms
    min_queue_position_score: 0.6
    min_queue_position_score_column: required_queue_score
    queue_position_score_column: queue_score
    min_borrow_availability_ratio: 0.5
    min_borrow_availability_ratio_column: required_borrow_available
    borrow_availability_column: borrow_available
    max_borrow_cost_bps: 25
    max_borrow_cost_bps_column: allowed_borrow_cost
    borrow_cost_column: borrow_cost
    max_tax_drag_bps: 20
    max_tax_drag_bps_column: allowed_tax_drag
    tax_drag_column: tax_drag
    max_turnover_pressure: 0.4
    max_turnover_pressure_column: allowed_turnover_pressure
    turnover_pressure_column: turnover_pressure
    max_capacity_usage_ratio: 0.6
    max_capacity_usage_ratio_column: allowed_capacity_usage
    capacity_usage_column: capacity_usage
    max_correlation_crowding_score: 0.7
    max_correlation_crowding_score_column: allowed_crowding
    correlation_crowding_column: correlation_crowding_score
    min_fee_edge_bps: 1
    min_fee_edge_bps_column: required_fee_edge
    fee_edge_column: fee_edge
```

- `profile` は `none`, `liquid_only`, `balanced`, `conservative` から選べる paper-only preset です。未指定の execution field だけを埋めるので、上の例のように `max_spread_bps` などを明示すると preset default よりその値を優先します。
- `liquid_only` は slippage / spread / depth の最低限の liquidity gate、`balanced` は latency / queue / turnover / capacity / crowding も含む標準 gate、`conservative` はより厳しい spread / depth / latency / queue / turnover / capacity / crowding / fee-edge gate を入れます。
- `slippage_bps` と `slippage_bps_column` は round trip の追加 drag として return から差し引き、`cost_drag_bps` に足します。column を使うと row ごとのコスト仮定に変えられます。
- `max_fill_fraction` と `max_fill_fraction_column` は約定した想定数量の割合です。`0.5` なら signal return は半分の exposure として評価されます。column を使うと row ごとの想定 fill に変えられます。
- `min_fill_fraction` と `min_fill_fraction_column` は、固定または row ごとの下限として `max_fill_fraction` と depth-based fill を掛けた有効約定率が小さすぎる trade を `execution_fill_fraction_too_low` として見送ります。
- `max_spread_bps` と `max_spread_bps_column` は entry quote の `spread_bps` が固定または row ごとの上限を超える場合に約定対象から外し、`blocked_reason_counts.microstructure_spread_too_wide` に記録します。
- `min_depth_usd` と `min_depth_usd_column` は entry quote の depth column が固定または row ごとの必要額未満なら約定対象から外します。column が無い場合は `microstructure_depth_missing`、額が足りない場合は `microstructure_depth_too_low` に記録します。
- `depth_column` は depth 判定に使う quote column です。省略時は `min_side_depth_10bps_usd` を使います。
- `depth_participation_rate` は depth のうち自分が取れる想定割合です。`notional_usd` がある場合、`depth * depth_participation_rate / notional_usd` で paper exposure をさらに縮小します。
- `max_latency_ms` と `max_latency_ms_column` は feature panel の latency column が固定または row ごとの上限を超える場合に約定対象から外し、欠損は `microstructure_latency_missing`、上限超過は `microstructure_latency_too_high` に記録します。
- `min_queue_position_score` と `min_queue_position_score_column` は feature panel の queue score が固定または row ごとの閾値未満なら約定対象から外し、欠損は `microstructure_queue_position_missing`、閾値未満は `microstructure_queue_position_too_low` に記録します。
- `min_borrow_availability_ratio` と `min_borrow_availability_ratio_column` は short signal の borrow availability が固定または row ごとの閾値未満なら見送り、`max_borrow_cost_bps` と `max_borrow_cost_bps_column` は short borrow cost の固定または row ごとの上限として使います。availability 欠損は `short_borrow_availability_missing`、不足は `short_borrow_availability_too_low`、cost 欠損は `short_borrow_cost_missing`、上限超過は `short_borrow_cost_too_high` に記録します。
- `max_tax_drag_bps` と `max_tax_drag_bps_column` は tax drag が欠損、または固定・row ごとの上限超過なら `tax_drag_missing` / `tax_drag_too_high` として約定対象から外します。
- `max_turnover_pressure` と `max_turnover_pressure_column` は turnover pressure が欠損、または固定・row ごとの上限超過なら `turnover_pressure_missing` / `turnover_pressure_too_high` として約定対象から外します。
- `max_capacity_usage_ratio` と `max_capacity_usage_ratio_column` は capacity usage が欠損、または固定・row ごとの上限超過なら `capacity_usage_missing` / `capacity_usage_too_high` として約定対象から外します。
- `max_correlation_crowding_score` と `max_correlation_crowding_score_column` は correlation crowding が欠損、または固定・row ごとの上限超過なら `correlation_crowding_missing` / `correlation_crowding_too_high` として約定対象から外します。
- `min_fee_edge_bps` と `min_fee_edge_bps_column` は fee edge が欠損、または固定・row ごとの閾値未満なら `fee_edge_missing` / `fee_edge_too_low` として約定対象から外します。負値の fee edge も扱えます。
- partial fill with row fill と depth-based fill は `position_weight` と掛け合わされます。`min_fill_fraction` または `min_fill_fraction_column` は `max_fill_fraction` / `max_fill_fraction_column` と depth-based fill を掛けた有効約定率の下限として使います。

## Temporal / Cadence Controls

曜日、時間帯、同一銘柄の cooldown、銘柄別の日次上限を指定できます。intraday、session filter、rebalance cadence、overtrade 防止の最小形です。

```yaml
rules:
  temporal:
    allowed_weekdays_utc: [0, 1, 2, 3, 4]
    allowed_hours_utc: [14, 15, 16, 17, 18, 19, 20]
    cooldown_minutes: 240
    max_signals_per_symbol_per_day: 2
```

- `allowed_weekdays_utc` は UTC の曜日です。`0` が月曜、`6` が日曜です。
- `allowed_hours_utc` は UTC の時です。`14` は 14:00 UTC 台です。
- `cooldown_minutes` は同じ execution symbol で前回採用 signal から指定分数未満の候補を見送ります。
- `max_signals_per_symbol_per_day` は同じ execution symbol の 1 日あたり採用上限です。
- 見送られた候補は削除せず、`side: none` と `block_reasons` に `temporal_weekday_filter`, `temporal_hour_filter`, `temporal_cooldown`, `temporal_symbol_daily_limit` のいずれかを残します。
- `optimizer.parameter_sweep` で `rules.temporal.cooldown_minutes` と `rules.temporal.max_signals_per_symbol_per_day` を比較できます。

## Position State / Pyramiding Controls

同一 execution symbol の仮想 open signal 数や open weight を制限できます。no-overlap、pyramiding 上限、同一銘柄の重複 entry 防止の paper-only selection rule です。

```yaml
rules:
  position:
    max_open_signals_per_symbol: 1
    max_open_position_weight_per_symbol: 1.0
    holding_horizon_minutes: 480
    require_open_position_for_markers: true
    allow_opposing_open_positions: false
```

- `max_open_signals_per_symbol` は同一 execution symbol で同時に open とみなす signal 数の上限です。`1` なら同じ symbol の重複保有を禁止します。
- `max_open_position_weight_per_symbol` は同一 execution symbol の open `position_weight` 合計上限です。
- `holding_horizon_minutes` を省略すると `backtest.label_horizon_minutes` を使います。
- `close` marker は仮想 open state を消し、`reduce` marker は `reduce_fraction` 分を減らし、`add` marker は `add_fraction` 分を増やし、`rebalance` marker は `rebalance_target_fraction` へ寄せます。
- `require_open_position_for_markers: true` にすると、仮想 open state が無い `close` / `reduce` / `add` / `rebalance` marker は `position_marker_without_open` として見送ります。
- `allow_opposing_open_positions: false` にすると、未期限の long がある時の short entry、または short がある時の long entry を `position_opposing_open_position` として見送ります。
- 見送られた候補は削除せず、`side: none` と `position_open_signal_limit` / `position_open_weight_limit` / `position_marker_without_open` / `position_opposing_open_position` の `block_reasons` に残します。
- これは paper signal selection の仮想保有状態であり、実 portfolio position や broker position を読みません。

## Event Windows / Calendar Filters

イベント時刻 column を使い、イベント前後だけ売買を許可する、またはイベント前後を blackout できます。決算前、重要指標発表、rebalance window、event-driven strategy の paper-only filter です。

```yaml
rules:
  event_windows:
    - name: earnings_pre
      event_ts_column: earnings_ts
      mode: allow
      before_minutes: 60
      after_minutes: 0
      block_reason: event_pre_earnings
    - name: macro_blackout
      event_ts_column: macro_ts
      mode: block
      before_minutes: 30
      after_minutes: 30
```

- `event_ts_column` は feature panel の timestamp column です。`datetime` または ISO 8601 string を使えます。
- `mode: allow` は `event_ts - before_minutes` から `event_ts + after_minutes` の範囲内だけを売買対象にします。範囲外は `<block_reason>_outside`、event 欠損は `<block_reason>_missing` で見送ります。
- `mode: block` は範囲内を見送ります。event 欠損は block しません。
- 見送られた候補は削除せず、`side: none` と `block_reasons` に理由を残します。
- event window は entry / side 判定後、multi-leg 展開前に評価します。

## Optimizer / Walk Forward

```yaml
backtest:
  split_method: walk_forward
  era_unit: week
optimizer:
  parameter_sweep:
    rules.exit.stop_loss_bps: [100, 150, 200]
    rules.sizing.position_weight: [0.5, 1.0]
  selection_metric: total_return
  selection_direction: maximize
  max_variants: 16
```

- `split_method: walk_forward` / `purged_walk_forward` は `summary.walk_forward_eras` に era 別 metrics を残します。multi-leg の場合は era ごとの `multi_leg_group_metrics` も残ります。
- `optimizer.parameter_sweep` は許可された spec path だけを grid search します。
- `optimizer.selection_metric` は `total_return` のような aggregate metric だけでなく、`multi_leg_group_metrics.total_return` のような variant summary 内の dotted path も使えます。
- `optimizer.selection_direction` は `maximize` / `minimize` / `auto` を選べます。`auto` は lower-is-better な metric を `minimize`、それ以外を `maximize` として解決し、`summary.optimizer.resolved_selection_direction` に残します。
- 結果は `strategy_backtest_metrics.json` の `summary.optimizer.variants` と `summary.optimizer.best_variant` に出ます。multi-leg variant では各 variant と best variant にも `multi_leg_group_metrics` が入ります。
- optimizer は任意 Python、任意式、外部API、live order を実行しません。

## Strategy Scorecard

`strategy-author-run --through backtest` は `data/research/strategy_backtest_metrics.json` の `summary.strategy_scorecard` に、使った `derived_features`、side counts、reason code counts、block reason counts、execution block reasons、exit reasons、pass/fail thresholds、multi-leg の compact group metrics を集約します。これは「どの feature と制約が strategy の通過・棄却に効いたか」を確認する paper-only explanation artifact です。実行済み signal の詳細診断が必要な場合は `summary.executed_signal_results` を使えますが、通常の結果確認は `summary.executed_signal_summary` の compact counts / returns / notional を優先します。

`--through paper-preview` では同じ情報が `TrialRecord.metrics.strategy_scorecard` と `PromotionDecision.scorecard_summary` にも残ります。multi-leg の場合、`scorecard_summary.multi_leg_group_metrics` には `groups[]` を除いた compact summary として group 数、complete / incomplete group 数、expected / executed leg 数、total return、average group return、win rate、worst group return、max drawdown、profit factor、average leg return imbalance、cost drag が入ります。profit factor は loss group が無い場合は JSON-safe に `null` です。promotion が `promote` され、かつ selected candidate が venue-suitable な通常 CLI 経路では、`PaperIntentPreview.scorecard_summary` にも引き継がれます。既定 `hold` や venue suitability block では intent は空配列ですが、なぜ止めたかは scorecard、rejection reason、candidate-level `block_reasons` で追えます。

## Cross Sectional Rotation

同一 timestamp の複数 symbol 候補を score で相対順位化し、上位を long、下位を short にできます。relative strength、top-bottom、sector rotation、pairs-like spread signal の最小形です。

```yaml
rules:
  side: auto
  entry:
    all:
      - column: trade_allowed
        op: is_true
  cross_sectional:
    long_top_n: 2
    short_bottom_n: 2
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
```

- `long_top_n` は timestamp 内の score 上位 N 件を `side: long` にします。
- `short_bottom_n` は timestamp 内の score 下位 N 件を `side: short` にします。
- `long_top_fraction` / `short_bottom_fraction` は universe size に応じて上位 / 下位 tail を割合で選びます。
- `group_column` を指定すると sector / theme / asset class ごとの top-bottom rotation にできます。
- `min_candidates`, `min_long_score`, `max_short_score` で、小さすぎる group や弱い tail を見送れます。
- 選ばれなかった中間候補は `side: none`、`block_reasons: ["cross_sectional_rank_filter"]` として artifact に残り、backtest からは除外されます。
- `rank_score` / `percentile_rank` は timestamp 内順位から再計算されます。
- `optimizer.parameter_sweep` で `rules.cross_sectional.long_top_n`, `short_bottom_n`, `long_top_fraction`, `short_bottom_fraction`, `min_candidates`, `min_long_score`, `max_short_score` を比較できます。

## Multi-Leg / Pair Trade

`rules.multi_leg` は anchor symbol の entry 判定を 1 回だけ行い、同じ timestamp に複数 leg の paper signal を展開します。pair trade、hedge、basket entry の最小形です。実 portfolio rebalance や live multi-leg order は発注しません。

```yaml
experiment:
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
rules:
  side: long
  entry:
    all:
      - column: spread_z
        op: gt
        value: 1
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 0.6
        reason_code: long_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.4
        stop_loss_bps: 140
        take_profit_bps: 260
        trailing_stop_bps: 110
        partial_take_profit_bps: 160
        partial_exit_fraction: 0.25
        # Optional: use feature columns for dynamic hedge ratio / leg notional / leg exits.
        # position_weight_column: hedge_ratio
        # notional_usd_column: hedge_notional_usd
        # stop_loss_bps_column: hedge_stop_bps
        # take_profit_bps_column: hedge_take_bps
        # partial_exit_fraction_column: hedge_partial_fraction
        # entry_type: limit
        # limit_offset_bps_column: hedge_limit_offset_bps
        # time_in_force_column: hedge_tif
        # timeout_minutes_column: hedge_timeout_minutes
        # post_only_column: hedge_post_only
        # slippage_bps_column: hedge_slippage_bps
        # max_fill_fraction: 0.5
        # min_fill_fraction_column: hedge_min_fill
        # max_spread_bps_column: hedge_spread_cap
        # max_latency_ms: 80
        # latency_column: hedge_latency_ms
        # min_queue_position_score_column: hedge_queue_required
        # queue_position_score_column: hedge_queue_score
        reason_code: hedge_leg
  sizing:
    position_weight: 2.0
    notional_usd: 1000
```

- `anchor_real_market_symbol` の feature row だけが entry / hold / score 判定に使われます。
- `legs[].real_market_symbol` は `experiment.symbol_bindings` に存在する必要があります。
- `side: same` は anchor の signal side と同じ方向、`side: opposite` は反対方向です。固定の `long` / `short` も使えます。
- leg の `position_weight` は global `sizing.position_weight` に掛けられます。
- leg の `position_weight_column` を指定すると、feature row の値を row ごとの hedge ratio / leg multiplier として使います。値が欠損なら固定 `position_weight` に fallback します。
- leg の `notional_usd` が未指定なら、global `sizing.notional_usd * leg.position_weight` を使います。
- leg の `notional_usd_column` を指定すると、feature row の値をその leg の想定 notional として使います。値が欠損なら固定 `notional_usd`、それも無ければ global notional と leg weight の積に fallback します。
- leg ごとに `stop_loss_bps`, `min_stop_loss_bps`, `max_stop_loss_bps`, `take_profit_bps`, `min_take_profit_bps`, `max_take_profit_bps`, `trailing_stop_bps`, `trailing_stop_activation_bps`, `partial_take_profit_bps`, `partial_exit_fraction`, `min_reward_risk_ratio` を固定値または同名の `_column` で上書きできます。未指定の field は通常の `rules.exit` / `regime_overrides` へ fallback します。
- leg ごとに `entry_type`, `limit_offset_bps`, `stop_offset_bps`, `time_in_force`, `timeout_minutes`, `post_only`, `reduce_only` を固定値または同名の `_column` で上書きできます。未指定の field は通常の `rules.order` へ fallback します。
- leg ごとに `slippage_bps`, `max_fill_fraction`, `min_fill_fraction`, `max_spread_bps`, `min_depth_usd`, `depth_participation_rate`, `max_latency_ms`, `min_queue_position_score`, `min_borrow_availability_ratio`, `max_borrow_cost_bps`, `max_tax_drag_bps`, `max_turnover_pressure`, `max_capacity_usage_ratio`, `max_correlation_crowding_score`, `min_fee_edge_bps` と同名の `_column`、および `depth_column`, `latency_column`, `queue_position_score_column`, `borrow_availability_column`, `borrow_cost_column`, `tax_drag_column`, `turnover_pressure_column`, `capacity_usage_column`, `correlation_crowding_column`, `fee_edge_column` を leg ごとに上書きできます。未指定の field は通常の `rules.execution` / `regime_overrides` へ fallback します。
- 展開された leg には `multi_leg_group_id`, `multi_leg_leg_index`, `multi_leg_leg_count`, `multi_leg_anchor_real_market_symbol` が付くため、pair / hedge / basket の同時発生 leg を artifact 上で束ねて追跡できます。
- 各 leg は通常の `strategy_signal.v1` として出るため、paper backtest では leg ごとの評価を維持します。加えて `strategy_backtest_metrics.json` の `summary.multi_leg_group_metrics` に group 数、complete / incomplete group 数、expected / executed leg 数、group 合算 return / average group return / win rate / worst group return / max drawdown / profit factor / average leg return imbalance / total notional / notional-weighted signal return / cost drag、group ごとの average leg return、leg return imbalance、notional-weighted return、`exit_reason_counts` が入ります。`notional_weighted_total_return` は実行済み leg の `signal_return` を `notional_usd` で重み付けした paper metric です。既存 `total_return` は leg の `signal_return` 合算のままです。

## Multi Strategy Bundle

複数の authoring YAML をまとめて paper-only portfolio として比較できます。

```bash
uv run sis strategy-author-bundle-run \
  --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
```

notional-aware な pair / hedge bundle を試す場合は次を使います。

```bash
uv run sis strategy-author-run \
  --spec docs/strategy_research_lab/examples/pair_hedge_notional_authoring_spec.yaml \
  --through backtest
uv run sis strategy-author-bundle-run \
  --bundle docs/strategy_research_lab/examples/notional_pair_hedge_bundle.yaml
```

```yaml
schema_version: strategy_authoring_bundle.v1
bundle_id: user_multi_strategy_v1
members:
  - spec_path: trend_pullback_authoring_spec.yaml
    allocation_weight: 0.7
  - spec_path: mean_reversion_authoring_spec.yaml
    allocation_weight: 0.3
portfolio:
  allocation_method: fixed_weight
  max_total_allocation_weight: 1.0
  selection_metric: total_return
  selection_direction: maximize
```

出力は次です。

- `data/research/strategy_authoring_bundle_result.json`
- `data/reports/strategy_authoring_bundle_report.md`

`portfolio.selection_metric` は `total_return` のような aggregate metric に加えて、`multi_leg_group_metrics.total_return` のような member summary 内の dotted path も使えます。pair / hedge / basket member を bundle 比較する場合は group-level return や complete group 数で best member を選べます。`portfolio.selection_direction` は `maximize` / `minimize` / `auto` を選べます。`auto` は `cost_drag_bps`、`incomplete_group_count`、`*_imbalance`、rejected / blocked / unfilled 系 count など lower-is-better な metric を自動で `minimize` として解決し、それ以外は `maximize` として扱います。解決後の方向は result JSON の `portfolio.resolved_selection_direction` に残ります。bundle 全体の `aggregate_metrics.multi_leg_group_metrics` には、member の effective allocation weight を掛けた weighted group return / notional-weighted return / cost drag / win rate / max drawdown / profit factor / leg imbalance、bundle 全体の total notional、group 数、complete / incomplete group 数、expected / executed leg 数も残ります。`strategy_authoring_bundle_report.md` にも `## Multi-Leg Group Metrics`、group completion rate、total notional、weighted notional return、weighted win rate、worst group return、weighted max drawdown、weighted profit factor、weighted average leg imbalance、member 別 weighted group return / weighted notional return / total notional / weighted win rate / weighted max drawdown / weighted leg imbalance が出ます。

`docs/strategy_research_lab/examples/notional_pair_hedge_bundle.yaml` は `portfolio.selection_metric: multi_leg_group_metrics.notional_weighted_total_return` と `selection_direction: auto` を使うため、pair / hedge member を notional-weighted return で比較できます。各 member spec は `position_weight_column` と `notional_usd_column` により、feature row の hedge ratio と hedge notional を leg に反映します。

bundle は各 member spec を個別に validate / signal build / backtest し、`effective_allocation_weight` と `weighted_total_return` を集約します。これは paper-only の比較であり、実ポートフォリオ注文や live rebalance は行いません。

`portfolio.allocation_method` は次を選べます。

- `fixed_weight`: `members[].allocation_weight` を使います。
- `equal_weight`: enabled member を同じ重みにします。
- `risk_parity`: member の paper `max_drawdown` を risk proxy として、drawdown が小さい member に大きめの重みを配ります。

どの方式でも `max_total_allocation_weight` があれば合計 exposure が cap を超えないよう比例縮小します。

## Strategy Patterns

現在の authoring DSL で表現しやすい戦略カテゴリです。いずれも live order ではなく paper-only signal / backtest です。

- trend following: `close_above_sma20`, `research_return_1d`, `adx`, `macd_line` などを entry に使う。
- mean reversion: `rsi`, `zscore`, `distance_from_ma`, `bollinger_percent_b` などを entry に使う。
- breakout: `new_high`, `range_breakout`, `donchian_upper`, `volume_spike`, `volume_zscore` などを entry に使う。
- volatility filter: `vix_level`, `atr_pct`, `realized_vol` を hold または entry に使う。
- long/short rotation: `side: auto` と `side_column` で方向を feature から選ぶ。
- pair / hedge style signal: `rolling_spread_zscore`, `rolling_corr`, `rolling_beta`, `tracking_error`, `information_ratio` で spread normalization、benchmark confirmation、active risk budget、information-ratio filter を作り、`side: auto` または `cross_sectional` で long / short を切り替える。
- exclusion / blackout rules: `entry.none`, `hold.none`, `long_entry.none`, `short_entry.none` で「どれにも該当しない時だけ」を直接書く。
- moving-average cross / adaptive threshold: `value_column` で `fast_ma > slow_ma` や `score > dynamic_threshold` を直接書く。
- local feature derivation: `derived_features` で spread、ratio、true range、ATR、Bollinger bands、Donchian channels、Keltner channels、Ichimoku cloud、MACD line、stochastic K/D、ADX、OBV、volume z-score、calendar features、rolling correlation / beta / spread z-score / tracking error / information ratio、order-flow imbalance、liquidity depth ratio、spread bps、funding bps、carry-adjusted return、volatility risk premium、put-call skew、liquidity stress、net exchange flow、on-chain activity ratio、sentiment weighted score、event surprise、fundamental value gap、risk-adjusted score、inverse volatility weight、cross-sectional rank、cross-sectional z-score / demean、group cross-sectional rank / z-score / demean、queue position score、latency penalty bps、maker-taker fee edge、borrow cost bps、borrow availability ratio、tax drag bps、rebalance drift、freshness score、staleness bps、data quality blend、ensemble vote count/ratio、regime transition score、drawdown from peak、rolling max drawdown、drawdown duration、turnover pressure、capacity usage ratio、correlation crowding score、lag、EMA、RSI、rolling min/max/mean/z-score/percentile-rank/skew/kurtosis を YAML 内で作る。
- explicit pair / hedge: `multi_leg` で anchor signal から long leg と short leg を同時に出し、leg ごとに固定または row-level の stop / take / trailing / partial exit 幅、order style、execution quality を変える。同じ anchor から展開された leg は `multi_leg_group_id` で追跡でき、backtest summary の `multi_leg_group_metrics` で pair / basket 単位の合算も確認できる。
- regime filter: `in` / `not_in` で bull、bear、event day などのカテゴリを entry / hold に使う。
- regime-specific risk: `regime_overrides` で high volatility 時だけ損切幅、利確幅、weight、slippage や row slippage を変える。
- cross-sectional top-bottom: `cross_sectional.long_top_n` / `short_bottom_n` で同時刻の上位 long・下位 short を作る。
- event window / calendar filter: `event_windows` で event 前後だけ許可、または event 前後を blackout する。
- session / rebalance cadence: `temporal` で曜日・時間帯・cooldown・日次上限を指定する。
- rebalance band: `rebalance_min_delta_fraction` や `rebalance_min_delta_fraction_column` で、小さすぎる drift の paper rebalance を抑制する。
- no-overlap / pyramiding cap: `position.max_open_signals_per_symbol` / `max_open_position_weight_per_symbol` / `allow_pyramiding` で同一銘柄の仮想 open exposure と同方向の増し玉可否を制限する。
- dynamic risk: `stop_loss_bps_column` / `take_profit_bps_column` に ATR・volatility 由来の bps を入れる。
- reward/risk gate: `min_reward_risk_ratio` と `min_reward_risk_ratio_column` で take profit 幅が stop loss 幅に対して小さすぎる候補を抑制する。
- staged exit: `partial_take_profit_bps` と `partial_exit_fraction` で部分利確を評価する。
- minimum hold: `min_holding_minutes` / `min_holding_minutes_column` で最低保有時間までは早期 exit を抑える。
- maximum hold: `max_holding_minutes` / `max_holding_minutes_column` で固定 horizon より前に時間切れ exit する。
- exit priority: `exit_priority` で同時成立した exit 条件の評価順を固定する。
- bracket / OCO lifecycle: `bracket.enabled` / `time_stop_minutes_column` / `break_even_after_bps_column` で stop / take / row-level break-even / partial-profit break-even / row-level time stop を束ねて評価する。
- trailing stop: `trailing_stop_bps` と `trailing_stop_activation_bps` で、利益が一定幅乗った後だけ戻りで抜ける条件を評価する。
- signal reversal: `exit_on_opposite_signal` で反対売買シグナルによる close / reversal を評価する。
- order style: `order.entry_type` で market / limit / stop-market entry を評価する。
- execution quality: `execution.profile` / `execution.slippage_bps` / `slippage_bps_column` / `max_fill_fraction` / `max_fill_fraction_column` / `min_fill_fraction` / `min_fill_fraction_column` / `max_spread_bps` / `max_spread_bps_column` / `min_depth_usd` / `min_depth_usd_column` / `max_latency_ms` / `max_latency_ms_column` / `min_queue_position_score` / `min_queue_position_score_column` / `min_borrow_availability_ratio` / `min_borrow_availability_ratio_column` / `max_borrow_cost_bps` / `max_borrow_cost_bps_column` / `max_tax_drag_bps` / `max_tax_drag_bps_column` / `max_turnover_pressure` / `max_turnover_pressure_column` / `max_capacity_usage_ratio` / `max_capacity_usage_ratio_column` / `max_correlation_crowding_score` / `max_correlation_crowding_score_column` / `min_fee_edge_bps` / `min_fee_edge_bps_column` で preset、滑り、row slippage、部分約定、min-fill gate with row threshold、spread gate with row threshold、depth gate with row threshold、depth-based fill、latency gate with row threshold、queue-position gate with row threshold、short-borrow availability/cost gate with row threshold、tax drag / turnover pressure / capacity / crowding / fee-edge with row threshold を評価する。
- risk parity / conviction sizing: `position_weight_column` に volatility inverse や confidence weight を入れる。
- volatility targeting: `sizing.volatility_target` / `volatility_column` で row ごとの paper exposure を目標ボラへ合わせる。
- drawdown / loss throttle: `risk_throttle.profile` / `risk_throttle` で drawdown、daily loss、loss streak が悪化した時に固定または row-level threshold で新規 entry を止め、`cooldown_minutes` で停止後の再開待ちを表現する。
- portfolio throttle: `portfolio.max_signals_per_timestamp` と `portfolio.max_turnover_weight_per_timestamp` で同時候補数を制限する。
- parameter sweep: `optimizer.parameter_sweep` で損切幅、利確幅、weight、horizon などを比較する。
- walk-forward review: `backtest.split_method` と `era_unit` で era 別の安定性を見る。
- multi-strategy portfolio: `strategy_authoring_bundle.v1` で複数 spec を allocation weight 付きで比較する。
- risk-parity portfolio: bundle の `allocation_method: risk_parity` で paper drawdown proxy による配分を比較する。

## Safety Boundary

この authoring flow は paper-only research です。

- live order は送信しない
- wallet は使わない
- exchange write は行わない
- profitability claim は出さない
- `paper-preview` でも最新 quote による本番発注はしない
