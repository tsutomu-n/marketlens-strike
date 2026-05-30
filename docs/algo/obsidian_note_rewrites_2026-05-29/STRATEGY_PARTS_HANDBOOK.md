# Strategy Parts Handbook

この文書は、原ノートから抽出した「戦略部品」を、実際に戦略を考える時に使える単位まで分解したものです。部品とは、コードのクラス名ではなく、戦略内で1つの責務を持つ機能単位です。

## 1. Universe Selector

役割: どの銘柄・市場・時間帯を監視対象にするかを決める。

何を防ぐ/改善するか: 低流動性、データ不足、上場直後だけの生存者バイアス、取引不能銘柄を避ける。

入力:
- 銘柄一覧、上場日、出来高、spread、取引所、チェーン、market cap、上場イベント。

出力:
- `watchlist`
- `excluded_with_reason`

判断ロジック例:
- BTC/ETHだけに限定する。
- 24h出来高が閾値未満なら除外する。
- Solana tokenならLP作成から一定時間未満は観測のみ。

最小の疑似実装:

```text
if volume_24h < min_volume: exclude("thin_liquidity")
elif age < min_age: observe_only("too_new")
else: include()
```

よくある誤用:
- 後から上がった銘柄だけをUniverseに入れる。
- 銘柄を増やして分散したつもりになる。

検証指標:
- 候補数、除外率、取引可能率、銘柄別DD、銘柄追加時の改善/悪化。

捨て条件:
- Universeを広げるほどノイズとDDだけが増える。

## 2. Data Collector

役割: 戦略判断に必要なデータを収集して保存する。

何を防ぐ/改善するか: 取れていないデータで検証する、liveとbacktestの粒度が違う、API障害を見逃す。

入力:
- OHLCV、order book、trades、funding、open interest、on-chain、news、token metadata。

出力:
- timestamp付きデータ
- 取得ログ
- 欠損/遅延/再接続ログ

判断ロジック例:
- 取得時刻とデータ時刻を両方保存する。
- APIエラー時に古いデータを返さず、staleとして止める。

最小の疑似実装:

```text
data = fetch()
if now - data.timestamp > freshness_limit: mark_stale()
save(data, fetched_at=now, source=source)
```

よくある誤用:
- 最新値だけ保存して、再現不能にする。
- 欠損を0や直前値で雑に埋める。

検証指標:
- 欠損率、遅延、重複率、API error rate、再取得差分。

捨て条件:
- 欠損や遅延が多く、シグナル時刻を再現できない。

## 3. Data Quality Gate

役割: データが戦略判断に使える状態かを判定する。

何を防ぐ/改善するか: 欠損、重複、未来参照、時刻ずれ、異常値で戦略が誤作動する。

入力:
- 保存済みデータ、schema、timestamp、期待頻度、source。

出力:
- `valid`
- `stale`
- `missing`
- `invalid_schema`
- `needs_rebuild`

判断ロジック例:
- 1分足に5分以上のgapがあれば、その期間のbacktestを無効化。
- on-chain日次データを分足シグナルに直接入れない。

最小の疑似実装:

```text
if missing_rate > max_missing: reject_dataset()
if any(feature_time > decision_time): reject_for_leakage()
```

よくある誤用:
- 欠損補完後のデータだけを見て問題がなかったことにする。

検証指標:
- missing_rate、duplicate_rate、schema_drift_count、leakage_check_result。

捨て条件:
- データ品質が悪く、結果の良し悪しを信用できない。

## 4. Feature Factory

役割: 生データを戦略判断に使う特徴量へ変換する。

何を防ぐ/改善するか: 生データを直接読みすぎる、未来情報を混ぜる、liveで計算できない特徴量を使う。

入力:
- OHLCV、order book、on-chain、news、token metadata、過去の取引状態。

出力:
- 特徴量テーブル
- 特徴量定義
- 利用可能時刻

判断ロジック例:
- `atr_14`, `realized_vol_24h`, `spread_bps`, `depth_1pct`, `token_age_minutes` を作る。

最小の疑似実装:

```text
feature[t] = rolling_function(data[:t])
assert feature.available_at <= decision_time
```

よくある誤用:
- 終値確定前の値を、確定済みのように使う。
- 特徴量を増やしすぎ、たまたま効いたものを採用する。

検証指標:
- 欠損率、重要度安定性、単純baselineへの寄与、walk-forward改善。

捨て条件:
- 特徴量追加でin-sampleだけ改善する。

## 5. Regime Detector

役割: 相場状態を分類し、戦略の稼働/停止/縮小を決める。

何を防ぐ/改善するか: トレンド戦略をレンジで動かす、高ボラで通常サイズを持つ、薄い市場に入る。

入力:
- MA傾き、ADX、realized volatility、spread、出来高、order book depth。

出力:
- `trend`
- `range`
- `high_vol`
- `panic`
- `thin_liquidity`
- `unknown`

判断ロジック例:
- ADX高くMA傾きがあるならtrend。
- spreadが広くdepthが薄いならthin_liquidity。
- realized volatilityが急拡大ならhigh_volまたはpanic。

最小の疑似実装:

```text
if spread_bps > max_spread or depth < min_depth: regime = "thin_liquidity"
elif realized_vol > panic_vol: regime = "panic"
elif adx > min_adx and abs(ma_slope) > min_slope: regime = "trend"
else: regime = "range"
```

よくある誤用:
- レジームを未来予測として扱う。
- 閾値を過去成績に合わせる。

検証指標:
- 状態別PnL、状態遷移頻度、skip後の回避損益、DD削減。

捨て条件:
- 判定遅れで悪い局面だけ通す。

## 6. Signal Generator

役割: エントリー候補を出す。

何を防ぐ/改善するか: 勘で入る、条件が曖昧なシグナルを使う。

入力:
- regime、特徴量、価格、出来高、order book、イベント。

出力:
- `candidate_long`
- `candidate_short`
- `no_signal`
- signal_reason
- invalidation_price

判断ロジック例:
- trend中に押し目が入り、直近安値を割らなければlong候補。
- breakout後のretestで出来高が増えればlong候補。

最小の疑似実装:

```text
if regime == "trend" and pullback_done and momentum_resumes:
    emit("candidate_long", stop=recent_swing_low)
else:
    emit("no_signal")
```

よくある誤用:
- シグナルだけで取引する。
- stopが定義されていないのにエントリーする。

検証指標:
- expectancy、entry後N本の逆行幅、trade_count、平均保有時間。

捨て条件:
- 方向は当たるが、stop距離やコストで期待値が消える。

## 7. Participation Filter

役割: シグナルが出ても入らない局面を除外する。

何を防ぐ/改善するか: 流動性不足、spread拡大、高ボラ、危険token、API障害中の取引。

入力:
- spread、depth、volatility、regime、token risk、data freshness、news risk。

出力:
- `allow`
- `skip`
- `pause`
- skip_reason

判断ロジック例:
- spreadが広いならskip。
- order book depthが薄いならサイズを落とすかskip。
- token safetyが未確認ならobserve only。

最小の疑似実装:

```text
if data_status != "valid": pause("stale_data")
elif spread_bps > max_spread: skip("wide_spread")
elif token_risk == "unsafe": skip("token_risk")
else: allow()
```

よくある誤用:
- フィルタを重ねすぎて取引が消える。
- 後から閾値を都合よく変える。

検証指標:
- skip率、skip後リターン、通過後expectancy、CVaR改善。

捨て条件:
- 良い取引だけ除外し、悪い取引を通す。

## 8. Token Safety Filter

役割: Solana/Meme tokenの売買不能、rug、凍結、権限リスクを除外する。

何を防ぐ/改善するか: 自動購入後に売れない、freezeされる、transfer feeで損をする、LPが抜かれる。

入力:
- mint authority、freeze authority、transfer fee、LP状態、holder集中、metadata、pool age、sell simulation。

出力:
- `safe_to_observe`
- `unsafe_skip`
- `needs_manual_review`
- risk_reasons

判断ロジック例:
- freeze authorityが残っていればunsafe。
- sell simulationが通らなければunsafe。
- pool ageが短すぎればobserve only。

最小の疑似実装:

```text
if freeze_authority_exists: unsafe("freezable")
elif sell_simulation_failed: unsafe("cannot_sell")
elif holder_top10_pct > max_holder_concentration: review("concentration")
else: safe_to_observe()
```

よくある誤用:
- safe_to_observeをsafe_to_buyと誤読する。
- socialあり、LPありだけで安全と判断する。

検証指標:
- 後から危険だったtokenの除外率、false safe率、売却可能性確認率。

捨て条件:
- 事前に売却可能性を確認できない。

## 9. Position Sizer

役割: どれだけ買う/売るかを決める。

何を防ぐ/改善するか: 良いシグナルでも大きすぎるサイズで破綻すること。

入力:
- account equity、risk budget、stop distance、volatility、liquidity、regime、同時ポジション。

出力:
- quantity
- max_notional
- risk_amount
- sizing_reason

判断ロジック例:
- 1取引の損失上限を資産の0.25%にする。
- stop距離が広いほど数量を小さくする。
- high_volやthin_liquidityではさらに縮小する。

最小の疑似実装:

```text
risk_amount = equity * risk_pct
qty = risk_amount / abs(entry_price - stop_price)
qty = min(qty, liquidity_cap, portfolio_cap)
if regime in ["panic", "thin_liquidity"]: qty *= 0
```

よくある誤用:
- 勝てそうな時に裁量でサイズを増やす。
- stop未定義のまま数量を出す。

検証指標:
- trade risk、portfolio risk、連敗時DD、tail loss。

捨て条件:
- 連敗やgapで想定損失を大きく超える。

## 10. Exit Module

役割: いつ減らす/利確する/損切りするかを決める。

何を防ぐ/改善するか: 利益を戻しすぎる、損失を放置する、天井当てを狙う。

入力:
- entry price、stop、ATR、保有時間、momentum、regime、含み益、order book。

出力:
- `hold`
- `reduce`
- `exit`
- new_stop
- exit_reason

判断ロジック例:
- ATR trailでstopを引き上げる。
- 一定時間進まなければtime stop。
- panic regimeなら即縮小。

最小の疑似実装:

```text
if price <= stop: exit("stop")
elif holding_time > max_holding and pnl <= 0: exit("time_stop")
elif atr_trail > stop: update_stop(atr_trail)
elif momentum_decay: reduce("decay")
```

よくある誤用:
- トレンド成熟度で天井を当てようとする。
- 利確だけ細かく、損切りが曖昧。

検証指標:
- 平均利益、最大含み益からの戻り、DD、保有時間、turnover。

捨て条件:
- 早降りが多く、大トレンド利益を削る。

## 11. Risk Guard

役割: 戦略全体を止める、縮小する、隔離する。

何を防ぐ/改善するか: API障害、連敗、急変、データ欠損、想定外ポジションで損失が拡大すること。

入力:
- daily PnL、drawdown、open exposure、error rate、data freshness、order failure、latency。

出力:
- `normal`
- `reduce_only`
- `pause_new_entries`
- `kill_switch`
- incident_reason

判断ロジック例:
- 日次損失上限到達で新規停止。
- APIエラー連発でkill switch。
- data staleでpause。

最小の疑似実装:

```text
if daily_loss < -daily_loss_limit: pause_new_entries("daily_loss")
if data_status != "valid": pause_new_entries("stale_data")
if unknown_position_detected: kill_switch("position_desync")
```

よくある誤用:
- alertだけ出して止めない。
- 例外時に注文を継続する。

検証指標:
- 停止発動回数、停止で避けた損失、false stop率、復帰時間。

捨て条件:
- 異常時に人間が何をすべきか分からない。

## 12. Execution Adapter

役割: 戦略判断を実際の注文・simulation・cancelに変換する。

何を防ぐ/改善するか: シグナルは良いのに約定で負ける、注文重複、cancel失敗、Jito/tip費用を無視する。

入力:
- order intent、size、price limit、time in force、route、risk state。

出力:
- order_id
- fill report
- reject reason
- landed/not landed
- execution cost

判断ロジック例:
- wide spreadならmarket order禁止。
- Jito routeならtip costとlanded率を記録。
- 注文前にrisk guardを再確認する。

最小の疑似実装:

```text
if risk_state != "normal": reject("risk_guard")
if spread_bps > max_market_spread and order_type == "market": reject("spread")
send_order()
record_ack_fill_cancel()
```

よくある誤用:
- backtest価格でそのまま約定したことにする。
- retryで重複注文を出す。

検証指標:
- slippage、fill rate、reject rate、latency、duplicate order count、tip cost。

捨て条件:
- 注文状態と実ポジションが同期できない。

## 13. Evaluation Harness

役割: 戦略候補を同じルールで検証し、採用/棄却を判断する。

何を防ぐ/改善するか: 良い結果だけを見て採用する、後から評価条件を変える。

入力:
- dataset、strategy config、cost model、split rule、metrics、trial log。

出力:
- scorecard
- pass/fail
- rejection_reason
- reproducible artifacts

判断ロジック例:
- train/test/walk-forwardを固定する。
- cost 2倍、slippage 2倍、期間変更、銘柄変更を必須にする。
- 試行回数を記録する。

最小の疑似実装:

```text
for split in walk_forward_splits:
    run_backtest(split, cost_model)
run_stress(cost_x=2, slippage_x=2)
if any(required_check_failed): reject()
```

よくある誤用:
- 最適化後にtest期間を選ぶ。
- 勝率やPFだけで判断する。

検証指標:
- out-of-sample expectancy、max DD、CVaR、turnover、stability、trial count。

捨て条件:
- 条件を少し変えると期待値が消える。

## 14. Monitoring Layer

役割: live/paper観測中に、データ、注文、損益、異常を監視する。

何を防ぐ/改善するか: 壊れているのに動き続ける、後から原因が分からない。

入力:
- heartbeat、data lag、API errors、order status、PnL、positions、logs。

出力:
- dashboard metrics
- alerts
- incident records
- stop signals

判断ロジック例:
- heartbeatが途切れたらpause。
- position mismatchならkill switch。
- paper signalとlive quoteの乖離を記録。

最小の疑似実装:

```text
if heartbeat_age > limit: alert_and_pause()
if position_local != position_exchange: kill_switch()
record(metric, timestamp)
```

よくある誤用:
- 可視化だけ作り、停止条件に接続しない。

検証指標:
- alert latency、incident count、false alert率、検知から停止までの時間。

捨て条件:
- 異常が起きても原因を追跡できない。

## 15. Research Assistant

役割: ニュース、論文、動画、ノートから仮説候補を作る。

何を防ぐ/改善するか: 面白い情報を即売買シグナルにすること。

入力:
- news、GitHub、docs、YouTubeメモ、SNS、研究ノート。

出力:
- hypothesis
- source
- confidence
- required_data
- validation_plan

判断ロジック例:
- ニュースは売買ではなくevent studyへ送る。
- AI/agent出力は必ず一次情報で確認する。

最小の疑似実装:

```text
claim = extract_claim(source)
if source_type in ["Medium", "YouTube"]: require_primary_verification()
create_hypothesis_card(claim, required_data, rejection_rule)
```

よくある誤用:
- AIが出した戦略をそのまま実装する。
- アフィリエイト記事を市場優位性と混同する。

検証指標:
- 仮説採用率、棄却率、一次情報確認率、後続実験化率。

捨て条件:
- 出典と反証条件がない。
