<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA5部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A5 — LLM Seed Lane

## A5.1 ゴール定義

既存SeedのMutationと、新しい利益メカニズムのWild Ideationを、Manual Packet方式で任意のLLMへ依頼し、回答を安全にImportしてCommon Archiveへ追加する。

LLMは利益評価者でも実行Agentでもない。仮説の構造化生成器である。

## A5.2 Entry Criteria

- A2 Archive/Identityが完成。
- A1 Technical SeedがArchiveにある。
- Common EnvelopeとLLM Payload Referenceが定義可能。
- 外部APIを呼ばない方針が確定。

A5はA3/A4と並行可能だが、ML SeedをPacketへ含める統合確認はA4後に追加する。

## A5.3 対象範囲

### 実装する

- LLM Packet
- Mutation Mode
- Wild Mechanism Mode
- Prompt Hash
- Response Schema
- Raw Response保存
- Semantic Validator
- Grounding Claim
- Unknown Operator
- Data Required
- Lineage
- Duplicate/Near Duplicate判定
- LLM Payload/Seed
- Manual CLI
- Prompt Injection防御

### 実装しない

- Provider API
- Web Research Agent
- Tool Calling
- Command実行
- 自動再Prompt
- 自動Candidate Export
- LLM Scoreによる採用

## A5.4 対象ファイル

```text
src/sis/strategy_idea_seeds/llm/
  models.py
  packet_builder.py
  response_reader.py
  semantic_validator.py
  grounding.py
  importer.py
  seed_builder.py
  rendering.py

schemas/
  strategy_idea_seed_llm_packet.v1.schema.json
  strategy_idea_seed_llm_response.v1.schema.json
  strategy_idea_seed_llm_import_report.v1.schema.json
  strategy_idea_seed_llm_payload.v1.schema.json

configs/strategy_idea_seeds/llm/
  mutation_packet_v1.yaml
  wild_mechanism_packet_v1.yaml

tests/strategy_idea_seeds/llm/
tests/fixtures/strategy_idea_seeds/llm/
```

## A5.5 二つのMode

### MUTATION

入力:

- Parent Seed
- Parent Lineage
- Technical/ML Payload Summary
- Allowed Mutation Axes
- Existing Semantic Descriptors
- Source Capabilities
- Unknown Operator Policy

必須出力:

- Parent ID
- Mutation Axes
- 変更後Profit Intent
- Observable Proxy
- Direction/Horizon
- Required Sources
- Alternative Explanation
- Falsification Question

### WILD_MECHANISM

必須問い:

```text
誰または何が制約されるか
どの資金移転または価格歪みを狙うか
何を観測するか
どの価格経路を予想するか
なぜ直ちに裁定されない可能性があるか
ContinuationとReversalの代替は何か
何のデータがあれば反証できるか
```

LLMがMechanismを説明できない場合も`SPECULATIVE_MECHANISM`として残せるが、Observable、Direction、Horizon、Required Sourceがない場合はAttempt止まりとする。

## A5.6 Packet契約

Packetには次を含める。

- Packet ID/Schema
- Prompt Hash
- Mode
- Seed Archive Snapshot Ref
- Parent Seeds
- Mechanism Catalog
- Operator Catalog
- Source Capability
- Existing Cluster Descriptors
- Prohibited Claims/Actions
- Required Response Schema
- External Grounding Blocks

外部文書の本文は`UNTRUSTED_REFERENCE_DATA`として区切り、指示として扱わない。

## A5.7 Grounding Claim

```yaml
claim_kind:
  EXTERNAL_FACT
  SOURCE_SPECIFICATION
  RESEARCH_FINDING
  USER_PRIOR
  MODEL_INFERENCE
  SPECULATION

support_status:
  SUPPORTED
  PARTIAL
  UNVERIFIED
  CONTRADICTED

source_refs:
```

SourceのないExternal Factは`UNVERIFIED`。LLM推論は`MODEL_INFERENCE`。機構仮説は`SPECULATION`。

## A5.8 Import手順

1. Packetを読込。
2. Packet SHA/Prompt Hashを確認。
3. Raw ResponseをImmutable保存。
4. JSON Syntaxを検証。
5. JSON Schemaを検証。
6. Parent IDとLineage Cycleを検証。
7. Boundary/Permission Claimを拒否。
8. OperatorをCatalog照合。
9. Unknown Operatorを`OPERATOR_REQUIRED`へ分類。
10. Required SourceをCapability照合。
11. Missing Sourceを`DATA_REQUIRED`へ分類。
12. Grounding Claimを検証。
13. 親Evidenceのコピーを削除/拒否。
14. A2 CanonicalizerでExact/Near Duplicateを確認。
15. Attempt/Seed/Import Reportを保存。
16. Common Archiveへ追加。

## A5.9 Security Boundary

拒否対象:

```text
API Key要求
Credential読込
Wallet使用
Signing
Exchange Write
Live/Paper Order
Shell Command実行
File削除
任意URL Fetch
親SeedのSupport/Lift/Engine Supportコピー
```

Response内のCodeやCommandは文字列として保存するだけで実行しない。

## A5.10 Public CLI

```bash
uv run sis strategy-idea-seeds-llm-packet-build   --mode MUTATION|WILD_MECHANISM   --archive-root <path>   --policy <path>   --out <path>
```

```bash
uv run sis strategy-idea-seeds-llm-import   --packet <path>   --response <path>   --archive-root <path>   --out <path>
```

## A5.11 詳細タスク

| ID | タスク |
|---|---|
| A5-01 | Packet/Response/Import Schemaを固定 |
| A5-02 | Packet Snapshot Builderを実装 |
| A5-03 | Mutation Modeを実装 |
| A5-04 | Wild Mechanism Modeを実装 |
| A5-05 | Raw Response Writer/Hashを実装 |
| A5-06 | Semantic Validatorを実装 |
| A5-07 | Grounding Claim Modelを実装 |
| A5-08 | Unknown Operator/Data Required処理を実装 |
| A5-09 | Evidence非継承検査を実装 |
| A5-10 | Duplicate/Lineage検査を実装 |
| A5-11 | LLM Seed Builder/Archive追加を実装 |
| A5-12 | CLI/Fixture/Hostile Testを追加 |

## A5.12 Test方針

- Prompt Hash不一致拒否。
- Schema不正拒否。
- Parent不在/Lineage Cycle拒否。
- Wallet/Command/Exchange Write Claim拒否。
- Unknown OperatorをSeedとして保持。
- Missing SourceをData Requiredとして保持。
- External FactのSourceなしをUnverifiedへ分類。
- Parent Evidenceコピーを拒否。
- 親Seedの言い換えをExact/Near Duplicateへ分類。
- Raw Responseを改変せず保存。
- Fixture Mutation/Wild ResponseをImport。

## A5.13 完了条件

### `IMPLEMENTATION_COMPLETE`

- Mutation/WildのPacketとImportがFixtureで完走。
- LLM SeedがCommon Archiveへ追加される。
- Grounding、Unknown Operator、Data Required、Lineageが保存される。
- Prompt Injection/Permission Claimを拒否する。
- 外部APIを必要としない。

### `CURRENT_DATA_OPERATIONAL`

- 現在ArchiveからManual Packetを作れる。
- 人間が取得した少なくとも一つのResponseをImportできる。
- 重複率、Schema不正率、Unknown Operator率をReportできる。

## A5.14 停止・再設計条件

- 自由文だけで構造化Responseが得られない。
- 外部事実と推論を分離できない。
- 言い換えでSeed数を水増しする。
- LLM文章の説得力を品質Scoreとして使う。
- Parent Evidenceをコピーする。
- Runtimeが外部Command/URLを実行する。

## A5.15 Gate G5

```text
CONTINUE_LLM_LANE
REDUCE_WILD_MODE
HOLD_LLM_LANE
REVISE_A5
```

Wild Modeが重複/幻覚中心なら、Mutation Modeのみ残せる。
