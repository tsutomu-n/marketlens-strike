# Strategy Parts Deep Dive

この文書は、`STRATEGY_PARTS_HANDBOOK.md` をさらに具体化したものです。戦略部品を「名前」ではなく、実際にテーブル、判定、検証へ落とすための詳細メモです。

数値は初期例です。実装時の採用値ではなく、検証で反証するための仮置きです。

## 1. 部品はどの順で動くか

基本の流れは次です。

```text
Universe Selector
  -> Data Collector
  -> Data Quality Gate
  -> Feature Factory
  -> Regime Detector
  -> Signal Generator
  -> Participation Filter
  -> Position Sizer
  -> Exit Module
  -> Execution Adapter
  -> Risk Guard / Monitoring Layer
  -> Evaluation Harness
```

重要なのは、`Signal Generator` より前に `Data Quality Gate` と `Regime Detector` があることです。多くの失敗は、シグナルが悪いのではなく、使うべきでないデータ・相場・銘柄でシグナルを動かすことで起きます。

## 2. 最小データスキーマ

### 2.1 OHLCV

| column | 意味 | 注意 |
|---|---|---|
| `symbol` | 銘柄 | 後から生き残った銘柄だけにしない |
| `ts_open` | 足の開始時刻 | timezoneを固定する |
| `ts_close` | 足の終了時刻 | close前に使うとリーク |
| `open/high/low/close` | 価格 | exchange/sourceを記録 |
| `volume` | 出来高 | quote/baseどちらか明記 |
| `fetched_at` | 取得時刻 | liveで利用可能だったかの判定に使う |
| `source` | 取得元 | API変更や差分確認に使う |

### 2.2 Order Book Summary

| column | 意味 | 使い道 |
|---|---|---|
| `best_bid/best_ask` | 最良気配 | spread計算 |
| `spread_bps` | spreadのbps | Participation Filter |
| `bid_depth_1pct/ask_depth_1pct` | 1%以内の厚み | Size Cap |
| `imbalance_1pct` | bid/askの偏り | 逆選択警戒 |
| `book_ts` | 板時刻 | 遅延検査 |
| `snapshot_id` | snapshot識別子 | delta欠落検査 |

### 2.3 Signal Candidate

| column | 意味 |
|---|---|
| `decision_time` | 判断時刻 |
| `symbol` | 銘柄 |
| `side` | long/short/observe |
| `reason` | 発火理由 |
| `entry_ref` | 参照価格 |
| `invalidation_price` | シナリオが壊れる価格 |
| `regime` | 判断時の相場状態 |
| `data_status` | valid/stale/missing |

### 2.4 Execution Report

| column | 意味 |
|---|---|
| `intent_id` | 戦略側の注文意図ID |
| `order_id` | 取引所側ID |
| `submitted_at` | 送信時刻 |
| `ack_at` | ack時刻 |
| `filled_at` | 約定時刻 |
| `expected_price` | 戦略上の想定価格 |
| `filled_price` | 実約定価格 |
| `slippage_bps` | 想定との差 |
| `reject_reason` | reject/cancel理由 |

## 3. Regime Detector の具体化

### 3.1 役割

Regime Detectorは「上がる/下がる」を予測する部品ではありません。今の戦略を通常稼働してよいか、縮小すべきか、停止すべきかを決める部品です。

### 3.2 例の判定

```text
if data_status != "valid":
    regime = "unknown"
elif spread_bps > 8 or depth_1pct < order_notional * 20:
    regime = "thin_liquidity"
elif realized_vol_1h > percentile_95_lookback:
    regime = "panic"
elif adx_14 > 25 and abs(ma_slope_50) > min_slope:
    regime = "trend"
else:
    regime = "range"
```

### 3.3 よくある失敗

- `trend` 判定が出た後に「だから上がる」と解釈する。
- 閾値を過去成績に合わせて、未来で機能しない。
- `unknown` を `normal` と同じ扱いにする。

### 3.4 検証

見るべきもの:

- regime別のtrade count
- regime別のexpectancy
- `range` で避けた損失
- `trend` と判定した直後の逆行幅
- regime切替頻度

合格例:

- `range` と `thin_liquidity` を除外した時、取引数は減るがDDも下がる。
- `panic` 時に新規停止すると、tail lossが下がる。

不合格例:

- skip率が高いだけで、通した取引の期待値が改善しない。

## 4. Signal Generator の具体化

### 4.1 役割

Signal Generatorは「候補」を出すだけです。ここで注文してはいけません。signalは、Participation Filter、Position Sizer、Risk Guardを通って初めて注文候補になります。

### 4.2 Trend Pullback Signal

```text
precondition:
  regime == "trend"
  data_status == "valid"

long candidate:
  close > ma_50
  ma_50_slope > 0
  price pulled back near ma_20 or prior breakout level
  short momentum turns up
  invalidation_price = recent_swing_low
```

出力:

```text
candidate_long
reason = "trend_pullback_resume"
entry_ref = current_mid
invalidation_price = recent_swing_low
```

### 4.3 誤用

- invalidation priceなしでcandidateを出す。
- signalを複数重ねて、確信度が高いと見なす。
- signalが出た回数だけを見て、entry後の逆行幅を見ない。

## 5. Participation Filter の具体化

### 5.1 役割

Participation Filterは「いいシグナルでも入らない」ための部品です。損失を減らす部品なので、利益を増やす部品だと誤解しない方がよいです。

### 5.2 判定順

```text
if data_status != "valid":
    pause("stale_or_missing_data")
elif regime in ["panic", "thin_liquidity", "unknown"]:
    skip("bad_regime")
elif spread_bps > max_spread:
    skip("wide_spread")
elif expected_slippage_bps > max_slippage:
    skip("slippage")
elif token_safety in ["unsafe", "needs_manual_review"]:
    skip("token_risk")
else:
    allow()
```

### 5.3 評価の見方

Participation Filterは、通した取引だけでなく、skipした取引も追跡します。

必要な比較:

- filterなしPnL
- filterありPnL
- skipされた取引の仮想PnL
- skip理由別の損益

良いfilter:

- skip後の仮想PnLが悪い。
- 通過後のtail lossが下がる。

悪いfilter:

- skipした取引の方が良かった。
- skip率が高すぎてtrade countが消える。

## 6. Position Sizer の具体化

### 6.1 役割

Position Sizerは「勝てそうだから大きく張る」部品ではありません。負けた時の損失を事前に決める部品です。

### 6.2 基本式

```text
risk_amount = equity * risk_per_trade
stop_distance = abs(entry_ref - invalidation_price)
raw_qty = risk_amount / stop_distance
qty = min(raw_qty, liquidity_cap, portfolio_cap)
```

例:

```text
equity = 1,000,000 JPY
risk_per_trade = 0.0025
risk_amount = 2,500 JPY
entry_ref = 10,000
invalidation_price = 9,750
stop_distance = 250
raw_qty = 10 units
```

### 6.3 追加制限

- `thin_liquidity`: qty = 0
- `panic`: qty = 0
- `high_vol`: qty *= 0.5
- `after_loss_streak`: qty *= 0.5
- `portfolio_exposure_near_limit`: qtyをさらに制限

### 6.4 よくある失敗

- stopが遠いのに同じ数量で入る。
- stopを後から広げる。
- 流動性capを見ずにサイズを出す。
- ML確率が高い時にサイズを増やす。

## 7. Exit Module の具体化

### 7.1 Exitは4種類に分ける

| 種類 | 目的 | 例 |
|---|---|---|
| Invalidation exit | 仮説が壊れたら切る | swing low割れ |
| Risk exit | 損失や急変で切る | daily loss、panic |
| Profit protection | 利益を守る | ATR trail、partial exit |
| Time exit | 進まない取引を閉じる | N本経過で撤退 |

### 7.2 判断例

```text
if price <= invalidation_price:
    exit("invalidation")
elif daily_loss_limit_hit:
    exit("risk_guard")
elif holding_bars > max_holding_bars and pnl <= 0:
    exit("time_stop")
elif atr_trail > current_stop:
    update_stop(atr_trail)
```

### 7.3 評価

- 平均利益
- 平均損失
- 最大含み益からの戻り
- 大トレンドの取り逃し
- 取引回数増加による手数料増

## 8. Token Safety Filter の具体化

### 8.1 役割

Token Safety Filterは、Solana/Meme tokenで「買ってはいけないもの」を除外する部品です。`safe_to_observe` は `safe_to_buy` ではありません。

### 8.2 判定項目

| 判定 | 入力 | 危険な状態 |
|---|---|---|
| Mint Authority | mint情報 | 追加発行可能 |
| Freeze Authority | mint情報 | 凍結可能 |
| Transfer Fee | token extension | 売買コスト不明 |
| Holder Concentration | holder分布 | 上位wallet集中 |
| LP/Pool | pool情報 | 流動性不足/抜ける可能性 |
| Sell Simulation | simulation | 売却失敗 |

### 8.3 判定順

```text
if freeze_authority_exists:
    unsafe("freezable")
elif mint_authority_exists:
    review("mintable")
elif sell_simulation_failed:
    unsafe("cannot_sell")
elif lp_depth < min_lp_depth:
    unsafe("thin_lp")
elif top_holder_pct > max_top_holder_pct:
    review("holder_concentration")
else:
    safe_to_observe()
```

### 8.4 検証

買わずに観測し、後から危険だったtokenをどれだけ除外できたかを見る。

必要なラベル:

- 価格が短時間で大幅下落
- 売却不能
- LP消失
- 凍結/転送不可
- holder集中からの売り

## 9. Execution Adapter の具体化

### 9.1 役割

Execution Adapterは、戦略判断を注文に変換する最後の関門です。ここで必ずRisk Guardを再確認します。

### 9.2 注文前チェック

```text
if risk_state != "normal":
    reject("risk_state")
if data_status != "valid":
    reject("stale_data")
if order_qty <= 0:
    reject("zero_qty")
if expected_slippage_bps > max_slippage:
    reject("slippage")
```

### 9.3 注文状態

最低限、次の状態を区別します。

- `created`
- `submitted`
- `acknowledged`
- `partially_filled`
- `filled`
- `cancel_requested`
- `cancelled`
- `rejected`
- `unknown`

`unknown` を放置してはいけません。position同期が取れるまで新規注文を止めます。

## 10. Evaluation Harness の具体化

### 10.1 採用の前に捨てる

評価は、良い結果を探す作業ではありません。悪条件で壊れる候補を捨てる作業です。

### 10.2 必須テスト

| テスト | 目的 |
---|---|
| Walk-forward | 時系列外で残るか |
| Cost x2 | 手数料に弱すぎないか |
| Slippage x2 | 約定前提が甘くないか |
| Different symbols | 銘柄固有の偶然ではないか |
| Different periods | 期間固有の偶然ではないか |
| Parameter neighborhood | 最適点だけではないか |
| Monte Carlo | 取引順序や偶然に弱すぎないか |

### 10.3 Scorecardに残す項目

- 仮説
- 使用部品
- 使ったデータ期間
- 除外したデータ
- cost/slippage前提
- 試したパラメータ数
- in-sample結果
- out-of-sample結果
- stress結果
- 採用/棄却理由

## 11. 部品同士の依存関係

### 11.1 Signalは単独で使わない

Signal Generatorの出力は、必ず次を通します。

```text
Signal -> Participation Filter -> Position Sizer -> Risk Guard -> Execution Adapter
```

### 11.2 MLはSignalよりFilter向き

LightGBMや時系列モデルは、最初から方向予測に使わず、次の補助に回します。

- signalを通す/見送る
- high-risk regimeを検出する
- volやrangeを予測してサイズを落とす
- anomaly時に止める

### 11.3 Solana botはBuy BotではなくObserverから始める

Solana bot系ノートから最初に作るべき流れはこれです。

```text
Token Discovery -> Token Safety Filter -> Paper Observation -> Sellability Check -> Manual Review
```

`Auto Buy` はこの後です。最初に作るものではありません。
