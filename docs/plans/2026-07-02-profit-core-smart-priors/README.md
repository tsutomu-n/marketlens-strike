<!--
作成日: 2026-07-02_00:00 JST
更新日: 2026-07-02_00:00 JST
-->

# Profit Core Smart Priors Implementation Plan

## 結論

次に実装するべきものは、単体の候補生成強化ではない。`marketlens-strike` の次Coreは、Smart Edge Candidate Factory、探索会計、候補別bridge、Backtest Kill Gate、Virtual Execution Gate、Risk-Taker Review、Actual Cash Report Gate を1本の検証throughputとして接続することです。

ただし、最初から全機能を大きく作らない。最初の実装単位は次の4つです。

1. `Smart Prior Generator v0`: feature list ではなく、flow cause から候補を作る。
2. `Trial Multiplicity Account v0`: 候補生成前に探索会計を固定する。
3. `Backtest Kill Gate v0`: backtest を攻める許可ではなく、候補を殺す装置にする。
4. `Virtual Execution Gate v0`: actual cash 前に、demo / testnet / fixture で order lifecycle と reconciliation を検証する。

`risk_taker_review` と `actual_cash_report_gate` は後段の最終判定器として維持する。C9 bridge と Strategy Authoring は完全なAddonではなく、候補を検証経路へ機械的に流すCore補助として扱う。NDX、Trade[XYZ]、generic Strategy Lab、optional backtest frameworks、full UI、full operations audit は明示scope時だけ使うAddonへ降格する。

## この計画の目的

この計画の目的は、貪欲な利益追求のために、個人・小口資金・高リスク許容の強みを活かしつつ、次の失敗を避ける実装順を固定することです。

- 候補数だけを増やし、false positive を増やす。
- backtest 上位候補を alpha proof と誤読する。
- C9 `BRIDGED` を経済的合格と誤読する。
- virtual PnL を actual cash と混ぜる。
- demo / testnet で execution lifecycle が壊れる候補を actual cash へ送る。
- LLM に良い戦略を選ばせ、narrative creep を増やす。
- Addon のPASSをCore判断へ昇格する。

## 最終Core定義

```text
Core =
  Smart Edge Candidate Factory
  + Multiplicity / Search Accounting
  + Candidate-to-Backtest Bridge
  + Backtest Kill Gate
  + Virtual Execution Gate
  + Risk-Taker Review
  + LLM Adversarial Evidence Review
  + Actual Cash Report Gate
```

## Addon定義

次はCoreのdefault pathに入れない。

- NDX / QQQ research gates。
- Trade[XYZ] read-only / quotes / data readiness。ただし Trade[XYZ] 明示scope時は維持。
- generic Strategy Lab 拡張。
- optional backtest frameworks の追加採用。
- broad AI review / AI narrative support。
- full Workbench Viewer UI。
- full operations / audit / remediation suite。
- historical migration docs。

Addonの制約:

1. AddonのPASSはCore判断へ昇格しない。
2. AddonのFAILでCore運用を止めない。
3. Addonはdefault runに入れない。
4. Addonはdaily decisionの主KPIにしない。
5. Addonは明示scope指定時だけ読む。

## Smart Prior の再定義

従来の候補生成は、funding、liquidation、mark/index basis、order-flow imbalance、spread、open interest、volatility compression などのfeature listに寄りやすい。この計画では、その下にある原因を先に扱う。

```text
Smart Prior =
  forced flow
  inventory / risk-transfer flow
  slow information flow
  constrained arbitrage
  crowded positioning
  behavioral / attention flow
  adverse-selection flow
  execution friction
  data observability
```

観測対象はその下に置く。

```text
funding
liquidation
mark/index basis
spot-perp basis
open interest
spread
order-flow imbalance
book depth
volume / turnover
on-chain / stablecoin flow
calendar / session / funding time
venue constraints
sentiment / attention
volatility regime
```

候補生成はfeature listから始めない。`誰が、なぜ、不利に動かされるのか` から始める。

## 実装方針

1. 既存 `strategy_idea_candidates` を破壊しない。
2. 新規Coreは `src/sis/edge_candidate_factory/` として分ける。
3. 既存 `strategy_idea_candidate_set.v1` へ最終的にexportできるが、Edge Factory固有の探索会計は新artifactに分ける。
4. 初期実装は依存追加なし。`polars`, `duckdb`, `pyarrow`, `pydantic`, `jsonschema` で完結させる。
5. `scipy`, `statsmodels`, `arch`, `scikit-learn`, `lightgbm` は後段optionalにする。P0 / P1 では入れない。
6. Bitget demo / Hyperliquid testnet / GRVT testnet の同時実装は禁止。Virtual Execution Gate v0は fixture/mock-first + Bitget demo opt-in を優先する。
7. LLMは approval ではなく adversarial negative-veto reviewer に限定する。

## 優先順位

### P0: 証跡と会計を先に固定

- `trial_multiplicity_account.v1`
- `smart_candidate_prior_report.v1`
- `edge_candidate_search_ledger.v1`

### P1: Smart Prior Generator v0

- forced flow
- constrained arbitrage
- funding / basis
- liquidation
- liquidity / spread no-trade filter
- volatility regime filter

### P2: Backtest Kill Gate v0

- `KILL`
- `INCONCLUSIVE_DATA`
- `RESEARCH_ONLY`
- `SHORTLIST_FOR_VIRTUAL`

### P3: Virtual Execution Gate v0

- fixture/mock first
- Bitget demo explicit opt-in
- no production exchange write
- no actual cash claim

### P4: Risk-Taker Review / Actual Cash integration

- existing `crypto-perp-risk-taker-review` remains final human-risk precheck.
- existing actual cash vocabulary remains source of truth.

### P5: LLM Adversarial Evidence Review

- missing artifact detection
- contradiction detection
- overclaim flag
- no gate override

## 文書構成

このフォルダには次を置く。

1. `README.md`: 全体方針、Core / Addon定義、実装順。
2. `01_TASK_CHAIN.md`: コーダーが順に実装できるタスクチェーン。
3. `02_ARTIFACT_CONTRACTS.md`: 新artifact、schema、status、fieldの契約。
4. `03_TEST_AND_ACCEPTANCE.md`: テスト方針、完了条件、CI確認。
5. `04_RESEARCH_BASIS.md`: 論文・実務知見と実装への落とし込み。

## 完了条件

この計画全体の初期完了条件は次です。

1. 新規schemaのJSON SchemaとPydantic modelが存在する。
2. Edge Candidate Factory v0が、同じsourceとconfigから同じcandidate inventoryを再生成できる。
3. 全candidate、全rejection、全trial count、validation peek count、sealed test non-use がartifactに残る。
4. Backtest Kill Gate v0が、攻める許可ではなく `KILL / INCONCLUSIVE_DATA / RESEARCH_ONLY / SHORTLIST_FOR_VIRTUAL` を返す。
5. Virtual Execution Gate v0が、PnLではなくorder lifecycle / cancel / reject / reduce-only close / flat reconciliationを評価する。
6. `actual_cash=false` と `cash_metric_basis=virtual_exchange` をvirtual artifactに固定する。
7. LLM reviewが入る場合でも、LLMはapproval、paper permission、live permission、actual cash判定を出さない。
8. `uv run python scripts/check_cli_catalog.py`, `uv run python scripts/check_current_docs.py`, `./scripts/check` が通る。

## 明示的な非目的

この計画では次を実装しない。

- production live trading。
- wallet / signing / exchange write の標準operator path許可。
- virtual PnL の actual cash 昇格。
- LLMによる戦略採用判断。
- GA / ML / GBDT / optimizer の初期Core採用。
- NDX / Trade[XYZ] のdefault path復帰。
- UI実装。

## 誤謬リスク

- 候補が賢いことと、利益が出ることは違う。
- market structureがあることと、edgeが残ることは違う。
- backtest passはattack permissionではない。
- C9 `BRIDGED` はtechnical bridge statusであり、economic passではない。
- virtual PnLはactual cashではない。
- BH/FDRは候補間依存が強い場合に甘くなり得る。
- PBO/DSR/White Reality Checkは、必要なfold matrixやtrial return seriesがなければ計算不能。`NOT_ESTIMABLE` は正式な停止結果として扱う。
- LLMは矛盾を見つける補助であり、裁定者ではない。
