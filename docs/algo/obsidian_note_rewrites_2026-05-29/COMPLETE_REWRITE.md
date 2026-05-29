# Complete Rewrite Of Obsidian Algo Notes

このドキュメントは、`../obsidian_note_copies/` の24本を、原本を読まなくても戦略準備に使える形へ再構成したものです。

## 0. 全体結論

原ノート群に共通する価値は「戦略部品の素材が多い」ことです。一方で、完成戦略、AI予測、bot自動化、低レイテンシー、オンチェーン優位性、ニュース自動化など、魅力的だが検証前の物語が多く混ざっています。

今後の使い方は次の順番に固定します。

1. まず売買しない。観測、記録、検証から始める。
2. 各ノートを `Universe`, `Data`, `Feature`, `Signal`, `Sizing`, `Exit`, `Execution`, `Risk Guard`, `Evaluation` に分解する。
3. 原ノートの「勝てる/稼げる/高精度/低遅延で有利」は、すべて仮説として扱う。
4. 実験は単純ベースラインから始める。複雑なモデルやbotは最後。
5. 採用条件より先に、捨て条件と停止条件を書く。

---

## 1. Core Trend Notes

### 1.1 `0212-Trend-Bot.md`

このノートは、上位足でトレンドを判定し、短期足で押し目買い/戻り売りを行うbot構想です。価値があるのは、単なるエントリーではなく、レバレッジ、マージンレシオ、ストップ、段階的利確、トレーリング、日次運用まで考えている点です。

ただし、上位足のトレンドがあるから短期足の押し目が期待値を持つ、という前提は未検証です。トレンドフォローは、大きなトレンドでは勝てますが、レンジ・急変・板の薄い時間帯で損失を積み上げます。

戦略部品としては、`Regime Detector`、`Pullback Signal`、`Position Sizer`、`Exit Module`、`Daily Risk Guard` に分けます。特に重要なのは、エントリー条件ではなく「稼働してはいけない相場」を先に作ることです。高スプレッド、低出来高、急変直後、連敗中、日次損失上限到達時は停止します。

実験するなら、まず BTC/ETH の高流動性ペアで、単純なMA/Donchianブレイクアウトと比較します。段階的利確やトレーリングは後から追加し、追加前後で最大DD、期待値、平均保有時間、turnoverが改善するかを見ます。

捨て条件は、手数料・slippage込みで単純トレンドフォローを上回らないこと、またはレンジ期間の損失が大きすぎることです。

### 1.2 `0714-Adaptive-Alpha-Trendトレードプログラム.md`

このノートは、AlphaTrendを中心に、データ処理、特徴量、異常検知、LightGBM、VaR/ES、stop/take profit、backtest、マルチ時間軸、センチメント、強化学習、代替データまで含む巨大構想です。

原本の問題は、機能を増やすほど戦略が強くなるように読める点です。実際には、機能を増やすほど、過学習、実装バグ、データリーク、運用不能のリスクが増えます。AlphaTrendは「戦略の核」ではなく、トレンド候補を作る1特徴量として扱うべきです。

重要な補正として、VaRは最大損失ではありません。信頼水準に対する損失分位点であり、tail riskは残ります。ES、stress test、gap/slippage、取引停止不能リスクを別に見る必要があります。また、stop lossは損失を完全には限定しません。急変時、板薄、API遅延、約定拒否で想定より悪化します。

使える部品は、`Feature Factory`、`Anomaly Filter`、`Model Layer`、`Risk Guard`、`Evaluation Harness` です。MLは価格予測ではなく、参加可否、リスク縮小、異常時停止の補助に限定します。

実験は、AlphaTrend単体 vs MA/Donchian/ATR breakoutから始めます。次に異常検知を足してDDが下がるかを見る。LightGBMや強化学習は、単純ベースラインに勝てる市場・期間が見つかってからです。

### 1.3 `0714-トレード戦略-Order-Book.md`

このノートは、注文簿の深さ、不均衡、傾斜、クラスタリング、機械学習で優位性を得るという内容です。原本の「板データの真の可能性」「競争市場で大きな優位性」という表現は、かなりマーケティング寄りです。

注文簿は情報量が多い一方、寿命が短く、自分が見た板に自分が約定できるとは限りません。方向予測に使うより、参加フィルタに使う方が現実的です。具体的には、spreadが広い、depthが薄い、cancelが急増、imbalanceが極端、板が飛ぶ、といった時に取引を見送るための部品にします。

戦略部品は `Participation Filter`、`Execution Cost Estimator`、`Size Cap`、`Order Type Selector` です。maker/taker、post-only、IOC、market orderの使い分けを検証対象にします。

実験は、既存シグナルに板フィルタを追加して、slippage、約定失敗率、想定価格との差が改善するかを見ること。板から次の価格方向を当てる実験は後回しです。

### 1.4 `0721-RiskGuard Crypto Engine(RGCE).md`

これは利益を出す戦略ではなく、botを壊れにくくする横断部品です。APIキー保護、データ統合、異常検知、テキスト処理、リスク監視などが含まれます。

重要なのは、防御機能を多く持つことではなく、異常時に確実に止まることです。API key暗号化だけでは不十分で、権限最小化、IP制限、read/write分離、ログマスク、dry-run、資金上限が必要です。

使う部品は `Security Guard`、`Data Freshness Gate`、`Position Exposure Guard`、`Kill Switch`、`Alerting`。戦略本体から独立させ、全戦略に同じ契約で適用します。

実験は障害注入です。価格欠損、WebSocket切断、REST 429、注文失敗、重複約定、残高取得失敗、急変、secretログ混入を起こし、止まるか確認します。

### 1.5 `0722-トレードシステム（SDH）.md`

SDHはデータハブ、低レイテンシー、VPS、Cloudflare、スキャルピング向け実装構想です。原本の危険は、低レイテンシー環境や多機能基盤を作れば優位性が出るように見える点です。

CloudflareやCDNは、一般的なWeb配信には有効ですが、取引所のmatching engineやWebSocket/APIの物理遅延を都合よく改善するものではありません。低レイテンシー競争は、取引所リージョン、network path、API制限、同業者の競争、MEVで成立するため、個人botが簡単に勝てる前提を置かない方がよいです。

SDHから取り出すべき部品は、低レイテンシー基盤ではなく、`Data Freshness Monitor`、`Execution Log`、`Error Budget`、`Kill Switch`、`Backtest/Live Gap Recorder` です。

最初の実験は取引しないデータ収集です。価格、板、WebSocket遅延、APIエラー、spread、約定可能性を1週間記録し、どの市場・時間帯なら検証に耐えるかを判断します。

---

## 2. Strategy Module Notes

### 2.1 `0507-戦略1_適応型ボラティリティ・スケーリング付きマルチシグナル・トレンド戦略.md`

このノートは、複数シグナルとボラティリティスケーリングを組み合わせたトレンド戦略です。使える核は、複数シグナルよりも、相場の荒さに応じてポジションを縮小する考え方です。

複数シグナルの一致は一見堅牢に見えますが、実際には取引回数が減り、過去の都合の良い局面だけを拾いやすくなります。最初は単一シグナルで、vol targetやATR sizingの有無を比較します。

実験では、単一シグナル、2シグナル、3シグナルを順に比較し、改善がどの部品から来たかを分離します。評価指標は総利益だけでなく、turnover、平均保有期間、DD、cost sensitivityです。

### 2.2 `0507-戦略2_レジームスイッチング・トレンドフォロー戦略.md`

これは、トレンドフォローを常時稼働させず、trend/range/high-vol/low-liquidityなどの状態で稼働を切り替える戦略です。

レジーム判定は未来を当てるものではありません。誤判定しても損失が限定される運転モード切替です。複雑なHMMやMLを使う前に、MA傾き、ADX、realized volatility、spread、volumeだけで十分です。

採用条件は、見送りによる機会損失より、避けた損失の方が安定して大きいこと。捨て条件は、トレンド終盤で参加し、レンジで損失を出すことです。

### 2.3 `0507-戦略3_オンチェーンデータ強化型トレンド確信度モデル戦略.md`

オンチェーン指標でトレンド確信度を作る案です。SOPR、MVRV、exchange flow、active address、fundingなどを使う想定ですが、短期売買でそのまま効くとは限りません。

オンチェーンデータは、ベンダー定義、更新遅延、履歴修正、チェーン差、料金に依存します。日次指標を分足/時間足の売買に入れると遅すぎることがあります。使うなら、中期レジーム、過熱警戒、ポジション縮小に寄せます。

実験は、価格だけのbaselineに指標を1つずつ足し、未使用期間でDDが下がるかを見る。複数指標を同時投入して良く見える結果は過学習を疑います。

### 2.4 `0507_戦略4_マルチアセット・ダイナミック・トレンドアロケーション戦略.md`

複数銘柄へ資金配分する戦略です。暗号資産では平時の分散が、急落時に消えやすい点が最大の注意点です。

平均分散最適化や複雑な配分モデルより、最初は流動性でUniverseを絞り、equal weight、vol target、銘柄上限、全体DD上限を使います。相関が急上昇した時にポジションを縮小できることが重要です。

実験はBTC/ETHだけから始め、大型L1/L2を追加するたびに、DD、turnover、同時損失、流動性低下時の約定コストを見る。

### 2.5 `0507-戦略5_「トレンドの成熟度」判定によるイグジット戦略.md`

トレンド終盤を見つけてExitする案です。危険なのは、天井や底を判定できるように見えることです。リアルタイムでは成熟度の判定は遅れたり外れたりします。

使うなら、天井を当てる部品ではなく、利益を守るExit Moduleとして扱います。ATR trail、時間切れ、部分利確、ボラ急拡大時縮小、勢い低下時縮小の比較が現実的です。

採用条件は、総利益だけでなく、利益分布、最大含み益からの戻り、DDが改善すること。捨て条件は、早降りが増えて大トレンドの利益を削ることです。

---

## 3. Model Research Notes

### 3.1 `0721-LightGBM パラメータチューニング.md`

LightGBMは強力ですが、金融時系列ではチューニングより先に、ラベル、時系列分割、特徴量の利用可能時点、手数料込み評価を固定する必要があります。

原ノートの「高精度」表現は補正します。LightGBMの役割は未来価格の予言ではなく、特徴量が取引判断に寄与するかを評価する補助です。classification accuracyやAUCが良くても、売買に変換すると手数料で消えることがあります。

実験順は、naive baseline、ロジスティック回帰、LightGBMの順。LightGBMを使う場合は、walk-forward、purge/embargo、feature importanceの安定性、別期間・別銘柄での劣化を見る。

公式パラメータはLightGBM docsで確認します。aliasやデフォルト値、deterministic関連、num_leaves/max_depth/min_data_in_leafの相互作用を古いメモのまま使わないこと。

### 3.2 `0725-時系列-予測モデル.md`

TimesFMやMOMENTなどの時系列モデルを扱うノートです。補正すべき点は、新しい時系列基盤モデルが金融売買でそのまま優位性になるわけではないことです。

価格方向予測より、volatility forecast、range forecast、anomaly score、regime shift detection、欠損補完の方が使いやすいです。予測モデルの出力を即エントリーにせず、参加可否やサイズ縮小に使います。

実験は、naive forecast、EWMA、ARIMA相当の単純手法と比較します。モデルが良くても、turnoverが増えたり、推論コストが高かったり、再現性が低ければ採用しません。

### 3.3 `0902-Genetic Alogo for Trading.md`

GA、HMM、AI agent、APIキー、コストなどが混ざるノートです。自律探索で良い戦略を見つける、という物語が最も危険です。

GAは探索力が強いほど、過去データへの適合が簡単になります。使うなら、売買ルール発見ではなく、部品組み合わせの仮説生成に限定します。fitnessには利益だけでなく、複雑性ペナルティ、DD、turnover、期間安定性を入れるべきです。

AI agentは、研究補助としては有用ですが、APIキー、外部送信、費用、再現性、幻覚が問題です。agentに売買判断やコード実行を任せないこと。

### 3.4 `1114_ポートフォリオ最適化.md`

ポートフォリオ最適化は、複数戦略/複数銘柄の配分に使えるが、暗号資産では入力推定誤差が大きく、相関が急変します。

平均リターンを推定して最適化するより、まず上限ルール、vol targeting、equal risk、最大DD制限を使います。複雑な最適化は、過去データに合わせて集中配分を作りやすい。

実験では、リバランス頻度、手数料、turnover、相関急上昇局面、同時損失を必ず見る。

---

## 4. Market Specific Notes

### 4.1 `0702-cryptofetch.md`

暗号資産データ取得ツールの構想です。価値は、戦略ではなくデータ基盤にあります。重要なのは、データが取れることではなく、取得時刻、遅延、欠損、rate limit、API仕様変更、再取得差分を記録できることです。

APIキーを環境変数で読むだけでは安全設計として不十分です。read-only key、権限分離、IP制限、ログマスク、secret rotation、取得失敗時の停止が必要です。

最初の実験は、1取引所、1銘柄、1足種で1週間記録し、欠損率、遅延、再取得差分を見ること。取引機能は後です。

### 4.2 `1021_SOLANA.md`

Solana program examples由来のノートです。取引botを作る前に、account、program、PDA、CPI、token、Token Extensions、signature、simulationを理解するための資料として扱います。

重要な補正は、多くの取引用途では独自on-chain programを作る必要がないことです。既存programとtoken仕様を正しく読む方が先です。特にtoken安全性では、mint authority、freeze authority、transfer fee、metadata、owner変更、LP状態、holder集中を見る必要があります。

実験はmainnetでなく、local/test環境でtoken account、mint、transfer、simulationの理解から始める。未知programや未知tokenをbotが自動で触る設計は採用しません。

### 4.3 `1107_自動化された暗号通貨ニュースで稼ぐ方法.md`

これは取引戦略ではありません。Bitgetの新規上場やニュースを自動で記事化し、紹介収益や関連サービスで収入を得るというマーケティング/アフィリエイト寄りの内容です。

戦略準備に使うなら、ニュースイベントの観測データとしてだけ使います。ニュース発生時刻、取得時刻、初動価格、出来高、spread、後続リターンを記録し、ニュース種別ごとの分布を見る。

誤謬リスクは大きいです。自動生成記事は著作権、出典、誤報、広告表示、金融プロモーション、取引所規約の問題があります。売買判断ではなく、research queueに入れるだけにします。

### 4.4 `1129-Solanaトレーディングボット.md`

Solana token botの設定ノートです。private key、RPC、WebSocket、snipe list、filter、Warp/Jito、利確、損切りなどが出ます。これは実運用候補ではなく、危険点の教材として扱います。

未知tokenの自動購入は、rug、freeze、transfer fee、流動性不足、売却不能、MEV、RPC障害、private key漏洩のリスクが高い。最初に作るべきは買うbotではなく、token safety observerです。

最低条件は、空wallet、資金上限、private keyをrepoやdocsに置かない、manual approval、simulation、sellability check、kill switch、ログマスクです。これがない限りpaper observationから進めません。

### 4.5 `1202-JitoとSolana.md`

Jito Bundlesのチュートリアル由来です。原ノートにはGTO/G2/Cheetoのような表記があり、音声認識/転記由来の誤りが混ざっている可能性が高いです。現在はJito公式docsで確認します。

Jito Bundlesは複数transactionを順序付きで扱い、slot内でall-or-nothingな実行を狙う仕組みですが、bundle失敗、slot境界、tip、leader、未着地、API仕様、費用があります。収益源ではなく、実行制約として理解します。

戦略に入れるなら、tip cost、landed率、latency、failed reason、simulation結果を記録し、Jitoを使わない場合より期待値が改善するかを検証します。低遅延で勝てる、という前提は置きません。

---

## 5. Execution And Stack Notes

### 5.1 `0710-VectorBT.md`

VectorBTは高速なbacktest/research道具です。原ノートのcookbookや採点は、そのまま信じません。デモコードの成績やパラメータ最適化結果は、戦略の証明ではありません。

使い方は、一次スクリーニング、indicator比較、パラメータ近傍の安定性確認です。実運用に近づける前に、イベント駆動の約定モデル、slippage、手数料、funding、注文失敗、データ欠損を別に確認します。

最適値ではなく、広い近傍で安定するかを見る。良い点が一点だけなら過学習です。

### 5.2 `0722-PyBotters.md`

PyBottersはPythonから取引所API/WebSocketを扱うための接続層候補です。API接続できることと、安全にbotを運用できることは別です。

重要なのは、WebSocket再接続、DataStoreの整合性、注文ID、重複注文、cancel失敗、position同期、rate limit、API key権限です。最初はpublic WebSocketの観測だけ。次にread-only private。注文は最後です。

secret placeholderが原ノートにありますが、実値は絶対にdocsやrepoへ置きません。

### 5.3 `1026_Backtest_Trade!.md`

バックテスト環境に関するノートです。バックテストは儲かる証明ではなく、候補を捨てるための検査です。

最初に固定するのは、データ期間、train/test、コスト、slippage、約定ルール、評価指標、除外条件、試行ログです。あとから評価方法を変えると、研究ではなく過去合わせになります。

手数料2倍、slippage2倍、期間変更、銘柄変更で壊れる戦略は捨てます。

### 5.4 `1031_Trading with polars.md`

Polarsは高速なデータ処理に有用ですが、速度は戦略品質ではありません。時系列では、sort、join_asof、rolling、group_by_dynamic、time zone、null処理の誤りがリークになります。

Pandas実装とPolars実装で小データの結果を照合し、同じ特徴量が出ることを確認します。lazy queryは便利ですが、`explain`などで処理計画を確認し、未来参照がないことをレビューします。

### 5.5 `1117_バックテストについて.md`

バックテストの基本ノートです。ここから採用する原則は、良い成績を探すのではなく、壊れる条件を探すことです。

最低限、walk-forward、cost sensitivity、stress、Monte Carlo、複数市場、複数期間、試行回数ログが必要です。勝率やPF単体では採用しません。

採用条件は「良い結果がある」ではなく「悪条件でも壊れ方が許容内」です。

---

## 6. 次に戦略を作るなら

優先順位は次の通りです。

1. `Trend + Risk Guard`
   - `0212-Trend-Bot`, `戦略2`, `戦略5`, `1117_バックテスト`
   - まず高流動性ペアだけで検証する。
2. `Order Book Participation Filter`
   - `Order-Book`, `PyBotters`, `cryptofetch`
   - 方向予測でなく、slippage削減を狙う。
3. `Token Safety Observer`
   - `SOLANA`, `Solana bot`, `Jito`
   - 買わない。未知tokenを観測し、危険判定を作る。
4. `Feature Factory + Walk Forward`
   - `Adaptive Alpha`, `LightGBM`, `Polars`, `VectorBT`
   - MLは最後。まず単純特徴量と検証基盤。
5. `Multi-Asset Risk Allocation`
   - `戦略4`, `ポートフォリオ最適化`
   - 複雑な最適化より、銘柄上限とvol target。

この順番なら、原ノートの魅力的な物語に引っ張られず、検証可能な戦略部品へ落とせます。

