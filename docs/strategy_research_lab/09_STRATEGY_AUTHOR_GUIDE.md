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

`rules.exit.stop_loss_bps` と `rules.exit.take_profit_bps` を指定した場合は、fixed horizon の手前でも、先に到達した stop loss / take profit quote で仮想 exit します。`trailing_stop_bps` と `partial_take_profit_bps` / `partial_exit_fraction` も paper backtest に反映できます。`min_holding_minutes` を指定すると、最低保有時間に到達するまで stop / take / trailing / partial / signal exit / bracket time stop を無視し、早すぎる noise exit を抑えた研究ができます。どの exit が使われたかは `strategy_backtest_metrics.json` の `summary.exit_reason_counts` に出ます。

`rules.exit.exit_on_opposite_signal: true` を指定すると、同じ execution symbol で反対方向の次シグナルが出た時点でも仮想 exit します。これは reversal、ドテン、close-on-sell / close-on-buy 型の評価用です。実注文は出しません。

`backtest.pass_thresholds` は `strategy_backtest_metrics.json` の `summary.pass_thresholds` と `summary.backtest_passed` に反映されます。`max_drawdown` は `-0.2` 以上なら pass、`cost_drag_bps`, `stale_rejected_count`, `halt_rejected_count` は threshold 以下なら pass、それ以外は threshold 以上なら pass です。

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
- OHLC/time-series: `true_range`, `atr`, `bollinger_upper`, `bollinger_lower`, `bollinger_width`, `bollinger_percent_b`, `donchian_upper`, `donchian_lower`, `donchian_mid`, `donchian_width`, `keltner_upper`, `keltner_lower`, `keltner_width`, `ichimoku_conversion`, `ichimoku_base`, `ichimoku_span_a`, `ichimoku_span_b`, `macd_line`, `stochastic_k`, `stochastic_d`, `adx`, `obv`, `volume_zscore`, `ts_weekday`, `ts_hour`, `ts_month`, `ts_day`, `lag`, `ewm_mean`, `rsi`, `rolling_min`, `rolling_max`, `rolling_mean`, `rolling_std`, `rolling_zscore`, `rolling_corr`, `rolling_beta`, `rolling_spread_zscore`, `rolling_autocorr`, `kelly_fraction`, `historical_var`, `expected_shortfall`
- flow/carry/liquidity/options-vol/on-chain/sentiment/event/fundamental/factor-ranking/execution-constraint/data-quality/ensemble/capacity: `order_flow_imbalance`, `liquidity_depth_ratio`, `spread_bps`, `funding_bps`, `carry_adjusted_return`, `vol_risk_premium`, `put_call_skew`, `liquidity_stress`, `net_exchange_flow`, `onchain_activity_ratio`, `sentiment_weighted_score`, `event_surprise`, `fundamental_value_gap`, `risk_adjusted_score`, `inverse_volatility_weight`, `cross_sectional_rank`, `cross_sectional_zscore`, `cross_sectional_demean`, `queue_position_score`, `latency_penalty_bps`, `maker_taker_fee_edge_bps`, `borrow_cost_bps`, `borrow_availability_ratio`, `tax_drag_bps`, `rebalance_drift`, `freshness_score`, `staleness_bps`, `data_quality_blend`, `ensemble_vote_count`, `ensemble_vote_ratio`, `regime_transition_score`, `drawdown_from_peak`, `turnover_pressure`, `capacity_usage_ratio`, `correlation_crowding_score`

time-series 系は `canonical_symbol` ごとに `ts` 順で評価します。`fill_null` を指定すると、初期 window やゼロ除算で出る null を指定値で埋めます。例えば breakout は `rolling_max` や `donchian_upper` で channel high を作り、`lag` で prior high にずらしてから現在 price と比較します。EMA crossover は `ewm_mean` で fast / slow EMA を作り、`value_column` で比較します。RSI mean reversion は `rsi` を作って oversold / overbought threshold と比較します。ATR volatility filter は `atr` を high / low / close columns から作って entry、hold、dynamic stop/target columns に使います。Bollinger 系は `window` と標準偏差倍率の `value`、未指定時 2.0 で upper / lower / width / percent_b を作り、band reversal、band breakout、volatility compression の条件に使えます。Keltner 系は close EMA center と ATR envelope を作ります。Ichimoku 系は conversion / base / span A / span B を作り、cloud breakout や trend filter に使えます。MACD は `macd_line` の `window` を fast span、`value` を slow span として作り、必要なら `ewm_mean` で signal line、`diff` で histogram を作れます。Stochastic は `stochastic_k` と `stochastic_d`、trend strength は `adx`、出来高確認は `obv` と `volume_zscore` を使います。Kelly / VaR 系は `kelly_fraction`, `historical_var`, `expected_shortfall` を rolling return column から作り、Kelly sizing、VaR filter、expected shortfall filter に使えます。Calendar 系は `ts_weekday` を Monday=0、`ts_hour` を 0-23、`ts_month` を 1-12、`ts_day` を 1-31 として作ります。Cross-asset / pair 系は同じ row にある asset return と benchmark return などから `rolling_corr`, `rolling_beta`, `rolling_spread_zscore` を作り、benchmark confirmation、relative strength、pair spread normalization に使えます。`rolling_autocorr` は 1 列の自己相関を作り、trend persistence や mean-reversion regime filter に使えます。Flow / carry / liquidity / options-vol 系は order book size imbalance、depth ratio、quoted spread bps、funding cost bps、carry-adjusted return、implied-realized vol premium、put-call skew、spread/depth stress を作り、order-flow continuation、thin-liquidity exclusion、funding/carry filter、vol risk premium、skew hedge、on-chain flow filter、sentiment confirmation、event surprise、fundamental value gap、factor ranking、cross-sectional standardization、queue-position filter、latency-cost filter、maker-taker fee edge、borrow availability and cost、tax drag filter、rebalance drift、data freshness filter、source-quality blend、ensemble vote filter、regime transition filter、rolling drawdown filter、turnover pressure、capacity usage、correlation crowding 条件に使えます。

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
    partial_take_profit_bps: 200
    partial_exit_fraction: 0.5
    min_holding_minutes: 120
    stop_loss_bps_column: atr_stop_bps
    take_profit_bps_column: atr_take_profit_bps
  sizing:
    position_weight: 1.0
    notional_usd: 1000
    volatility_target: 0.20
    volatility_column: realized_vol
    max_volatility_scaled_position_weight: 1.5
  order:
    entry_type: market
  bracket:
    enabled: true
    bracket_type: oco
    break_even_after_bps: 100
    time_stop_minutes: 180
  portfolio:
    max_signals_per_timestamp: 3
    allocation_method: score_proportional
    target_total_position_weight: 1.0
    allocation_volatility_column: realized_vol
  risk_throttle:
    max_drawdown_column: strategy_drawdown
    max_drawdown_floor: -0.20
    daily_loss_column: daily_pnl
    daily_loss_floor: -0.10
    loss_streak_column: loss_streak
    max_loss_streak: 3
```

- `side: long` / `side: short` で買い・売りの方向を選べます。
- `side: auto` / `side_column` で、row ごとに long / short / hold を切り替えられます。explicit close は `rules.close` で出します。
- `hold` は「条件が悪いので見送り」を signal artifact に残します。
- `close` は「反対売買を開かずに閉じる」paper close signal を出します。`exit_on_close_signal` が true の entry は、次の close signal で仮想 exit します。
- `reduce` は「反対売買を開かずに一部だけ縮小する」paper reduce signal を出します。`exit_on_reduce_signal` が true の entry は、次の reduce signal で `reduce_fraction` 分を仮想 exit します。
- `add` は「新しい独立 trade ではなく既存 paper position に追加する」paper add signal を出します。`exit_on_add_signal` が true の entry は、次の add signal で `add_fraction` 分を追加入りします。
- `rebalance` は「新しい独立 trade ではなく既存 paper position を目標 exposure に寄せる」paper rebalance signal を出します。`exit_on_rebalance_signal` が true の entry は、次の rebalance signal で `rebalance_target_fraction` へ縮小または追加します。
- `stop_loss_bps: 150` は 1.5% 逆行で仮想損切します。
- `take_profit_bps: 300` は 3.0% 有利に動いたら仮想利確します。
- `exit_on_opposite_signal` は同じ symbol の反対シグナルで仮想 exit します。
- `exit_on_close_signal` は同じ symbol の explicit close signal で仮想 exit します。
- `exit_on_reduce_signal` は同じ symbol の explicit reduce signal で一部縮小します。`reduce_fraction_column` を使うと row ごとに縮小率を変えられます。
- `exit_on_add_signal` は同じ symbol の explicit add signal で増し玉します。`add_fraction_column` を使うと row ごとに追加率を変えられます。
- `exit_on_rebalance_signal` は同じ symbol の explicit rebalance signal で paper exposure を目標値へ近づけます。`rebalance_target_fraction_column` を使うと row ごとに目標 exposure を変えられます。
- `trailing_stop_bps` は含み益のピークからの戻り幅で仮想 exit します。
- `partial_take_profit_bps` と `partial_exit_fraction` は、一部利確して残りを horizon / stop / trailing に回します。
- `min_holding_minutes` は、指定分数に到達するまで stop / take / trailing / partial / close / reduce / add / rebalance / opposite / bracket time stop を paper-only に遅らせます。
- `bracket.enabled: true` は stop / take profit / time stop / break-even stop を OCO 的に paper 評価します。
- `*_bps_column` を指定すると、ATR やボラティリティから作った feature column で row ごとに損切・利確幅を変えられます。column 値が空の場合は固定値を fallback にします。
- `sizing.position_weight` は backtest return に掛ける paper weight です。`position_weight_column` で row ごとの重みも使えます。
- `sizing.notional_usd` は paper candidate に残す想定 notional です。live order には変換しません。
- `sizing.volatility_target` は `volatility_column` の値に応じて `position_weight` を `target / observed` で拡大縮小します。`max_volatility_scaled_position_weight` があれば上限で cap します。
- `order.entry_type: market` は signal 時刻以降の最初の quote で入る paper 評価です。
- `portfolio.max_signals_per_timestamp` は同一 timestamp の trade signal を rank score 上位 N 件に絞ります。
- `portfolio.max_total_position_weight` / `max_long_position_weight` / `max_short_position_weight` / `max_symbol_position_weight` は同一 timestamp の paper exposure を制限します。超過候補は `side: none` と `portfolio_*_exposure_limit` の `block_reasons` に残ります。
- `portfolio.allocation_method: equal_weight` は同一 timestamp の採用候補へ `target_total_position_weight` を均等配分します。
- `portfolio.allocation_method: score_proportional` は同一 timestamp の採用候補へ正の `raw_score` 比例で `target_total_position_weight` を配分します。全 score が 0 以下または欠損なら均等配分へ fallback します。
- `portfolio.allocation_method: inverse_volatility` は `allocation_volatility_column` の正の値の逆数で `target_total_position_weight` を配分します。全 volatility が 0 以下または欠損なら均等配分へ fallback します。
- `portfolio.allocation_method: dollar_neutral` は long / short の gross weight が半分ずつになるように配分します。片側の候補しかない timestamp では、反対側の half target は使わず、その timestamp の exposure は半分に抑えられます。
- `portfolio.allocation_method: beta_neutral` は `allocation_beta_column` を使い、long beta exposure と short beta exposure が釣り合うように配分します。片側の beta が無い、0、または候補が片側だけの場合は dollar-neutral と同じ half target 配分へ fallback します。
- `portfolio.allocation_method: group_neutral` は `group_column` ごとに long / short gross weight が半分ずつになるように配分します。group が欠けた候補は neutral allocation 上は 0 weight になり、group exposure 制限と組み合わせると fail-closed で見送られます。
- `risk_throttle` は drawdown、daily loss、loss streak の feature column によって新規 signal を止めます。止めた候補は `side: none` と `risk_throttle_*` の `block_reasons` に残ります。
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
```

override できる値:

- exit: `stop_loss_bps`, `take_profit_bps`, `trailing_stop_bps`, `partial_take_profit_bps`, `partial_exit_fraction`
- sizing: `position_weight`, `notional_usd`
- execution: `slippage_bps`, `max_fill_fraction`, `max_spread_bps`, `min_depth_usd`, `depth_participation_rate`

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
    time_stop_minutes: 180
```

- `bracket_type: oco` は v1 で唯一の bracket type です。
- `stop_loss_bps` / `take_profit_bps` は先に到達したほうで exit し、`summary.exit_reason_counts.bracket_stop_loss` または `bracket_take_profit` に出ます。
- `break_even_after_bps` は含み益が指定 bps 以上になった後、return が 0 以下へ戻ったら `bracket_break_even_stop` で exit します。
- `time_stop_minutes` は entry quote から指定分数後以降の最初の quote で残り position を `bracket_time_stop` として閉じます。
- partial take profit と併用した場合、部分利確後の残り position が bracket stop / take / break-even / time stop の対象です。

## Order Style Entry

entry を成行相当だけでなく、limit / stop-market 相当で評価できます。これは paper-only の約定シミュレーションであり、本物の指値注文・逆指値注文は出しません。

```yaml
rules:
  order:
    entry_type: limit
    limit_offset_bps: 50
    timeout_minutes: 120
```

- `entry_type: market` は signal 時刻以降の最初の quote で入ります。
- `entry_type: limit` は long なら基準 entry quote より `limit_offset_bps` だけ安い価格、short なら高い価格に到達した時だけ入ります。
- `entry_type: stop_market` は long なら基準 entry quote より `stop_offset_bps` だけ高い価格、short なら低い価格に到達した時だけ入ります。
- `timeout_minutes` を過ぎても条件に届かない場合は未約定として `summary.entry_order_unfilled_count` と `blocked_reason_counts.entry_order_unfilled` に出ます。
- 約定した注文種別は `summary.entry_order_type_counts` に出ます。

## Execution Quality

slippage、partial fill、spread / depth / latency / queue-position / short borrow / tax drag / turnover / fee edge による venue microstructure 条件も paper-only で評価できます。これは約定品質の仮定を backtest に入れるだけで、実注文には変換しません。

```yaml
rules:
  execution:
    slippage_bps: 25
    max_fill_fraction: 0.5
    max_spread_bps: 15
    min_depth_usd: 10000
    depth_column: min_side_depth_10bps_usd
    depth_participation_rate: 0.25
    max_latency_ms: 100
    latency_column: observed_latency_ms
    min_queue_position_score: 0.6
    queue_position_score_column: queue_score
    min_borrow_availability_ratio: 0.5
    borrow_availability_column: borrow_available
    max_borrow_cost_bps: 25
    borrow_cost_column: borrow_cost
    max_tax_drag_bps: 20
    tax_drag_column: tax_drag
    max_turnover_pressure: 0.4
    turnover_pressure_column: turnover_pressure
    min_fee_edge_bps: 1
    fee_edge_column: fee_edge
```

- `slippage_bps` は round trip の追加 drag として return から差し引き、`cost_drag_bps` に足します。
- `max_fill_fraction` は約定した想定数量の割合です。`0.5` なら signal return は半分の exposure として評価されます。
- `max_spread_bps` は entry quote の `spread_bps` が指定値を超える場合に約定対象から外し、`blocked_reason_counts.microstructure_spread_too_wide` に記録します。
- `min_depth_usd` は entry quote の depth column が指定額未満なら約定対象から外します。column が無い場合は `microstructure_depth_missing`、額が足りない場合は `microstructure_depth_too_low` に記録します。
- `depth_column` は depth 判定に使う quote column です。省略時は `min_side_depth_10bps_usd` を使います。
- `depth_participation_rate` は depth のうち自分が取れる想定割合です。`notional_usd` がある場合、`depth * depth_participation_rate / notional_usd` で paper exposure をさらに縮小します。
- `max_latency_ms` は feature panel の latency column が上限を超える場合に約定対象から外し、欠損は `microstructure_latency_missing`、上限超過は `microstructure_latency_too_high` に記録します。
- `min_queue_position_score` は feature panel の queue score が閾値未満なら約定対象から外し、欠損は `microstructure_queue_position_missing`、閾値未満は `microstructure_queue_position_too_low` に記録します。
- `min_borrow_availability_ratio` と `max_borrow_cost_bps` は short signal だけに適用します。availability 欠損は `short_borrow_availability_missing`、不足は `short_borrow_availability_too_low`、cost 欠損は `short_borrow_cost_missing`、上限超過は `short_borrow_cost_too_high` に記録します。
- `max_tax_drag_bps` は tax drag が欠損または上限超過なら `tax_drag_missing` / `tax_drag_too_high` として約定対象から外します。
- `max_turnover_pressure` は turnover pressure が欠損または上限超過なら `turnover_pressure_missing` / `turnover_pressure_too_high` として約定対象から外します。
- `min_fee_edge_bps` は fee edge が欠損または閾値未満なら `fee_edge_missing` / `fee_edge_too_low` として約定対象から外します。負値の fee edge も扱えます。
- partial fill と depth-based fill は `position_weight` と掛け合わされます。

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
```

- `max_open_signals_per_symbol` は同一 execution symbol で同時に open とみなす signal 数の上限です。`1` なら同じ symbol の重複保有を禁止します。
- `max_open_position_weight_per_symbol` は同一 execution symbol の open `position_weight` 合計上限です。
- `holding_horizon_minutes` を省略すると `backtest.label_horizon_minutes` を使います。
- 見送られた候補は削除せず、`side: none` と `position_open_signal_limit` / `position_open_weight_limit` の `block_reasons` に残します。
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

- `split_method: walk_forward` / `purged_walk_forward` は `summary.walk_forward_eras` に era 別 metrics を残します。
- `optimizer.parameter_sweep` は許可された spec path だけを grid search します。
- 結果は `strategy_backtest_metrics.json` の `summary.optimizer.variants` と `summary.optimizer.best_variant` に出ます。
- optimizer は任意 Python、任意式、外部API、live order を実行しません。

## Strategy Scorecard

`strategy-author-run --through backtest` は `data/research/strategy_backtest_metrics.json` の `summary.strategy_scorecard` に、使った `derived_features`、side counts、reason code counts、block reason counts、execution block reasons、exit reasons、pass/fail thresholds を集約します。これは「どの feature と制約が strategy の通過・棄却に効いたか」を確認する paper-only explanation artifact です。

`--through paper-preview` では同じ情報が `TrialRecord.metrics.strategy_scorecard` と `PromotionDecision.scorecard_summary` にも残ります。promotion が `promote` されて intent が作られる通常 CLI 経路では、`PaperIntentPreview.scorecard_summary` にも引き継がれます。既定 `hold` では intent は空配列ですが、なぜ止めたかは scorecard と rejection reason で追えます。

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
        # Optional: use feature columns for dynamic hedge ratio / leg notional.
        # position_weight_column: hedge_ratio
        # notional_usd_column: hedge_notional_usd
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
- 各 leg は通常の `strategy_signal.v1` として出るため、paper backtest では leg ごとに独立評価されます。

## Multi Strategy Bundle

複数の authoring YAML をまとめて paper-only portfolio として比較できます。

```bash
uv run sis strategy-author-bundle-run \
  --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
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
- pair / hedge style signal: `rolling_spread_zscore`, `rolling_corr`, `rolling_beta` で spread normalization や benchmark confirmation を作り、`side: auto` または `cross_sectional` で long / short を切り替える。
- exclusion / blackout rules: `entry.none`, `hold.none`, `long_entry.none`, `short_entry.none` で「どれにも該当しない時だけ」を直接書く。
- moving-average cross / adaptive threshold: `value_column` で `fast_ma > slow_ma` や `score > dynamic_threshold` を直接書く。
- local feature derivation: `derived_features` で spread、ratio、true range、ATR、Bollinger bands、Donchian channels、Keltner channels、Ichimoku cloud、MACD line、stochastic K/D、ADX、OBV、volume z-score、calendar features、rolling correlation / beta / spread z-score、order-flow imbalance、liquidity depth ratio、spread bps、funding bps、carry-adjusted return、volatility risk premium、put-call skew、liquidity stress、net exchange flow、on-chain activity ratio、sentiment weighted score、event surprise、fundamental value gap、risk-adjusted score、inverse volatility weight、cross-sectional rank、cross-sectional z-score / demean、queue position score、latency penalty bps、maker-taker fee edge、borrow cost bps、borrow availability ratio、tax drag bps、rebalance drift、freshness score、staleness bps、data quality blend、ensemble vote count/ratio、regime transition score、drawdown from peak、turnover pressure、capacity usage ratio、correlation crowding score、lag、EMA、RSI、rolling min/max/mean/z-score を YAML 内で作る。
- explicit pair / hedge: `multi_leg` で anchor signal から long leg と short leg を同時に出す。
- regime filter: `in` / `not_in` で bull、bear、event day などのカテゴリを entry / hold に使う。
- regime-specific risk: `regime_overrides` で high volatility 時だけ損切幅、利確幅、weight、slippage を変える。
- cross-sectional top-bottom: `cross_sectional.long_top_n` / `short_bottom_n` で同時刻の上位 long・下位 short を作る。
- event window / calendar filter: `event_windows` で event 前後だけ許可、または event 前後を blackout する。
- session / rebalance cadence: `temporal` で曜日・時間帯・cooldown・日次上限を指定する。
- no-overlap / pyramiding cap: `position.max_open_signals_per_symbol` / `max_open_position_weight_per_symbol` で同一銘柄の仮想 open exposure を制限する。
- dynamic risk: `stop_loss_bps_column` / `take_profit_bps_column` に ATR・volatility 由来の bps を入れる。
- staged exit: `partial_take_profit_bps` と `partial_exit_fraction` で部分利確を評価する。
- minimum hold: `min_holding_minutes` で最低保有時間までは早期 exit を抑える。
- bracket / OCO lifecycle: `bracket.enabled` で stop / take / break-even / time stop を束ねて評価する。
- trailing stop: `trailing_stop_bps` で利益を伸ばしつつ戻りで抜ける条件を評価する。
- signal reversal: `exit_on_opposite_signal` で反対売買シグナルによる close / reversal を評価する。
- order style: `order.entry_type` で market / limit / stop-market entry を評価する。
- execution quality: `execution.slippage_bps` / `max_fill_fraction` / `max_spread_bps` / `min_depth_usd` / `max_latency_ms` / `min_queue_position_score` / `min_borrow_availability_ratio` / `max_borrow_cost_bps` / `max_tax_drag_bps` / `max_turnover_pressure` / `min_fee_edge_bps` で滑り、部分約定、spread gate、depth-based fill、latency gate、queue-position gate、short-borrow gate、tax / turnover / fee-edge gate を評価する。
- risk parity / conviction sizing: `position_weight_column` に volatility inverse や confidence weight を入れる。
- volatility targeting: `sizing.volatility_target` / `volatility_column` で row ごとの paper exposure を目標ボラへ合わせる。
- drawdown / loss throttle: `risk_throttle` で drawdown、daily loss、loss streak が悪化した時に新規 entry を止める。
- portfolio throttle: `portfolio.max_signals_per_timestamp` で同時候補数を制限する。
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
