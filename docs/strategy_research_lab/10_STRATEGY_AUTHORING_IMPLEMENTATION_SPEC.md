# Strategy Authoring Implementation Spec

`strategy_authoring_spec.v1` は、ユーザーが宣言型 YAML で Strategy Lab signal を作るための interface です。

## Public CLI

```bash
uv run sis strategy-author-init --template trend_pullback --out PATH
uv run sis strategy-author-validate --spec PATH
uv run sis strategy-author-explain --spec PATH --out PATH
uv run sis strategy-author-run --spec PATH --through signals
uv run sis strategy-author-run --spec PATH --through backtest
uv run sis strategy-author-run --spec PATH --through paper-preview
uv run sis strategy-author-train-model --spec PATH --target-column COLUMN --feature-column COLUMN --out-spec PATH
uv run sis strategy-author-bundle-run --bundle PATH
```

`--through` は段階実行です。後段を指定すると前段も実行します。

## Source Of Truth

新 authoring flow の signal 正本は `data/research/strategy_signals.parquet` です。`data/research/signals.csv` は互換用 legacy export です。

backtest は `strategy_signals.parquet` から `ResearchSignal` へ変換し、既存 backtest bridge に渡します。`build-backtest` の legacy CSV default には依存しません。

## YAML Sections

- `experiment`: strategy id、family、version、symbol bindings、run profile
- `data`: feature panel、quote parquet、cost model
- `rules`: side、side_column、timeframe、entry / long_entry / short_entry / hold / close / reduce / add / rebalance conditions、exit rules、sizing rules、order simulation、bracket/OCO lifecycle、execution quality、portfolio throttle、position state controls、temporal controls、event windows、cross-sectional selection、score、confidence、reason code
- `backtest`: split method、era unit、fixed horizon、purge、embargo、min trade count
- `promotion`: paper-preview の既定 decision

## Validation

validation は次を stop condition にします。

- YAML root が object ではない
- schema version が `strategy_authoring_spec.v1` ではない
- feature panel が存在しない
- rule / score が参照する column が feature panel に存在しない
- `rules.score.model_score.coefficients` が空
- `rules.score.model_score.intercept`, `missing_value`, score weight が finite number ではない
- hold rule が参照する column が feature panel に存在しない
- close rule が参照する column が feature panel に存在しない
- reduce rule または `rules.exit.reduce_fraction_column` が参照する column が feature panel に存在しない
- add rule または `rules.exit.add_fraction_column` が参照する column が feature panel に存在しない
- condition の `value_column` が feature panel に存在しない
- condition group の `all`, `any`, `none` がすべて空
- `rules.derived_features[].columns` が feature panel または先行 derived feature に存在しない
- `rules.derived_features[].name` が重複している
- rolling derived feature の `window` が 0 以下または未指定
- `side_column`, `long_entry`, `short_entry`, exit `*_column`, sizing `*_column` が参照する column が feature panel に存在しない
- `symbol_bindings.real_market_symbol` の row が feature panel に存在しない
- `backtest.label_horizon_minutes` が 0 以下
- `rules.confidence` が 0.0 から 1.0 の範囲外
- `rules.exit.stop_loss_bps` / `take_profit_bps` が負数
- `rules.exit.trailing_stop_bps` / `partial_take_profit_bps` が負数
- `rules.exit.partial_exit_fraction` が 0.0 から 1.0 の範囲外
- `rules.exit.reduce_fraction` が 0.0 から 1.0 の範囲外
- `rules.reduce` があるのに `rules.exit.reduce_fraction` / `reduce_fraction_column` のどちらも無い
- `rules.exit.add_fraction` が 0.0 から 1.0 の範囲外
- `rules.add` があるのに `rules.exit.add_fraction` / `add_fraction_column` のどちらも無い
- `rules.sizing.position_weight` / `notional_usd` が負数
- `rules.sizing.volatility_target` が 0 以下
- `rules.sizing.volatility_target` があるのに `volatility_column` が無い、空、または feature panel に存在しない
- `rules.sizing.max_volatility_scaled_position_weight` が負数
- `rules.order.entry_type=limit` なのに `limit_offset_bps` が無い
- `rules.order.entry_type=stop_market` なのに `stop_offset_bps` が無い
- `rules.order.limit_offset_bps` / `stop_offset_bps` / `timeout_minutes` が負数
- `rules.bracket.time_stop_minutes` / `break_even_after_bps` が負数
- `rules.bracket.enabled=true` なのに stop / take / trailing / time stop / break-even stop のいずれも無い
- `rules.execution.slippage_bps` が負数
- `rules.execution.max_fill_fraction` が 0.0 から 1.0 の範囲外
- `rules.execution.max_spread_bps` / `min_depth_usd` が負数
- `rules.execution.depth_column` が空文字
- `rules.execution.depth_participation_rate` が 0.0 から 1.0 の範囲外
- `rules.portfolio.max_signals_per_timestamp` が 0 以下
- `rules.portfolio.max_total_position_weight` / `max_long_position_weight` / `max_short_position_weight` / `max_symbol_position_weight` が負数
- `rules.portfolio.allocation_method` が `none`, `equal_weight`, `score_proportional`, `inverse_volatility` 以外
- `rules.portfolio.allocation_method` が `none` 以外なのに `target_total_position_weight` が無い
- `rules.portfolio.target_total_position_weight` が負数
- `rules.portfolio.allocation_method=inverse_volatility` なのに `allocation_volatility_column` が無い、空、または feature panel に存在しない
- `rules.position.max_open_signals_per_symbol` が 0 以下
- `rules.position.max_open_position_weight_per_symbol` が負数
- `rules.position.holding_horizon_minutes` が 0 以下
- `rules.risk_throttle` の column と threshold が片方だけ指定されている
- `rules.risk_throttle.*_column` が空または feature panel に存在しない
- `rules.risk_throttle.max_loss_streak` が 0 以下
- `rules.temporal.allowed_weekdays_utc` が 0 から 6 の範囲外
- `rules.temporal.allowed_hours_utc` が 0 から 23 の範囲外
- `rules.temporal.cooldown_minutes` が負数
- `rules.temporal.max_signals_per_symbol_per_day` が 0 以下
- `rules.event_windows[].event_ts_column` が feature panel に存在しない
- `rules.event_windows[].name` が空または重複している
- `rules.event_windows[].before_minutes` / `after_minutes` が負数
- `rules.event_windows[].block_reason` が空文字
- `rules.cross_sectional.long_top_n` / `short_bottom_n` が 0 以下
- `rules.cross_sectional` があるのに `rules.score.weighted_sum` と `rules.score.model_score` の両方が空
- `rules.multi_leg.enabled=true` なのに `anchor_real_market_symbol` または `legs` が無い
- `rules.multi_leg.legs[].real_market_symbol` が `experiment.symbol_bindings` に存在しない
- `rules.multi_leg.legs[].position_weight` / `notional_usd` が負数
- `rules.multi_leg.legs[].position_weight_column` / `notional_usd_column` が空または feature panel に存在しない
- `rules.regime_overrides[].when` が空
- `rules.regime_overrides[]` の risk / sizing / execution override 値が負数または 0.0 から 1.0 範囲外
- `rules.regime_overrides[].name` が重複している
- `rules.side=auto` なのに `side_column`, `long_entry`, `short_entry`, `cross_sectional` のいずれも無い

## Signal Compilation

compiler は feature panel を `canonical_symbol`, `ts` で sort し、symbol binding の `real_market_symbol` に一致する row だけを評価します。

`rules.derived_features` がある場合は、entry / hold / score / side 判定より前に strategy-local column を追加します。row-wise op は `add`, `sub`, `mul`, `div`, `ratio`, `diff`, `pct_diff`, `abs`, `neg`, `max`, `min`, `mean`、rolling op は `rolling_mean`, `rolling_std`, `rolling_zscore` です。rolling op は `canonical_symbol` ごとに `ts` 順で評価します。任意式、任意 Python、外部コード実行はしません。

entry 判定は `all AND any AND none` です。`all` は全条件 true、`any` は空なら true・非空なら 1 つ以上 true、`none` は全条件 false の時に true です。`gt` / `gte` / `lt` / `lte` / `eq` / `neq` は `value` または `value_column` のどちらか 1 つだけを右辺に取れます。`in` / `not_in` は non-empty list の membership 判定です。

hold 判定は entry より先に評価します。hold 条件を満たした row は `side: none`、`block_reasons: ["hold_rule"]`、`reason_codes: [rules.hold_reason_code]` の `strategy_signal.v1` として記録します。これは「見送り」の研究記録であり、`ResearchSignal` 変換と backtest の売買対象からは除外します。

close 判定は hold / entry より先に評価します。close 条件を満たした row は `side: close`、`reason_codes: [rules.close_reason_code]` の `strategy_signal.v1` として記録します。close signal は entry としては評価せず、`rules.exit.exit_on_close_signal=true` の既存 entry signal を fixed horizon より前に閉じるための paper-only exit marker として使います。

reduce 判定は close / hold / entry より先に評価します。reduce 条件を満たした row は `side: reduce`、`reason_codes: [rules.reduce_reason_code]`、`reduce_fraction` の `strategy_signal.v1` として記録します。reduce signal は entry としては評価せず、`rules.exit.exit_on_reduce_signal=true` の既存 entry signal を fixed horizon より前に一部縮小するための paper-only exit marker として使います。

add 判定は close / reduce / hold / entry より先に評価します。add 条件を満たした row は `side: add`、`reason_codes: [rules.add_reason_code]`、`add_fraction` の `strategy_signal.v1` として記録します。add signal は独立 entry としては評価せず、`rules.exit.exit_on_add_signal=true` の既存 entry signal に追加入りするための paper-only scale-in marker として使います。

rebalance 判定は close / reduce / add / hold / entry より先に評価します。rebalance 条件を満たした row は `side: rebalance`、`reason_codes: [rules.rebalance_reason_code]`、`rebalance_target_fraction` の `strategy_signal.v1` として記録します。rebalance signal は独立 entry としては評価せず、`rules.exit.exit_on_rebalance_signal=true` の既存 entry signal を paper target exposure へ寄せる resize marker として使います。target が現在の paper exposure より小さい場合は reduce、大きい場合は add として評価します。

`rules.side=auto` では row ごとの方向を決めます。優先順は `hold`、`long_entry` / `short_entry`、`side_column`、通常 `entry` です。`long_entry` と `short_entry` が同時に true の場合は `side: none`、`block_reasons: ["ambiguous_side"]` として記録し、売買対象から除外します。

`rules.risk_throttle` がある場合は、entry / side / event window 判定後、multi-leg 展開前に feature row の risk state を評価します。

- `max_drawdown_column <= max_drawdown_floor` なら `risk_throttle_max_drawdown` で block する。
- `daily_loss_column <= daily_loss_floor` なら `risk_throttle_daily_loss` で block する。
- `loss_streak_column >= max_loss_streak` なら `risk_throttle_loss_streak` で block する。
- risk throttle block は signal を削除せず、`side: none` として残し、backtest の売買対象から除外する。

`rules.multi_leg.enabled=true` の場合は、`anchor_real_market_symbol` の feature row だけを entry / hold / score 判定に使い、通過した trade signal を `legs` に展開します。`side=same` は anchor signal side と同方向、`side=opposite` は反対方向へ解決します。leg の `position_weight` は global `sizing.position_weight` に掛け、`position_weight_column` がある場合は feature row の値を row ごとの leg multiplier として優先します。leg `notional_usd_column` がある場合は feature row の値を leg notional として優先します。leg `notional_usd` が無い場合は global `notional_usd * leg multiplier` を使います。これは paper-only の leg 展開であり、broker の atomic multi-leg order や live rebalance ではありません。

`rules.regime_overrides` がある場合は、trade signal row の risk / sizing / execution 値を作る時に上から順に `when` を評価し、最初に一致した override を適用します。override できる値は exit bps、partial exit fraction、position weight、notional、slippage、fill fraction、spread/depth threshold、depth participation です。`*_column` がある exit / sizing 値は row の dynamic column 値を優先します。一致した regime は `reason_codes` に `regime:<name>` として残します。

通過 row は `strategy_signal.v1` row へ変換されます。

- `execution_symbol` は symbol binding から決める
- `real_market_symbol` は feature panel の `canonical_symbol`
- `reason_codes` は `rules.reason_code`
- `parameter_hash` は YAML payload の stable hash
- `confidence` は `rules.confidence`
- `stop_loss_bps` / `take_profit_bps` / `trailing_stop_bps` / `partial_take_profit_bps` / `partial_exit_fraction` / `exit_on_opposite_signal` / `exit_on_close_signal` / `exit_on_reduce_signal` / `exit_on_add_signal` は `rules.exit` から引き継ぐ。`*_column` がある場合は row の column 値を優先し、空なら固定値へ fallback する。
- `bracket_type` / `bracket_time_stop_minutes` / `bracket_break_even_after_bps` は `rules.bracket` から引き継ぐ。`rules.bracket.enabled=false` の場合は `bracket_type=none` とする。
- `position_weight` / `notional_usd` は `rules.sizing` から引き継ぐ。`position_weight` は backtest return の paper weight として使う。
- `rules.sizing.volatility_target` がある場合は、row の `volatility_column` が正の数値なら `position_weight * volatility_target / volatility_column` へ変換し、`max_volatility_scaled_position_weight` があれば上限で cap する。volatility が欠損または 0 以下なら base `position_weight` を使う。
- `entry_order_type` / `entry_limit_offset_bps` / `entry_stop_offset_bps` / `entry_timeout_minutes` は `rules.order` から引き継ぐ。
- `slippage_bps` / `max_fill_fraction` / `max_spread_bps` / `min_depth_usd` / `depth_column` / `depth_participation_rate` は `rules.execution` から引き継ぐ。
- `portfolio.max_signals_per_timestamp` がある場合は、同一 `ts_signal` の trade signal を `rank_score` 降順で上位 N 件に制限する。hold / ambiguous signal は記録として残す。
- `portfolio.allocation_method=equal_weight` / `score_proportional` / `inverse_volatility` がある場合は、同一 `ts_signal` の採用候補の `position_weight` を `target_total_position_weight` に正規化する。`score_proportional` は正の `raw_score` 比例で配分し、全 score が 0 以下または欠損なら equal weight に fallback する。`inverse_volatility` は `allocation_volatility_column` の正の値の逆数で配分し、全 volatility が 0 以下または欠損なら equal weight に fallback する。
- `portfolio.max_total_position_weight` / `max_long_position_weight` / `max_short_position_weight` / `max_symbol_position_weight` がある場合は、同一 `ts_signal` の trade signal を `rank_score` 降順で採用し、超過候補を `side: none`、`block_reasons` に `portfolio_total_exposure_limit`, `portfolio_long_exposure_limit`, `portfolio_short_exposure_limit`, `portfolio_symbol_exposure_limit` のいずれかを残す。

`rules.cross_sectional` がある場合は、entry 通過後の同一 `ts_signal` 候補を `raw_score` で順位化します。

- `long_top_n` は上位 N 件を `side: long` にする
- `short_bottom_n` は下位 N 件を `side: short` にする
- top と bottom が重なる場合は top を優先し、同じ row を long/short 両方にはしない
- score が無い row は `side: none`、`block_reasons: ["cross_sectional_score_missing"]` にする
- 選抜されない中間 row は `side: none`、`block_reasons: ["cross_sectional_rank_filter"]` にする
- `rank_score` / `percentile_rank` は timestamp 内の相対順位へ更新する

`rules.temporal` がある場合は、cross-sectional selection の後、portfolio timestamp throttle の前に trade signal を cadence filter へ通します。

- `allowed_weekdays_utc` は `ts_signal.weekday()` で評価する。0 が月曜、6 が日曜。
- `allowed_hours_utc` は `ts_signal.hour` で評価する。
- `cooldown_minutes` は同じ `execution_symbol` の前回採用 signal から指定分数未満なら block する。
- `max_signals_per_symbol_per_day` は同じ `execution_symbol` と UTC date の採用数上限として評価する。
- temporal block は signal を削除せず、`side: none`、`block_reasons` に `temporal_weekday_filter`, `temporal_hour_filter`, `temporal_cooldown`, `temporal_symbol_daily_limit` のいずれかを残す。
- temporal block は backtest の売買対象から除外する。

`rules.position` がある場合は、temporal selection の後、portfolio timestamp throttle の前に同一 `execution_symbol` の仮想 open signal を評価します。

- open window は `rules.position.holding_horizon_minutes` があればそれを使い、なければ `backtest.label_horizon_minutes` を使う。
- `max_open_signals_per_symbol` は同一 execution symbol の open signal 数上限として評価する。
- `max_open_position_weight_per_symbol` は同一 execution symbol の open `position_weight` 合計上限として評価する。
- position block は signal を削除せず、`side: none`、`block_reasons` に `position_open_signal_limit` または `position_open_weight_limit` を残す。
- これは paper-only の selection rule であり、broker position や live portfolio state は読まない。

`rules.event_windows` がある場合は、entry / side 判定後、multi-leg 展開前に event timestamp column を評価します。

- `event_ts_column` は feature panel の `datetime` または ISO 8601 string を使う。
- `mode=allow` は `event_ts - before_minutes` から `event_ts + after_minutes` の範囲内だけを採用する。
- `mode=allow` で範囲外なら `block_reasons` に `<block_reason>_outside`、event 欠損なら `<block_reason>_missing` を残す。
- `mode=block` は範囲内だけを block し、event 欠損は block しない。
- `block_reason` が未指定なら `event_window_<name>` を使う。
- event block は signal を削除せず、`side: none` として残し、backtest の売買対象から除外する。

## Backtest

`strategy-author-run --through backtest` は fixed horizon で評価します。

- entry quote は `ts_client >= ts_signal` の最初の quote
- `rules.order.entry_type=market` は entry quote で約定したものとして評価する
- `rules.order.entry_type=limit` は long なら entry quote より `limit_offset_bps` 安い価格、short なら高い価格に達した最初の quote を entry とする
- `rules.order.entry_type=stop_market` は long なら entry quote より `stop_offset_bps` 高い価格、short なら低い価格に達した最初の quote を entry とする
- `rules.order.timeout_minutes` を過ぎても entry 条件に到達しない場合は未約定とし、`summary.entry_order_unfilled_count` と `blocked_reason_counts.entry_order_unfilled` に記録する
- exit quote は entry quote から `label_horizon_minutes` 後以降の最初の quote
- `rules.exit.stop_loss_bps` / `take_profit_bps` がある場合は、fixed horizon までの quote を順に見て最初に到達した stop loss / take profit を exit として使う
- `rules.exit.stop_loss_bps_column` / `take_profit_bps_column` がある場合は、signal row ごとの bps を使う
- `trailing_stop_bps` は fixed horizon までの最良含み益からの戻り幅で exit する
- `partial_take_profit_bps` / `partial_exit_fraction` は一部利確 leg と残り leg を合成して return を計算する
- `rules.bracket.enabled=true` の場合、stop loss / take profit の exit reason は `bracket_stop_loss` / `bracket_take_profit` として記録する
- `rules.bracket.break_even_after_bps` がある場合、指定 bps 以上の含み益到達後に return が 0 以下へ戻ると `bracket_break_even_stop` で exit する
- `rules.bracket.time_stop_minutes` がある場合、entry quote から指定分数後以降の最初の quote で残り position を `bracket_time_stop` として exit する
- bracket は paper-only OCO lifecycle であり、実 broker の bracket / OCO order は作らない
- `rules.execution.slippage_bps` は round trip の追加 drag として return から差し引き、`cost_drag_bps` に足す
- `rules.execution.max_fill_fraction` は `position_weight` と掛け合わせて exposure を縮小する
- `rules.execution.max_spread_bps` は entry quote の `spread_bps` が指定値を超える場合に entry を paper-only で block する
- `rules.execution.min_depth_usd` は entry quote の `depth_column` を確認し、不足または欠損なら entry を paper-only で block する
- `rules.execution.depth_participation_rate` と signal の `notional_usd` がある場合、depth から取れる想定数量で paper exposure をさらに縮小する
- `exit_on_opposite_signal=true` の場合、同一 execution symbol の反対方向シグナルが fixed horizon より先に来たら、その時刻以降の最初の quote を exit とし、`summary.exit_reason_counts.opposite_signal` に記録する
- `exit_on_close_signal=true` の場合、同一 execution symbol の `side: close` signal が fixed horizon より先に来たら、その時刻以降の最初の quote を exit とし、`summary.exit_reason_counts.close_signal` に記録する。close signal 自体は trade entry として評価しない
- `exit_on_reduce_signal=true` の場合、同一 execution symbol の `side: reduce` signal が fixed horizon より先に来たら、その時刻以降の最初の quote で `reduce_fraction` 分だけ部分 exit し、残り position は horizon / stop / take profit まで維持する。`summary.exit_reason_counts` には `reduce_signal` を含む exit reason を記録する。reduce signal 自体は trade entry として評価しない
- `exit_on_add_signal=true` の場合、同一 execution symbol の `side: add` signal が fixed horizon より先に来たら、その時刻以降の最初の quote で `add_fraction` 分だけ追加入りし、元 position と追加分を同じ exit lifecycle で評価する。`summary.exit_reason_counts` には `add_signal` を含む exit reason を記録する。add signal 自体は独立 trade entry として評価しない
- `exit_on_rebalance_signal=true` の場合、同一 execution symbol の `side: rebalance` signal が fixed horizon より先に来たら、その時刻以降の最初の quote で `rebalance_target_fraction` の target exposure に寄せる。target が現在値より小さい場合は縮小、大きい場合は追加入りとして paper return に反映する。`summary.exit_reason_counts` には `rebalance_signal` を含む exit reason を記録する。rebalance signal 自体は独立 trade entry として評価しない
- `position_weight` は signal return に掛ける。これは paper backtest の重みであり、live position size ではない
- cost は `data.cost_model_path` が存在すれば使い、無ければ quote spread fallback を使う
- metrics は既存 `BacktestMetrics` を JSON と Markdown に出す
- exit reason count は `summary.exit_reason_counts` に出す
- `split_method=walk_forward` / `purged_walk_forward` は `summary.walk_forward_eras` に era ごとの signal count / aggregate metrics を出す
- `optimizer.parameter_sweep` がある場合は、許可された spec path だけを grid sweep し、`summary.optimizer.variants` と `summary.optimizer.best_variant` に paper-only 比較結果を出す
- `pass_thresholds` は aggregate metrics と比較し、`summary.pass_thresholds`, `summary.pass_all_thresholds`, `summary.backtest_passed` に出す
- `summary.backtest_passed` は `min_trade_count` と `pass_thresholds` の両方を満たした場合だけ true

optimizer は任意式や任意 Python を実行しません。許可 path は `rules.confidence`, `rules.exit.*bps`, `rules.exit.partial_exit_fraction`, `rules.sizing.position_weight`, `rules.portfolio.max_signals_per_timestamp`, `rules.temporal.cooldown_minutes`, `rules.temporal.max_signals_per_symbol_per_day`, `rules.cross_sectional.long_top_n`, `rules.cross_sectional.short_bottom_n`, `backtest.label_horizon_minutes` です。

## Score Model Adapter

`rules.score.model_score` は v1 では paper-only の線形 score adapter です。学習、外部 model load、pickle 実行、任意 Python 実行はしません。

- `model_type=linear` のみ許可する
- `raw_score = weighted_sum + activation(intercept + sum(column * weight))`
- `weighted_sum` が無い場合も `model_score` だけで `raw_score` を作れる
- `activation` は `identity`, `sigmoid`, `tanh`, `clamp_0_1`
- `missing_value` が `null` の場合、非数値または欠損の coefficient term は無視する
- `missing_value` が number の場合、非数値または欠損の coefficient term はその値で補う
- `rules.cross_sectional` は `weighted_sum` または `model_score` のどちらかがあれば使える

`strategy-author-train-model` は feature panel から `model_score` を生成する paper-only helper です。

- `target_column` と `feature_column` は feature panel に存在する必要がある
- `symbol_bindings.real_market_symbol` に一致する row だけを使う
- target と feature が numeric の row だけを使う
- ordinary least squares に `ridge_lambda` を加えた normal equation を解く
- 出力 JSON は `strategy_authoring_model_score.v1`
- `--out-spec` がある場合は `rules.score.model_score` を埋めた YAML spec を書く
- 外部 model artifact load、pickle、任意 Python、live order、broker write は実行しない

## Multi Strategy Bundle

`strategy_authoring_bundle.v1` は複数の `strategy_authoring_spec.v1` を paper-only portfolio として比較します。

- `members[].spec_path` は bundle YAML からの相対 path または絶対 path
- `members[].allocation_weight` は paper aggregation 用の重み
- `portfolio.allocation_method=fixed_weight` は `members[].allocation_weight` を使う
- `portfolio.allocation_method=equal_weight` は enabled member を均等配分する
- `portfolio.allocation_method=risk_parity` は member の paper `max_drawdown` の絶対値を risk proxy とし、逆数配分する
- `portfolio.max_total_allocation_weight` がある場合、合計 weight が cap を超えないよう比例縮小する
- 各 member は既存の authoring validate / signal build / backtest をそのまま通す
- 出力は `strategy_authoring_bundle_result.v1`
- `weighted_total_return` は member の `total_return * effective_allocation_weight` の合計

出力 artifact:

- `data/research/strategy_authoring_bundle_result.json`
- `data/reports/strategy_authoring_bundle_report.md`

## Paper Preview

`strategy-author-run --through paper-preview` は paper-only artifact を出します。

- `trial_ledger.jsonl`
- `paper_candidate_pack.json`
- `promotion_decision.json`
- `paper_intent_preview.json`

既定 decision は `hold` です。operator review を挟むため、既定では `paper_intent_preview.json` は空配列です。

## Non Goals

- live order submission
- wallet access
- exchange write
- arbitrary Python plugin
- arbitrary expression eval
- arbitrary / external ML training
- external model artifact loading
- external model loading / pickle execution
- live bracket / OCO order submission
- live portfolio optimizer
- unbounded / arbitrary parameter optimizer
- profitability guarantee
