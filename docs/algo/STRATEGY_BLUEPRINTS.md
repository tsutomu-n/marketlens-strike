# Strategy Blueprints

この文書は、[STRATEGY_PARTS_CATALOG.md](STRATEGY_PARTS_CATALOG.md) の部品を組み合わせた実験候補です。完成戦略ではなく、検証可能な仮説として扱います。

## 1. Trend + OrderBook Confirmation

狙い:
- 長期トレンドで方向を決め、板でエントリー可否を絞る。

部品:
- Universe Selector: BTC/ETH/SOLなど流動性が十分な銘柄。
- Data Collector: OHLCV + order book snapshot。
- Feature Factory: ADX、200MA slope、ATR、spread、imbalance、depth slope。
- Regime Detector: trend/range/high-vol。
- Signal Generator: pullback or breakout retest。
- Participation Filter: spread上限、imbalance継続、薄板回避。
- Exit Module: ATR stop + trailing。
- Risk Guard: daily loss stop、連敗停止。

最小実験:
- 板フィルタなしのtrend strategyをbaselineにする。
- 板フィルタありで entry直後N本の逆行、slippage、PF、MDDを比較する。

捨て条件:
- trade countがbaselineの30%未満になる。
- slippage改善が小さいのに期待値が落ちる。
- high-vol局面でtail lossが増える。

## 2. Regime + RiskGuard Trend System

狙い:
- 同じシグナルでも、市場状態によりサイズ、停止条件、exitを変える。

部品:
- Universe Selector: 主要暗号資産または流動性上位銘柄。
- Feature Factory: realized vol、ADX、volume spike、drawdown from local high。
- Regime Detector: trend/range/high-vol/panic。
- Signal Generator: trend pullback。
- Position Sizer: volatility targeting + max leverage cap。
- Exit Module: regime別stop/trailing。
- Risk Guard: daily loss、max DD、data quality stop。

最小実験:
- fixed size + fixed exitをbaselineにする。
- regime別 sizing/exitを追加して、MDD、CVaR、連敗長、net returnを比較する。

捨て条件:
- returnだけ改善し、MDD/CVaRが悪化する。
- regime分類が頻繁に切り替わり、turnoverが増えすぎる。
- walk-forwardで改善が消える。

## 3. Pump.fun Event Watcher

狙い:
- Pump.fun/Meme tokenをすぐ売買せず、卒業前後や初回バウンスのイベントを観測する。

部品:
- Universe Selector: Pump.funで特定market cap帯、Raydium移行、ATH更新などのイベント銘柄。
- Data Collector: WebSocket、market cap、liquidity、volume、token age、holder distribution。
- Feature Factory: dev holding、insider supply、new wallet buy、drawdown from ATH、social presence。
- Participation Filter: データ品質と明確な危険条件だけ除外。
- Evaluation Harness: 1m/5m/15m/60m/24h後リターンのイベントスタディ。
- Monitoring Layer: 収集件数、欠損、API error、イベント分布を記録。

最小実験:
- 売買せず、イベントテーブルを作る。
- 各特徴量が将来リターンに持つ寄与を単変量、多変量で見る。
- 約定不能とslippageを悪めに仮定する。

捨て条件:
- イベント数が少なすぎる。
- 収集データの欠損が多い。
- 条件を重ねると候補が消える。
- コスト込みで初回バウンスの期待値が消える。

## 3.5. Solana Token Safety Gate

狙い:
- Meme/Solana銘柄の参加前に、凍結、mint、holder集中、流動性、bot wallet露出の危険を除外する。

部品:
- Universe Selector: Pump.fun、Raydium、Photon/BullX等で見つかった候補。
- Data Collector: token metadata、authority情報、holder分布、pool/liquidity、売買可否。
- Token Safety Filter: freeze authority、mint authority、holder concentration、liquidity risk。
- Risk Guard: unsafe判定時は新規停止し、manual reviewに送る。

最小実験:
- 売買はせず、候補トークンに安全性ラベルを付ける。
- 除外したトークンの24時間後状態を追跡する。
- false positiveとfalse negativeを記録する。

捨て条件:
- 権限情報を安定して取得できない。
- unsafe判定が多すぎて観測対象が消える。
- manual reviewなしに攻撃的なtoken設計へ転用される。

## 4. Feature Factory + Walk-Forward Gate

狙い:
- 特徴量を増やしても、検証ゲートを通ったものだけ残す。

部品:
- Data Collector: OHLCV、板、オンチェーン、イベント。
- Feature Factory: テクニカル、volatility、liquidity、order book、token metrics。
- Evaluation Harness: walk-forward、cost model、slippage model、parameter stability。
- Monitoring Layer: feature drift、欠損率、重要度変化。

最小実験:
- 既存baselineに特徴量を1グループずつ追加する。
- in-sample改善ではなく、walk-forward改善だけ採用する。
- trade count、turnover、parameter sensitivityも同時に見る。

捨て条件:
- 特定期間だけ良い。
- 重要度が期間ごとに大きく変わる。
- コスト込みで改善しない。
- liveで取得できない特徴量に依存する。

## 5. Multi-Strategy Allocation

狙い:
- 1つの戦略ではなく、複数戦略への資本配分で安定性を上げる。

部品:
- Universe Selector: 複数銘柄または複数戦略。
- Signal Generator: trend、mean reversion、event watcherなど。
- Position Sizer: strategy allocation、vol targeting、correlation cap。
- Risk Guard: strategy-level stop、portfolio-level stop。
- Evaluation Harness: 単独戦略と合成戦略を比較。

最小実験:
- 各戦略を独立評価する。
- rolling Sharpe、DD、correlationから上限制約つき配分を作る。
- 合成equity curveが単独ベストより滑らかになるかを見る。

捨て条件:
- 相関が高く、分散効果がない。
- 配分変更でturnoverが増えすぎる。
- 単独戦略の劣化を隠しているだけになる。

## 6. Research Assistant For Strategy Review

狙い:
- LLMを売買判断ではなく、戦略ログの要約、異常説明、レビュー観点の生成に限定して使う。

部品:
- Data Collector: trade logs、features、market snapshots、news。
- Research Assistant Layer: natural language insight、experiment brief、review checklist。
- Monitoring Layer: insight生成履歴、出典、レビュー結果。

最小実験:
- 既存のbacktest結果をLLMに要約させる。
- 要約には必ず元指標とsource noteを添える。
- 人間レビューで誤り、過剰断定、出典不足を記録する。

捨て条件:
- 出典なしの断定が多い。
- 指標の解釈ミスが多い。
- 秘密値や未公開ログをプロンプトに流す必要がある。
