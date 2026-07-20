<!--
作成日: 2026-07-14_20:59 JST
更新日: 2026-07-14_22:08 JST
-->

# 仮説探索エンジン方向性 D01: 小資本・正の歪度・Campaign運用

初回記録日時: 07月14日(火)_午後8時59分11秒.

敵対的完全性レビュー更新日時: 07月14日(火)_午後9時08分35秒.

## 0. この文書の位置づけ

この文書は、Profit-Seeking Hypothesis Search Engineへ追加する第一の大方向を、後から別方向と比較・統合できる形で保存する設計判断スナップショットである。現時点では設計上の記録であり、コード、schema、config、CLI、data、Backtest、取引所接続を実装した証拠ではない。

- 方向性ID: `D01_CONVEX_CAMPAIGN`
- 状態: `DIRECTION_ADOPTED / IMPLEMENTATION_NOT_STARTED`
- 優先度: 現行計画の一般的な利益探索目的より上位
- 対象市場: Crypto Perpetual Futuresのみ
- 対象段階: research、simulation、Backtest、Kill、人間レビュー
- 対象外: Paper注文、live注文、actual cash、wallet、signing、exchange write、将来利益の保証
- 現在地: `PRE-CP0 / PLAN-ONLY`

「現行より上位」とは、既存のKill、安全境界、trial完全性、データ分離を弱めることではない。探索目的と候補評価の中心を、平均的に滑らかな戦略から、小資本で大きな生活Impactを狙える正の歪度戦略へ移すことを意味する。既存の容赦ない検問は、この方向性を守るために維持または強化する。

既存の実装計画とCheckpoint憲章への統合は、今後ほかの方向性も受け取った後に行う。この文書だけを根拠にbranch作成、CP0開始、実装開始、data取得を行わない。

### 0.1 読み方と決定レベル

この文書では、思想、設計判断、実験候補、未検証仮説、未決事項を混ぜない。

| レベル | 意味 | この文書での扱い |
| --- | --- | --- |
| `DIRECTION_ADOPTED` | 目指す方向として採用済み | 後のmaster plan統合で原則維持する |
| `POLICY_ADOPTED` | 設計方針として採用済み | 数値校正前でも契約の向きは維持する |
| `SIMULATION_CANDIDATE` | Simulatorで比較する初期値 | 良い成績だけを事後採用しない |
| `FUTURE_CHALLENGER` | 初期実装では無効な後段案 | データと基準model成立後だけ比較する |
| `UNVERIFIED_HYPOTHESIS` | 経験則または市場仮説 | dataで反証可能にし、事実として扱わない |
| `DECISION_REQUIRED` | 現行判断同士が衝突または定義不足 | 解消までschema、実装、利益計算へ固定しない |
| `NOT_IMPLEMENTED` | code/schema/CLIが存在しない | 文書に書かれていても利用可能と呼ばない |

### 0.2 採用判断台帳

| ID | 判断 | レベル | 備考 |
| --- | --- | --- | --- |
| `D01-D001` | Crypto Perpetual Futuresだけを対象にする | `DIRECTION_ADOPTED` | spot、option、dated futuresは対象外 |
| `D01-D002` | 正の歪度と365日Impact到達確率を中心にする | `DIRECTION_ADOPTED` | Sharpeや月次平滑性を最上位にしない |
| `D01-D003` | Idea生成は攻撃的、資金昇格は保守的にする | `DIRECTION_ADOPTED` | Kill、安全境界、trial完全性を強化する |
| `D01-D004` | 複数機体、Reload Pool、Vault、Generationを使う | `POLICY_ADOPTED` | 配分値は資産帯別に校正する |
| `D01-D005` | 1tradeのriskを機体残高比例にする | `POLICY_ADOPTED` | Grid値はsimulation候補 |
| `D01-D006` | 途中Ratchetで初期元本50%をVaultへ保護する | `POLICY_ADOPTED` | 発動倍率は資産帯別候補 |
| `D01-D007` | Reloadを自動化せずGateを必須にする | `POLICY_ADOPTED` | Pool floorは1機体分 |
| `D01-D008` | Rebaseは1.6倍、24時間、全position close後に判定する | `POLICY_ADOPTED` | 数値は将来校正対象 |
| `D01-D009` | Rebase利益を運用50%、Vault 50%へ分ける | `POLICY_ADOPTED` | 既存Vaultの再投入可否は未決 |
| `D01-D010` | 月次16%を報告KPIにし、未達risk増加を禁止する | `POLICY_ADOPTED` | 取引quotaではない |
| `D01-D011` | Kellyとvolatility/correlation overlayを初期無効にする | `POLICY_ADOPTED` | 後段challenger |
| `D01-U001` | Ratchet後の「10倍」が機体残高か総Campaign wealthか | `DECISION_REQUIRED` | 後述の10倍/10.5倍矛盾 |
| `D01-U002` | Ratchet Vaultを次Rebaseの再投入原資へ含めるか | `DECISION_REQUIRED` | 保護の意味を左右する |
| `D01-U003` | ImpactをVault、出金、総資産のどれで判定するか | `DECISION_REQUIRED` | primary estimand未固定 |

### 0.3 現在の実装境界

read-only照合で確認できた現状は次である。

- `src/sis/strategy_idea_candidates/generator.py`は13 familyの決定論的grid generatorであり、ML discoveryではない。
- `src/sis/strategy_model_loop/`はtraining data、label、split、seed、search space、trial、holdoutを記録する監査面であり、XGBoostやLightGBMを学習する実装ではない。
- `pyproject.toml`にXGBoost、LightGBM、SHAPの直接依存はない。D01は依存追加を認可していない。
- D01が想定する8つのcapital/campaign schemaはすべて未作成である。
- 現在の30 Event、5 Episode程度のsampleでは、tail discovery、ML generalization、Pool破綻確率を推定できない。
- 現在のSP_STATEはCP0 docs-onlyであり、D01を実装するAllowedFilesを持たない。

したがって、D01は「設計方向として採用済み」であって「engine、Simulator、ML、capital layerが利用可能」ではない。

### 0.4 未決事項への推奨回答

`D01-U001`、`D01-U002`、`D01-U003`と残リスクへの推奨回答を、[D01推奨解決案 R01](./HYPOTHESIS_SEARCH_ENGINE_DIRECTION_01_RECOMMENDED_RESOLUTIONS_2026-07-14.md)へ独立記録した。

- recommendation status: `PENDING_USER_ADOPTION`
- D01 decision status: 3件とも`DECISION_REQUIRED`のまま
- master-plan/SP_STATE/codeへの反映: なし

推奨案は、Generation全体wealthで成功倍率を判定し、Vaultを自動再投入せず、保護済み純利益で生活Impactを測る。ユーザー採用前に確定仕様として扱わない。

## 1. 背景と狙い

中心にある経験則は、20回の小さな失敗を許容しても、1回の巨大な勝ちがそれらを大幅に覆せるなら、低勝率自体は欠陥ではないというものである。目指すのは高勝率、低変動、滑らかな月次収益ではない。

> 小さな損失を繰り返し許容し、少数の大きな利益を逃さず取り、小規模な元本から1年間で生活に実質的な影響を与える利益へ到達する確率を高める。

概念上のpayoffは次である。

```text
通常損失    -1R
Tail成功   +10R / +20R / +40R
勝率        低くてもよい
損失側      事前に制限する
利益側      早すぎる利確で閉じない
```

これは、小さく勝ってまれに大きく負けるMartingale型とは逆方向を狙う。ただし、レバレッジを上げるだけでは正の期待値や正の歪度は生まれない。leverage、liquidation、強制ロスカット、zero-cutをedgeの代替にせず、独立した破綻要因として検査する。

### 1.1 `R`を二種類に分ける

元資料では`1R`が二つの意味で使われており、そのままでは期待値、ML label、最大損失を誤計算する。以後は必ず分ける。

| 単位 | 定義 | 例 |
| --- | --- | --- |
| `R_trade` | 1trade開始時に予約する予定最大損失 | 機体残高500 USD、risk 1%なら5 USD |
| `R_campaign` | 1Generationの初期機体残高`B` | 5,000 USD構成なら500 USD |

```text
R_trade_usd = settled_machine_balance_at_entry * risk_fraction
R_campaign_usd = generation_initial_balance = B
```

Tail Opportunity Minerの`+10R / +20R / +40R`は原則`R_trade`で表す。機体死亡`-500 USD`と成功時の収穫は`R_campaign`で表す。`+10R_trade`と`+10R_campaign`を同じ列、threshold、平均へ混ぜない。全artifactは`r_unit_kind`、USD分母、entry時点の残高、fee/funding/slippage込みかを保存する。

### 1.2 検証対象となる市場仮説

次は方向性を選んだ理由ではあるが、現時点の事実認定ではない。

- Crypto Perpetual FuturesはFXや株より機械的technical ruleが有効である。
- 高volatilityは費用と破綻確率を上回るtail opportunityを提供する。
- 個人裁量で得られた経験則を、固定ruleとCampaignへ再現できる。
- 小額機体でもminimum orderと費用を超えて非対称payoffを維持できる。

これらは`UNVERIFIED_HYPOTHESIS`として、no-trade、単純rule、他regime、他symbol、他eraで反証する。採用理由を検証結果の代わりに使わない。

## 2. North Starの変更

この方向性で最優先する量は、Sharpe、勝率、候補数、月次利益の滑らかさではない。

> 費用、資金枯渇、執行制約、機体間相関を考慮したうえで、所定期間内に確定利益が生活Impact目標へ到達する確率

主要な反対指標は、Impact到達前にReload Poolまたは運用資金が枯渇する確率である。したがって、方向性の成否は少なくとも次の組で判定する。

```text
P(365日以内にImpact目標へ到達)
P(Impact到達前にPoolが補給不能になる)
P(CampaignまたはCapital Epochが破綻する)
Impact到達までの時間
到達までに必要な損失・補給・費用
```

月次目標は生活Impactを表すKPIであり、取引ノルマではない。未達を理由にrisk fraction、leverage、取引回数を増やしてはならない。

### 2.1 目的関数の階層

Primary estimandはまだ`D01-U003`で未確定だが、後から都合のよい指標を選ばないため、階層を先に固定する。

1. **Primary**: 365日以内の確定生活Impact到達確率。
2. **Co-primary downside**: 到達前のPool補給停止、Capital Epoch停止、system ruin確率。
3. **Time**: Impact到達日数、無収入期間、capital-time。
4. **Economics**: fee/funding/slippage後のVault増分、追加元本、data/compute/operator費用。
5. **Diagnostics**: Sharpe、勝率、hit rate、drawdown、tail count、model score。

Primaryとco-primaryを一つのweighted scoreへ潰さない。Impact到達率が高くてもruin確率が許容不能なら不採用にでき、ruinが低くてもImpact到達率がno-trade同等なら構築価値なしとする。

### 2.2 月次KPIと年間Impactの関係

基準例の5,000 USDに対する月800 USDは16%であり、単純年額は9,600 USD、初期元本の192%である。

```text
anchor_monthly_impact = 800 USD
reference_annual_impact = 12 * 800 = 9,600 USD
reference_annual_impact_ratio = 9,600 / 5,000 = 1.92
```

これは12か月連続で16%を達成する運用命令でも、16%複利を要求する式でもない。内部transfer、Ratchet、Pool移動、Scale Reserve移動を利益として数えず、外部追加資金も分母と収益から分離する。

### 2.3 Ratio decayの暫定式

資産増加後の報告KPI候補は次である。

```text
r(C) = r0 * (C0 / C)^gamma
```

- `C0 = 5,000 USD`
- `r0 = 0.16 / month`
- `gamma = 0.5`は`SIMULATION_CANDIDATE`

`C`に総資産、運用上限、Vault込み資産のどれを使うかは未決である。式をSizing、Reload、leverageへ逆流させない。

## 3. 現行MarketLens Strikeとの接続思想

現行MarketLens Strikeは自動売買システムではなく、次のresearch chainを持つ審査基盤として扱う。

```text
攻撃的に仮説を作る
-> 検証可能なCandidateProgramへ変換する
-> leakage、データ不足、コスト、未来情報を検査する
-> NO_TRADE、単純baseline、現行championと比較する
-> 弱い候補をKILLする
-> survivorだけを正式Backtestへ送る
-> 人間レビューへ渡す
```

既存の決定論的generator、trial ledger、Model Loop監査情報は再利用候補だが、現時点の固定familyと有限gridだけでは本方向性が要求する豊富な発想を満たさない。新しいgeneratorやMLは既存Killを迂回せず、全attempt、失敗、重複、手動変更を同じledgerへ残す。

## 4. 攻撃的発想と保守的昇格

設計原則は次である。

> Idea generationは極端に攻撃的にする。資金投入へ近づくほど検問を厳しくする。

低勝率を理由に自動棄却しない。代わりに次を確認する。

- 通常損失と異常損失が本当に制限されているか。
- 10R、20R、40R級のtail opportunityが複数の独立episodeに存在するか。
- Tail到達前に機体、Reload Pool、Capital Epochが生存できるか。
- 利益が単一の偶然、単一symbol、単一regime、単一eraへ集中していないか。
- fee、funding、spread、slippage、latency後にも非対称性が残るか。
- 小口資金で注文、stop、minimum notionalを現実に満たせるか。
- 複数機体が同じ市場局面で同時死亡しないか。
- liquidation依存の見せかけのedgeになっていないか。

## 5. 発想機構の追加方向

### 5.1 Tail Opportunity Miner

市場の各時点から、`-1R`へ先に到達する条件と、`+3R / +5R / +10R / +20R / +40R`へ先に到達する条件を、複数horizonで探索する。

候補horizon:

```text
15分 / 1時間 / 4時間 / 1日 / 3日 / 14日 / 30日 / 90日
```

候補featureには、価格変化、volatility圧縮・拡大、funding、mark-index乖離、出来高、open interest、liquidation、spread、order book imbalance、BTCとaltcoinの先行遅行、時間帯、曜日、高安からの距離を含め得る。ただし、実際に利用可能なfeatureはprovenance、license、`available_at`、欠損率、取得費用を通過したものだけに限定する。

### 5.2 Convex Meta-Labeler

既存戦略のsignalを新しく作るのではなく、各signalを`TAKE / NO_TRADE`へ分類し、tail到達確率を改善する追加条件を探索する。既存戦略との改善前後を直接比較でき、探索空間も狭いため、Tail Opportunity Minerより先に検討する有力候補である。

### 5.3 MLの役割

XGBoostとLightGBMを別々の発想方式として数えない。

- XGBoost: 基準model候補。
- LightGBM: challenger、再現性・安定性確認候補。
- 両者が近いルールを発見: evidenceを強める材料。
- 一方だけが発見: evidence gradeを下げる材料。

ML出力を直接Shortlistまたは売買判断にしない。浅い木、feature allowlist、monotonic constraint、interaction constraint、SHAP、tree path、fold/seed/model間安定性を使い、人間が読める固定ルールへ蒸留してから既存検問へ戻す。

```text
ML discovery
-> UNVERIFIED_ML_DISCOVERED
-> 固定ルールへ蒸留
-> CandidateProgram
-> 既存K0/K1/K2/Backtest/Kill
```

現在の30 Event、5 Episode程度の証拠ではML discovery、tail確率、real-market robustnessを判定しない。

### 5.4 Tail label contract

`+10Rへ先に到達`という文章だけではlabelは再現できない。最低限、次をmanifestへ固定する。

- decision timestamp、feature cutoff、entry order timestamp、entry fill timestamp。
- side、entry fill、stop価格、`R_trade_usd`、position notional。
- upper barrier、lower barrier、maximum horizon、exit policy。
- signal判定価格、stop/liquidation trigger価格、実行fill価格のsource。
- maker/taker fee、funding schedule、spread、slippage、latency scenario。
- contract multiplier、tick、quantity step、minimum notional、margin mode。
- barrier hit時のpartial fill、gap、same-bar ambiguity、missing tickの扱い。
- horizon終了時のcensoringとno-outcome class。

labelは概念的に次の順で作る。

```text
entry時点でR_tradeを固定
-> future pathを時系列順に走査
-> costを含むlower/upper executable barrierの先着を判定
-> horizonまで未到達ならCENSORED/TIMEOUT
```

OHLC bar内でupperとlowerの両方に触れ、tick/trade sequenceがない場合、利益側先着を仮定しない。`AMBIGUOUS_INTRABAR_ORDER`として除外または保守側判定し、そのpolicyをtrial universeへ残す。mark価格でliquidationが発生し得る一方、chartやsignalがlast priceの場合があるため、単一価格列で全判定を代用しない。

### 5.5 重複eventとclass imbalance

全timestampから多horizon labelを作ると、ほぼ同じfuture pathを共有する重複sampleが大量発生する。row数を独立episode数と数えない。

- 同一symbolのoverlapping horizonをepisode/clusterへ束ねる。
- purgeとembargoをpolicy_record_onlyのままにせず、実装・検証されるまでML readinessをBLOCKする。
- tail classの少なさをclass weightやoversamplingだけで「証拠増加」に変えない。
- base rate、precision/recall、calibration、expected value、coverageを同時に見る。
- horizonで結果が未確定のright-censored sampleをloss扱いに丸めない。
- symbol、era、regime、directionを跨ぐ外挿を、random row splitで正当化しない。

### 5.6 Model一致の限界

XGBoostとLightGBMが同じdata、feature、label、splitを使って似たruleを出しても、独立した二つの市場証拠にはならない。両者ともtree boostingであり、共有data error、label leakage、selection biasを同時に再現できる。

- model一致は`implementation/model-class robustness diagnostic`とする。
- 一致をp-value、episode数、独立再現回数へ加算しない。
- 不一致は即KILLではなく、feature interaction、seed、split、class imbalanceへの感度として調べる。
- 真のconfirmationは未使用era、未使用symbol群、未使用partition、または別research epochで行う。

### 5.7 Rule distillationの二重過適合防止

SHAPやtree pathを見て人間が固定ruleへ直す行為は、新しいresearch decisionである。元modelを評価したvalidationへ蒸留ruleを再投入してはならない。

```text
model探索trial
-> rule候補抽出trial
-> 人間による選択event
-> 新CandidateProgram
-> 新しい未使用evaluation partition
```

- 抽出した全rule、棄却rule、手修正、threshold変更をledgerへ残す。
- SHAPは予測寄与の説明であり、因果性、tradability、OOS profitの証明ではない。
- model scoreが高くても固定ruleが同じpayoffを再現できなければ候補を昇格しない。
- modelそのものを直接売買へ使う経路はD01初期scope外とする。

### 5.8 Dependencyと実装順

現行`pyproject.toml`にはXGBoost、LightGBM、SHAPがない。lockfileに別dependency経由でscikit-learnが見えても、直接利用可能なpublic contractとは扱わない。

1. 先にlabel contractとdeterministic fixtureを作る。
2. 既存ruleを使うConvex Meta-Labelerの価値を最小spikeで測る。
3. model追加が同一budgetで限界発見価値を増やす場合だけdependency案を審査する。
4. XGBoostとLightGBMを同時に追加せず、基準model成立後にchallengerを追加する。
5. 依存追加、license、binary wheel、Python 3.13、CPU/RSS、reproducibilityを専用branchと別計画で審査する。

## 6. Capital Epoch、機体、Poolの基本モデル

総運用元本を、稼働機体と再補給単位へ分ける。

```text
C = (n + q) * B
```

- `C`: Capital Epochで認める最大同時運用元本。
- `n`: 初期稼働機体数。
- `q`: Reload Poolが持つ補給単位数。
- `B`: 1機体の初期確定口座残高。

5,000 USDの基準例:

```text
C = 5,000 USD
n = 6
q = 4
B = 500 USD

5,000 = (6 + 4) * 500
```

これは、6機を稼働させながら4機分の死亡を補給可能にする初期構成である。6つのcodeがあることは6種類の独立riskを意味しない。symbol、direction、family、holding horizon、entry regime、primary riskによる`risk_fingerprint`でClusterを作る。

### 6.1 資金bucketを分離する

同じ取引所口座または同じcash残高に見えても、論理上は次を別ledgerにする。

| Bucket | 使用目的 | 同一Epochの新規riskへ使用 |
| --- | --- | --- |
| `machine_working_balance` | 各Generationのtradeとmargin | 可、ただしrisk cap内 |
| `reload_pool` | Reload Gate通過後の新Generation | 可、Reload専用 |
| `scale_reserve` | 成功収穫後、次Rebase判断待ち | 原則不可 |
| `profit_vault` | Ratchet/Rebaseで保護した利益 | 不可 |
| `external_withdrawal` | 運用系から外へ確定した生活利益 | 不可、system外 |

物理的に同一cross-margin accountへ置き、取引所が全available balanceをmarginとして使えるなら、台帳上のVaultは保護にならない。D01は論理分離だけで保護済みと主張せず、margin mode、auto-margin replenishment、collateral scope、API/order設定をvenue別に検証する。

### 6.2 資金保存則

内部transferを利益に見せないため、全てのsettled boundaryで次を成立させる。

```text
external_initial_capital
+ subsequent_external_contributions
+ cumulative_gross_realized_pnl
- cumulative_fee
- cumulative_funding
- cumulative_slippage_and_execution_loss
- completed_external_withdrawals
= active_machine_settled_balances
  + reload_pool
  + scale_reserve
  + profit_vault
  + other_settled_receivables
  - settled_liabilities
```

open positionがあるsnapshotではunrealized PnL、reserved maximum loss、margin、pending fundingを別に表示し、上のsettled保存則と混ぜない。Ratchet、成功収穫、Reload、Rebaseは左辺のprofitを増やさず、右辺bucket間の移動だけを発生させる。

### 6.3 Operating capitalとsystem wealth

次を同じ`equity`という名前で混ぜない。

```text
operating_capital
= active_machine_balances + reload_pool

protected_capital
= profit_vault

pending_scale_capital
= scale_reserve

system_net_wealth
= operating_capital + protected_capital + pending_scale_capital
```

`C`はCapital Epochがriskへ認めたoperating capであり、system net wealthの永久上限ではない。Impact、Rebase trigger、drawdownの各分母にどの量を使うかを別fieldで固定する。

### 6.4 5,000 USD例の初期保存

```text
6 machine * 500 USD = 3,000 USD
reload_pool           = 2,000 USD
scale_reserve         =     0 USD
profit_vault          =     0 USD
--------------------------------
system_net_wealth     = 5,000 USD
```

機体1台のRatchetで250 USDをVaultへ移す場合、機体残高が250 USD減りVaultが250 USD増えるだけで、system net wealthは変わらない。

## 7. 機体CampaignとGeneration

機体は1回のtradeではなく、成功または死亡まで続くCampaignである。

```text
Generation開始
-> tradeを反復
-> Ratchet判定
-> 成功 / 死亡 / 継続
-> 成功またはReload許可後に新Generation
```

5,000 USDの基準例では、1機体は500 USDから開始する。成功上限は、全ポジション終了後の確定口座残高で判定する。建玉notional、使用margin、1回の損失上限、含み益込みequityとは別概念である。

- 保有中に含み益で上限を超えても、それだけでは強制決済しない。
- 全ポジション終了後、feeとfunding確定後の残高で判定する。
- 成功後は次Generationの種銭を残し、それ以外を所定ledgerへ移す。
- 最低注文不能額以下または実質0なら死亡候補とする。
- 死亡後のReloadは自動で行わない。

`machine_id`と`generation_id`を分け、成功までの世代数、補給回数、経過日数、死亡理由、regime、family別Pool消費を追跡する。

### 7.1 Generationで固定するもの

一つのGeneration中に次を変更すると、途中までの成績と後半のriskを同じCampaignとして比較できない。

- strategy/candidate idとspec hash。
- initial balance `B`、balance cap multiple、Ratchet policy。
- risk fraction policy、margin/notional/leverage cap。
- symbol universe、direction、timeframe、holding horizon。
- cost/execution model、venue contract、margin mode。
- data partition、code/config version。

変更が必要なら、旧Generationを`BLOCKED_POLICY_CHANGED`または所定の終了状態へ閉じ、新Generationとして全trialとmultiplicityへ課金する。勝っている途中だけruleを変えて成功扱いしない。

### 7.2 死亡、BLOCKED、ERRORを分ける

`machine balance < minimum executable balance`だけでは死亡理由が不明である。

- 正常なstrategy lossで最低実行額を割った: `MACHINE_DEAD_NORMAL_LOSS`。
- gap、異常slippage、liquidation、ADL: `MACHINE_BLOCKED_ABNORMAL_EXECUTION`。
- data欠損、時刻矛盾、計算失敗: `MACHINE_ERROR_EVIDENCE_INVALID`。
- venue停止、contract変更、delisting: `MACHINE_BLOCKED_VENUE_EVENT`。
- Strategy Gate失効: `MACHINE_BLOCKED_STRATEGY_INVALIDATED`。
- 長期間signalも成功も死亡もない: `MACHINE_EXPIRED`または`MACHINE_DORMANT`。

残高比例riskでは残高が数学的に0へ到達せず、極小額で永遠に残る可能性がある。minimum executable balance、maximum campaign duration、maximum trade count、maximum inactive durationを事前固定する。

### 7.3 成功収穫のroute

成功時に残高上限を超えたovershootを切り捨てない。

```text
settled_balance = H + overshoot
retain_for_next_generation = B_next_or_old_policy
success_harvest = settled_balance - retain_for_next_generation
```

success harvestの既定routeは`scale_reserve`であり、Ratchetで保護した額は`profit_vault`に残す。Reload Poolの不足を成功利益で自動充填するかは別policyとし、暗黙に混ぜない。

## 8. 採用済みの資本管理方針

### 8.1 1回のRisk

1回の許容損失額は、固定USDではなくtrade開始時点の機体残高に比例させる。

```yaml
research_grid:
  - 0.005
  - 0.010
  - 0.015
  - 0.020
  - 0.030
stress_only:
  - 0.050
```

`0.5% / 1.0% / 1.5% / 2.0% / 3.0%`は研究Gridであり、成績のよい値だけを事後選択して本採用しない。`5%`は通常候補へ昇格させず、破綻感度を見るstress専用とする。

### 8.1.1 Risk fractionから注文量への変換

Risk fractionはloss保証ではなく、entry時に予約する予定損失budgetである。

```text
planned_trade_risk_usd
= settled_machine_balance_at_entry * risk_fraction

raw_notional
≈ planned_trade_risk_usd
  / executable_stop_distance_fraction
```

実注文量は次の全上限の最小値を通す。

```text
allowed_notional
= min(
    raw_notional,
    max_position_notional,
    max_margin_in_use * max_leverage,
    venue_risk_tier_cap,
    machine_reserved_loss_cap,
    cluster_aggregate_cap,
    Pool_survival_cap
  )
```

- stopまでの距離へfee、spread、slippage、latency、gap bufferを含める。
- liquidation priceはstopより十分外側でなければならない。
- 複数positionの`reserved_max_loss`合計を機体risk cap以下にする。
- stop orderが存在しても約定価格を保証された損失上限と呼ばない。
- 最小quantityへ丸めることで予定riskを超える場合は`NO_TRADE_MINIMUM_SIZE`。
- fee/fundingだけで`R_trade`の所定比率を超える場合は`NO_TRADE_FEE_DRAG`。

### 8.1.2 残高成長時の絶対risk増加

比例Sizingでは同じ1%でも、500 USD機体の5 USDから4,000 USD機体の40 USDへ絶対riskが8倍になる。これは採用済み方針の意図した性質だが、Ratchetで利益を守る目的と衝突し得る。

- `risk_fraction`と`absolute_risk_usd`を両方報告する。
- balance bandごとの絶対上限をsimulation候補に含める。
- Tail hit率が同じでも、成功直前の絶対損失増大でCampaign ruinが悪化するか比較する。
- proportionalと`min(proportional, absolute cap)`を同一trade streamで比較する。

### 8.2 Ratchetによる利益保護

`PURE_10X_OR_ZERO`は主方式として採用しない。成功倍率に応じた途中地点で、初期元本の50%をProfit Vaultへ移し、同じCapital Epochでは再投入しない。

| Campaign成功倍率 | Ratchet発動地点 | 回収額 |
| ---: | ---: | ---: |
| 10倍 | 初期残高の4倍 | 初期元本の50% |
| 6倍 | 初期残高の3倍 | 初期元本の50% |
| 3倍 | 初期残高の2倍 | 初期元本の50% |
| 2倍 | 初期残高の1.5倍 | 初期元本の50% |

5,000 USD構成の例:

```text
機体初期残高       500 USD
4倍到達          2,000 USD
Profit Vaultへ     250 USD
Ratchet後残高     1,750 USD
```

### 8.2.1 「10倍」とRatchetの数理衝突

現在までの会話では、5,000 USDは「Ratchet回収後も、機体自身の確定口座残高が到達すべき上限」と確認されている。この意味を採用すると、`success_multiple`という名前は総Campaign wealth倍率を表さない。

```text
B = 500 USD
K = machine balance cap multiple = 10
w = ratchet withdrawal / B = 0.5

成功時の機体残高             = K * B       = 5,000 USD
途中でVaultへ移した額         = w * B       =   250 USD
成功時に機体+Vaultが持つ総額  = (K + w) * B = 5,250 USD
元本Bに対するnet増分           = (K + w - 1) * B = 4,750 USD
```

したがって、Ratchetなしの理想化した`-1 / +9 R_campaign`とは異なり、現在のaccount-balance-cap解釈では`-1 / +9.5 R_campaign`になる。ほかの5機とPoolに損失がなければ、system net wealthは9,500 USDではなく9,750 USDになる。

総Campaign wealthを厳密に10倍で止めたい場合は、成功条件を次へ変える必要がある。

```text
machine_settled_balance + cumulative_ratchet_withdrawals >= K * B
```

これは`D01-U001`である。現時点では、過去に確認されたaccount-balance-cap解釈を記録上の現行案とするが、`K=10`を総wealth 10倍や`+9R_campaign`と呼ばない。schema名は`machine_balance_cap_multiple`と`campaign_total_wealth_multiple`へ分離する。

### 8.2.2 Ratchetの一回性

RatchetはGenerationごとに一度だけ発動する。4倍へ到達して回収後に残高が下がり、再び4倍を超えても二度目の250 USDを回収しない。

- `ratchet_triggered_at`、pre/post balance、transfer id、Vault ledger hashを保存する。
- thresholdをtrade保有中のunrealized equityで判定しない。
- 全position close、fee/funding確定後にatomic transferする。
- crash/resumeで二重回収しないidempotency keyを持つ。
- thresholdを一回のtradeで飛び越えた場合も一度だけ回収する。

### 8.3 資産帯別の成功倍率

資産規模が大きくなるほどCampaign成功倍率を下げる方針を採用する。次の数値は固定本番仕様ではなく、Campaign Simulatorで比較する初期候補である。

| Capital Epoch最大同時運用額 | 初期成功倍率候補 |
| ---: | ---: |
| 100〜1,999 USD | 10倍 |
| 2,000〜9,999 USD | 6倍 |
| 10,000〜49,999 USD | 3倍 |
| 50,000〜150,000 USD | 2倍 |

資産帯ごとの機体数、補給単位、minimum executable balance、margin、notional、leverage、同時position数は別に校正する。100 USDで6機を機械的に作らない。

### 8.4 Reload PoolとReload Gate

Pool残高が機体初期残高1台分以下になったら、新規Reloadを停止する。5,000 USD構成では、初期Pool 2,000 USD、補給単位500 USD、停止下限500 USDである。

Reloadは次を満たす場合だけ許可する。

- Poolが停止下限より上。
- machine、family、risk clusterの補給回数上限内。
- Strategy Gateが現在も有効。
- 通常の想定損失による死亡である。
- 異常slippage、データ欠損、取引所障害ではない。
- 同一Market Episodeの連続死亡、同一symbol/direction集中、cluster過密が上限内。
- ClusterがQuarantineされていない。

異常死亡はReload成功・通常損失・strategy KILLのどれにも混ぜず、原因別のBLOCKED/ERRORとして扱う。

Pool残高が停止下限と等しい場合もReloadしない。残った1機体分は「あと1回使える資金」ではなく、停止・調査・移行のためのsystem survival reserveである。既存open positionを即時強制決済する規則ではないが、新規Generation、Reload、新規risk増加を止める。

Reload Gateの判断順は、evidence validity、abnormal execution、Strategy Gate、Cluster quarantine、Pool floor、machine/family reload budget、aggregate exposureの順とする。前段BLOCKEDを後段のPool余力で上書きしない。

### 8.5 Rebase

段階式Rebase、利益半分隔離、縮小条件を採用する。

```yaml
trigger_multiple: 1.6
confirmation_hours: 24
requires_all_positions_closed: true
profit_redeployment_ratio: 0.5
profit_vault_ratio: 0.5
applies_to_new_generations_only: true
```

```text
現在運用上限       5,000 USD
確認済み総資産     8,000 USD
増加利益           3,000 USD
新しい運用上限     6,500 USD
Profit Vault       1,500 USD
```

Rebase判定には含み益を使わない。全position終了後の確定資産から、fee、funding、予約済み最大損失、未確定債務を反映する。既存Generationの途中条件は変えず、新しいGenerationから新しい資金設定を使う。

### 8.5.1 Rebase対象資産の未解決点

RatchetでProfit Vaultへ移した資金は「同じCapital Epochでは再投入しない」と決定されている。一方、Rebase例は確認済み総資産8,000 USDの増加利益3,000 USDを半分再投入する。この総資産に既存Profit Vaultを含めると、保護した資金を新Epochで再びriskへ戻す可能性がある。

最低限、次を別fieldにする。

```text
rebase_observation_equity
rebase_redeployment_eligible_equity
ratchet_vault_locked_equity
completed_external_withdrawals
```

観測上はVault込みsystem wealthで1.6倍到達を認識しても、再投入原資をscale reserveだけに限定する案と、次EpochでVaultの一部を解禁する案は別trialとして扱う。現時点では`D01-U002`であり、Vaultを暗黙に再投入しない。

### 8.5.2 Rebaseのatomic境界

- 全機体のpositionがcloseしている同一snapshotで判定する。
- 24時間window中の最小confirmed valueを使い、途中で閾値を割ればtimerをresetする。
- Rebase計算、Vault transfer、新capital policy publishを一つのcommit manifestで結ぶ。
- old Generationはold policy hashのまま継続し、new Generationだけnew policy hashを使う。
- Rebaseと20% downscaleが同じboundaryで競合する場合は、縮小/BLOCKEDを優先し、拡大しない。
- crash/resumeでEpochを二重作成、Vaultを二重transferしない。

### 8.6 縮小条件

次の場合、新Generationの機体sizeまたはCapital Epoch最大同時運用額を一段階縮小する。

- Rebase後の運用上限から20%以上のdrawdown。
- Poolが機体1台分以下。
- 同一Risk Clusterで2機以上死亡。
- 異常slippageまたは取引所障害。
- Strategy Gate失効。
- 複数機体の相関集中。

縮小幅、解除条件、再拡大のcooldownは未決であり、後から良い結果に合わせて選ばずSimulatorの事前固定候補として比較する。

Drawdownの基準は`rebase後operating_cap high-water mark`を候補とし、Profit Vaultと外部withdrawalを分母から除く。Vaultへ移しただけでdrawdownが発生したように見せず、逆にVaultを足してoperating lossを隠さない。正確なbasisは未決事項としてschemaで明示する。

### 8.7 月次Impact KPI

基準例は5,000 USDに対して月800 USD、月次16%である。これは強制的な月次損益目標ではない。

- 未達回収のためのrisk、leverage、trade count増加を禁止する。
- 資産増加後は必要ratioを徐々に下げる。
- 初期ratio decay候補は`gamma = 0.5`。
- 365日Impact到達率、無収入月数、年間確定利益分布、time-to-targetを主要指標にする。

### 8.8 後段のSizing

初期段階ではDistributionally Robust Kellyとvolatility/correlation overlayを無効にする。データ蓄積後のchallengerとしてのみ追加する。

```text
actual risk fraction
= min(
    Robust Kelly,
    capital-band cap,
    Pool survival cap,
    Risk Cluster cap,
    venue executable cap
  )
```

Overlayはtail opportunityを削る主目的関数ではなく、高volatility、同一方向集中、cluster過密時の安全縮小または停止に限定する。

### 8.9 必須基準モデル

適応方式の価値を測るため、単純modelを消さない。

```yaml
rebase_trigger: 1.6
profit_redeployment: 0.5
profit_vault: 0.5
risk_fraction: fixed
kelly_adjustment: false
volatility_adjustment: false
```

全方式、全parameter、失敗結果を保存し、成績のよい設定だけを報告しない。

## 9. Campaign Simulatorへ要求する評価

個別Strategy Backtestだけでは、この方向性の成否を判定できない。機体、Generation、Reload Pool、Scale Reserve、Profit Vault、Rebase、Clusterを同じ市場時系列上で動かすCampaign Simulatorが必要になる。

### 9.1 必須評価指標

| 指標 | 判定したいこと |
| --- | --- |
| average / median loss R | 通常損失が小さいか |
| maximum loss R | 異常時も損失が制御されるか |
| average win R | 成功時の利益が十分大きいか |
| tail hit rate | 10R、20R、40Rへの到達率 |
| independent tail episodes | 独立した大勝ち局面が複数あるか |
| winner concentration | 単一trade、symbol、era依存でないか |
| maximum losing streak distribution | Poolと機体が耐えられるか |
| campaign ruin probability | Generation/Campaignが死亡する確率 |
| pool ruin probability | Impact到達前に補給不能になる確率 |
| impact target probability | 365日以内に生活Impact目標へ届く確率 |
| time to target | 成功までの時間 |
| no-income month distribution | 収益の疎らさを生活面から評価できるか |
| reload count / cost | 成功までに必要な再補給量 |
| fee-to-R ratio | 小額帯で費用負けしないか |
| cluster death / overlap | 複数機体が同時に死ぬか |
| Vault realized profit | 再投入せず保護できた利益 |

機体を独立Bernoulliとして抽選しない。同じMarket Episodeをまとめてresampleし、同一方向、同一symbol、同一family、Pool補給後もregimeが継続する状況を保持する。

### 9.2 必須停止理由候補

```text
TAIL_EXPECTANCY_NOT_POSITIVE
PAYOFF_ASYMMETRY_NOT_PROVEN
MAX_LOSS_NOT_BOUNDED
TAIL_WINNER_SAMPLE_INSUFFICIENT
MAX_LOSING_STREAK_EXCEEDS_BUDGET
CAMPAIGN_RUIN_PROBABILITY_TOO_HIGH
IMPACT_TARGET_PROBABILITY_TOO_LOW
FEE_DRAG_TOO_HIGH_AT_MINIMUM_CAPITAL
LIQUIDATION_DEPENDENT_EDGE
POOL_RUIN_PROBABILITY_TOO_HIGH
RELOAD_BUDGET_EXHAUSTED
POOL_FLOOR_BREACHED
ABNORMAL_EXECUTION_LOSS
CORRELATED_MACHINE_CLUSTER_EXCEEDED
STRATEGY_GATE_NO_LONGER_VALID
TARGET_CHASING_RISK_ESCALATION
```

### 9.3 理想化二択モデルの用途と限界

Ratchet導入前に、死亡`-1 R_campaign`、成功`+9 R_campaign`と単純化すると、feeを無視した期待値は次である。

```text
EV / R_campaign = p * 9 - (1 - p)
break-even p = 1 / 10 = 10%
```

この10%は設計保証でも必要成功率の推定値でもない。実Campaignは多数trade、時間、Ratchet、可変risk、cost、Reload、相関を含む。さらにaccount-balance-cap方式でRatchetを別に回収する現行案なら理想成功payoff自体が`+9.5 R_campaign`となり、単純break-evenは約9.52%へ変わる。

どちらの数値も、次を無視しているためadmission thresholdに使わない。

- 成功までのtrade数と時間価値。
- fee、funding、spread、slippage、latency。
- success前のRatchet、overshoot、partial fill。
- Reload回数と他機体の同時死亡。
- tail episode依存と非定常性。
- finite 365-day horizonとcensoring。
- data/compute/operator費用。

Simulatorはこの二択式をsanity fixtureとして再現できるべきだが、real-market判定はevent-driven pathで行う。

### 9.4 Simulator入力契約

最低限、次をhash付きで固定する。

1. Strategy/CandidateProgramとversion。
2. signal、entry、exit、stop、position sizing policy。
3. market data source、symbol universe、event/available/ingest time。
4. mark/index/last、funding、trade、book、liquidation、OIの可用性。
5. cost/execution scenarioとvenue contract snapshot。
6. Capital Epoch policy、machine assignment、Generation policy。
7. risk cluster definitionとaggregate cap。
8. Reload、Ratchet、success harvest、Rebase、downscale policy。
9. data partition、walk-forward split、purge、embargo、sealed status。
10. deterministic seed、resampling seed、code/config identity。

入力不足を既定値0へ変換しない。booksがないならqueue/impactを観測済みとせず、保守推定または`EXECUTION_EVIDENCE_MISSING`へ分ける。

### 9.5 Chronological replayとresampling

第一の評価は実chronologyを保ったevent-driven replayである。同一timestampに複数機体がsignalを出す場合、資本占有、margin、cluster cap、order priorityを同時に解決する。

追加のuncertainty評価では、row単位shuffleではなくMarket Episodeまたは依存を保つblockでresampleする。

- bull/bear、volatility expansion/compression、liquidity shockを壊さない。
- 同一symbol/方向の複数機体死亡を独立抽選しない。
- Pool補給直後も同じregimeが継続する経路を残す。
- delisted/failed symbolをwinner universeから消さない。
- 同じ巨大tail eventを複数独立winnerとして複製しない。

30 Event、5 EpisodeからMonte Carlo回数だけ増やしても情報量は増えない。resample数と独立episode数を別表示する。

### 9.6 比較実験の分解

Strategy edgeとcapital wrapperの効果を混ぜない。同一trade streamへ異なるcapital policyを適用する比較と、同一capital policyへ異なるstrategyを適用する比較を分ける。

| 比較軸 | Baseline | Challenger | 判定目的 |
| --- | --- | --- | --- |
| strategy | no-trade / simple incumbent | convex strategy | 売買edgeがあるか |
| machine wrapper | single account | multi-machine | 機体分割に増分価値があるか |
| Ratchet | no Ratchet | adopted Ratchet | protected profitとImpact率が改善するか |
| Sizing | fixed risk | proportional risk | 成長とruinのtrade-off |
| Reload | no Reload | gated Reload | optionalityが追加損失を上回るか |
| Rebase | no Rebase | 1.6x/50-50 | 再投資がImpact率を改善するか |
| adaptive sizing | fixed baseline | Robust Kelly | 後段challengerの限界価値 |
| overlay | none | vol/correlation safety | tailを消さずruinを下げるか |

capital policyのGridもstrategy trialと同じmultiple-testing universeへ含める。Strategyとcapital policyを同じvalidationで同時に選び、その組だけsealedへ送らない。

### 9.7 判定値の不確実性

- Impact到達率、Pool ruin率、tail hit率をpoint estimateだけで報告しない。
- episode/block単位のinterval、上方/下方bound、sample-size basisを保存する。
- ruinが0回観測されても、ruin確率0としない。
- tail winnerが1件だけならwinner contributionをleave-one-episode-outで除き、全成績消失を確認する。
- thresholdを少し動かして結論が反転する場合は`NOT_ESTIMABLE`。
- policy選択、risk Grid、success倍率、Ratchet地点、Rebase値を全trialへ課金する。
- Backtest overfitting検査はstrategyだけでなくcapital policy selectionも対象にする。

### 9.8 D01固有のstop / defer規則

- 独立tail episode不足: `DEFER_DATA(TAIL_EPISODES_INSUFFICIENT)`。
- min capitalでfee-to-Rが上限超過: その資産帯を`NOT_EXECUTABLE`。
- proportional riskがfixed baselineよりImpact率を上げずruinだけ増やす: proportional案をKILL。
- Ratchetがtail到達率を過度に落とし、Vault増分も改善しない: Ratchet設定をKILL。
- machine分割が相関集中を隠すだけ: multi-machine wrapperをKILLまたは再cluster化。
- Reloadが期待Impact増分よりPool ruin増分を大きくする: Reload policyを停止。
- 連続epochでincumbentを上回らない: D01 build expansionを停止。

DEFERは永久保留ではない。必要な次の反証data、最大追加費用、expiryを持たない候補は終了する。

## 10. 必要な状態遷移の叩き台

次の設計段階で、遷移条件、優先順位、atomic ledger更新をschemaへ落とす。

```text
MACHINE_GENERATION_READY
-> MACHINE_ACTIVE
-> MACHINE_RATCHETED
-> MACHINE_SUCCESS | MACHINE_DEAD | MACHINE_BLOCKED

MACHINE_DEAD
-> RELOAD_PENDING
-> RELOAD_ALLOWED | RELOAD_REJECTED | CLUSTER_QUARANTINED

CAPITAL_EPOCH_ACTIVE
-> REBASE_CONFIRMING
-> REBASE_APPLIED | REBASE_CANCELLED
-> CAPITAL_DOWNSCALED | CAPITAL_EPOCH_STOPPED
```

異常slippage、取引所障害、データ欠損、未確定fee/funding、open positionがある場合、成功、死亡、Reload、Rebaseへ都合よく分類しない。

### 10.1 同一boundaryでの判定優先順位

同じtrade closeまたはEpoch snapshotで複数条件が成立した場合、次の順で判定する。

1. artifact/hash/data/clock不整合なら`RUN_INVALID`。
2. venue障害、異常slippage、liquidation/ADLなら`BLOCKED_ABNORMAL_EXECUTION`。
3. Strategy Gate失効、forbidden data readなら`BLOCKED_STRATEGY_INVALIDATED`。
4. fee/funding/liability確定後のsettled balanceを計算する。
5. Ratchet未発動でthreshold到達ならRatchetを一度だけcommitする。
6. Ratchet後残高でsuccess/death/continueを判定する。
7. deathならCluster quarantineを先に更新する。
8. Reload Gateをevidence、Cluster、Pool、budget、exposureの順で判定する。
9. 全machine snapshot成立後、downscale/stopをRebaseより先に判定する。
10. blockerがなく全position closeならRebase confirmationを更新する。

順序自体をmanifest versionへ含める。異なる順序の結果を同一policy trialとして混ぜない。

### 10.2 状態ごとのpermission

| 状態 | 新規trade | Reload | Rebase | 成功/利益主張 |
| --- | ---: | ---: | ---: | ---: |
| `MACHINE_ACTIVE` | policy内で可 | 不可 | machine単独では不可 | 不可 |
| `MACHINE_RATCHETED` | policy内で可 | 不可 | machine単独では不可 | 不可 |
| `MACHINE_SUCCESS` | 次Generationまで不可 | 不要 | Epoch側判断 | Campaign成功のみ |
| `MACHINE_DEAD_NORMAL_LOSS` | 不可 | Gate後のみ | 不可 | 不可 |
| `MACHINE_BLOCKED_*` | 不可 | 不可 | 不可 | 不可 |
| `CLUSTER_QUARANTINED` | cluster全体不可 | 不可 | 不可 | 不可 |
| `CAPITAL_DOWNSCALED` | 新policy内のみ | 再審査 | 拡大不可 | 不可 |
| `CAPITAL_EPOCH_STOPPED` | 不可 | 不可 | 不可 | 不可 |

### 10.3 常時成立させるinvariant

- 1 GenerationでRatchet transferは最大1件。
- 1 deathに対するReload decisionは最大1件。
- Reload transfer額はPool減少額と新machine増加額が一致する。
- Vault、Pool、Scale Reserve間transferは資金保存則を破らない。
- Pool floor以下で`RELOAD_ALLOWED`は0件。
- blocked/invalid machineからsuccessは作れない。
- old Generationのpolicy hashはRebase後も不変。
- internal transferをPnL、Impact、winnerへ数えない。
- generated Campaign数とsuccess/death/blocked/activeのcount conservation差は0。
- resume後のdecision、resource charge、cash transfer重複は0。

## 11. 現時点の統合設定

```yaml
direction:
  id: D01_CONVEX_CAMPAIGN
  status: DIRECTION_ADOPTED_IMPLEMENTATION_NOT_STARTED
  market_scope: crypto_perpetual_futures_only

capital_rebase:
  trigger_multiple: 1.6
  confirmation_hours: 24
  requires_all_positions_closed: true
  profit_redeployment_ratio: 0.5
  profit_vault_ratio: 0.5
  ratchet_vault_redeployment_eligible: UNSET
  applies_to_new_generations_only: true

machine_risk:
  sizing_method: proportional_to_machine_balance
  r_unit: R_trade
  research_grid: [0.005, 0.010, 0.015, 0.020, 0.030]
  stress_only: [0.050]
  absolute_risk_cap_policy: UNSET
  aggregate_reserved_loss_cap: UNSET
  robust_kelly_enabled: false
  volatility_overlay_enabled: false

machine_ratchet:
  trigger_once_per_generation: true
  withdrawal_amount_initial_balance_ratio: 0.5
  withdrawal_destination: profit_vault
  withdrawal_counts_toward_machine_balance_cap: false
  trigger_policy:
    success_10x: 4.0
    success_6x: 3.0
    success_3x: 2.0
    success_2x: 1.5

pool:
  reload_stop_floor_units: 1
  automatic_reload: false
  reload_requires_gate: true
  floor_equality_blocks_reload: true

machine_balance_cap_multiple:
  policy: capital_band_variable
  simulation_candidates:
    100-1999: 10
    2000-9999: 6
    10000-49999: 3
    50000-150000: 2

monthly_target:
  role: reporting_kpi_only
  anchor_capital_usd: 5000
  anchor_monthly_profit_usd: 800
  anchor_ratio: 0.16
  annual_reference_profit_usd: 9600
  impact_accounting_basis: UNSET
  must_not_increase_risk_when_behind: true
  ratio_decay_exponent: 0.5
```

## 12. Conceptual Artifact Inventory

元資料で挙げられた次の8 artifactは、現時点ではすべてrepoに存在しない。ここでは責務と最低fieldだけを記録し、schema作成を許可しない。

| Artifact候補 | 責務 | 最低限必要な情報 |
| --- | --- | --- |
| `capital_epoch_policy.v1` | Epochの資本契約 | C、asset band、machine/reload数、Rebase/downscale、policy hash |
| `machine_campaign.v1` | Generation lifecycle | machine/generation id、strategy hash、B、K、Ratchet、state、trade refs |
| `machine_risk_fingerprint.v1` | 相関cluster判定 | symbol、direction、family、horizon、regime、primary risk、cluster version |
| `shared_pool_ledger.v1` | Reload Poolの増減 | opening/closing、transfer、reload decision ref、floor、conservation |
| `profit_vault_ledger.v1` | 保護利益の増減 | Ratchet/Rebase source、lock scope、withdrawal、redeploy permission |
| `machine_reload_decision.v1` | Reload Gate | death ref、evidence status、cluster、pool、budget、decision/reason |
| `capital_rebase_decision.v1` | Rebase/downscale | observation equity、eligible equity、24h window、transfer、new policy hash |
| `portfolio_campaign_simulation.v1` | Campaign全体評価 | input hashes、scenario、metrics、interval、decisions、boundary flags |

### 12.1 共通lineage

全artifactへ次を共通で持たせる。

- schema version、producer version、created_at UTC。
- run id、research epoch id、capital epoch id。
- machine id、generation id、candidate/strategy id。
- code/config/policy hash。
- source/split/market-data/cost/execution hash。
- trial universe ref、human/AI feedback ref。
- previous commit manifest hash、idempotency key。
- paper/live/cash/wallet/signing/exchange-write permission false。

### 12.2 Append-onlyとatomicity

Pool、Vault、machine残高を別fileへ独立appendして擬似transactionを作らない。一つのeconomic eventについて、debit、credit、state transition、decision reason、resource chargeをimmutable segmentへ書き、checksum付きcommit manifestを最後にpublishする。partial eventは次stageが読まない。

### 12.3 現行surfaceとの適合

| 現行surface | 再利用できるもの | そのままでは足りないもの |
| --- | --- | --- |
| `strategy_idea_candidates` | deterministic candidate、失敗/重複ledger、source hash | ML discovery、tail label、capital policy trial |
| `strategy_model_loop` | data/label/split/seed/search-space/trial記録 | trainer、feature builder、purge/embargo実行、rule distillation |
| `strategy_backtest_trial_ledger` | artifact存在/hash、success-only防止の一部 | 全parameter attempt、cash transfer、generation lifecycle |
| Strategy Authoring | 固定ruleへのmaterialization | Campaign/Pool/Vault表現 |
| Backtest engine | trade lifecycle、funding、cost、portfolio基盤 | multi-machine Campaign、Ratchet、Reload、Rebase、Vault |
| Crypto Perp Kill chain | fail-closed bias/no-cash/leaderboard | D01専用tail/ruin/Impact gate |

既存contractへ無理に全責務を押し込まない。一方で、D01専用の巨大な別Backtest engineも作らず、trade resultを既存Backtestから受け、Campaign Simulatorが上位資本状態を評価する境界を第一候補とする。

## 13. 未決事項

次は採用済み思想ではなく、Campaign Simulatorまたは将来の方向性統合で決める。

1. 生活Impact目標を年間確定利益、Vault残高、出金額、総資産のどれで判定するか。
2. 資産帯別の稼働機体数、Reload単位数、minimum executable balance。
3. `max_margin_in_use`、`max_position_notional`、`max_leverage`、`max_concurrent_positions`。
4. risk clusterの距離、上限、Quarantine解除条件。
5. Rebase後の一段階縮小幅、cooldown、再拡大条件。
6. 成功倍率候補とRatchet地点の検出力、費用、Pool生存性による校正。
7. Vaultを生活利益として出金する条件と、Scale Reserveとの境界。
8. `gamma = 0.5`、24時間確認、20% drawdownの校正。
9. strategy、capital policy、machine assignmentを固定する時点と再割当条件。
10. MLに必要なsource、期間、独立episode、feature availability、license、data費用。
11. venueごとのminimum order、fee、funding、slippage、liquidation、negative balance関連条件。
12. Campaign Simulatorの状態遷移、Artifact Schema、idempotency、resume契約。

13. `D01-U001`: 10倍を機体残高上限とする現行解釈で、総Campaign wealthが10.5倍になることを意図しているか。
14. `D01-U002`: Ratchet Vaultを次Capital EpochのRebase原資へ含めるか。
15. `R_trade` barrierをmark、last、executable fillのどれで測るか。
16. Campaignのmaximum duration、maximum trades、dormant expiry。
17. success harvestをScale ReserveからReload Poolへ移せる条件。
18. Impact KPIに税、生活出金、外部入出金をどこまで含めるか。
19. Strategyとcapital policyの探索partitionをどう分けるか。
20. data不足時のDEFER expiryと最大data acquisition費用。

未決事項は、実装者が合理的に推測して埋めてはならない。経済結果を変える分岐はartifact fieldを`UNSET`にし、該当runをBLOCKする。

## 14. 誤謬・破綻リスク

- 高倍率目標を置くこと自体はedgeの証拠ではない。
- 1回のtail winnerを再現可能な分布と誤認しやすい。
- 成功倍率へ到達したsurvivorだけを見ると、死亡GenerationとReload消費を隠せる。
- 機体数はrisk diversificationの証拠ではない。
- 機体残高比例riskは、機体成長時に1tradeの絶対損失も増やす。
- Ratchetは元本の一部を保護するが、残りの含み・確定利益を成功まで再リスクに晒す。
- Reloadを繰り返せば、1機体500 USDという表面上の損失上限を超えてfamily全体がPoolを消費する。
- Rebaseと成功倍率を同じdataで多数試行すると、capital policy自体へoverfitする。
- 小額帯ではfee、funding、minimum order、tick、slippageが理論Rを破壊し得る。
- 大額帯ではcapacity、market impact、liquidity、venue concentrationにより小額時のedgeを外挿できない。
- 月次16%を心理的ノルマへ転用すると、禁止したtarget chasingが運用判断へ侵入する。
- Vaultを再投入可能なPoolと混同すると、保護利益が見せかけになる。
- zero-cut、liquidation、exchange failureを損切り機構として期待すると、通常損失の上限を証明できない。
- 現在の証拠量ではML、tail probability、Campaign ruin probabilityを推定できない。
- `R_trade`と`R_campaign`を混ぜると、tail倍率、損益分岐、最大連敗を桁違いに誤計算する。
- Ratchet回収を成功倍率へ加えるか否かで、10倍と10.5倍が混在する。
- XGBoostとLightGBMの一致を独立再現と誤認できる。
- SHAPで説明できることを因果性またはtradabilityと誤認できる。
- overlapping label rowを独立sampleと数え、tail evidenceを水増しできる。
- OHLCだけでsame-bar barrier順序を都合よく決められる。
- zero observed ruinをruin probability zeroと誤認できる。
- Strategyとcapital policyを同じvalidationで最適化し、二重にoverfitできる。
- Scale Reserve、Vault、Reload Pool間のtransferを収益と二重計上できる。
- cross-marginやauto-marginにより、論理Vaultが実際にはposition collateralへ使われ得る。
- Profit Vault込みsystem wealthでdrawdownを薄め、operating lossを隠せる。
- Rebase直後の拡大とdownscale条件が同時成立したとき、都合のよい方だけ適用できる。
- minimum executable balance未満にならない機体を永久にactiveとして生存率を水増しできる。
- positive-skew候補を証拠不足で永久DEFERし、研究墓場を作れる。

これらは方向性を弱める理由ではない。攻撃性を、無根拠なleverageやgate緩和ではなく、発想数、payoffの右裾、機会捕捉、資源再配分へ向けるための反証条件である。

### 14.1 Venue前提を一般化しない

Perpetualのloss boundaryはvenue、contract、isolated/cross/portfolio margin、mark price、maintenance margin、insurance fund、ADL、auto-margin設定で変わる。例えばBybitの公式資料でも、cross marginはavailable balanceをmarginに使い、liquidationはmark price/account MMRで決まり、insurance fund不足時はADLが関与すると説明されている。これはBybitを採用する決定ではなく、「cryptoなら初期投資以下」と一律に固定できない反例である。

venue未選定の段階では、次をすべて`UNKNOWN`にする。

- negative balanceに対する利用者責任。
- liquidation/ADL時のfillとPnL。
- cross collateral範囲。
- stopよりliquidationが先行する条件。
- insurance fundの適用範囲。
- outage、delisting、contract変更時の処理。

## 15. 比較・テスト契約

### 15.1 Deterministic fixture

最低限、次をRedにしてから各contractを実装する。

1. 500 USD、risk 1%から`R_trade = 5 USD`になる。
2. minimum quantity丸めでrisk超過する注文がNO_TRADEになる。
3. 4倍到達でRatchetが一度だけ発動する。
4. 4倍到達、回収、残高低下、再到達でも二重回収しない。
5. success capを飛び越えたovershootが保存される。
6. Ratchet後successで10倍/10.5倍の選択契約どおり保存則が成立する。
7. normal death、abnormal execution、data errorが別状態になる。
8. Poolが1 unitと等しい場合Reloadを拒否する。
9. 同一Clusterの2機死亡でQuarantineし、別codeでもReloadしない。
10. Strategy Gate失効後のReloadを拒否する。
11. Rebase確認中に1.6倍を割ると24h timerをresetする。
12. Rebaseと20% downscale同時成立時に拡大しない。
13. old GenerationのpolicyがRebaseで変わらない。
14. crash/resumeでRatchet、Reload、Rebase transferを二重計上しない。
15. Pool、Vault、Scale Reserve、machineの資金保存差が常に0になる。

### 15.2 Known-case economic fixture

- no-edge + high leverage: tail winnerが見えても長期Impactで不採用。
- stable convex edge: fee後も複数独立episodeでtailが残る。
- single lucky winner: leave-one-episode-outで成績消失。
- correlated machines: individual PASSでもPool ruinでBLOCK。
- fee-dominated micro account: 100 USD帯をNOT_EXECUTABLE。
- Ratchet-too-early: Vaultは増えるがtail到達率が崩れる。
- no-Ratchet giveback: tail直前利益を失いImpact率が下がる。
- Reload death spiral: positive standalone EVでもPoolが先に枯れる。
- Rebase overgrowth:短期成長後の絶対risk増加でruinが悪化する。
- missing books/mark/funding: execution evidence不足で昇格しない。

### 15.3 Property / mutation test

- boundary flagをtrueへmutateするとvalidation failure。
- transfer片側を削るとconservation failure。
- policy hashを変えるとresume failure。
- Vaultをoperating collateralへ足すとprotection failure。
- trial ledgerから失敗policyを抜くとcount/hash failure。
- same-bar barrier順序をprofit側へ固定するとambiguity fixture failure。
- blocked stateをSUCCESSへ変えるとtransition failure。

### 15.4 検証レベル

| レベル | 言えること | 言えないこと |
| --- | --- | --- |
| contract fixture | 数式・遷移・保存則が正しい | 市場edge |
| synthetic known-case | 既知条件を区別できる | real-market確率 |
| historical replay | 過去pathでの挙動 | 将来profit |
| protected OOS | 未使用sampleでの候補確認 | live fill、将来保証 |
| Campaign hostile E2E | orchestrationがfail-closed | Paper/live permission |

## 16. 現行Checkpointへの影響案

これはmaster plan更新ではなく、後の統合時に落とす必要がある差分一覧である。

| CP | D01で追加すべき証拠 |
| --- | --- |
| CP0 | Impact accounting、二種類のR、capital band、ML/data readiness、venue/margin契約、10倍/10.5倍決定 |
| CP1 | Capital Epoch、machine/generation、Pool/Vault/Reserve、transition、conservation schema |
| CP2 | capital policy trial、human distillation、cash eventを含むledger/lineage |
| CP3A | 既存core generatorがD01 CandidateProgramを表現できるか |
| CP4 | leakage、ambiguous label、minimum size、liquidation依存をstatic KILL |
| CP5 | `R_trade` cheap screen、tail lane、fee-to-R、false-kill shadow audit |
| CP3B | Convex Meta-Labelerを先行spikeし、Tail Miner/MLをsource別admission |
| CP6 | Strategyとcapital policyの全trial、overlap、rare-event uncertainty、protected inference |
| CP7 | existing Backtest結果からCampaign Simulatorへlossless binding、portfolio/Pool ruin評価 |
| CP8 | atomic cash ledger、status、resume、resource profile |
| CP9 | legacy artifactをCampaign successへ自動昇格しないmigration |
| CP10 | Ratchet/Reload/Rebase crash、correlated death、venue anomaly、zero-survivor hostile E2E |
| CP11 | D01新導線が証明されるまで旧writer/CLIを削除しない |

D01を上位方向へ置くなら、CP0のprimary economic estimandとCP7のBacktest接続だけを少し変えるのでは足りない。trial universe、state、cash ledger、ML feedback、Campaign SimulatorをCP1から一貫させる必要がある。一方、他方向性との比較前にこの差分をSP_STATEへ入れてはならない。

## 17. 調査根拠と適用限界

- [Risk-Constrained Kelly Gambling](https://arxiv.org/abs/1603.06183): growth最大化とdrawdown確率制約を分ける根拠。D01のRobust Kelly採用を証明するものではなく、将来challenger設計の参考。
- [The Probability of Backtest Overfitting](https://escholarship.org/uc/item/4w1110bb): 多数のstrategy/capital policyからwinnerを選ぶ選択過適合を検査すべき根拠。
- [Bybit Insurance Fund](https://www.bybit.com/en/help-center/article/Insurance-Fund): liquidation損失、insurance fund、ADLの関係がvenue mechanismに依存する例。
- [Bybit Order Execution and Liquidation FAQ](https://www.bybit.com/en/help-center/article/FAQ-Order-Execution-and-Liquidation): mark price、margin mode、stopとliquidationの違いを別data/contractとして扱う根拠。
- [Bybit Auto-Margin Replenishment](https://www.bybit.com/en/help-center/article/Auto-Margin-Replenishment?category=cd60af6303161fd598): isolated設定でもavailable balanceが自動追加され得る例。Vaultの物理分離確認が必要な根拠。

論文や一取引所の仕様を、D01の数値閾値や全venueの一般則へ流用しない。採用venue、jurisdiction、account/margin modeが決まった時点で公式contractを再取得し、hashと取得日時をCP0/CP7 evidenceへ残す。

## 18. 今後の統合規則

今後追加する方向性は`D02`以降として別文書へ記録し、初期段階ではD01へ混ぜない。各方向性について、少なくとも次を揃える。

- 目的とNorth Starへの影響。
- 現行計画に対する優先度。
- 採用済み判断と初期simulation候補。
- Kill条件と安全境界。
- 必要data、費用、実装量。
- D01との相乗効果、競合、排他条件。
- 失敗時の停止境界。

複数方向性を受け取った後、master plan、Checkpoint Goal、CP0 feasibility contractへ統合する。統合時は、方向性を足し合わせて巨大scopeにせず、限界発見価値、必要証拠、build/data/compute費用から順序とbuild ceilingを決める。

## 19. 次の設計段階

この方向性だけについて次に具体化する対象は、Campaign Simulatorの評価契約、状態遷移、Artifact Schemaである。ただし、ほかの方向性を受け取る予定があるため、明示指示までは設計・実装を進めない。

その前に`D01-U001`、`D01-U002`、`D01-U003`を明示決定する必要がある。特に10倍/10.5倍の意味とVaultのRebase再投入可否が未確定のままでは、Campaign Simulatorの資金保存fixtureとprimary estimandを一意に作れない。

推奨回答は[D01-R01](./HYPOTHESIS_SEARCH_ENGINE_DIRECTION_01_RECOMMENDED_RESOLUTIONS_2026-07-14.md)に記録済みである。採否はまだ確定していない。
