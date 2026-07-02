<!--
作成日: 2026-07-02_00:00 JST
更新日: 2026-07-02_00:00 JST
-->

# Research Basis: Profit Core Smart Priors

## 結論

候補生成を強化する理由は、候補数そのものを増やすためではない。検証する価値がある候補を増やし、同時にfalse positive、検証渋滞、実行不能候補を殺すためです。

この計画では、Edge Candidate Factoryをfeature list generatorではなく、flow-cause based generatorとして設計する。funding、liquidation、mark/index basis、order-flow imbalance、spread、open interest、volatility compression は重要な観測対象だが、priorの上位概念ではない。上位概念は forced flow、inventory / risk-transfer flow、slow information、constrained arbitrage、crowded positioning、behavioral attention、adverse selection、execution friction、data observability です。

## 実装に直接効く研究知見

### 1. Backtest overfitting and lucky winner risk

Bailey, Borwein, Lopez de Prado, Zhu の “The Probability of Backtest Overfitting” は、投資backtestでは通常のholdoutが不安定になり得ること、CSCVによりbacktest overfitting probabilityを推定する考え方を示す。

実装への落とし込み:

- 候補生成器は全candidate、全rejection、全trial countを保存する。
- best candidateだけを見せるUIを作らない。
- PBOはfold-by-candidate outcome matrixがある時だけ `AVAILABLE` とし、無い場合は `NOT_ESTIMABLE` にする。
- `NOT_ESTIMABLE` を失敗ではなく、正式な停止・保留結果として扱う。

Reference:

- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

### 2. Deflated Sharpe Ratio and effective trial count

Bailey and Lopez de Prado の Deflated Sharpe Ratio は、selection bias、backtest overfitting、sample length、non-normal returnを考慮してSharpeの有意性を補正する発想です。

実装への落とし込み:

- Sharpeやreturnだけを候補rankの主KPIにしない。
- `effective_trial_count_status` と `effective_trial_count` をartifactに保存する。
- 候補が互いに相関している場合、単純candidate countではなくcluster/effective countを将来計算できる形にする。
- DSRは必要なreturn seriesとtrial distributionが無い場合、`NOT_ESTIMABLE` とする。

Reference:

- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

### 3. White Reality Check and data snooping

White の Reality Check は、同じデータを何度も使ってmodel selectionした時に、best modelの見かけの優位性がdata snoopingで生まれる問題を扱う。Hansen SPA は、White Reality Checkが低品質モデル集合に引きずられる問題を改善する方向です。

実装への落とし込み:

- `searched_universe` と `candidate_inventory` を保存する。
- full trial setが無いcandidate evaluationはreviewに進めない。
- Reality Check / SPAはv0で実装しないが、必要入力不足を `NOT_ESTIMABLE` として明示する。

References:

- https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569

### 4. Factor zoo and higher significance threshold

Harvey, Liu, Zhu は、多数のfactorが発見される状況では、通常のt-stat 2.0程度では甘く、より高いハードルが必要だと論じる。

実装への落とし込み:

- 新規候補ほど探索会計とout-of-sample evidenceを重く見る。
- `raw_validation_metrics` をproofと呼ばない。
- literature-seeded candidate と pure data-mined candidate を分ける。
- old factor cloneはnovel discoveryではなく clone / redundant として扱う。

Reference:

- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314

### 5. Publication decay and crowding risk

McLean and Pontiff は、学術文献にあるreturn predictorのout-of-sampleおよびpublication後のpredictability低下を示す。

実装への落とし込み:

- 文献由来のcandidateも現在のvenue / cost / liquidityで再検証する。
- `publication_decay_risk` または `crowding_risk` をmechanism cardに保存する。
- `known_factor_clone` と `novel_candidate` を分ける。

Reference:

- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623

### 6. FDR and dependency caution

Benjamini-Hochberg FDRは多重検定のthroughput controlに向く。ただしcandidate同士は独立ではない。RSI 14 / 15 / 16、breakout 20 / 21 / 22 のような候補は強く相関する。

実装への落とし込み:

- BH/FDRだけを合格条件にしない。
- candidate clusterとsimilar candidate countを保存する。
- v0では `effective_trial_count_status=NOT_ESTIMABLE` を許容する。
- 依存が強い場合は将来BYまたはcluster-aware adjustmentへ進める。

Reference:

- https://www.jstor.org/stable/2346101
- https://www.jstor.org/stable/3098017

### 7. Perpetual futures funding is mechanism, not income

Perpetual futuresでは満期がなく、fundingがperp価格とspot/index価格の乖離を抑える。これは構造的mechanismだが、固定収益源ではない。

実装への落とし込み:

- funding candidateは、funding rate単体で出さない。
- mark/index basis、position crowding、holding horizon、fee、slippage、forced exit riskをセットで保存する。
- fundingは `source_required` であり、欠損時はcandidateをBLOCKする。

Reference:

- https://arxiv.org/abs/2212.06888

### 8. Liquidation and leverage risk

Crypto futuresでは高レバレッジ、清算、極端returnがtail riskを大きくする。liquidationはforced flow priorとして重要だが、reversalとcontinuationを決め打ちしてはいけない。

実装への落とし込み:

- liquidation candidateは `REVERSAL`, `CONTINUATION`, `NO_TRADE` を同じevent setで比較する。
- liquidation sourceが無い場合はBLOCKする。
- spread widening、book depth evaporation、post-event liquidity recoveryをkill conditionに含める。

Reference:

- https://arxiv.org/abs/2102.04591

### 9. Market microstructure and OFI caution

Order-flow imbalance、book depth、spread、quote ageは短期予測やexecution qualityに関係する。ただし、小口個人にとってはデータ保存、timestamp alignment、latency、fill qualityの実務負荷が大きい。

実装への落とし込み:

- v0ではOFIを主signalではなくNO_TRADE filterとして優先する。
- book depthやOFIが無い場合、候補を無理にactual cashへ送らない。
- virtual execution gateでpartial fill、cancel、reconcileを検査する。

References:

- https://arxiv.org/abs/1708.02715
- https://arxiv.org/abs/2506.05764

### 10. AMM LVR and adverse selection

AMM LPのloss-versus-rebalancingは、古い価格やプール価格が裁定業者に抜かれるadverse-selection構造を説明する。これはCEX perp v0のCoreではないが、future priorとして重要。

実装への落とし込み:

- DEX/AMMはPhase 2以降。
- AMM candidateはadverse-selection flowとして扱う。
- CEX-DEX lagやoracle lagと組み合わせる。

Reference:

- https://arxiv.org/abs/2208.06046

### 11. Kaggle / Numerai style validation leakage

Kaggle public leaderboardやNumerai validation diagnosticsは、adaptiveに見続けるとholdoutへのoverfitを起こす。Numeraiはscoringが遅れて確定し、validation diagnosticsの過信にも注意が必要です。

実装への落とし込み:

- sealed holdoutはselectionに使わない。
- `validation_peek_count` を保存する。
- 一度OOS失敗を見て直した候補は、その同じOOSを再度true OOSとして扱わない。
- LLM reviewでもsealed holdout汚染をoverclaimとして検出する。

References:

- https://arxiv.org/abs/1502.04585
- https://docs.numer.ai/numerai-tournament/scoring

### 12. Virtual execution is execution evidence, not profit evidence

CEX demo / testnet / virtual executionは、利益証拠ではなくorder lifecycle証拠です。Bitget demoはvirtual fundsとdemo API keyを持ち、RESTでは `paptrading: 1` headerを使う。Hyperliquidはtestnet URLがあり、mainnetと同様のrequestをtestnetへ送れる。GRVTもtestnet auth endpoint、API key / wallet login、session cookie、account idを持つ。

実装への落とし込み:

- Virtual Execution GateはPnLを主KPIにしない。
- order accepted、reject reason、partial fill、cancel、reduce-only close、flat reconciliation、fee/funding-like fieldsを検査する。
- `actual_cash=false`, `cash_metric_basis=virtual_exchange`, `production_exchange_write_used=false` を固定する。

References:

- https://www.bitget.com/api-doc/common/demotrading/restapi
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api
- https://api-docs.grvt.io/

## Core prior ranking

小口資金・高リスク許容・個人開発を前提に、最初に扱うpriorは次の順にする。

| Rank | Prior | 初期扱い | 理由 |
|---:|---|---|---|
| 1 | forced flow | Core | 清算、stop、funding負担など不利な売買が生まれる |
| 2 | execution friction | Core | 実行不能候補を最初から落とす |
| 3 | constrained arbitrage / basis | Core | perp固有で小口にも観測しやすい |
| 4 | crowded positioning | Core | funding、OI、basis、liquidationと接続しやすい |
| 5 | liquidity / spread regime | Core filter | alphaよりNO_TRADE filterとして重要 |
| 6 | volatility regime | Core filter | standalone causeではなく条件付け |
| 7 | OI / volume impulse | Core candidate | source品質に依存するが有用 |
| 8 | OFI / LOB | Phase 2 | 強い可能性はあるが実装・latency負荷が大きい |
| 9 | on-chain / stablecoin flow | Phase 2 | 遅延・分類誤り・混雑リスクが大きい |
| 10 | sentiment / attention | Phase 3 | narrativeとoverfitのリスクが大きい |
| 11 | pure RSI / MACD | helper | 主役ではなく構造priorの補助feature |
| 12 | ML-discovered features | Phase 3 | accountingなしでは危険 |

## Design consequences

### Candidate generation starts from cause, not feature

悪い設計:

```text
feature = funding_rate
if high funding then short
```

良い設計:

```text
cause_prior = crowded_positioning + constrained_arbitrage
mechanism = crowded long pays high funding and basis may mean-revert if execution friction is low
observables = funding_rate, mark_index_basis_bps, OI, spread_bps
counter_hypothesis = trend continuation dominates basis reversion
kill_conditions = adverse funding shift, spread widening, NO_TRADE leads, virtual reconcile failure
```

### Volatility compression is not a structural cause

`volatility_compression` は統計状態であり、forced flowではない。breakout candidateのregime filterには使えるが、これだけでedge priorと呼ばない。

### Technical indicators are helper features

RSIやMACDは排除しない。ただし、単独priorではなく、liquidation、funding、basis、spreadなどの構造priorを補助するfeatureとして扱う。

### Execution-aware candidate generation is mandatory

候補生成時点で次を持つ。

```text
min_notional_ok
tick_size_ok
lot_size_ok
expected_spread_bps
fee_rate_available
funding_available
operator_time_minutes
capital_tied_up_minutes
unexecutable_reason
```

これが無い候補はBacktestへ送らない。

### Negative controls are required

候補ごとにnegative controlを指定する。

例:

```text
liquidation reversal candidate -> random non-liquidation shock control
funding candidate -> same trend without funding extreme control
basis candidate -> basis-neutral window control
```

## What not to optimize

最初に最適化してはいけないもの:

- best Sharpe。
- best total return。
- LLM narrative plausibility。
- number of generated candidates alone。
- virtual PnL。
- backtest pass count。

最適化するもの:

- logged candidate throughput。
- rejection throughput。
- source completeness。
- execution feasibility。
- low operator time。
- short feedback loop。
- actual cash learning rate。

## Open risks

1. Research sources may not transfer to Bitget / Hyperliquid / GRVT current microstructure.
2. Public research findings may be crowded or decayed.
3. Candidate family thresholds can overfit if repeatedly adjusted after validation.
4. Virtual execution can give false confidence if PnL is considered.
5. Smart Prior scoring can become another hidden optimizer unless its weights are fixed before the run.
6. `effective_trial_count` is hard when candidates are correlated and no return matrix exists.
7. LLM negative review can overflag; machine-checkable hard blockers must be separated from soft warnings.

## Final implementation rule

候補を賢くする。ただし、自分の賢さを信用しない。

```text
Generate smart priors.
Log every trial.
Expose every rejection.
Kill aggressively.
Forward only executable candidates.
Treat virtual as execution evidence.
Treat actual cash as the first economic evidence.
```
