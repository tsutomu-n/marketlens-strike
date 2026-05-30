# Strategy Authoring Current Summary

この文書は、2026-05-30 時点の `strategy_authoring_spec.v1` でユーザーが作れる売買ロジックを、コードを正として整理したものです。

正本はコードです。特に次を優先します。

- `src/sis/research/strategy_lab/authoring.py`
- `src/sis/backtest/bridge.py`
- `src/sis/backtest/signals.py`
- `src/sis/research/strategy_lab/signal_artifact.py`
- `src/sis/research/strategy_lab/specs.py`
- `schemas/strategy_authoring_spec.v1.schema.json`
- `tests/test_strategy_authoring.py`

## 結論

ユーザーは YAML だけで、entry、long / short 分岐、hold、close、reduce、add、rebalance、損切、利確、部分利確、トレーリングストップ、最低保有時間、OCO 的 bracket、position sizing、portfolio exposure、risk throttle、時間帯 filter、event filter、cross-sectional rotation、multi-leg / pair trade、parameter sweep、paper backtest、paper-preview まで作れます。

ただし、これは paper-only research / preview flow です。live order、wallet signing、exchange write、broker queue priority、order book event replay を含む full venue microstructure replay はまだできません。

## 作れる戦略タイプ

| 戦略タイプ | 現状 |
| --- | --- |
| Trend following | EMA / MACD / ADX / moving average cross / Donchian / Ichimoku / Keltner / channel breakout を derived feature と condition で表現できる。 |
| Mean reversion | RSI、rolling z-score、rolling percentile rank、rolling skew/kurtosis、mean reversion score、Bollinger band、rolling min/max、spread z-score を使える。 |
| Breakout | Donchian、Keltner、Bollinger、true range、ATR、volume z-score、volatility breakout を使える。 |
| Momentum / relative strength | rolling return、cumulative return、slope、cross-sectional rank / z-score / demean、risk-adjusted score、benchmark beta / correlation を使える。 |
| Kelly / tail-risk sizing | `kelly_fraction`, `historical_var`, `expected_shortfall` を rolling return column から作り、Kelly sizing 候補、VaR filter、expected shortfall filter に使える。 |
| Pair trade / hedge | rolling spread z-score、rolling beta、multi-leg、dynamic hedge ratio column で paper signal を展開できる。 |
| Long / short rotation | `rules.cross_sectional` で top / bottom n または fraction を global または group ごとに選べる。 |
| Event-driven | `rules.event_windows` で event 前後だけ許可、または blackout できる。 |
| Multi-timeframe confirmation | `data.confirmation_panels` を backward as-of join し、上位足 trend / macro / regime column を条件に使える。 |
| Regime-aware strategy | `rules.regime_overrides` で regime ごとに損切、利確、weight、notional、slippage、fill、spread/depth threshold を切り替えられる。 |
| Risk-managed portfolio selection | 同時 signal 数、total / long / short / net / symbol / group / group-net exposure、risk throttle、position overlap を制限できる。 |
| Bundle comparison | `strategy_authoring_bundle.v1` で複数 authoring spec を fixed / equal / risk-parity allocation で比較できる。 |

## 売買シグナルでできること

| 機能 | YAML surface | 挙動 |
| --- | --- | --- |
| 買い / 売り方向 | `rules.side`, `rules.side_column`, `rules.long_entry`, `rules.short_entry` | fixed side、column side、long / short 条件分岐、auto side を作れる。 |
| Entry 条件 | `rules.entry`, `rules.long_entry`, `rules.short_entry` | `all` / `any` / `none` condition group で売買候補を作る。 |
| Hold / 見送り | `rules.hold` | 条件一致 row を `side: none` / `block_reasons: ["hold_rule"]` として残し、backtest 対象から外す。 |
| Explicit close | `rules.close`, `rules.exit.exit_on_close_signal` | close marker で既存 paper position を閉じる。close marker 自体は反対 trade を開かない。 |
| Reduce / 部分縮小 | `rules.reduce`, `rules.exit.exit_on_reduce_signal`, `reduce_fraction`, `reduce_fraction_column` | 既存 paper position を指定 fraction だけ縮小する。 |
| Add / 増し玉 | `rules.add`, `rules.exit.exit_on_add_signal`, `add_fraction`, `add_fraction_column` | 既存 paper position に exposure を追加する。独立 trade としては開かない。 |
| Rebalance / exposure resize | `rules.rebalance`, `rules.exit.exit_on_rebalance_signal`, `rebalance_target_fraction`, `rebalance_target_fraction_column` | 既存 paper position を target exposure に寄せる。 |
| 反対シグナル exit | `rules.exit.exit_on_opposite_signal` | 同一 execution symbol の反対方向 signal で paper exit する。 |
| Reason / audit | `reason_codes`, `block_reasons`, `strategy_scorecard` | signal 採用理由、見送り理由、execution block、exit reason を artifact に残す。 |

## 損切・利確・保有管理でできること

| 機能 | YAML surface | 挙動 |
| --- | --- | --- |
| 固定損切 | `rules.exit.stop_loss_bps` | bps 幅で stop loss を評価する。 |
| 動的損切 | `rules.exit.stop_loss_bps_column` | ATR や volatility 由来の row 値を stop loss 幅に使える。 |
| 固定利確 | `rules.exit.take_profit_bps` | bps 幅で take profit を評価する。 |
| 動的利確 | `rules.exit.take_profit_bps_column` | row 値を take profit 幅に使える。 |
| トレーリングストップ | `rules.exit.trailing_stop_bps`, `trailing_stop_bps_column` | 有利方向の最高値 / 最安値からの戻りで exit する。 |
| 部分利確 | `rules.exit.partial_take_profit_bps`, `partial_exit_fraction` | 到達時に一部を利確し、残りを維持する。 |
| 最低保有時間 | `rules.exit.min_holding_minutes` | 指定時間までは stop / take / trailing / partial / close / reduce / add / rebalance / opposite / bracket time stop を遅らせる。 |
| Bracket / OCO | `rules.bracket.enabled`, `time_stop_minutes`, `break_even_after_bps` | stop / take / break-even / time stop を OCO 的 paper lifecycle として評価する。 |
| Fixed horizon | `backtest.label_horizon_minutes` | 通常の評価 horizon。minimum hold がより長い場合は minimum hold まで延長する。 |

## 条件 DSL でできること

`Condition` は固定値比較だけでなく、列同士の比較と状態変化を扱えます。

- `gt`, `gte`, `lt`, `lte`, `eq`, `neq`
- `between`
- `in`, `not_in`
- `value_column` による column-to-column comparison
- `crosses_above`, `crosses_below`
- `rising`, `falling`
- `consecutive_gt`, `consecutive_gte`, `consecutive_lt`, `consecutive_lte`, `consecutive_eq`, `consecutive_neq`
- `all`, `any`, `none` condition group

これにより、moving average cross、adaptive threshold、regime filter、blackout / exclusion rule、持続条件、ブレイクアウト条件を任意 Python なしで書けます。

## Feature engineering でできること

`rules.derived_features` は strategy-local column を作ります。主なカテゴリは次です。

- arithmetic: `add`, `sub`, `mul`, `div`, `ratio`, `diff`, `pct_diff`, `abs`, `neg`, `max`, `min`, `mean`
- price / volatility: `true_range`, `atr`, `rolling_volatility`, `annualized_volatility`, `realized_variance`, `downside_volatility`
- channel / band: `bollinger_upper`, `bollinger_lower`, `bollinger_width`, `bollinger_percent_b`, `donchian_upper`, `donchian_lower`, `donchian_mid`, `donchian_width`, `keltner_upper`, `keltner_lower`, `keltner_width`
- trend / oscillator: `ewm_mean`, `rsi`, `macd_line`, `stochastic_k`, `stochastic_d`, `adx`, `obv`, `volume_zscore`, `ichimoku_conversion`, `ichimoku_base`, `ichimoku_span_a`, `ichimoku_span_b`
- returns / statistics: `pct_change`, `log_return`, `lag`, `rolling_return`, `rolling_sum`, `rolling_mean`, `rolling_std`, `rolling_zscore`, `rolling_percentile_rank`, `rolling_skew`, `rolling_kurtosis`, `sharpe_like`, `sortino_like`, `kelly_fraction`, `historical_var`, `expected_shortfall`, `cumulative_return`, `slope`, `mean_reversion_score`, `distance_from_ma`, `rolling_min`, `rolling_max`
- pair / benchmark: `rolling_corr`, `rolling_beta`, `rolling_spread_zscore`, `rolling_autocorr`
- market microstructure / capacity features: `order_flow_imbalance`, `liquidity_depth_ratio`, `spread_bps`, `queue_position_score`, `latency_penalty_bps`, `capacity_usage_ratio`, `turnover_pressure`, `correlation_crowding_score`
- flow / carry / options / sentiment / fundamentals: `funding_bps`, `carry_adjusted_return`, `vol_risk_premium`, `put_call_skew`, `liquidity_stress`, `net_exchange_flow`, `onchain_activity_ratio`, `sentiment_weighted_score`, `event_surprise`, `fundamental_value_gap`, `risk_adjusted_score`, `cross_sectional_rank`
- quality / ensemble / regime: `freshness_score`, `staleness_bps`, `data_quality_blend`, `ensemble_vote_count`, `ensemble_vote_ratio`, `regime_transition_score`, `drawdown_from_peak`, `rolling_max_drawdown`, `drawdown_duration`
- calendar: `ts_weekday`, `ts_hour`, `ts_month`, `ts_day`

制約: 任意式、任意 Python、外部 plugin、pickle model loading はしません。

## Sizing / portfolio / risk でできること

| 機能 | YAML surface | 挙動 |
| --- | --- | --- |
| 固定 weight | `rules.sizing.position_weight` | paper exposure weight を signal に残し、backtest に反映する。 |
| 動的 weight | `position_weight_column` | row 値を paper exposure weight に使う。 |
| Notional metadata | `notional_usd`, `notional_usd_column` | 想定 notional を signal / candidate に残す。depth-based fill にも使う。 |
| Volatility targeting | `volatility_target`, `volatility_column`, `max_volatility_scaled_position_weight` | row volatility に応じて paper weight を縮小・上限管理する。 |
| Portfolio exposure cap | `max_total_position_weight`, `max_long_position_weight`, `max_short_position_weight`, `max_abs_net_position_weight` | 同一 timestamp の total / long / short / net exposure を制限する。 |
| Symbol cap | `max_symbol_position_weight` | 同一 symbol の同時 exposure を制限する。 |
| Group cap | `max_group_position_weight`, `max_group_abs_net_position_weight`, `group_column` | sector / theme / asset class など任意 group の gross / net exposure を制限する。 |
| Allocation | `allocation_method`, `target_total_position_weight`, `allocation_volatility_column`, `allocation_beta_column`, `group_column` | equal weight、score proportional、inverse volatility、dollar neutral、beta neutral、group neutral に正規化する。beta neutral は beta column、group neutral は group column が必要。neutral 系は片側しかない timestamp / group では反対側の half target を使わない。 |
| Risk throttle | `rules.risk_throttle` | drawdown、daily loss、loss streak で新規 paper signal を止める。 |
| Position overlap | `rules.position` | 同一 symbol の仮想 open signal 数と open weight を制限する。 |

## Execution quality でできること

| 機能 | YAML surface | 挙動 |
| --- | --- | --- |
| Slippage | `rules.execution.slippage_bps` | paper return から round-trip drag として差し引き、`cost_drag_bps` に足す。 |
| Partial fill | `rules.execution.max_fill_fraction` | paper exposure を指定 fraction に縮小する。 |
| Spread gate | `rules.execution.max_spread_bps` | entry quote の `spread_bps` が上限超過なら `microstructure_spread_too_wide` で block する。 |
| Depth gate | `rules.execution.min_depth_usd`, `depth_column` | depth 欠損なら `microstructure_depth_missing`、不足なら `microstructure_depth_too_low` で block する。 |
| Depth-based fill | `rules.execution.depth_participation_rate` + `notional_usd` | depth から取れる想定数量で paper exposure を縮小する。 |
| Latency gate | `rules.execution.max_latency_ms`, `latency_column` | feature panel の latency が欠損なら `microstructure_latency_missing`、上限超過なら `microstructure_latency_too_high` で block する。 |
| Queue-position gate | `rules.execution.min_queue_position_score`, `queue_position_score_column` | feature panel の queue score が欠損なら `microstructure_queue_position_missing`、閾値未満なら `microstructure_queue_position_too_low` で block する。 |
| Short-borrow gate | `rules.execution.min_borrow_availability_ratio`, `borrow_availability_column`, `max_borrow_cost_bps`, `borrow_cost_column` | short signal だけに適用し、borrow availability 欠損 / 不足、borrow cost 欠損 / 上限超過を block する。long signal には適用しない。 |
| Tax / turnover / fee-edge gate | `rules.execution.max_tax_drag_bps`, `tax_drag_column`, `max_turnover_pressure`, `turnover_pressure_column`, `min_fee_edge_bps`, `fee_edge_column` | tax drag、turnover pressure、maker/taker fee edge の snapshot 値で、コスト過大または fee edge 不足の trade を paper-only に block する。 |

現時点の注意: latency / queue-position は feature panel または derived feature の snapshot 値を signal artifact に焼き込み、entry 時点の paper gate として評価します。broker queue priority、order book event replay、maker/taker priority を含む full venue microstructure replay は未実装です。

## Paper-only boundary

できることは、研究用 signal artifact、fixed-horizon backtest、candidate pack、promotion decision、paper intent preview までです。

できないこと:

- live order submission
- wallet signing
- exchange write API
- broker position を読む portfolio rebalance
- live multi-leg order / live OCO order
- `PromotionDecision` から live trading へ進む導線
- Strategy Lab artifact だけを根拠にした profitability / paper-ready / live-ready claim

## 実務上の読み方

1. まず [09_STRATEGY_AUTHOR_GUIDE.md](09_STRATEGY_AUTHOR_GUIDE.md) で YAML の書き方を見る。
2. できる / できないの全体像はこの文書で確認する。
3. 厳密な validation と実装契約は [10_STRATEGY_AUTHORING_IMPLEMENTATION_SPEC.md](10_STRATEGY_AUTHORING_IMPLEMENTATION_SPEC.md) を見る。
4. 現時点の最新 capabilities と CLI chain は [08_CURRENT_CAPABILITIES.md](08_CURRENT_CAPABILITIES.md) を見る。
5. 実装差分を判断する時は tests と schema を確認し、docs だけで実装済み判定しない。

## 検証済みの現状

最新 full check では、次を確認済みです。

- `./scripts/check`: pass
- pytest: `474 passed`
- pyrefly: `0 errors`
- current-docs lint: `checked 76 current docs: links, EOF, and legacy roots ok`

docs-only 確認でも、`uv run python scripts/check_current_docs.py` が `checked 76 current docs: links, EOF, and legacy roots ok` で通っています。
