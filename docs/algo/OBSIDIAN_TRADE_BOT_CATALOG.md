# Obsidian Vault: Trade/Bot Catalog

Source vault: `/home/tn/Docs/algo/obsidian-vault`

抽出方針:
- タグとフォルダ名ではなく、本文タイトル、見出し、技術語、戦略語、取引所語、検証語で拾った。
- 「多少でも役立つ」を広めに解釈し、直接戦略、検証、データ取得、Bot 実装、運用補助まで含めた。
- 既存の秘密値はこの文書へ転記しない。

## このカタログから見える戦略テーマ

- `トレンド追随`
  - AlphaTrend 系、Trend-Bot 系、uptrend_bot 系がある。
  - 発想: 長期足で regime を決め、短期足は押し目/戻りだけを取る。
- `板・マイクロ構造`
  - Order Book 系、PyBotters 系、Bybit/Solana 実装系がある。
  - 発想: 価格予測より約定改善、ダマシ回避、ブレイク前の需給偏り検出に使う。
- `モデル駆動`
  - LightGBM、時系列予測、勾配ブースティング、遺伝的アルゴリズム、Monte Carlo がある。
  - 発想: 方向そのものより、取引可否、閾値調整、regime 分類、配分最適化に使う。
- `Bot 実装/自動化`
  - API、Crawler、Agent、Prompt 系が多い。
  - 発想: データ収集、ニュース監視、研究補助、執行補助を別プロセス化できる。
- `運用基盤`
  - Ubuntu、self-host、Proxmox、security 系が多い。
  - 発想: シグナル改善より先に、安定稼働、再接続、時刻同期、デプロイを整えるべき場面がある。

## A. 直接トレード/Bot に近い

- `00605_DexBot_Pumpfun.md`
- `0124-SOLANA-TRADE.md`
- `0205-重要Hyperliquid_API_KEY.md`
- `0212-Trend-Bot.md`
- `0630-Bybit-API-KEY.md`
- `0710-Strategy0010.md`
- `0710-VectorBT.md`
- `0714-Adaptive-Alpha-Trendトレードプログラム.md`
- `0714-AlphaTrendを超えて。.md`
- `0714-トレード戦略-Order-Book.md`
- `0715-Alt-Alpha-Trend改2131.md`
- `0721-RiskGuard Crypto Engine(RGCE).md`
- `0722-PyBotters.md`
- `0729-Teams-BOT-開発.md`
- `0902-Genetic Alogo for Trading.md`
- `0905-M15戦略 for Hyperliquid Prep.md`
- `1021_SOLANA.md`
- `1026_Backtest_Trade!.md`
- `1031_Trading with polars.md`
- `1106_Trading Tool.md`
- `1114_ポートフォリオ最適化.md`
- `1117_uptrend_botΧ.md`
- `1117_バックテストについて.md`
- `1122_SOL_web3.md`
- `1129-Solanaトレーディングボット.md`
- `1201-Self-Hosted Bot Protection.md`
- `1202-API-Devbot.md`
- `1202-JitoとSolana.md`
- `1202-Solana Development.md`
- `1202-トークンが凍結されている場合、凍結を解除する方法.md`
- `1221-Q-bot.md`
- `1221-テクニカルを超えて.md`
- `1223-BOT-PHOTON-and-NeoBullX.md`
- `@@@1222-Bybit_Bot_main_API-Key.md`
- `@@@@@_LobeChat_VPN.md`
- `@@Prompts-for-あるごトレードAI.md`
- `Meme-Tokens!/1228-Get x10 Profits.md`

## B. モデル・予測・最適化

- `0203-MS-Azuru-AI.md`
- `0708-戦略めも.md`
- `0711-IRIS金融.md`
- `0715-勾配ブースティングアリゴリズム.md`
- `0721-LightGBM パラメータチューニング.md`
- `0725-時系列-予測モデル.md`
- `0726-資料：金融とトレード.md`
- `0906_モンテカルロ.md`
- `1101_時系列予測.md`
- `1127-ベクトル検索.md`
- `1129-価格予測.md`
- `1201-Create Time Series Animations.md`
- `数理モデル統計学的手法/遺伝的アルゴリズム_0325.md`

## C. データ取得・リサーチ自動化・実装補助

- `0025-0604 Mem0.md`
- `0103-AI-agent-crypto.md`
- `0105-Eliza-AI-Agents.md`
- `0108-crypto AI agent.md`
- `0226 OSS Mastra.md`
- `0310-awesome-mcp-servers.md`
- `0506-Bruno-API-Tool.md`
- `0510-ScrapeGraph情報収集.md`
- `0515-Google-Gemini-API-KYE.md`
- `0518-AI-Setting-Prompt.md`
- `0522_公開されているAPIについて.md`
- `0525-Gemini-API-Key.md`
- `0702-cryptofetch.md`
- `0703-CE(Claude Engineer).md`
- `0708-@System-prompt-IRIS.md`
- `0710-APIs.md`
- `0711-定量的トレード戦略開発プロンプト.md`
- `0714-Tool-Crawlee-Scraping-Library.md`
- `0716-Tool-GPT-Academic.md`
- `0717-2108-Tool-CE.md`
- `0722-1141-コード解析ツール案.md`
- `0726-リサーチツールを作ろう！.md`
- `0726-資料_APIs.md`
- `0809-ai-docmerge.md`
- `0907_GRAP (Graph-Based Repository Analyzer Prompt).md`
- `0911_CustomInstructions_Prompt.md`
- `1004_crawl4ai.md`
- `1005_AI_News.md`
- `1021_Tutorial_How to Build AI Agents in Plain English.md`
- `1022_Agent0.md`
- `1103_Crawl4AI LLM Friendly Web Crawler & Scrapper.md`
- `1103_Scraper_maxun.md`
- `1122_multi-agent-orchestrator.md`
- `1129-Firecrawl.md`
- `1130-CopilotKit.md`
- `1202-Qwen-Agent.md`
- `1223-Haystack-サーバーRAGで使えそう.md`
- `251124_AIログ取得ブックマークレット.md`
- `LLM-Prompts/@0516_Prompt_SARB、CERA、CGRRP.md`
- `LLM-Prompts/@0527-Prompt-system(Coding+).md`
- `LLM-Prompts/@0706_Prompts.md`
- `LLM-Prompts/@0911_Prompt翻訳.md`
- `LLM-Prompts/@@0710-ChatGPTs解析プロンプト.md`
- `LLM-Prompts/@@0712-改訂版IRISカスタムインストラクション.md`
- `LLM-Prompts/@@0819_AIMEEプロセス_思考プロセス.md`

## D. インフラ・運用・セキュリティ

- `0102-selfhost_reddit.md`
- `0502-MemoUbuntu-24.04_開発環境構築ガイド.md`
- `0502-サーバーの管理と保守と運用.md`
- `0502自宅サーバーを公開する際のセキュリティ設定ガイド.md`
- `0502開発環境のセキュリティ.md`
- `0503-Linux-Commands.md`
- `0503-中小企業向けのセキュアなオフィスシステムを導入、開発、保守.md`
- `0510-SELF-HOST-Dokploy.md`
- `0515-PROXMOX VIRTUAL ENVIRONMENT(PVE)のインストール.md`
- `0519-ProxmoxExtension.md`
- `0521-Ubuntu開発環境構築.md`
- `0521-Ubuntu開発環境構築ガイド.md`
- `0522-2235-Ubuntu24.04+Zsh.md`
- `0530-新環境での開発環境構築.md`
- `0730-Docerファイルのベストプラクティス.md`
- `0909_コンテナの監視_Dozzle.md`
- `0911_Proxmoxを使ったホームラボのベストプラクティス.md`
- `0918_WezTerm.md`
- `1017_WSLにUbuntu24.10をセットアップするガイド.md`
- `1022_Whisper_WebUI.md`
- `1030-1451-Tab-Manager環境構築\`setup.sh\`.md`
- `1030_DevContainer「Tab-Manager」004.md`
- `1129-Linuxシステムのセキュリティ.md`
- `1130-ProxmoxUpdate.md`
- `1203-Proxmox Helper Scripts.md`
- `1203-Proxmox-VE-8.3.0.md`
- `1228-Proxmox-VE/1228-fast-pool-defoult.md`
- `1230-HomeLab.md`
- `Ubuntu/uv(python).md`
- `Ubuntu/Pythonでの開発.md`
- `Ubuntu/Python環境構築.md`
- `Ubuntu/開発_Units_Tests.md`

## E. すぐ使いそうな観点

- 戦略の叩き台:
  - `0714-Adaptive-Alpha-Trendトレードプログラム.md`
  - `0715-Alt-Alpha-Trend改2131.md`
  - `0212-Trend-Bot.md`
  - `1117_uptrend_botΧ.md`
- バックテスト/評価:
  - `0710-VectorBT.md`
  - `1026_Backtest_Trade!.md`
  - `1117_バックテストについて.md`
  - `1114_ポートフォリオ最適化.md`
  - `0906_モンテカルロ.md`
- 執行/取引所接続:
  - `0722-PyBotters.md`
  - `0714-トレード戦略-Order-Book.md`
  - `1129-Solanaトレーディングボット.md`
  - `1202-JitoとSolana.md`
- 予測/特徴量:
  - `0721-LightGBM パラメータチューニング.md`
  - `0715-勾配ブースティングアリゴリズム.md`
  - `0725-時系列-予測モデル.md`
  - `1101_時系列予測.md`
- 自動調査/ニュース/情報収集:
  - `1107_自動化された暗号通貨ニュースで稼ぐ方法.md`
  - `0702-cryptofetch.md`
  - `1103_Crawl4AI LLM Friendly Web Crawler & Scrapper.md`
  - `1129-Firecrawl.md`

## 気づきメモ

- 戦略候補を考える時、vault 内の材料は `単一モデルを磨く` より `複数レイヤを積む` 方向に豊富。
- 価格系列だけのノートより、`板` `ニュース` `取引所固有制約` `Bot の停止条件` を含むノートの方が、実運用へ近い。
- `Backtest` 系ノートは複数あるが、共通する論点は「研究速度」と「多時間軸対応」。つまり戦略の中身以前に研究基盤がボトルネックになりやすい。
- `Solana` 系が複数あるので、CEX 中心ではなく on-chain 執行や meme/token 監視まで視野を広げられる。
- `ポートフォリオ最適化` は資産配分だけでなく、戦略配分、銘柄配分、時間帯配分の設計にも読み替えられる。
- `遺伝的アルゴリズム` と `LightGBM` は、売買ルールの自動発見よりも、既存ルールの補助フィルタや閾値最適化として使う方が現実的に見える。

## これから戦略を考える時の問い

- どのノートが `エントリー精度` を上げるのか。
- どのノートが `見送り判断` を上げるのか。
- どのノートが `損失の膨張を止める` のか。
- どのノートが `研究の回転速度` を上げるのか。
- どのノートが `実運用の事故率` を下げるのか。
- 1つのノートを深掘るより、2-3枚を組み合わせた時に新しい戦略像が出るか。

## 組み合わせの例

- `Trend-Bot` + `Order Book` + `RiskGuard`
  - 方向、タイミング、停止条件を分離する構成。
- `Adaptive Alpha Trend` + `LightGBM` + `VectorBT`
  - 指標戦略へ ML フィルタを重ねて高速検証する構成。
- `PyBotters` + `Bybit/Solana` ノート群 + `Self-Hosted Bot Protection`
  - 実執行と運用保守を最初から一体で考える構成。
- `ニュース/収集系` + `時系列予測` + `ポートフォリオ最適化`
  - 銘柄選定、regime 判定、配分決定を分ける構成。

## 注意

- `API_KEY` や取引所認証がファイル名に出ているノートは、再利用前に秘密情報の扱いを必ず分離する。
- 一部は直接実装ノートではなく、記事メモ、比較メモ、ツール調査を含む。
- このカタログは「候補を落とさない」ことを優先しているため、広めに載せている。
