# Individual Note Details

24本の原ノートを、原本なしで判断できる独立カードとして再構成します。各カードでは、部品名を並べるだけでなく、その部品が何を判断し、何を入力し、何を出力し、どこで壊れるかまで書きます。

## 01 Core Trend

### 1. `0212-Trend-Bot.md`

要旨: 上位足トレンドを見て、短期足で押し目/戻りを狙うbot構想。稼働/停止、マージンレシオ、部分利確、トレーリング、日次運用まで含む。

補正: トレンド判定は未来予測ではなく、入ってよい相場を絞る運転モード。レンジ相場での損失を最初に測る。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Regime Detector | トレンド相場か、レンジ/高ボラで停止すべきか | MA傾き、ADX、ATR、出来高、spread | `trend`, `range`, `panic`, `pause` | 上位足トレンドを未来予測と誤認する | 状態別PnL、レンジ期間DD |
| Pullback Signal | トレンド中の押し目/戻りが終わったか | 短期足価格、直近高安、momentum | `candidate_long/short` | 押し目ではなく落ち始めを拾う | entry後N本の逆行幅 |
| Position Sizer | stop距離に対して数量を決める | equity、risk_pct、stop_distance | qty、risk_amount | 勝てそうな時に裁量で増やす | 連敗時DD、1取引損失 |
| Exit Module | 利確/損切り/トレーリングを決める | entry、ATR、holding_time、PnL | hold/reduce/exit | 利確だけ細かく損切りが曖昧 | 平均利益、最大含み益からの戻り |
| Daily Kill Switch | その日の新規取引を止めるか | daily PnL、連敗数、API状態 | normal/pause/kill | alertだけで止めない | 停止発動で避けた損失 |

捨て条件: 手数料・slippage込みで単純MA/Donchianより安定しない。レンジ損失が大トレンド利益を食う。

### 2. `0714-Adaptive-Alpha-Trendトレードプログラム.md`

要旨: AlphaTrend、特徴量、異常検知、LightGBM、VaR/ES、backtest、RL、代替データまで含む巨大構想。

補正: 全部入り戦略としてではなく、部品カタログとして使う。AlphaTrendは主役ではなく、トレンド候補を作る1特徴量。VaRは最大損失ではなく分位点であり、stop lossも損失を完全には限定しない。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Feature Factory | 価格/出来高から戦略特徴量を作る | OHLCV、ATR、RSI、MACD、AlphaTrend | feature table | 特徴量を増やすほど良いと誤認 | feature追加前後のOOS差分 |
| Anomaly Filter | データ異常/急変で止めるか | 異常値、vol spike、欠損 | valid/skip/pause | 異常検知を売買シグナルにする | 異常時DD削減 |
| Participation Model | 候補シグナルを通すか | 特徴量、regime、過去結果 | pass/skip probability | MLを価格予言器にする | logistic baselineとの比較 |
| Risk Guard | 損失上限やtail riskを制御する | VaR/ES、DD、position、API状態 | reduce/pause/kill | VaRを最大損失と誤解 | stress、gap、tail loss |
| Walk-forward Harness | 過去合わせかを検査する | split、config、cost model | pass/fail、scorecard | in-sample最適化を採用する | walk-forward安定性 |

捨て条件: 部品を増やすほどin-sampleだけ良くなり、未使用期間で崩れる。

### 3. `0714-トレード戦略-Order-Book.md`

要旨: 板の深さ、不均衡、傾斜、クラスタリング、MLで板パターンを読む構想。

補正: 板は方向予測より、参加してよいか、サイズを落とすか、成行を避けるかの判断に使う。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Spread Filter | spreadが許容範囲か | best bid/ask | allow/skip | spreadを固定コスト扱いする | spread別expectancy |
| Depth Filter | 注文サイズに対して板が厚いか | depth、order size | allow/size_cap/skip | 見えている板に約定できると仮定 | fill rate、slippage |
| Imbalance Monitor | 極端な板偏りが逆選択か | bid/ask depth imbalance | risk flag | imbalanceを方向予測に直結 | entry後逆行幅 |
| Size Cap | 板厚に対して最大数量を決める | depth_1pct、liquidity | max_qty | 大きすぎる注文で滑る | size別slippage |
| Order Type Selector | maker/taker/IOCを選ぶ | spread、urgency、depth | order_type | 常に成行で入る | fill/cancel/latency比較 |

捨て条件: 板条件が短寿命で、liveまたはpaperで再現できない。

### 4. `0721-RiskGuard Crypto Engine(RGCE).md`

要旨: botの防御・監視・異常検知・secret管理をまとめた構想。

補正: 安全性は暗号化や機能数ではなく、異常時に確実に止まること。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Security Guard | secretや権限が安全か | API権限、ログ、env、設定 | safe/unsafe | APIキー保存だけで安全とする | secret scan、権限監査 |
| Data Freshness Gate | データが古くないか | fetched_at、event_time | valid/stale | 古いデータで売買する | stale注入テスト |
| Exposure Guard | 建玉が上限内か | position、equity、risk cap | normal/reduce | 残高取得失敗を無視 | position desync test |
| Kill Switch | 即停止すべきか | error rate、unknown position、DD | kill/pause | alertだけで注文継続 | 障害注入テスト |
| Incident Log | 後で原因追跡できるか | errors、orders、state | incident record | ログが散在し復旧不能 | incident再現性 |

捨て条件: 異常時に人間が何をすべきか分からない。

### 5. `0722-トレードシステム（SDH）.md`

要旨: データハブ、低レイテンシー、VPS、Cloudflare、スキャルピング基盤構想。

補正: CDNやVPSで取引所matching engineへの距離問題が解決するわけではない。低レイテンシーより、まずデータ鮮度と障害記録。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Data Hub | 複数ソースを同じ時刻軸で保存できるか | OHLCV、book、API logs | normalized stream | 統合で時刻ずれを隠す | source別lag |
| Latency Monitor | 遅延が取引可能範囲か | send/receive timestamp | latency metric | CDNで低遅延化できると誤認 | p50/p95/p99 latency |
| Execution Journal | 注文判断と結果を追えるか | order intent、ack、fill | journal row | 結果だけ保存する | order lifecycle再現 |
| Error Budget | API障害が許容内か | error rate、reconnect | normal/degraded | 多少のエラーを無視 | error別PnL影響 |
| Backtest-live Gap Recorder | backtest仮定とlive観測の差 | simulated fill、paper quote | gap report | backtestを実運用同等と誤認 | quote gap、fill gap |

捨て条件: インフラ構築が目的化し、期待値検証が遅れる。

## 02 Strategy Modules

### 6. `0507-戦略1_適応型ボラティリティ・スケーリング付きマルチシグナル・トレンド戦略.md`

要旨: 複数シグナルとボラティリティスケーリングを使うトレンド戦略案。

補正: 複数シグナル一致は堅牢化ではなく、過去合わせにもなる。まずボラティリティによるサイズ制御を単独で評価する。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Signal Combiner | 複数シグナルをどう統合するか | MA、RSI、breakout、momentum | combined_signal | 一致数を確信度と誤認 | シグナル数別OOS |
| Volatility Target | 目標リスクに合わせて縮小するか | realized vol、target vol | size_multiplier | 低ボラで過大化する | vol別DD |
| ATR Sizer | stop距離に対し数量を決める | ATR、entry、stop | qty | ATRが急変に遅れる | gap時損失 |
| High-vol Stop | 高ボラ時に止めるか | vol spike、range拡大 | pause/reduce | 高ボラの好機も消す | skip後リターン |

捨て条件: シグナルを増やすほど取引数が減り、偶然の良い局面だけ残る。

### 7. `0507-戦略2_レジームスイッチング・トレンドフォロー戦略.md`

要旨: 相場状態に応じてトレンド戦略の稼働を切り替える案。

補正: レジーム判定は未来予測ではなく、戦略の運転モード。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Regime Detector | trend/range/high_volを分ける | ADX、MA slope、vol、spread | regime | 判定を未来予測扱い | 状態別PnL |
| Participation Mode | 稼働/停止/観測を選ぶ | regime、data quality | allow/pause/observe | 停止が多すぎる | skip率と回避損益 |
| Risk Mode | レジーム別サイズを決める | regime、vol、DD | size_multiplier | high-volで通常サイズ | regime別DD |
| Stop Mode | 急変時の停止ルール | panic flag、gap、API error | kill/pause | stopを裁量で外す | shock期間損失 |

捨て条件: 判定遅れでトレンド終盤に入り、レンジで損する。

### 8. `0507-戦略3_オンチェーンデータ強化型トレンド確信度モデル戦略.md`

要旨: SOPR、MVRV、exchange flow等でトレンド確信度を作る案。

補正: オンチェーン日次指標は短期売買には遅い。中期レジームや過熱警戒に使う。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| On-chain Collector | 指標が使える時刻に取れているか | SOPR、MVRV、flows | timestamped indicators | 改訂後データを使う | availability check |
| Overheat Score | 過熱/冷却局面か | z-score、flow、funding | overheat/cool/neutral | ファンダメンタルと過信 | 過熱後DD |
| Risk-on/off Filter | 参加縮小すべきか | on-chain score、price regime | allow/reduce/skip | 短期entryへ直結 | 日足以上で検証 |
| Position Multiplier | 確信度でサイズを調整するか | score、base size | multiplier | 高scoreで過大化 | multiplier別DD |

捨て条件: データ遅延や改訂を入れると効果が消える。

### 9. `0507_戦略4_マルチアセット・ダイナミック・トレンドアロケーション戦略.md`

要旨: 複数銘柄のトレンドと動的配分の案。

補正: 暗号資産は急落時に相関が上がりやすい。最適化より上限ルールが先。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Universe Selector | 追加銘柄が検証に耐えるか | volume、age、spread | include/exclude | 上がった銘柄だけ選ぶ | 銘柄追加時差分 |
| Vol Target | 銘柄別ボラに応じるか | realized vol | target weight | 低ボラ銘柄過大化 | 銘柄別DD |
| Correlation Guard | 同時損失が増えるか | rolling corr、market beta | reduce/pause | 平時相関だけ見る | crisis corr |
| Portfolio Drawdown Stop | 全体DDで止めるか | portfolio equity curve | normal/reduce/kill | 個別戦略だけ見る | portfolio DD |

捨て条件: 上昇相場だけで分散効果が見える。

### 10. `0507-戦略5_「トレンドの成熟度」判定によるイグジット戦略.md`

要旨: トレンド終盤を判定してExitする案。

補正: 天井を当てるのではなく、戻り許容幅と縮小条件を決める。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| ATR Trail | stopをどこへ引き上げるか | ATR、price、trend | new_stop | trailを近くしすぎる | 利益取り逃し/戻り |
| Time Stop | 進まない取引を切るか | holding_time、PnL | exit/hold | 伸びる前に切る | holding time別PnL |
| Partial Exit | どこで一部利確するか | R multiple、vol | reduce_qty | 利益を削りすぎる | 分割有無比較 |
| Momentum Decay Exit | 勢い低下で縮小するか | momentum、volume、slope | reduce/exit | ノイズで出る | trend profit capture |

捨て条件: 早降りで大トレンド利益を削る。

## 03 Model Research

### 11. `0721-LightGBM パラメータチューニング.md`

要旨: LightGBMのパラメータ、探索、正則化、学習設定のメモ。

補正: 価格予測モデルではなく、取引する/しない、サイズを落とす/落とさないの補助。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Feature Scorer | どの特徴量が効くか | feature table、label | importance/stability | importanceを因果と誤認 | split別安定性 |
| Participation Classifier | signalを通すか | candidate features | pass_probability | 確率でサイズを増やす | cost込みexpectancy |
| Model Drift Monitor | モデルが壊れたか | prediction distribution、feature stats | valid/drift | driftを無視して継続 | PSI、分布差 |

捨て条件: AUCは良いが売買に変換すると消える。

### 12. `0725-時系列-予測モデル.md`

要旨: TimesFM、MOMENT、パッチング等の時系列モデルメモ。

補正: 基盤モデルが金融売買にそのまま強いとは限らない。vol/range/anomaly/regimeの補助に限定する。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Vol Forecast | 次期間の荒さを見積もる | past returns、range | expected_vol | vol予測を方向予測に使う | realized vol error |
| Range Forecast | 値幅を見積もる | OHLCV history | expected_range | entry根拠にする | range coverage |
| Anomaly Score | 通常と違う状態か | residual、forecast error | anomaly_score | anomalyで逆張りする | anomaly後DD |
| Forecast Residual Feature | 予測誤差を特徴量にする | forecast、actual | residual feature | 未来actualを混ぜる | leakage check |

捨て条件: 推論コストやturnoverで期待値が消える。

### 13. `0902-Genetic Alogo for Trading.md`

要旨: GA、HMM、AI agent、APIキー、コストが混在する研究メモ。

補正: GAは戦略発見機ではなく、過学習を起こしやすい探索器。仮説生成に限定する。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Hypothesis Generator | 試す候補を作る | notes、features、constraints | hypothesis | AI案を即実装 | human review |
| Search Space Limiter | 探索範囲を制限する | allowed parts、param ranges | bounded search | 自由度が高すぎる | trial count |
| Complexity Penalty | 複雑すぎる案を罰する | rule count、params | penalty score | 複雑さを性能と誤認 | complexity vs OOS |

捨て条件: 探索回数を増やすほど過去成績だけ改善する。

### 14. `1114_ポートフォリオ最適化.md`

要旨: ポートフォリオ最適化、分散、リスク配分のメモ。

補正: 平均リターン推定に基づく最適化は入力誤差に弱い。まず上限ルールとvol target。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Equal Risk | 各銘柄のリスクを揃える | vol、equity | weight | vol推定を過信 | vol regime別DD |
| Vol Target | 全体リスクを目標化する | portfolio vol | leverage/multiplier | 低ボラで過大化 | crisis loss |
| Max Weight | 1銘柄集中を防ぐ | weights | capped weights | 成績良い銘柄に集中 | concentration |
| Correlation Spike Guard | 相関急上昇で縮小する | rolling corr | reduce/pause | 平時相関で安心する | stress period |

捨て条件: 急落時に相関が上がり、同時損失を出す。

## 04 Market Specific

### 15. `0702-cryptofetch.md`

要旨: 暗号資産データ取得ツール構想。

補正: データが取れることより、取得時刻、遅延、欠損、再取得差分が重要。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| OHLCV Collector | 足データを再現可能に取る | exchange API | candles | 確定前足を使う |再取得差分 |
| Orderbook Collector | 板を時系列保存する | snapshot/delta | book state | delta欠落を無視 | snapshot consistency |
| Funding Collector | fundingを保存する | funding API | funding history | fundingコスト無視 | funding込みPnL |
| Freshness Monitor | データが古くないか | fetched_at、event_time | valid/stale | 古いデータで売買 | stale注入 |

捨て条件: 欠損時に古いデータを静かに返す。

### 16. `1021_SOLANA.md`

要旨: Solana program examples由来の基礎メモ。

補正: 多くの取引用途では独自on-chain programは不要。既存programとtoken仕様確認が先。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Token Safety Filter | token権限が危険か | mint/freeze/fee/holder | safe/review/unsafe | observeをbuy可能と誤認 | 後日危険率 |
| Simulation Gate | transactionが通るか | tx、account state | pass/fail | simulation成功を利益保証と誤認 | sim vs actual |
| Program Allowlist | 触ってよいprogramか | program id | allow/reject | 未知programを許可 | allowlist review |
| Account Parser | account状態を解釈する | account data | parsed state | schema誤読 | fixture test |

捨て条件: 未知programや未知tokenを自動で触る。

### 17. `1107_自動化された暗号通貨ニュースで稼ぐ方法.md`

要旨: ニュース自動生成と紹介収益のマーケティング系メモ。

補正: 取引戦略ではなく、イベント観測とcomplianceの資料。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Event Collector | ニュース発生を記録する | source、timestamp | event record | 取得時刻を混同 | first_seen差分 |
| Source Timestamp | 情報がいつ利用可能か | published_at、fetched_at | usable_at | 後知恵リーク | latency analysis |
| News Type Classifier | どの種類のイベントか | title、body、source | listing/news/rumor | 分類を売買根拠にする | type別forward return |
| Compliance Guard | 公開/紹介/広告リスクを判定 | source、affiliate、claims | ok/review | 宣伝と研究を混同 | compliance checklist |

捨て条件: 紹介収益や記事生成が目的化する。

### 18. `1129-Solanaトレーディングボット.md`

要旨: Solana token botの設定、snipe list、filter、Warp/Jito、利確/損切りメモ。

補正: 買うbotではなく、まずtoken safety observer。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Mint Authority Check | 追加発行リスクがあるか | mint authority | safe/unsafe | authority有無だけで全判断 | 後日rug率 |
| Freeze Check | 凍結リスクがあるか | freeze authority | safe/unsafe | freezeなしなら安全と誤認 | unsafe除外率 |
| LP Check | 流動性が十分か | pool size、lock状態 | ok/review/unsafe | LP量だけを見る | sell slippage sim |
| Sellability Check | 売れるか | sell simulation | pass/fail | buyだけsimulation | sell pass rate |
| Manual Approval | 人間確認が必要か | risk flags | approve/reject/review | 自動承認にする | review outcome |

捨て条件: private keyをrepo/config/docsに置く、資金上限がない、自動購入する。

### 19. `1202-JitoとSolana.md`

要旨: Jito Bundlesチュートリアル由来のメモ。

補正: GTO/G2/Cheeto等は転記誤りの可能性があり、公式docsで確認する。古いstake比率を現在値にしない。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Bundle Sender | bundleを送るか | tx list、tip、route | sent/rejected | bundleなら必ず通る | landed rate |
| Simulation Gate | 送信前に失敗を弾けるか | transaction、state | pass/fail | simulationを保証と誤認 | sim vs landed |
| Tip Cost Tracker | tip込みで期待値があるか | tip、PnL、landed | net result | tipを無視 | tip感応度 |
| Landed Rate Monitor | 実際に着地したか | status、slot、latency | landed/not_landed | 送信成功を着地と誤認 | route別landed率 |

捨て条件: tip/失敗/インフラ費用で期待値が消える。

## 05 Execution And Stack

### 20. `0710-VectorBT.md`

要旨: VectorBT cookbook、indicator、最適化、複数銘柄検証メモ。

補正: vectorized backtestは実運用の約定モデルではない。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Parameter Sweep | パラメータ近傍が安定か | ranges、strategy | heatmap/results | 最適点だけ見る | 近傍安定性 |
| Indicator Prototype | 指標候補を試す | OHLCV | signals/features | デモ成績を信じる | baseline比較 |
| Cost Sensitivity Test | コストで消えるか | fee、slippage | stressed results | 手数料を軽視 | cost 2倍 |

捨て条件: 探索範囲を広げた時だけ良い点が見つかる。

### 21. `0722-PyBotters.md`

要旨: PyBottersのREST/WebSocket/API接続メモ。

補正: API接続できることと、安全に注文できることは別。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Public WS Collector | public dataを安定取得できるか | WebSocket stream | normalized events | 切断を見逃す | reconnect test |
| Private Read State | 残高/建玉を読めるか | private REST/WS | account state | read失敗で古い状態 | state freshness |
| Order Gateway | 注文/cancelを安全に送るか | order intent | ack/fill/cancel | retry重複注文 | idempotency test |
| Reconnect Monitor | 再接続時に状態が壊れないか | connection events | healthy/degraded | reconnect後の差分無視 | forced disconnect |

捨て条件: 注文ID、再試行、cancel、position同期を管理できない。

### 22. `1026_Backtest_Trade!.md`

要旨: backtest/trade検証環境メモ。

補正: backtestは儲かる証明ではなく、候補を捨てる検査。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Data Contract | 検証データの条件を固定する | dataset、schema | contract | 後から期間変更 | reproducibility |
| Cost Model | 手数料/資金調達を入れる | fee、funding、borrow | net pnl | grossだけ見る | cost stress |
| Slippage Model | 約定価格差を入れる | spread、depth、size | adjusted fills | candle price約定 | paper comparison |
| Trial Log | 試行回数を記録する | config、result | decision log | 都合の良い試行だけ残す | trial count |

捨て条件: 手元でしか再現できない。

### 23. `1031_Trading with polars.md`

要旨: Polarsで時系列データを高速処理するメモ。

補正: 速度より、時刻順、join_asof、rolling、null処理の正しさが重要。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Lag Feature | 過去値だけを使えているか | sorted time series | lag columns | 未来参照 | fixture expected |
| Rolling Feature | rolling窓が正しいか | time series | rolling stats | window端点ミス | pandas比較 |
| Asof Join | 異なる頻度を結合する | left/right time series | joined table | 未来データ結合 | asof direction test |
| Schema Check | 入力列が想定通りか | dataframe schema | pass/fail | 型変化を見逃す | schema snapshot |

捨て条件: join/rollingの時刻意味を説明できない。

### 24. `1117_バックテストについて.md`

要旨: backtestの基本注意点メモ。

補正: 良い結果を探すのではなく、壊れる条件を探す。

抽出部品テーブル:

| 部品 | 何を判断するか | 入力 | 出力 | 誤用リスク | 検証方法 |
|---|---|---|---|---|---|
| Walk-forward | 時間外検証で残るか | sequential splits | OOS results | random splitする | split別PnL |
| Stress Test | 悪条件で壊れないか | cost/slippage shock | stressed result | 平時だけ見る | cost 2倍 |
| Monte Carlo | 順序や偶然に強いか | trade returns | distribution | 平均だけ見る | DD分布 |
| Reject Rule | 捨て条件を固定する | metrics、threshold | reject/pass | 後から条件変更 | decision log |
| Decision Log | 判断根拠を残す | config/result/reason | log | 成功だけ記録 | auditability |

捨て条件: 少し条件を変えるだけで期待値が消える。
