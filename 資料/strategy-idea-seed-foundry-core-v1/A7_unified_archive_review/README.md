<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA7部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A7 — Unified Archive / Review Product

## A7.1 ゴール定義

Technical、ML、LLM、Mutation、Counterfactualを一つのSeed Archiveへ統合し、Raw資産を失わず、人間が判断可能なReview Packetへ圧縮する。

A7はSeedの採否を決めない。読む順序と多様性を管理する。

## A7.2 Entry Criteria

- A6が`IMPLEMENTATION_COMPLETE`。
- すべてのLane FragmentがA2 Archive契約へ準拠。
- Lane別Canonicalizerが存在。
- Review Policyと表示上限をConfigで定義済み。

## A7.3 対象範囲

### 実装する

- Fragment再検証
- Exact Group
- Semantic Cluster
- Provenance統合
- Cross-run History
- Descriptor Archive
- Representative/Challenger/Wildcard
- Review Bucket
- Deterministic Round-robin
- Data Acquisition Backlog
- JSON/Markdown Review
- Public CLI

### 実装しない

- 利益Score
- Embedding/Vector DB
- Full MAP-Elites
- Human Label学習
- Candidate Shortlist
- Automatic Promotion

## A7.4 対象ファイル

```text
src/sis/strategy_idea_seeds/archive/
  exact_groups.py
  semantic_clusters.py
  cluster_policy.py
  history.py
  descriptor_archive.py

src/sis/strategy_idea_seeds/review/
  models.py
  buckets.py
  representative.py
  diversity.py
  data_backlog.py
  builder.py
  rendering.py

schemas/
  strategy_idea_seed_cluster_set.v1.schema.json
  strategy_idea_seed_history.v1.schema.json
  strategy_idea_seed_review_packet.v1.schema.json
  strategy_idea_seed_data_backlog.v1.schema.json

configs/strategy_idea_seeds/review_policy_v1.yaml

tests/strategy_idea_seeds/archive/
tests/strategy_idea_seeds/review/
```

## A7.5 Fragment再検証

Reducer前に各Fragmentを再検証する。

- Schema Version
- Payload Ref/Hash
- Boundary
- Seed Record ID
- Signature Version
- Parent存在
- Artifact Hash
- Run Key

不正Fragmentは隔離し、他Fragmentの処理を継続できる。

## A7.6 Exact Group

同じExact SignatureのSeedをGroup化する。

Group内で保持:

```text
seed_record_ids
source_lanes
provenance_signatures
first_seen_at
last_seen_at
run_ids
```

Recordは削除しない。

## A7.7 Semantic Cluster

二段階にする。

1. Descriptorで候補集合を狭める。
2. Lane-specific Canonical Structureを比較する。

Descriptor:

```text
mechanism_class
capture_archetype
path_archetype
direction
horizon_bucket
observable_set
required_source_bundle
```

Merge Policyは保守的にする。確信できない場合は別Clusterへ置く。Over-mergeは異なる仮説を失うため、Under-mergeより重大である。

Core v1でEmbeddingを使わない。

## A7.8 Cross-run History

```text
NEW_CLUSTER
RECURRENT_CLUSTER
THRESHOLD_VARIANT
DORMANT_REAPPEARED
KNOWN_EXACT_RULE
```

同一Dataset/Configの再実行は「再発見」と数えない。新しいSource Snapshot、異なるLane、異なるWindowなどのProvenanceを区別する。

## A7.9 Descriptor Archive

Cell Key:

```text
source_lane
mechanism_class
capture_archetype
path_archetype
direction
horizon
source_capability_class
```

各Cell:

```text
representative
challengers
wildcard
all_seed_ids
```

Full MAP-Elitesではない。Quality最適化を行わず、多様な表示枠を確保するためのArchiveである。

## A7.10 Review Bucket

### REVIEW_STRIKE

- Direction/Horizon/Observableが明確。
- Historical Sourceがある、またはML Rule Observationがある。
- MechanismまたはRuleが具体的。
- 利益証明を意味しない。

### REVIEW_WILD

- 新規Mechanism。
- Unknown Operator。
- Speculativeだが反証可能。

### REVIEW_DISAGREEMENT

- Engine Disagreement。
- Continuation/Reversal競合。
- Contrarian/Counterfactual。
- Threshold Unstable。

### DATA_ACQUISITION

- Missing Historical Source。
- Forward Collection Required。
- 必要Sourceと検証質問が明確。

## A7.11 Representative選定

単一総合Scoreを作らない。Lexicographic PolicyをVersion管理する。

例:

1. Boundary/Schema有効。
2. Required SourceとObservableが明確。
3. Evidence Scopeが広いものを表示上優先。
4. 条件数が少なく読めるものを優先。
5. Cross-lane再発見を表示上優先。
6. Stable Seed IDでTie-break。

これは採用判定ではなく表示選定である。

## A7.12 Diversity Selection

Bucketごとに次をRound-robinする。

```text
mechanism_class
source_lane
direction
horizon
```

Review Limitを超えたSeedはArchiveに残す。

Review Packetの件数はConfigで設定し、初期Fixtureでは50以下、Manual Runでは運用テストで調整する。

## A7.13 Data Acquisition Backlog

Required Sourceごとに集約する。

```text
source_key
affected_cluster_count
representative_seed_ids
required_fields
minimum_history
point_in_time_requirement
acquisition_question
```

「Dataがない」だけでなく、「何を取ればどの仮説を検証可能にできるか」を示す。

## A7.14 Artifact

```text
review/
├── strategy_idea_seed_set.json
├── exact_groups.json
├── semantic_clusters.json
├── seed_history.json
├── descriptor_archive.json
├── data_acquisition_backlog.json
├── strategy_idea_seed_review_packet.json
└── strategy_idea_seed_review_packet.md
```

## A7.15 Public CLI

```bash
uv run sis strategy-idea-seeds-review-build   --archive-root <path>   --review-policy <path>   --prior-archive <optional-path>   --out <path>
```

## A7.16 詳細タスク

| ID | タスク |
|---|---|
| A7-01 | Fragment Revalidatorを実装 |
| A7-02 | Exact Groupを実装 |
| A7-03 | Semantic Cluster Policyを実装 |
| A7-04 | Cross-run Historyを実装 |
| A7-05 | Descriptor Archiveを実装 |
| A7-06 | Review Bucketを実装 |
| A7-07 | Representative Policyを実装 |
| A7-08 | Deterministic Round-robinを実装 |
| A7-09 | Data Acquisition Backlogを実装 |
| A7-10 | JSON/Markdown Rendererを実装 |
| A7-11 | CLIを追加 |
| A7-12 | Overmerge/Undermerge/Diversity Testを追加 |

## A7.17 Test方針

- Exact Duplicateを一Groupへまとめる。
- Threshold Variantを同Cluster候補へ置く。
- 異なるMechanismを誤Mergeしない。
- Technical/ML/LLMの同仮説を同Clusterにし、Provenanceを残す。
- 同一Run再実行をRecurrentと誤認しない。
- BucketごとのRound-robinが一Family独占を防ぐ。
- Review外SeedがArchiveに残る。
- Data BacklogがMissing Sourceを正しく集約。
- Policy Version変更でManifest Hashが変わる。
- Seed入力順序変更でReview結果が不変。

## A7.18 完了条件

### `IMPLEMENTATION_COMPLETE`

- 全Laneを一つのArchive/Reviewへ統合できる。
- Exact/Semantic/Provenanceを分離できる。
- Cross-run Historyが動作。
- Review BucketとDiversity Selectionが決定論的。
- Raw Seed/Attemptを失わない。
- Data Backlogを生成できる。
- 単一利益Scoreが存在しない。

### `CURRENT_DATA_OPERATIONAL`

- 現在のTechnical/ML/LLM ArchiveからReviewを生成。
- 0件Bucketも正しく表示。
- Review件数とArchive件数の差を説明できる。
- Human ReviewerがSeed、根拠範囲、Known Gap、必要Sourceを追える。

## A7.19 停止・再設計条件

- 自然言語文字列差分だけでNovelty判定する。
- 異なるMechanismをOver-mergeする。
- Review外Seedを削除する。
- 利益らしさScoreで一列順位付けする。
- 一つのLane/FamilyがReviewを独占する。
- Data Requiredが具体的Source要件を持たない。

## A7.20 Gate G6

```text
CONTINUE_A8
REVISE_A7
HOLD_RELEASE
```

Human Reviewで「同じSeedの言い換えが多い」「必要情報が追えない」場合はA8へ進まない。
