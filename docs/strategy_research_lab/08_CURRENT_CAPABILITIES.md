<!--
作成日: 2026-05-30_14:13 JST
更新日: 2026-06-11_21:34 JST
-->

# Current Capabilities

この文書は、2026-06-09 時点の Strategy Research Lab で実際にできることを記録します。

正本はコードです。特に `src/sis/commands/research.py`, `src/sis/research/strategy_lab/`, `src/sis/research_protocol/`, `src/sis/paper/runner.py`, `tests/test_strategy_lab_commands.py` を優先します。

より具体的な説明と専門用語の言い換えは [08_CURRENT_CAPABILITIES_EXPLAINED.html](08_CURRENT_CAPABILITIES_EXPLAINED.html) で読めます。

ユーザーが YAML で作れる売買ロジック、buy / sell signal、hold、損切、portfolio / execution 制約、未実装領域の整理は [11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md](11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md) で確認できます。

今回までに追加・整理した Strategy Authoring 機能、execution quality gate、paper-only 境界、検証済み状態は [12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md](12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md) で確認できます。

生成しうる strategy archetype ごとの対応状況、DSL surface、証拠 test、paper-only 境界は [13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md](13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md) で確認できます。

## 結論

今の Strategy Research Lab は、登録済み generator または `StrategyExperimentSpec` YAML/JSON から signal artifact を作り、paper-only の trial / candidate / promotion / intent preview まで進められます。加えて、`strategy_authoring_spec.v1` YAML から宣言型 rule を signal artifact / fixed-horizon backtest / paper-preview artifact へ進められます。

`execution_venue` は current contract では `trade_xyz` と `bitget_demo` を許可します。`bitget_demo` は demo execution 検証用であり、Bitget production live や外部 API 接続成功を意味しません。最短の backtest-first 入口は local baseline seed です。

NDX/QQQ family は research/backtest artifact として保持できますが、現行 paper path では venue suitability gate により selected candidate、paper intent、raw `paper-from-intents` JSON、legacy `paper-step` order generation で止まります。これは Strategy Lab export や alpha 否定ではなく、paper routing 不許可の境界です。

ただし、これは live-ready 証明ではありません。現行 authoring backtest は fixed-horizon の研究用 metrics であり、paper weight / notional は扱えますが、wallet / signing / exchange write は含みません。

## できるようになったこと

### 1. 登録済み generator から signal artifact を作れる

```bash
uv run sis strategy-preview
uv run sis strategy-preview --generator-id sp500_trend_rates_vix
```

できること:

- default generator `qqq_trend_rates_vix` で `XYZ100 -> QQQ` の Strategy Lab signal artifact を作れる。
- registered generator `sp500_trend_rates_vix` で `SP500 -> SPY` の signal artifact を作れる。
- no-signal 時も empty schema 付き `strategy_signals.parquet` と `strategy_signal_manifest.json` を残せる。
- legacy export `data/research/signals.csv` も出るが、Strategy Lab の正本は `data/research/strategy_signals.parquet`。

主要 artifact:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signal_manifest.json`
- `data/research/strategy_signals.jsonl`
- `data/research/signals.csv`
- `data/reports/strategy_signals_preview.md`

### 1.1. StrategyExperimentSpec YAML/JSON から signal artifact を作れる

```bash
uv run sis strategy-experiment-run --spec path/to/strategy_experiment.yaml
```

できること:

- `StrategyExperimentSpec` の `generator_id` で登録済み generator を選べる。
- `strategy_id`, `strategy_family`, `strategy_version`, `symbol_bindings` は spec 側の値を signal artifact / manifest lineage に反映する。
- `parameter_grid` は cartesian 展開され、各 variant の signal に `parameter_hash` と `parameter_grid:<hash>` reason code が付く。
- built-in generator の `qqq_trend_rates_vix` と `sp500_trend_rates_vix` は `min_source_confidence`, `max_vix_level` / `vix_gate`, `min_research_return_1d`, `timeframe` を signal 条件または出力 timeframe として消費できる。
- `--max-variants` で grid 爆発を止められる。未登録 generator、空の grid value、variant 上限超過は exit code 2 で止まる。
- paper-only artifact を作るだけで、live order / wallet / exchange write は実行しない。

### 1.5. YAML でユーザー定義 rule を作れる

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/notional_pair_hedge_bundle.yaml
```

外部 API なしで最初の baseline backtest を通す場合:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

できること:

- `strategy_authoring_spec.v1` YAML で entry 条件、hold 条件、explicit close / reduce / add / rebalance 条件、side、`side: auto`、timeframe、score、paper-only 線形 `model_score` / train-model adapter、temporal / cadence control、event-window calendar filters、bracket-OCO lifecycle with row-level break-even/time-stop、backtest horizon を書ける。
- `strategy-backtest-acceptance` で `strategy_backtest_metrics.json` の `backtest_passed`、min trade count、threshold、paper-only boundary を local artifact として判定できる。
- `rules.side_column`, `long_entry`, `short_entry`, `close`, `reduce`, `add`, `rebalance` で row ごとの long / short / hold / close / reduce / add / rebalance marker を出せる。
- condition DSL は固定値比較、列同士の比較、`between`、`in` / `not_in`、`none` exclusion group に対応し、moving average cross、adaptive threshold、regime filter を直接書ける。
- `rules.derived_features` で spread、ratio、true range、ATR、Bollinger bands、Donchian channels、Keltner channels、Ichimoku cloud、MACD line、stochastic K/D、ADX、OBV、volume z-score、calendar features、rolling correlation / beta / spread z-score / tracking error / information ratio、Kelly fraction、historical VaR、expected shortfall、order-flow imbalance、liquidity depth ratio、spread bps、funding bps、carry-adjusted return、volatility risk premium、put-call skew、liquidity stress、net exchange flow、on-chain activity ratio、sentiment weighted score、event surprise、fundamental value gap、risk-adjusted score、inverse volatility weight、cross-sectional rank、cross-sectional z-score / demean、group cross-sectional rank / z-score / demean、queue position score、latency penalty bps、maker-taker fee edge、borrow cost bps、borrow availability ratio、tax drag bps、rebalance drift、freshness score、staleness bps、data quality blend、ensemble vote count/ratio、regime transition score、drawdown from peak、rolling max drawdown、drawdown duration、turnover pressure、capacity usage ratio、correlation crowding score、lag、EMA、RSI、rolling min/max/mean/std/z-score/percentile-rank/skew/kurtosis などの strategy-local feature を YAML 内で作れ、EMA crossover / MACD trend-following / stochastic oscillator / ADX trend-strength / RSI mean-reversion / Kelly sizing / VaR filter / expected shortfall filter / Ichimoku cloud breakout / Donchian breakout / Keltner envelope / Bollinger band reversal / band breakout / volume-confirmed breakout / cross-asset confirmation / benchmark-relative strength / pair spread normalization / tracking-error budget / information-ratio filter / order-flow continuation / thin-liquidity exclusion / funding-carry filter / volatility risk premium / skew hedge / on-chain flow filter / sentiment confirmation / event surprise / fundamental value gap / factor ranking / group-aware factor normalization / queue-position filter / latency-cost filter / maker-taker fee edge / borrow availability and cost / tax drag filter / rebalance drift / data freshness filter / source-quality blend / ensemble vote filter / regime transition filter / rolling drawdown filter / max-drawdown-duration filter / turnover pressure / capacity usage / correlation crowding / seasonality filter / intraday session filter / volatility compression / volatility breakout / percentile-rank exhaustion / tail-shape regime filter / channel / momentum 条件を任意 Python なしで表現できる。
- `rules.multi_leg` で anchor signal から複数 long / short leg を同時 timestamp の paper signal として展開でき、leg ごとの hedge ratio / notional は固定値または feature column で動的に指定できる。leg ごとの stop / take / trailing / partial exit 幅、order style、execution quality も固定値または feature column で上書きでき、同じ anchor から出た leg 群は `multi_leg_group_id` で追跡でき、backtest summary で group 合算 return と notional-weighted signal return も確認できる。
- `rules.exit.stop_loss_bps` / `take_profit_bps` / `min_reward_risk_ratio` / `trailing_stop_bps` / `trailing_stop_activation_bps` / `partial_take_profit_bps` と `*_column` で、固定幅または row ごとの動的幅の損切・利確・reward/risk gate・部分利確・activation threshold 付きトレーリングストップを評価できる。`rules.bracket.break_even_after_partial_take_profit` で、部分利確後の残り position を break-even stop 待ちへ移せる。`rules.exit.min_holding_minutes` / `min_holding_minutes_column` で、最低保有時間に到達するまで stop / take / trailing / partial / signal exit / bracket time stop を paper-only に遅らせられる。`rules.exit.max_holding_minutes` / `max_holding_minutes_column` で、fixed horizon より前に row 固有の time stop も評価できる。
- `rules.close` と `rules.exit.exit_on_close_signal` で、反対売買を開かない explicit close signal による paper exit を評価できる。
- `rules.reduce` と `rules.exit.exit_on_reduce_signal` / `reduce_fraction` で、反対売買を開かない explicit reduce signal による paper 部分縮小を評価できる。
- `rules.add` と `rules.exit.exit_on_add_signal` / `add_fraction` で、独立 trade を開かない explicit add signal による paper 増し玉を評価できる。
- `rules.rebalance` と `rules.exit.exit_on_rebalance_signal` / `rebalance_target_fraction` で、独立 trade を開かない explicit rebalance signal による paper exposure resize を評価できる。
- `rules.bracket.enabled` と bracket / exit column fields で fixed or row-level stop / take profit / break-even / partial-profit break-even / time stop を OCO 的な paper lifecycle として評価できる。
- `rules.order.entry_type` / `entry_type_column` / `limit_offset_bps_column` / `stop_offset_bps_column` / `time_in_force` / `time_in_force_column` / `timeout_minutes_column` / `post_only` / `post_only_column` / `reduce_only` で、固定または row ごとの market / limit / stop-market、row-level offset、GTC / GTD / IOC / FOK、row-level timeout、row-level post-only limit、reduce-only の paper entry constraint を評価できる。
- `rules.cross_sectional.long_top_fraction` / `short_bottom_fraction` で universe size に応じた上位 / 下位 tail rotation を作れ、`group_column` で sector / theme / asset class などの group ごとの top-bottom rotation、`min_candidates` で小さすぎる group の見送り、`min_long_score` / `max_short_score` で弱い top / bottom の見送りもできる。
- `rules.sizing.position_weight` / `notional_usd` / `volatility_target`, `rules.risk_throttle.profile` / `rules.risk_throttle`, and `rules.portfolio.max_signals_per_timestamp` で paper backtest weight、想定 notional、drawdown / daily loss / loss streak gate、停止後 cooldown、同時候補数制限を記録・評価できる。
- `rules.portfolio.max_total_position_weight` / `max_total_position_weight_column` / `max_long_position_weight` / `max_long_position_weight_column` / `max_short_position_weight` / `max_short_position_weight_column` / `max_abs_net_position_weight` / `max_abs_net_position_weight_column` / `max_symbol_position_weight` / `max_symbol_position_weight_column` / `max_group_position_weight` / `max_group_position_weight_column` / `max_group_abs_net_position_weight` / `max_group_abs_net_position_weight_column` + `group_column` で同一 timestamp の total / long / short / net / symbol / sector・theme・asset class などの任意 group exposure と group 内 net exposure を固定または row 由来の上限で制限できる。
- `rules.portfolio.allocation_method` / `target_total_position_weight` / `target_total_position_weight_column` で同一 timestamp の採用候補を equal weight、score proportional、inverse volatility、dollar neutral、beta neutral、group neutral に固定または row 由来の target で正規化できる。
- `rules.position.max_open_signals_per_symbol` / `max_open_position_weight_per_symbol` / `allow_pyramiding` で同一銘柄の仮想 open signal 数、open weight、同方向の増し玉可否を制限できる。
- `rules.regime_overrides` で regime ごとに損切、利確、weight、notional、slippage、max-fill、min-fill、spread/depth 条件を切り替えられる。
- `rules.execution.slippage_bps` / `slippage_bps_column` / `max_fill_fraction` / `max_fill_fraction_column` / `min_fill_fraction` / `min_fill_fraction_column` / `max_spread_bps` / `max_spread_bps_column` / `min_depth_usd` / `min_depth_usd_column` / `depth_participation_rate` / `max_latency_ms` / `max_latency_ms_column` / `min_queue_position_score` / `min_queue_position_score_column` / `min_borrow_availability_ratio` / `min_borrow_availability_ratio_column` / `max_borrow_cost_bps` / `max_borrow_cost_bps_column` / `max_tax_drag_bps` / `max_tax_drag_bps_column` / `max_turnover_pressure` / `max_turnover_pressure_column` / `max_capacity_usage_ratio` / `max_capacity_usage_ratio_column` / `max_correlation_crowding_score` / `max_correlation_crowding_score_column` / `min_fee_edge_bps` / `min_fee_edge_bps_column` で滑り、row slippage、部分約定、min-fill gate with row threshold、spread gate with row threshold、depth gate with row threshold、depth-based fill、latency gate with row threshold、queue-position gate with row threshold、short-borrow availability/cost gate with row threshold、tax drag / turnover pressure / capacity / crowding / fee-edge with row threshold を paper-only に評価できる。
- `rules.temporal.allowed_weekdays_utc` / `allowed_hours_utc` / `cooldown_minutes` / `max_signals_per_symbol_per_day` で曜日・時間帯・同一銘柄 cooldown・銘柄別日次上限を評価できる。
- `rules.event_windows` で event timestamp column の前後だけを許可、または event 前後を blackout し、見送り理由を signal artifact に残せる。
- `optimizer.parameter_sweep` で許可された spec path の paper-only grid search を行い、best variant と全 variant metrics を記録できる。
- `backtest.split_method=walk_forward` / `purged_walk_forward` で era 別 aggregate metrics を記録できる。
- `strategy_backtest_metrics.json` の `summary.executed_signal_summary` で実行済み signal の side / symbol / timeframe / exit reason count、return、cost、notional を compact に確認できる。verbose 診断 row は `summary.executed_signal_results` に残る。
- `strategy_backtest_metrics.json` の `summary.strategy_scorecard` で、使った derived feature、side counts、reason code、block reason、execution block reason、exit reason、pass/fail threshold を集約できる。
- `strategy_scorecard` は paper-preview 時に `TrialRecord.metrics.strategy_scorecard` と `PromotionDecision.scorecard_summary` へ伝播し、promote された `PaperIntentPreview` には `scorecard_summary` として残せる。
- `strategy_authoring_bundle.v1` で複数 authoring spec を allocation weight / equal weight / risk-parity 付きで比較し、bundle-level aggregate metrics を出せる。
- rule が参照する feature column と symbol binding を validate できる。
- `data/research/strategy_signals.parquet` を正本として出せる。
- hold 条件に当たった row は `side: none` / `block_reasons: ["hold_rule"]` として記録し、backtest の売買対象からは除外できる。
- Strategy Lab signal を直接 backtest bridge に渡し、legacy `signals.csv` を正本にしない。
- `--through paper-preview` で paper-only の `trial_ledger.jsonl`, `paper_candidate_pack.json`, `promotion_decision.json`, `paper_intent_preview.json` まで出せる。既定 `hold` では intent は空配列だが、ledger と promotion decision には scorecard 要約が残る。

主要 artifact:

- `data/research/strategy_authoring_run.json`
- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `schemas/strategy_authoring_backtest_result.v1.schema.json`
- `data/research/strategy_authoring_bundle_result.json`
- `schemas/strategy_authoring_bundle_result.v1.schema.json`
- `data/reports/strategy_authoring_explain.md`
- `data/reports/strategy_backtest_report.md`
- `data/reports/strategy_authoring_bundle_report.md`

### 2. signal artifact を TrialRecord に評価記録できる

```bash
uv run sis evaluate-strategy-lab
```

できること:

- `data/research/trial_ledger.jsonl` に `TrialRecord` を append-only に記録できる。
- 同じ signal artifact と同じ parameter set の `trial_id` を重複追記しない。
- `signal_artifact_run_id` で signal artifact と trial を接続できる。
- 1 artifact に複数の strategy / symbol identity が混ざる場合は exit code 2 で止まる。
- 空または重複した `signal_id` を含む signal artifact は exit code 2 で止まる。
- empty signal artifact は manifest lineage がある場合だけ no-signal trial として記録できる。

主要 artifact:

- `data/research/trial_ledger.jsonl`
- `data/reports/strategy_trial_report.md`

### 3. rank threshold sweep を paper-only に記録できる

```bash
uv run sis evaluate-strategy-lab --rank-thresholds 0.2,0.8
```

できること:

- comma-separated の `rank_score` threshold ごとに `TrialRecord` を作れる。
- threshold 別 trial は同じ `trial_group_id` にまとまる。
- threshold / `--candidate-limit` / `--split-method` / `--era-unit` ごとに `parameter_hash` と `trial_id` が分かれる。
- default evaluation は互換性のため `generator-default-{run_id}` と `trial-{run_id}` を維持する。

注意:

- threshold sweep は paper-only の比較記録です。
- `rank_threshold` は新しい `strategy_id` ではなく、同じ strategy の parameter variant として扱う。

### 4. 複数 selected signal を candidate 化できる

```bash
uv run sis evaluate-strategy-lab --candidate-limit 0
uv run sis build-paper-candidate-pack
```

できること:

- default evaluation は最新 `ts_signal` の 1 signal を `metrics.selected_signal_ids` に記録する。
- `--candidate-limit 0` で threshold 通過 signal 全件を `selected_signal_ids` に記録できる。
- `build-paper-candidate-pack` は `TrialRecord.metrics.selected_signal_ids` から複数 `TradeCandidate` を作れる。
- selected trial の `signal_artifact_run_id` が現在の signal artifact と一致しない場合は exit code 2 で止まる。
- selected signal ID が現在の signal artifact に見つからない場合は exit code 2 で止まる。

主要 artifact:

- `data/research/paper_candidate_pack.json`
- `data/reports/paper_candidate_pack.md`

### 5. era 別 signal count metrics を残せる

```bash
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit trading_day
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit week
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit month
```

できること:

- `metrics.split_method` に `single_window`, `walk_forward`, `purged_walk_forward` を記録できる。
- `metrics.era_unit` に `session`, `trading_day`, `week`, `month` を記録できる。
- `metrics.era_signal_counts` と `metrics.era_count` を残せる。

注意:

- これは era 別 signal count metrics です。
- PnL 計算や walk-forward 検証 engine ではありません。

### 6. paper-only preview まで artifact chain を進められる

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
```

できること:

- `PaperCandidatePack` から `PromotionDecision` を作れる。
- `PaperCandidatePack.selected_candidate_ids` は `status="candidate"`、空の `block_reasons`、venue-suitable の候補だけに制限される。
- `hold` / `reject` / `promote` の判断 artifact を残せる。
- required evidence が揃わない `promote` は validation で止まる。
- `PromotionDecision.source_pack_id` と `PaperCandidatePack.pack_id` の不一致を exit code 2 で止められる。
- `PaperIntentPreview` は `paper_only=true`, `live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false` のまま出せる。
- NDX/QQQ family の `trade_xyz` / `bitget_demo` paper intent は現行 suitability guard で拒否される。

主要 artifact:

- `data/research/promotion_decision.json`
- `data/bot/paper_intent_preview.json`
- `data/reports/promotion_decision.md`
- `data/reports/paper_intent_preview.md`

### 7. paper runner で preview を再検証できる

```bash
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

できること:

- `PaperIntentPreview` を最新 quote と paper broker state で再検証できる。
- raw JSON で直接渡された `PaperIntentPreview` も Pydantic model で再検証し、venue-unsuitable な NDX/QQQ family を拒否できる。
- expired intent, latest quote missing, paper broker block を stop reason として残せる。
- paper order / fill / position artifact と observation ledger を書ける。
- observation ledger は `live_order_submitted=false`, `wallet_used=false`, `exchange_write_used=false` を明示する。

主要 artifact:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

## よく使う実行例

Default signal から paper candidate pack まで:

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
```

StrategyExperimentSpec から paper candidate pack まで:

```bash
uv run sis strategy-experiment-run --spec path/to/strategy_experiment.yaml
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
```

SP500 generator:

```bash
uv run sis strategy-preview --generator-id sp500_trend_rates_vix
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
```

Threshold sweep と複数 candidate:

```bash
uv run sis evaluate-strategy-lab --rank-thresholds 0.2,0.8 --candidate-limit 0
uv run sis build-paper-candidate-pack
```

Era metrics 付き sweep:

```bash
uv run sis evaluate-strategy-lab \
  --rank-thresholds 0.2,0.8 \
  --candidate-limit 0 \
  --split-method walk_forward \
  --era-unit trading_day
```

## まだできないこと

- 任意式、任意 Python、外部 plugin を実行する full experiment engine。
- broker 固有 queue priority、order book event replay、maker/taker priority を含む full venue microstructure replay。現行の latency / queue-position は feature snapshot 値による paper gate まで。
- train/test 再学習を伴う full walk-forward / purged walk-forward engine。
- 複数戦略をまたぐ本格 portfolio optimizer や live rebalance engine。paper bundle の equal_weight / risk_parity allocation は対応済み。
- live order, wallet signing, exchange write。
- `PromotionDecision.decision=promote` から live trading へ進む導線。
- Strategy Lab artifact だけを根拠にした profitability / paper-ready / live-ready claim。

## 受け入れ済みの検証

current verification は固定の pass count ではなく、作業時点で次を再実行して確認します。

```bash
uv run pytest tests/test_strategy_lab_commands.py -q
uv run pytest tests/strategy_authoring -q
uv run pytest tests/test_strategies.py tests/test_strategy_lab_signal_registry.py tests/test_research_signals_artifact.py tests/test_strategy_lab_commands.py tests/test_strategy_lab_candidate_pack.py tests/test_strategy_lab_schemas.py -q
uv run pytest tests/test_research_pipeline.py tests/test_cli_smoke.py -q
uv run python scripts/check_current_docs.py
./scripts/check
git diff --check
```

2026-06-06 docs-only spot check:

- `uv run python scripts/check_current_docs.py`: pass, current-doc allowlist checked successfully
