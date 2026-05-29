# Source To Appendix Map

原ノート24本を、どの付録で実務資料に変換したかの対応表です。原本の物語を保存するのではなく、戦略準備に使える部品、検査、テンプレートへ分解します。

| 原ノート | 主な変換先 | 変換後の扱い |
|---|---|---|
| `0212-Trend-Bot.md` | `05_WORKED_EXAMPLE_TREND_PULLBACK.md`, `02_COMPONENT_CARDS.md` | trend signalを注文命令ではなくcandidateとして扱う |
| `0714-Adaptive-Alpha-Trendトレードプログラム.md` | `07_MODEL_AND_FEATURE_RISK_SHEETS.md`, `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md` | 巨大AI構想をfeature/model/risk検査に分解 |
| `0714-トレード戦略-Order-Book.md` | `02_COMPONENT_CARDS.md`, `04_ARTIFACT_EXAMPLES.md` | 方向予測よりparticipation/slippage filterとして扱う |
| `0721-RiskGuard Crypto Engine(RGCE).md` | `02_COMPONENT_CARDS.md`, `09_CHECKLISTS_AND_TEMPLATES.md` | risk guardと停止条件のカードに変換 |
| `0722-トレードシステム（SDH）.md` | `01_PIPELINE_DIAGRAMS.md`, `03_REPO_IMPLEMENTATION_MAP.md` | システム構想をpipeline境界へ分解 |
| `0507-戦略1_適応型ボラティリティ...md` | `02_COMPONENT_CARDS.md`, `05_WORKED_EXAMPLE_TREND_PULLBACK.md` | volatility scalingをsizer/risk縮小へ限定 |
| `0507-戦略2_レジームスイッチング...md` | `02_COMPONENT_CARDS.md`, `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md` | regime detectorを予測ではなく稼働制御にする |
| `0507-戦略3_オンチェーンデータ...md` | `08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md`, `07_MODEL_AND_FEATURE_RISK_SHEETS.md` | on-chainを確信度でなく危険除外と観測に使う |
| `0507_戦略4_マルチアセット...md` | `09_CHECKLISTS_AND_TEMPLATES.md` | portfolio allocationは後段。まず単一戦略の検証が先 |
| `0507-戦略5_トレンドの成熟度...md` | `02_COMPONENT_CARDS.md`, `05_WORKED_EXAMPLE_TREND_PULLBACK.md` | exit moduleとtime/risk/profit exitへ分解 |
| `0721-LightGBM パラメータチューニング.md` | `07_MODEL_AND_FEATURE_RISK_SHEETS.md` | 価格予測ではなくfilter/model risk資料へ変換 |
| `0725-時系列-予測モデル.md` | `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md`, `07_MODEL_AND_FEATURE_RISK_SHEETS.md` | forecastを売買命令にせず、残差やregime補助へ限定 |
| `0902-Genetic Alogo for Trading.md` | `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md`, `10_NARRATIVE_RISK_FLASHCARDS.md` | 探索は過剰最適化リスクとして扱う |
| `1114_ポートフォリオ最適化.md` | `09_CHECKLISTS_AND_TEMPLATES.md` | sizing/exposure管理テンプレートへ落とす |
| `0702-cryptofetch.md` | `04_ARTIFACT_EXAMPLES.md`, `03_REPO_IMPLEMENTATION_MAP.md` | data collectorとsource confidenceの例へ変換 |
| `1021_SOLANA.md` | `08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md` | account/token/program理解と安全確認へ変換 |
| `1107_自動化された暗号通貨ニュースで稼ぐ方法.md` | `10_NARRATIVE_RISK_FLASHCARDS.md`, `09_CHECKLISTS_AND_TEMPLATES.md` | news automationを観測/ラベル付けに限定 |
| `1129-Solanaトレーディングボット.md` | `08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md` | auto buyではなくobserver-firstとsellability check |
| `1202-JitoとSolana.md` | `08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md`, `11_CURRENTNESS_SOURCE_NOTES.md` | 低遅延優位ではなくexecution observation |
| `0710-VectorBT.md` | `07_MODEL_AND_FEATURE_RISK_SHEETS.md`, `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md` | vectorized screeningと実約定検査を分ける |
| `0722-PyBotters.md` | `03_REPO_IMPLEMENTATION_MAP.md`, `11_CURRENTNESS_SOURCE_NOTES.md` | 接続層候補。bot安全性とは分ける |
| `1026_Backtest_Trade!.md` | `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md`, `04_ARTIFACT_EXAMPLES.md` | backtestを採用証明ではなく棄却検査にする |
| `1031_Trading with polars.md` | `07_MODEL_AND_FEATURE_RISK_SHEETS.md` | 高速化ではなくfeature correctness検査へ変換 |
| `1117_バックテストについて.md` | `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md`, `09_CHECKLISTS_AND_TEMPLATES.md` | scorecardとreject rulesへ落とす |

## Coverage Check

| 領域 | 付録での補強 |
|---|---|
| 戦略部品 | `02_COMPONENT_CARDS.md` |
| repo実装先 | `03_REPO_IMPLEMENTATION_MAP.md` |
| 実成果物 | `04_ARTIFACT_EXAMPLES.md` |
| 具体例 | `05_WORKED_EXAMPLE_TREND_PULLBACK.md` |
| 検証 | `06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md` |
| ML/feature | `07_MODEL_AND_FEATURE_RISK_SHEETS.md` |
| Solana/Jito | `08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md` |
| 作業テンプレート | `09_CHECKLISTS_AND_TEMPLATES.md` |
| ナラティブ誤謬 | `10_NARRATIVE_RISK_FLASHCARDS.md` |
| currentness | `11_CURRENTNESS_SOURCE_NOTES.md` |
