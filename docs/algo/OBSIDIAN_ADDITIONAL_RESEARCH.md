# Obsidian Vault 追加調査メモ

調査日: 2026-05-28  
対象: `/home/tn/Docs/algo/obsidian-vault`  
目的: システムトレード、Bot、戦略立案に少しでも使えるノートの追加発掘。タグやカテゴリだけでなく、本文キーワードから再探索した。

## 結論

追加で見る価値が高いノートは、主に次の4群。

- Meme/Solana/Pump.fun系の実運用ヒント: `00605_DexBot_Pumpfun.md`, `0124-SOLANA-TRADE.md`, `1202-SolVal Guardian (SG).md`, `1205-MeME-token-Tools.md`, `Meme-Tokens!/1228-Get x10 Profits.md`
- Adaptive Alpha Trendの改善計画/実装断片: `0710-Strategy0010.md`, `0714-AlphaTrendを超えて。.md`, `0715-Alt-Alpha-Trend改2131.md`, `1117_uptrend_botΧ.md`
- モデル・検証・最適化: `0715-勾配ブースティングアリゴリズム.md`, `0906_モンテカルロ.md`, `1101_時系列予測.md`, `数理モデル統計学的手法/遺伝的アルゴリズム_0325.md`
- 研究/実装を進めるためのプロンプト・設計支援: `0711-IRIS金融.md`, `0711-定量的トレード戦略開発プロンプト.md`, `@@Prompts-for-あるごトレードAI.md`

ただし、APIキーや秘密鍵を含むノートが複数あるため、vault全体の無差別コピーは危険。コピーする場合は、先に秘匿情報検出とマスク処理を入れるべき。

## 追加で見つかった高優先ノート

### `00605_DexBot_Pumpfun.md`

- Pump.funトークン監視Botの仕様メモ。
- PumpPortal WebSocket `wss://pumpportal.fun/api/data` を使い、時価総額が `$65,000-$69,000` 付近のトークンを監視する構想。
- 収集対象は token address、market cap、price movement、pool creation、trading pattern、risk indicators。
- FastAPI、Python 3.12、WebSocket、asyncio、Pydanticという実装スタックが明記されている。

使える気づき:
- 最初から「売買Bot」ではなく「データ収集Bot」として作る発想がよい。MemeBotの前段として、勝ちパターンの教師データを貯める設計に向く。
- market cap帯を固定して観測することで、Pump.fun固有の「卒業前後」イベントを定量化できる。
- market cap、token age、volume、insider/dev保有率、social有無を同じイベントテーブルに入れると、後続でルール/MLの両方に使える。

### `1202-SolVal Guardian (SG).md`

- Solana系の自動取引/監視システム構成案。
- コア機能: 市場データ監視、シグナル生成、取引実行、リスク管理。
- 周辺機能: system monitoring、performance analysis、metrics analyzer、storage、key manager、WebSocket client、Streamlit dashboard、logging、config manager。

使える気づき:
- Botを「strategy」だけで作らず、監視、リスク、保存、UI、鍵管理まで機能境界を切っている。
- `market_monitor -> signal_generator -> executor -> risk_manager` の流れは、marketlens-strike側の実験設計にも転用しやすい。
- 実運用に近づけるなら、最初に `data collection only`、次に `paper signal`、最後に `execution` の順に分けるべき。

### `Meme-Tokens!/1228-Get x10 Profits.md`

- PumpFun/BullX系のスキャルピング戦略メモ。
- 具体的な条件が多い:
  - Dev holdingの上限
  - Insider wallet supplyの上限
  - Social有無
  - Snipers数
  - volume閾値
  - market cap閾値
  - token age
  - Raydium限定
  - liquidity閾値
  - SOLのマクロ方向
  - 最高値からの下落率
  - 2-3 SOL程度の新規ウォレット買い
- 「初回バウンス」「Dev Sell後」「ATH Break」「4-6本のローソク」など、イベント駆動の入口が多い。

使える気づき:
- これは投資助言としては危険だが、戦略研究の材料としては具体的。特に「フィルター候補」と「検証すべき仮説」が多い。
- そのまま真似るのではなく、次の特徴量に分解してバックテスト/イベントスタディ化するのがよい。
  - `dev_holding_pct`
  - `insider_supply_pct`
  - `token_age_minutes`
  - `volume_5m`
  - `mcap`
  - `liquidity`
  - `drawdown_from_ath_pct`
  - `new_wallet_buy_count`
  - `new_wallet_buy_size_sol`
  - `social_presence_score`
  - `sol_macro_trend`

### `0710-Strategy0010.md`

- Adaptive Alpha Trend系プロジェクトの構成案。
- strategy、features、feature_management、utils、observers、config、testsの分離。
- 目的は、マルチタイムフレーム分析、異常検知、機械学習を組み合わせた適応型トレンド戦略。
- Isolation Forest、LightGBM、SHAP、VaR/ES、特徴量管理TUIに言及。

使える気づき:
- トレンド戦略を単一インジケータで終わらせず、異常検知と説明可能性を足している。
- `feature_management` を独立させる発想は重要。戦略アイデアを増やすほど、特徴量の採用/除外/重要度確認が必要になる。

### `0714-AlphaTrendを超えて。.md`

- Adaptive Alpha Trend改善計画。
- 過適合対策、ウォークフォワード最適化、L1/L2正則化、ベクトル化、並列処理、CVaR/ES、Kelly、ATR、ベイズ最適化、オンライン学習、現実的な取引コスト、スリッページ、ストレステストに触れている。

使える気づき:
- 今後の戦略検討では、アイデアより先に検証仕様を固定した方がよい。
- 最低限の検証セット:
  - time-series split
  - walk-forward
  - transaction cost
  - slippage
  - stress period
  - monte carlo
  - parameter stability
  - leakage check

### `0715-Alt-Alpha-Trend改2131.md`

- Adaptive Alpha Trendの実装断片が多い。
- risk_management、backtesting、data、models、visualization、utilsの拡張構成。
- structured logger、alert system、advanced profiler、parallel optimizer、adaptive resource managerなど、運用寄りの部品がある。

使える気づき:
- 実装サンプルはそのまま採用せず、部品名と責務分解の参考にする。
- 「戦略コード」と「運用監視コード」を同じ層に混ぜない設計に使える。

### `1117_uptrend_botΧ.md`

- uptrend botのPython実装案。
- data_manager、predictor、regime_identifier、risk_manager、trading_bot、utilsという構成。
- 短期モデルにLightGBM、長期モデルにProphet、複数時間軸、最大レバレッジ、最大DD、stop loss、take profitを設定ファイルで持つ。

使える気づき:
- トレンドBotには「短期予測」と「長期レジーム判定」を分ける設計が向く。
- live execution前に、`predictor` と `regime_identifier` の一致/不一致を記録するだけでも研究価値がある。

### `1106_Trading Tool.md`

- VeighNa/vn.pyの紹介メモ。
- CTA strategy、CTA backtester、portfolio strategy、algo trading、risk manager、web trader、data recorderなどが一覧化されている。

使える気づき:
- 既存OSSの機能分解リストとして有用。
- marketlens-strikeで全部作らず、必要な機能名を「将来の比較対象」として使える。

## 中優先ノート

### `0715-勾配ブースティングアリゴリズム.md`

- XGBoost/LightGBMの比較、時系列への適用、仮想通貨戦略への応用メモ。
- 使い道は、価格予測そのものよりも「特徴量重要度」「非線形ルール抽出」「軽量な分類器」にある。
- 注意点: 時系列CV、リーク対策、手数料込み評価がないと過大評価しやすい。

### `0906_モンテカルロ.md`

- 戦略の安定性評価、ランダム性、リスク分布確認に使える。
- トレード順序のシャッフル、リターン系列の再標本化、スリッページ悪化シナリオなどに転用できる。

### `1101_時系列予測.md`

- 時系列予測モデルの研究メモ。
- 予測モデルを直接売買判断に使うより、レジーム判定、ボラティリティ予測、異常検知の補助に使う方が現実的。

### `数理モデル統計学的手法/遺伝的アルゴリズム_0325.md`

- GA、NSGA-III、MOEA/D、CMA-ES、サロゲート支援GAなどのまとめ。
- 使い道は「戦略そのものの発見」より、パラメータ探索、多目的最適化、しきい値探索。
- 目的関数は単純な利益最大化ではなく、`return`, `max_drawdown`, `turnover`, `trade_count`, `parameter_stability` を同時に見るべき。

### `0711-IRIS金融.md` / `0711-定量的トレード戦略開発プロンプト.md` / `@@Prompts-for-あるごトレードAI.md`

- 定量トレード支援AI向けのプロンプト/ペルソナ。
- そのまま使うより、戦略レビューのチェックリストに分解すると使いやすい。
- 抽出できる観点:
  - 目的市場
  - 時間軸
  - データソース
  - 特徴量
  - 検証方法
  - リスク管理
  - 実行制約
  - 運用監視
  - 規制/倫理/セキュリティ

## 低優先または周辺ノート

### `0103-AI-agent-crypto.md`

- AI Agent系クリプト銘柄/インフラの相場テーマメモ。
- 直接のBot実装ではないが、テーマローテーションやニュース/セクターウォッチに使える。

### `0124-SOLANA-TRADE.md`

- Solana取引用ツールキット `listen` のメモ。
- AI AgentがSolanaとやり取りする道具として参考になる。
- 実装に使うなら、現時点のGitHub/ドキュメント確認が必要。

### `1202-Solana Development.md`

- Solana開発環境構築メモ。
- Bot戦略そのものではなく、Solana実行環境を作る時の補助資料。

### `1206-ai-hedge-fund.md`

- AI hedge fund系のOSS/概念メモ。
- 実装思想や構成比較には使えるが、現物戦略の即戦力ではない。

## コピーしない、またはマスク必須のノート

以下は本文にAPIキー、秘密鍵、トークン、2FA/リカバリコード、接続URL、認証情報らしきものが含まれる。docs配下へ生コピーしない。

- `0205-重要Hyperliquid_API_KEY.md`
- `@@@1222-Bybit_Bot_main_API-Key.md`
- `@@@@@_LobeChat_VPN.md`
- `1202-API-Devbot.md`
- `0630-Bybit-API-KEY.md`
- `0503-Image-Upload-Cloudinary.md`
- `0119--Personal Access Token Github.md`
- `0515-Google-Gemini-API-KYE.md`

扱い:

- 参照するなら「存在」と「目的」だけを索引化する。
- 値は絶対にdocsへ転記しない。
- 既に有効な可能性があるため、外部サービス側でローテーション対象として扱う。
- vault全体コピーをするなら、先に secret scanner を通し、検出ファイルは除外またはマスク版だけ生成する。

## 追加戦略アイデア

### 1. Pump.fun Graduation Watcher

狙い:
- Pump.funの卒業前後イベントだけを観測し、売買ではなくイベントデータを蓄積する。

入力:
- token address
- market cap
- liquidity
- token age
- volume
- holder distribution
- dev holding
- insider supply
- social presence
- buy wallet size
- SOL trend

仮説:
- `$65k-$69k` 付近のmarket cap帯、または卒業直前/直後で、特定の流動性・保有分布・買い手構成を満たす銘柄だけに短期優位が残る可能性がある。

検証:
- まず売買せず、全イベントを保存。
- 1分、5分、15分、60分後リターンをラベル化。
- 手数料、スリッページ、約定不能を悪めに入れる。

### 2. Meme Token First Bounce Detector

狙い:
- 急騰後の急落から最初の反発だけを検出する。

条件候補:
- ATHからの下落率が一定以上。
- 直近5分volumeが一定以上。
- 新規ウォレット買いが出る。
- dev/insider比率が閾値以下。
- liquidityが最低ライン以上。
- SOL地合いが悪すぎない。

注意:
- ノート内の勝率や利益主張は検証前提にしない。
- 実運用より先にイベントスタディとして扱う。

### 3. Trend + Regime Two-Layer Bot

狙い:
- 短期モデルが買いでも、長期レジームが悪い時は見送る。

構成:
- `short_term_predictor`: LightGBMなどで短期方向/ボラを推定。
- `regime_identifier`: トレンド、レンジ、高ボラ、崩壊局面を判定。
- `risk_manager`: レジームごとにポジション上限、SL/TP、取引停止条件を変更。

使えるノート:
- `0710-Strategy0010.md`
- `0714-AlphaTrendを超えて。.md`
- `1117_uptrend_botΧ.md`

### 4. Feature Factory + Walk-Forward Gate

狙い:
- アイデアを増やすほど過学習するため、特徴量追加をゲート制にする。

採用条件:
- walk-forwardで改善。
- 取引コスト込みで改善。
- パラメータ感度が鈍い。
- 特定期間だけの改善ではない。
- turnoverが増えすぎない。

使えるノート:
- `0714-AlphaTrendを超えて。.md`
- `0715-勾配ブースティングアリゴリズム.md`
- `0906_モンテカルロ.md`
- `数理モデル統計学的手法/遺伝的アルゴリズム_0325.md`

### 5. Multi-Objective Parameter Search

狙い:
- 利益最大化だけでなく、DD、売買回数、スリッページ耐性、安定性を同時に最適化する。

候補:
- NSGA-III
- MOEA/D
- CMA-ES
- surrogate-assisted GA

目的関数:
- maximize: net return, Sharpe/Sortino
- minimize: max drawdown, turnover, tail loss, parameter sensitivity
- constraint: minimum trade count, maximum exposure, live latency

## 次にコピーするならこの順

安全寄りに追加コピーする候補:

1. `00605_DexBot_Pumpfun.md`
2. `0710-Strategy0010.md`
3. `0714-AlphaTrendを超えて。.md`
4. `0715-Alt-Alpha-Trend改2131.md`
5. `1117_uptrend_botΧ.md`
6. `1202-SolVal Guardian (SG).md`
7. `Meme-Tokens!/1228-Get x10 Profits.md`
8. `0715-勾配ブースティングアリゴリズム.md`
9. `0906_モンテカルロ.md`
10. `1101_時系列予測.md`
11. `数理モデル統計学的手法/遺伝的アルゴリズム_0325.md`

コピー除外またはマスク必須:

1. `0205-重要Hyperliquid_API_KEY.md`
2. `@@@1222-Bybit_Bot_main_API-Key.md`
3. `@@@@@_LobeChat_VPN.md`
4. `1202-API-Devbot.md`
5. `0630-Bybit-API-KEY.md`

## 誤謬リスク

- YouTube要約やX由来のノートは、数字や勝率が誇張されている可能性が高い。
- API/OSSの仕様は現時点で変わっている可能性がある。実装に入る前に公式ドキュメントまたはリポジトリで確認する。
- ノート内のコード断片は、動作保証ではなく設計メモとして扱う。
- Meme token系は流動性、MEV、約定遅延、ラグプル、凍結、バンドル、API制限の影響が大きい。バックテストだけでは危険。
- secretを含むノートがあるため、vault全体コピーや公開リポジトリへの追加は必ずマスク処理が必要。

