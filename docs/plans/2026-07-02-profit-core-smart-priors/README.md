<!--
作成日: 2026-07-02_00:00 JST
更新日: 2026-07-03_11:35 JST
-->

# Profit Core Smart Priors Implementation Plan

## 結論

このフォルダは、Profit Core Smart Priors の設計バックログです。次にそのまま実装する作業列ではない。

現実的な次作業は [../2026-07-03-profit-core-reality-check/README.md](../2026-07-03-profit-core-reality-check/README.md) の Reality Check Sprint です。既存候補生成、search ledger、C9 bridge、risk review、actual-cash readiness を読んで、候補がどこで止まるかを先に測る。その結果の `next_single_blocker_to_fix` がこのフォルダのどの設計を実装対象へ昇格するかを決める。

Reality Check の前に、次の5つをまとめて実装しない。

1. `Smart Prior Generator v0`: feature list ではなく、flow cause から候補を作る。
2. `Trial Multiplicity Account v0`: 候補生成前に探索会計を固定する。
3. `Backtest Kill Gate v0`: backtest を攻める許可ではなく、候補を殺す装置にする。
4. `Virtual Execution Gate v0`: actual cash 前に、demo / testnet / fixture で order lifecycle と reconciliation を検証する。
5. `Risk / Actual Cash Handoff Contract v0`: 既存 `crypto-perp-risk-taker-review` と `crypto-perp-actual-cash-report-gate` へ渡せるもの、渡してはいけないものを固定する。

`risk_taker_review` と `actual_cash_report_gate` は後段の最終判定器として維持する。C9 bridge と Strategy Authoring は完全なAddonではなく、候補を検証経路へ機械的に流すCore補助として扱う。NDX、Trade[XYZ]、generic Strategy Lab、optional backtest frameworks、full UI、full operations audit は明示scope時だけ使うAddonへ降格する。

## 実行ゲート

このフォルダのT1以降は、Reality Check Sprint の後だけ実装候補にする。

先に確認するもの:

```text
docs/plans/2026-07-03-profit-core-reality-check/README.md
docs/plans/2026-07-03-profit-core-reality-check/01_CURRENT_REPO_FACTS.md
docs/plans/2026-07-03-profit-core-reality-check/06_NEXT_DECISION_AFTER_DOGFOOD.md
```

実装へ進む条件:

1. `profit_core_reality_check.v1` または同等の手元artifactで、既存pipelineの blocker 分布が出ている。
2. `next_single_blocker_to_fix` が Smart Prior / multiplicity / kill gate / virtual lifecycle / actual-cash handoff のいずれかを指している。
3. その blocker を解く最小PRが、このフォルダのタスク1つ以下に対応している。
4. source / bridge / actual-cash rows 不足を、候補生成強化やLLMで隠していない。

Reality Check なしでこのフォルダを上から実装すると、既存pipelineの詰まりを測る前に新しい仕組みを足すことになり、false positive と保守負債を増やす。

## この計画の目的

この計画の目的は、貪欲な利益追求のために、個人・小口資金・高リスク許容の強みを活かしつつ、次の失敗を避ける設計境界を固定することです。

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
- existing `crypto-perp-actual-cash-report-gate` requires actual-cash rows and must not consume virtual/backtest artifacts as cash evidence.
- handoff artifact records candidate refs, backtest kill gate refs, virtual gate refs, and explicit `actual_cash_rows_required=true`.
- existing actual cash vocabulary remains source of truth.

### P5: LLM Adversarial Evidence Review

- missing artifact detection
- contradiction detection
- overclaim flag
- no gate override

## 文書構成

このフォルダには次を置く。

1. `README.md`: 全体方針、Core / Addon定義、Reality Check実行ゲート。
2. `01_TASK_CHAIN.md`: Reality Check後に必要部分だけ選ぶタスクチェーン。
3. `02_ARTIFACT_CONTRACTS.md`: 新artifact、schema、status、fieldの契約。
4. `03_TEST_AND_ACCEPTANCE.md`: テスト方針、完了条件、CI確認。
5. `04_RESEARCH_BASIS.md`: 論文・実務知見と実装への落とし込み。
6. `05_FUTURE_OUT_OF_SCOPE_ITEMS.md`: 今回範囲外4項目を profit-first に扱うための停止条件文書、既存CLIの読み方、優先順位、誤謬リスク。
7. `06_REALISTIC_PROFIT_READINESS_CHECKPOINTS.md`: 今できる / 一部できる / 入力不足で止める profit-readiness 実装チェックポイント。

## 完了条件

この設計バックログを実装対象へ昇格する場合の完了条件は次です。Reality Check Sprint が別の blocker を示した場合、この完了条件をそのまま採用しない。

1. 新規schemaのJSON SchemaとPydantic modelが存在する。
2. Edge Candidate Factory v0が、同じsourceとconfigから同じcandidate inventoryを再生成できる。
3. 全candidate、全rejection、全trial count、validation peek count、sealed test non-use がartifactに残る。
4. Backtest Kill Gate v0が、攻める許可ではなく `KILL / INCONCLUSIVE_DATA / RESEARCH_ONLY / SHORTLIST_FOR_VIRTUAL` を返す。
5. Backtest Kill Gate v0が読む既存backtest artifact、抽出metric、`NOT_ESTIMABLE` 条件が明示される。
6. Virtual Execution Gate v0が、PnLではなくorder lifecycle / cancel / reject / reduce-only close / flat reconciliationを評価する。
7. `actual_cash=false` と `cash_metric_basis=virtual_exchange` をvirtual artifactに固定する。
8. 新artifactのboundaryが既存repoの安全検出語彙を含む。
9. Risk / Actual Cash handoffが、virtual/backtest artifactをactual cash evidenceとして渡さない。
10. LLM reviewが入る場合でも、LLMはapproval、paper permission、live permission、actual cash判定を出さない。
11. `uv run python scripts/check_cli_catalog.py`, `uv run python scripts/check_current_docs.py`, `./scripts/check` が通る。

## 明示的な非目的

この計画では次を実装しない。

- production live trading。
- wallet / signing / exchange write の標準operator path許可。
- virtual PnL の actual cash 昇格。
- LLMによる戦略採用判断。
- GA / ML / GBDT / optimizer の初期Core採用。
- NDX / Trade[XYZ] のdefault path復帰。
- UI実装。
- Reality Check Sprint を飛ばしてT1から順に実装すること。

## 誤謬リスク

- 候補が賢いことと、利益が出ることは違う。
- market structureがあることと、edgeが残ることは違う。
- backtest passはattack permissionではない。
- C9 `BRIDGED` はtechnical bridge statusであり、economic passではない。
- virtual PnLはactual cashではない。
- BH/FDRは候補間依存が強い場合に甘くなり得る。
- PBO/DSR/White Reality Checkは、必要なfold matrixやtrial return seriesがなければ計算不能。`NOT_ESTIMABLE` は正式な停止結果として扱う。
- LLMは矛盾を見つける補助であり、裁定者ではない。
- PR #17 を「次に上から実装する作業列」と誤読すると、既存pipelineの実測 blocker を見ずに新規Coreを増やす。
