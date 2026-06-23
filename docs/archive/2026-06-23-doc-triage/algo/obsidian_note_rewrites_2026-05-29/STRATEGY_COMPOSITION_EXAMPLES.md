<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Strategy Composition Examples

この文書は、部品を実際の戦略案へ組み合わせる例です。主軸は、純粋な売買発生シグナルです。

共通の流れ:

```text
Universe -> Data -> Feature -> Signal -> Filter -> Size -> Exit -> Execution -> Risk Guard -> Evaluation
```

## 1. Trend Continuation With Risk Guard

目的: `0212-Trend-Bot` 系の発想を、過剰なbot構想ではなく、検証可能なtrend continuation signalにする。

Universe:
- 高流動性で履歴が長い銘柄だけ。

Data:
- OHLCV、spread、約定可能価格、data freshness。

Feature:
- MA slope、ADX、ATR、realized volatility、直近高値/安値。

Signal:
- trend regime中に、同方向の短期momentumが再開した時だけcandidateを出す。
- 直近swing low/highをinvalidation候補にする。

Filter:
- range、panic、unknown regimeではskip。
- spreadが広い時はskip。

Size:
- `risk_amount = equity * risk_pct`
- `qty = risk_amount / stop_distance`

Exit:
- invalidation stop、ATR trail、time stopを比較。

Evaluation:
- MA cross、Donchian breakout、buy-and-holdをbaselineにする。
- cost 2倍、slippage 2倍、期間変更で壊れるかを見る。

## 2. Pullback Resume Strategy

目的: trend中の押し目を、明確なinvalidation付きの売買発生シグナルにする。

Universe:
- trendが計測できる流動性銘柄。

Data:
- OHLCV、MA20/MA50、swing high/low、spread。

Feature:
- distance_to_sma20_pct、sma50_slope、short_momentum、realized_vol。

Signal:
- `regime == trend`
- `close > sma50`
- `sma50_slope > 0`
- `abs(distance_to_sma20_pct) <= threshold`
- `short_momentum_turns_up == true`

Filter:
- event blackout、panic、wide spreadはskip。

Size:
- stop distanceが遠いほどqtyを小さくする。

Exit:
- pullback low割れ、time stop、profit protection。

Evaluation:
- entry直後の最大逆行幅、DD、trade count、skip PnLを見る。

## 3. Breakout With Retest

目的: false breakoutを減らすため、breakout直後ではなくretest成功をsignalにする。

Universe:
- rangeが定義しやすく、出来高と価格履歴が安定する銘柄。

Data:
- OHLCV、volume、ATR、range high/low。

Feature:
- range_width、volatility_compression、breakout_flag、retest_hold_flag。

Signal:
- range highを上抜ける。
- その後、旧range highを維持する。
- momentumが再開する。

Filter:
- breakout candle直後だけではentryしない。
- event gap直後はskip。

Size:
- retest lowをinvalidationにしてrisk-based sizing。

Exit:
- range内へ戻ったらexit。

Evaluation:
- simple breakoutと比較し、false breakout率と取り逃しを同時に見る。

## 4. Mean Reversion In Range Regime

目的: trend followと別物として、range regime限定の逆張りsignalを検証する。

Universe:
- spreadが狭く、急変時の約定悪化が小さい銘柄。

Data:
- OHLCV、band/z-score、realized volatility、regime。

Feature:
- z_score、band_position、range_regime_flag、panic_flag。

Signal:
- `regime == range`
- z-score extreme
- volatilityがpanicではない

Filter:
- trend regime、panic、wide spreadではskip。

Size:
- trend followより小さく始める。

Exit:
- meanへ戻ったら利確。
- regimeがtrendへ移ったら損切りまたは停止。

Evaluation:
- simple RSIと比較。
- trend日に損失が集中しないかを見る。

## 5. Volatility Compression Breakout

目的: 低volatilityからの拡大局面だけをbreakout候補にする。

Universe:
- gapが少なく、volumeが安定する銘柄。

Data:
- OHLCV、ATR、band width、volume。

Feature:
- ATR percentile、band_width_percentile、range boundary、volume expansion。

Signal:
- volatility compression後にrange boundaryを抜ける。

Filter:
- event gap、wide spread、thin liquidityはskip。

Size:
- range幅またはATRをstop distanceにする。

Exit:
- range内へ戻ったらexit。
- trend continuationならtrail。

Evaluation:
- Donchian breakoutと比較。
- slippage込みで期待値が残るかを見る。

## 6. Regime Filtered Base Signal

目的: 売買シグナルを増やすのではなく、同じbase signalを通す環境を絞る。

Universe:
- base signalの取引数が十分ある銘柄。

Data:
- base signal、volatility、trend slope、spread、market status。

Feature:
- regime、panic flag、thin liquidity flag。

Signal:
- base signalはそのまま。

Filter:
- allowed regime以外はskip。

Size:
- high volではqty縮小。

Exit:
- base signalのexitを維持。

Evaluation:
- filterなしと比較。
- skipした取引の仮想PnLを必ず見る。

## 7. Order Book Participation Filter

目的: Order Bookノートを方向予測ではなく、既存signalの参加可否・約定コスト削減部品として使う。

Universe:
- 板が厚く、WebSocket品質が安定する銘柄。

Data:
- top-of-book、depth、trades、spread、snapshot/delta状態。

Feature:
- spread_bps、depth_1pct、imbalance、depth_slope、recent_trade_pressure。

Signal:
- 既存のtrend / pullback / breakout signalを使う。
- order book単体ではentryしない。

Filter:
- spread_bps > thresholdならskip。
- depth不足ならskipまたはsize cap。
- imbalanceが極端で逆選択が疑われるならskip。

Evaluation:
- filterなしと比較し、slippage、fill rate、entry後逆行幅を見る。

## 8. LightGBM Participation Model

目的: LightGBMを価格予測ではなく、取引参加可否の補助に使う。

Universe:
- base signalで十分な取引数がある銘柄。

Data:
- OHLCV、volatility、spread、regime、過去signal outcome。

Feature:
- ATR、MA slope、ADX、spread_bps、time-of-day、regime。

Signal:
- ルールベースのcandidate signalを先に出す。

Filter:
- LightGBMはcandidateを通す/見送る確率補助に限定する。

Size:
- 予測確率でサイズを増やさない。低確率時に縮小/skipする。

Evaluation:
- logistic regressionと比較。
- AUCではなく、cost込みexpectancy、DD、turnoverを見る。

## 9. Multi-Asset Risk Allocation

目的: 複数銘柄のシグナルを、最適化しすぎずに配分する。

Universe:
- 高流動性の少数銘柄から開始。

Data:
- 銘柄別OHLCV、volatility、correlation、volume、spread。

Signal:
- 各銘柄のsignalは独立に出す。

Filter:
- 相関急上昇時は新規を減らす。
- 薄い銘柄は除外する。

Size:
- equal weight、vol target、risk capを比較する。
- 1銘柄、1戦略、全体の上限を持つ。

Evaluation:
- equal weightをbaselineにする。
- 最適化配分が急落時に集中損失を出さないかを見る。

## 10. Crypto/DeFi Specific: Token Safety Observer

目的: Solana botノートを自動購入ではなく、安全観測器に変換する。通常のシグナル検討では後回し。

Signal:
- buy signalは出さない。
- `safe_to_observe`, `unsafe_skip`, `needs_manual_review` のみ出す。

Filter:
- freeze authorityあり、sell simulation失敗、LP不明、holder集中大はunsafe。

Execution:
- mainnet注文は行わない。
- simulationとmetadata取得だけ。

Evaluation:
- 後から危険だったtokenをどれだけ除外できたか。
- false safe率を見る。

## 11. Crypto/DeFi Specific: Jito Execution Observation

目的: Jitoを収益源ではなく、execution qualityの観測対象として扱う。通常のシグナル設計とは別枠。

Signal:
- 売買発生シグナルではない。
- execution route比較の観測対象。

Evaluation:
- standard tx vs Jito route。
- tip、latency、landed率、failure reasonを記録する。

Reject:
- tip/失敗/インフラ費用で期待値が消える。
