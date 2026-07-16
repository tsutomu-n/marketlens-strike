<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA6部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A6 — Mutation / Counterfactual / Cross-lane

## A6.1 ゴール定義

Technical、ML、LLMのSeedから兄弟仮説、反対仮説、他レーンへの研究Requestを決定論的に生成する。親SeedのEvidenceを子へ継承しない。

Mutationは仮説の増殖であり、証拠の増加ではない。

## A6.2 Entry Criteria

- A4とA5が`IMPLEMENTATION_COMPLETE`。
- A2 Identity/Archive/Resumeが動作。
- Technical/ML/LLM PayloadのCanonicalizerが存在。
- Mutation Budgetと最大Generation DepthをConfigで定義済み。

## A6.3 対象範囲

### 実装する

- Deterministic Mutation Operator
- Counterfactual
- Generation Depth
- Parent/Child Lineage
- Evidence Reset
- Mutation Attempt Ledger
- Budget/Resume
- Technical→ML Request
- ML→LLM Request
- LLM→Technical Request
- Public CLI

### 実装しない

- Mutation Seedの自動評価
- Recursive無制限進化
- GP/MCTS/GFlowNet
- 他レーンの自動実行
- Candidate Export

## A6.4 対象ファイル

```text
src/sis/strategy_idea_seeds/mutation/
  models.py
  applicability.py
  operators.py
  engine.py
  counterfactual.py
  evidence_reset.py
  budget.py

src/sis/strategy_idea_seeds/cross_lane/
  models.py
  technical_to_ml.py
  ml_to_llm.py
  llm_to_technical.py

schemas/
  strategy_idea_seed_mutation_attempt.v1.schema.json
  strategy_idea_seed_cross_lane_request.v1.schema.json

configs/strategy_idea_seeds/mutation_policy_v1.yaml

tests/strategy_idea_seeds/mutation/
tests/strategy_idea_seeds/cross_lane/
```

## A6.5 Mutation Operator

Core v1:

```text
DIRECTION_FLIP
HORIZON_NEIGHBOR
THRESHOLD_TIGHTEN
THRESHOLD_LOOSEN
CONDITION_DROP
CONDITION_COMPLEMENT
CAPTURE_CONTINUATION_TO_REVERSAL
CAPTURE_REVERSAL_TO_CONTINUATION
REGIME_RESTRICTION
ENTRY_TIMING_CONCEPT
DATA_EXPANDING_SOURCE
```

各Operatorは次を返す。

```text
APPLIED
NOT_APPLICABLE
INVALID_RESULT
PRUNED_BUDGET
DUPLICATE_RESULT
```

Not ApplicableもAttempt Ledgerへ残す。

## A6.6 Counterfactual

Counterfactualは観測証拠を持たない。

```yaml
direct_support: false
seed_tags:
  - COUNTERFACTUAL
```

例:

```text
Funding極端負 + Volume増 → Long Squeeze
    ↓
Funding極端正 + Volume増 → Short Squeeze
```

反転が型・単位・意味上成立しない場合はAttempt止まり。

## A6.7 Evidence Reset

子Seedへ継承しない。

```text
support_rows
support_distinct_events
tail_lift
observation_metrics
engine_support
grounding_support
```

継承してよい。

```text
parent_seed_ids
source requirements
operator lineage
mechanism parent
known gaps
```

## A6.8 Generation Depth

Core v1既定:

```text
max_generation_depth=1
```

Mutation SeedをさらにMutationしない。必要性が実測された場合だけ将来拡張する。

## A6.9 Cross-lane Request

### Technical→ML

Technical仮説の条件/Mechanismを、A3 Label/Horizonで探索するRequestを作る。ML Supportを付けない。

### ML→LLM

ML Ruleについて、複数のMechanism仮説、Alternative Explanation、必要Sourceを考えるRequestを作る。因果を確定しない。

### LLM→Technical

LLM SeedをOperator Catalogで表現可能か検査するRequestを作る。Unknown Operatorがあれば自動AST化しない。

Request生成後、他Laneは自動実行しない。Operatorが明示的に該当CLIを実行する。

## A6.10 Budget/Resume

安定順序:

```text
parent seed_record_id
operator id
operator parameter
```

Cursor:

```text
next_parent_index
next_operator_index
next_parameter_index
```

同一Mutation AttemptはRun Keyで再利用する。

## A6.11 Public CLI

```bash
uv run sis strategy-idea-seeds-expand   --archive-root <path>   --mutation-policy <path>   --out <path>
```

## A6.12 詳細タスク

| ID | タスク |
|---|---|
| A6-01 | Mutation Attempt/Result Modelを実装 |
| A6-02 | Applicability Matrixを実装 |
| A6-03 | Core Mutation Operatorsを実装 |
| A6-04 | Counterfactualを実装 |
| A6-05 | Evidence Resetを実装 |
| A6-06 | Generation Depth/Budget/Cursorを実装 |
| A6-07 | Cross-lane Request Modelsを実装 |
| A6-08 | Technical→ML Requestを実装 |
| A6-09 | ML→LLM Requestを実装 |
| A6-10 | LLM→Technical Requestを実装 |
| A6-11 | Archive/CLIへ接続 |
| A6-12 | Property/Lineage/Resume Testを追加 |

## A6.13 Test方針

- Parent Evidenceが子に存在しない。
- Generation Depth超過を拒否。
- Direction FlipのLong/Short対称性。
- Condition ComplementのOperator/Unit妥当性。
- Not ApplicableをLedgerへ記録。
- Operator順序変更で結果集合不変。
- Duplicate MutationをSeed水増ししない。
- Counterfactual `direct_support=false`。
- Cross-lane Requestが他Laneを実行しない。
- Resume後結果がClean Runと一致。

## A6.14 完了条件

### `IMPLEMENTATION_COMPLETE`

- 三レーンのSeedに適用可能なMutationが動作。
- Evidence非継承がModel/Schema/Testで保証される。
- CounterfactualとCross-lane Requestが生成される。
- Budget、Cursor、Resumeが機能。
- 全AttemptがArchiveに残る。

### `CURRENT_DATA_OPERATIONAL`

- 現在ArchiveのSeedから兄弟仮説を生成できる。
- Data Required Mutationを保持できる。
- Mutation爆発率、Duplicate率、Invalid率をReportできる。

## A6.15 停止・再設計条件

- Evidenceを子へコピーする。
- Mutationを利益改善と表現する。
- Generation Depthが無制限。
- 言い換えだけでSeed数が増える。
- Cross-lane Requestが他Laneを自動実行する。
- Budget超過Attemptを黙って捨てる。
