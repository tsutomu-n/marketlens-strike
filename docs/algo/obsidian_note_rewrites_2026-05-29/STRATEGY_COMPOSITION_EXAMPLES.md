# Strategy Composition Examples

この文書は、部品を実際の戦略案へ組み合わせる例です。共通の流れは次です。

`Universe -> Data -> Feature -> Signal -> Filter -> Size -> Exit -> Execution -> Risk Guard -> Evaluation`

## 1. Trend + Risk Guard

目的: `0212-Trend-Bot` 系の発想を、過剰なbot構想ではなく、検証可能なトレンド戦略にする。

Universe:
- BTC/ETHなど高流動性ペアだけ。

Data:
- OHLCV、spread、funding、API error、約定可能価格。

Feature:
- MA slope、ADX、ATR、realized volatility、直近高値/安値。

Signal:
- trend regime中のpullback完了。
- 直近swing low/highをstop候補にする。

Filter:
- spreadが広い時はskip。
- high_vol/panicでは新規停止。

Size:
- `risk_amount = equity * risk_pct`
- `qty = risk_amount / stop_distance`

Exit:
- initial stop、ATR trail、time stop、partial exitを比較。

Execution:
- backtestではlimit/marketの仮定を明記。
- paperでは約定想定価格と実quoteとの差を記録。

Risk Guard:
- 日次損失、連敗、data stale、position mismatchで停止。

Evaluation:
- MA/Donchian/AlphaTrendを比較。
- cost 2倍、slippage 2倍、期間変更で壊れるかを見る。

## 2. Order Book Participation Filter

目的: Order Bookノートを方向予測ではなく、約定コスト削減部品として使う。

Universe:
- 板が厚く、WebSocket品質が安定するCEX銘柄。

Data:
- top-of-book、depth、trades、spread、cancel/update頻度。

Feature:
- spread_bps、depth_1pct、imbalance、depth_slope、recent_trade_pressure。

Signal:
- 既存のtrend signalを使い、order book単体ではentryしない。

Filter:
- spread_bps > thresholdならskip。
- depth不足ならskipまたはsize cap。
- imbalanceが極端で逆選択が疑われるならskip。

Size:
- depthに対して最大参加率を決める。

Exit:
- 板が急に薄くなったらreduceまたはexit。

Execution:
- maker/taker、post-only、IOCを比較する。

Risk Guard:
- WebSocket lag、snapshot/delta不整合、API errorで停止。

Evaluation:
- filterなしと比較し、slippage、fill rate、entry後逆行幅を見る。

## 3. Token Safety Observer

目的: Solana botノートを自動購入ではなく、安全観測器に変換する。

Universe:
- 新規Solana token、ただし最初は観測のみ。

Data:
- mint authority、freeze authority、transfer fee、LP、holder集中、metadata、pool age、sell simulation。

Feature:
- token_age、lp_depth、top_holder_pct、authority_flags、sellability_status。

Signal:
- buy signalは出さない。
- `safe_to_observe`, `unsafe_skip`, `needs_manual_review` のみ出す。

Filter:
- freeze authorityあり、sell simulation失敗、LP不明、holder集中大はunsafe。

Size:
- 実弾なし。paper observationのみ。

Exit:
- 取引しないためexitなし。観測終了条件だけ持つ。

Execution:
- mainnet注文は行わない。
- simulationとmetadata取得だけ。

Risk Guard:
- private key不要の範囲に限定する。
- credentialを使う段階に進めない。

Evaluation:
- 後から危険だったtokenをどれだけ除外できたか。
- false safe率を見る。

## 4. LightGBM Participation Model

目的: LightGBMを価格予測ではなく、取引参加可否の補助に使う。

Universe:
- Trend baselineで一定の取引数がある銘柄。

Data:
- OHLCV、volatility、spread、order book summary、regime、過去signal outcome。

Feature:
- ATR、MA slope、ADX、spread_bps、depth、time-of-day、regime。

Signal:
- ルールベースのcandidate signalを先に出す。

Filter:
- LightGBMはcandidateを通す/見送る確率補助に限定する。

Size:
- 予測確率でサイズを増やさない。低確率時に縮小/skipする。

Exit:
- 既存Exitを使う。MLにExitを任せない。

Execution:
- 通常のexecution adapterを使い、ML出力は注文に直接つながない。

Risk Guard:
- model drift、feature missing、予測分布の崩れでML filterを無効化。

Evaluation:
- logistic regressionと比較。
- AUCではなく、cost込みexpectancy、DD、turnoverを見る。

## 5. Multi-Asset Risk Allocation

目的: 複数銘柄のトレンド戦略を、最適化しすぎずに配分する。

Universe:
- BTC/ETHから開始。流動性と履歴が十分な銘柄だけ段階追加。

Data:
- 銘柄別OHLCV、volatility、correlation、volume、spread。

Feature:
- realized_vol、rolling_corr、drawdown、liquidity score。

Signal:
- 各銘柄のtrend signalは独立に出す。

Filter:
- 相関急上昇時は新規を減らす。
- 薄い銘柄は除外する。

Size:
- equal weight、vol target、risk capを比較する。
- 1銘柄、1戦略、全体の上限を持つ。

Exit:
- 銘柄別Exitに加え、portfolio DD stopを持つ。

Execution:
- 同時発注時の流動性とturnoverを記録する。

Risk Guard:
- portfolio exposure、同時損失、correlation spikeで縮小。

Evaluation:
- equal weightをbaselineにする。
- 最適化配分が急落時に集中損失を出さないかを見る。

