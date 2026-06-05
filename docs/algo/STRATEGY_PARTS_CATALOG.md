<!--
作成日: 2026-05-28_20:41 JST
更新日: 2026-06-05_08:11 JST
-->

# Strategy Parts Catalog

汎用的な戦略を作るための部品カタログです。各部品は、単独で差し替えられるように、目的、入力、出力、失敗モード、検証指標を持ちます。

## 1. Universe Selector

目的:
- 取引対象を選ぶ。

入力:
- 市場種別: CEX, DEX, Solana, Pump.fun, Meme token, BTC/ETHなど。
- 流動性、出来高、market cap、上場/生成時刻、テーマ、ニュース。

出力:
- 監視対象銘柄リスト。
- 除外理由つきの除外リスト。

差し替え候補:
- 固定銘柄: BTC/ETH/SOLなど。
- テーマ銘柄: AI-agent、Solana ecosystemなど。
- イベント銘柄: Pump.fun卒業前後、Raydium移行、ATH更新など。

失敗モード:
- 対象を広げすぎてノイズが増える。
- 対象を絞りすぎてtrade countが消える。
- 生存者バイアスのある銘柄だけで検証する。

検証指標:
- 候補数、除外率、実際に取引可能だった割合、対象別リターン分布。

関連ノート:
- `00605_DexBot_Pumpfun.md`
- `0124-SOLANA-TRADE.md`
- `0103-AI-agent-crypto.md`
- `Meme-Tokens!/1228-Get x10 Profits.md`

## 2. Data Collector

目的:
- 戦略と検証に必要なデータを収集、保存する。

入力:
- OHLCV、板、WebSocketイベント、オンチェーン情報、ニュース、SNS、APIレスポンス。

出力:
- timestamp付きの正規化データ。
- 欠損、遅延、再接続、レート制限のログ。

差し替え候補:
- CEX API
- PyBotters
- PumpPortal WebSocket
- DEX Screener/Birdeye系API
- ニュース/リサーチ収集Bot

失敗モード:
- timestampが揃わない。
- 欠損や重複を検出できない。
- API制限によりデータが歪む。
- backtestデータとliveデータの粒度が違う。

検証指標:
- 欠損率、重複率、遅延、再接続回数、API error rate、保存件数。

関連ノート:
- `0722-PyBotters.md`
- `00605_DexBot_Pumpfun.md`
- `0722-トレードシステム（SDH）.md`
- `1202-SolVal Guardian (SG).md`

## 3. Feature Factory

目的:
- 生データを戦略で使える特徴量へ変換する。

入力:
- OHLCV、板、オンチェーン、イベント、ニュース、銘柄メタデータ。

出力:
- 特徴量テーブル。
- 特徴量の定義、計算周期、欠損扱い。

差し替え候補:
- テクニカル: ADX, ATR, RSI, MACD, Bollinger Bands。
- 板: imbalance, depth slope, spread, absorption proxy。
- Meme/Solana: token age, liquidity, market cap, dev holding, insider supply, new wallet buy。
- 研究補助: social presence, news count, theme score。

失敗モード:
- 未来情報を混ぜる。
- 特徴量を増やしすぎて過学習する。
- 欠損処理で分布を歪める。
- liveで計算できない特徴量を使う。

検証指標:
- 特徴量欠損率、重要度安定性、walk-forward改善、leakage検査結果。

関連ノート:
- `1031_Trading with polars.md`
- `0710-Strategy0010.md`
- `0715-勾配ブースティングアリゴリズム.md`
- `0507-戦略3_オンチェーンデータ強化型トレンド確信度モデル戦略.md`

## 4. Regime Detector

目的:
- 市場状態を分類し、戦略選択やサイズ調整に使う。

入力:
- ADX、realized volatility、volume spike、trend slope、spread proxy、order book summary。

出力:
- `trend`, `range`, `high_vol_trend`, `panic`, `thin_liquidity` などの状態。
- 判定信頼度。

差し替え候補:
- ルールベース。
- LightGBM/XGBoost。
- 時系列モデル。
- volatility clustering。

失敗モード:
- ラベル定義が曖昧。
- 状態が頻繁に切り替わりすぎる。
- 過去の極端相場に過適合する。

検証指標:
- 状態別PnL、状態遷移頻度、DD削減、classifier stability。

関連ノート:
- `0507-戦略2_レジームスイッチング・トレンドフォロー戦略.md`
- `0721-LightGBM パラメータチューニング.md`
- `1101_時系列予測.md`
- `1221-テクニカルを超えて.md`

## 5. Signal Generator

目的:
- エントリー候補を出す。

入力:
- regime、特徴量、価格、板、イベント。

出力:
- `candidate_long`, `candidate_short`, `no_signal`。
- エントリー根拠と想定stop。

差し替え候補:
- trend pullback。
- breakout retest。
- first bounce。
- order book confirmation。
- event-triggered watchlist。

失敗モード:
- シグナル数が多すぎる。
- 方向だけ当たり、約定後に逆行する。
- 相場状態を無視して発火する。

検証指標:
- expectancy、win rate、profit factor、entry後N本の逆行幅、trade count。

関連ノート:
- `0212-Trend-Bot.md`
- `0714-Adaptive-Alpha-Trendトレードプログラム.md`
- `0714-トレード戦略-Order-Book.md`
- `Meme-Tokens!/1228-Get x10 Profits.md`

## 6. Participation Filter

目的:
- シグナルが出ても、入らない局面を除外する。

入力:
- liquidity、spread、volatility、order book、SOL地合い、異常スコア、ニュース/テーマ、token risk。

出力:
- `allow`, `skip`, `pause`。
- 見送り理由。

差し替え候補:
- liquidity filter。
- anomaly skip filter。
- SOL macro filter。
- dev/insider risk filter。
- spread/slippage filter。

失敗モード:
- フィルタを重ねすぎて取引が消える。
- 良いシグナルも除外しすぎる。
- 検証後に都合よく閾値を合わせる。

検証指標:
- skip率、skip後の回避損益、通過後expectancy、CVaR改善。

関連ノート:
- `0714-AlphaTrendを超えて。.md`
- `0721-RiskGuard Crypto Engine(RGCE).md`
- `0906_モンテカルロ.md`
- `Meme-Tokens!/1228-Get x10 Profits.md`
- `1202-トークンが凍結されている場合、凍結を解除する方法.md`

## 6.5. Token Safety Filter

目的:
- Solana/Meme tokenの売買不能、rug、凍結、権限リスクを事前に除外する。

入力:
- mint authority、freeze authority、holder distribution、liquidity lock、pool age、dev wallet、insider supply、trading enable/disable状態。

出力:
- `safe_to_observe`, `unsafe_skip`, `needs_manual_review`。
- 除外理由。

差し替え候補:
- freeze authority check。
- mint authority check。
- holder concentration check。
- liquidity/pool risk check。
- sniper-attraction pattern as defensive risk score。

失敗モード:
- 権限情報を取得できず安全と誤判定する。
- 悪性トークンを検知できない。
- 条件を厳しくしすぎて観測対象が消える。
- 攻撃的なトークン設計に転用してしまう。

検証指標:
- 除外率、除外後の事後rug/freeze発生率、false positive、manual review率。

関連ノート:
- `1202-トークンが凍結されている場合、凍結を解除する方法.md`
- `0527_Rugg_計画とSniper分析.md`
- `1223-BOT-PHOTON-and-NeoBullX.md`

## 7. Position Sizer

目的:
- 取引サイズを決める。

入力:
- volatility、ATR、equity、DD、signal confidence、regime、戦略間相関。

出力:
- position size、max exposure、leverage cap。

差し替え候補:
- fixed fraction。
- ATR sizing。
- volatility targeting。
- Kelly fraction with cap。
- strategy allocation。

失敗モード:
- 勝率が低い戦略でサイズが膨らむ。
- high-vol局面で過大リスクを取る。
- 複数戦略の相関を無視する。

検証指標:
- MDD、CVaR、risk of ruin、exposure、turnover、equity curve smoothness。

関連ノート:
- `1114_ポートフォリオ最適化.md`
- `0507-戦略1_適応型ボラティリティ・スケーリング付きマルチシグナル・トレンド戦略.md`
- `0507_戦略4_マルチアセット・ダイナミック・トレンドアロケーション戦略.md`

## 8. Exit Module

目的:
- いつ降りるかを決める。

入力:
- entry price、ATR、trend maturity、time in trade、order book、profit state、regime。

出力:
- stop loss、take profit、trailing stop、time stop、panic exit。

差し替え候補:
- ATR stop。
- fixed R multiple。
- trailing。
- trend maturity exit。
- liquidity exit。

失敗モード:
- 利確が早すぎる。
- 損切りが広すぎる。
- トレンド終盤で利益を返す。
- 流動性低下時に逃げられない。

検証指標:
- average R、MAE/MFE、profit giveback、holding period、tail loss。

関連ノート:
- `0507-戦略5_「トレンドの成熟度」判定によるイグジット戦略.md`
- `0212-Trend-Bot.md`
- `0714-AlphaTrendを超えて。.md`

## 9. Risk Guard

目的:
- 戦略が壊れた時に止める。

入力:
- realized PnL、DD、連敗数、API状態、約定状態、データ欠損、position exposure。

出力:
- reduce size、pause new entries、close positions、hard stop。

差し替え候補:
- daily loss limit。
- max drawdown stop。
- losing streak stop。
- data quality stop。
- API/execution stop。

失敗モード:
- 止める条件が遅すぎる。
- 一時的なDDで止めすぎる。
- data/API異常を戦略損益と混同する。

検証指標:
- stop発動回数、stop後回避損益、false stop rate、最大損失削減。

関連ノート:
- `0721-RiskGuard Crypto Engine(RGCE).md`
- `1202-SolVal Guardian (SG).md`
- `0715-Alt-Alpha-Trend改2131.md`

## 10. Execution Adapter

目的:
- paper/live、CEX/DEX、API差分を吸収する。

入力:
- intended order、position size、venue、price constraints、rate limit。

出力:
- order result、fill、slippage、error、retry state。

差し替え候補:
- paper executor。
- PyBotters。
- CEX REST/WebSocket。
- Solana/DEX executor。

失敗モード:
- backtestとliveの約定前提が違う。
- API retryで重複注文する。
- rate limitでシグナルが遅れる。
- slippageを記録しない。

検証指標:
- fill rate、slippage、latency、reject rate、retry count、duplicate order count。

関連ノート:
- `0722-PyBotters.md`
- `1106_Trading Tool.md`
- `1202-SolVal Guardian (SG).md`

## 10.5. API And Data Source Registry

目的:
- データソース、API、RPC、レート制限、認証方式、利用可否を管理する。

入力:
- API名、用途、認証有無、rate limit、費用、取得できるデータ、禁止事項。

出力:
- data source registry。
- strategyごとの必要API一覧。
- secret requiredフラグ。

差し替え候補:
- public APIs。
- DEX/Solana APIs。
- CEX APIs。
- self-hosted collectors。

失敗モード:
- API仕様変更に気づけない。
- 秘密値をdocsへ混入する。
- rate limitを無視してliveで欠損する。
- 無料枠前提で本番相当の検証をする。

検証指標:
- API error rate、rate limit hit、coverage、cost、secret exposure count。

関連ノート:
- `0522_公開されているAPIについて.md`
- `0710-APIs.md`

## 11. Evaluation Harness

目的:
- 戦略を安全に捨てるための検証基盤。

入力:
- strategy config、historical data、cost model、slippage model、walk-forward settings。

出力:
- metrics、equity curve、trade log、stress results、rejection reason。

差し替え候補:
- vectorbt。
- Polars。
- custom event replay。
- Monte Carlo。
- genetic/parameter search。

失敗モード:
- コストなしで評価する。
- 同じ期間で最適化と評価をする。
- trade countが少なすぎる。
- parameterが少し変わるだけで壊れる。

検証指標:
- net return、PF、MDD、CVaR、Sharpe/Sortino、turnover、parameter stability。

関連ノート:
- `0710-VectorBT.md`
- `1026_Backtest_Trade!.md`
- `1117_バックテストについて.md`
- `0906_モンテカルロ.md`
- `数理モデル統計学的手法/遺伝的アルゴリズム_0325.md`

## 12. Monitoring Layer

目的:
- 研究、paper、liveの状態を観測する。

入力:
- data quality、signals、orders、fills、PnL、exceptions、resource usage。

出力:
- logs、metrics、alerts、dashboard、daily report。

差し替え候補:
- structured logger。
- metrics analyzer。
- Streamlit/dashboard。
- alert system。

失敗モード:
- 壊れているのに気づけない。
- paperとliveの差分を記録しない。
- データ欠損と戦略悪化を区別できない。

検証指標:
- alert precision、incident count、MTTR、data gap count、paper/live divergence。

関連ノート:
- `1202-SolVal Guardian (SG).md`
- `0715-Alt-Alpha-Trend改2131.md`
- `0722-トレードシステム（SDH）.md`

## 13. Security And Exposure Guard

目的:
- Bot、dashboard、API、collectorを外部公開する時の攻撃面を小さくする。

入力:
- 公開URL、認証、rate limit、WAF、ログ、API key管理、IP制限。

出力:
- exposure checklist。
- required protections。
- block/alert log。

差し替え候補:
- WAF/reverse proxy。
- rate limit。
- basic auth or SSO。
- IP allowlist。
- secret scanner。

失敗モード:
- dashboardやcollectorを無防備に公開する。
- API keyをログやdocsへ漏らす。
- bot保護が強すぎて自分のcollectorも止める。
- 攻撃ログを監視しない。

検証指標:
- blocked request count、auth failure count、secret scanner hits、public endpoint inventory。

関連ノート:
- `1201-Self-Hosted Bot Protection.md`
- `1202-SolVal Guardian (SG).md`

## 14. Research Assistant Layer

目的:
- LLMやAI agentを、売買判断ではなく調査、説明、候補生成、ログ要約に使う。

入力:
- strategy logs、market summaries、feature importance、news、source notes。

出力:
- natural language insight。
- review checklist。
- experiment brief。
- anomaly explanation。

差し替え候補:
- Streamlit + local LLM。
- AI agent workflow。
- prompt templates。
- RAG over source notes。

失敗モード:
- LLMの説明を売買根拠として過信する。
- 出典不明の要約を正本化する。
- hallucinationを検証なしで採用する。
- 秘密値をプロンプトへ流す。

検証指標:
- citation coverage、human review rate、hallucination count、secret prompt exposure count。

関連ノート:
- `1107_毎分ストックデータを取得し、トレンドを分析し、リアルタイムでわかりやすい説明を提供.md`
- `1228-AI Agent Blueprint.md`
- `0711-定量的トレード戦略開発プロンプト.md`
