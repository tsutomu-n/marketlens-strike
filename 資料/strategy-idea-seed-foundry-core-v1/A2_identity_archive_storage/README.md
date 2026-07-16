<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA2部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A2 — Identity / Archive / Storage Foundation

## A2.1 ゴール定義

ML、LLM、Mutationによる大量生成を開始する前に、Seedの同一性、発見経路、Immutable Fragment、Reducer、Idempotency、Resumeを完成させる。

A2完了時には、同じ仮説が再実行または別レーンで再発見されても、Seed数を誤って水増しせず、発見経路を失わず、途中失敗から再開できる。

## A2.2 Entry Criteria

- A1が`IMPLEMENTATION_COMPLETE`。
- A1のAttempt LedgerとSeed Setが存在する。
- Technical PayloadのCanonical化対象Fieldが明示されている。
- A1の実件数と想定将来件数を記録済み。

## A2.3 対象範囲

### 実装する

- Domain Canonicalization正式版
- Seed Record ID
- Exact Signature
- Semantic Descriptor
- Provenance Signature
- Canonicalizer Protocol
- Technical Canonicalizer
- Immutable Worker Fragment
- Single Reducer
- JSON/JSONL/Parquet役割分離
- Atomic Write
- Run Key
- Idempotency
- Resume Cursor
- Failed Fragment Retry
- Archive Manifest
- 再構築可能なDuckDB Index

### 実装しない

- ML/LLM Canonicalizer本体
- 最終Cross-lane Cluster
- Embedding/Vector Search
- Full Review Packet
- Distributed Queue

## A2.4 対象ファイル

```text
src/sis/strategy_idea_seeds/identity/
  protocol.py
  technical.py
  signatures.py

src/sis/strategy_idea_seeds/storage/
  atomic.py
  models.py
  fragments.py
  parquet_writer.py
  reducer.py
  run_keys.py
  resume.py
  index.py

src/sis/strategy_idea_seeds/archive/
  models.py
  repository.py

schemas/
  strategy_idea_seed_fragment_manifest.v1.schema.json
  strategy_idea_seed_archive_manifest.v1.schema.json
  strategy_idea_seed_run_state.v1.schema.json

configs/strategy_idea_seeds/archive_policy_v1.yaml

tests/strategy_idea_seeds/identity/
tests/strategy_idea_seeds/storage/
tests/strategy_idea_seeds/archive/
```

A1のWriterはA2のStorage Serviceを使うよう変更する。A1 Artifact契約は後方互換を維持する。

## A2.5 同一性モデル

### Seed Record ID

一つの生成記録を識別する。再発見経路を残すため、同一仮説でも別Producer/Parent/Runなら別Recordになり得る。

### Exact Signature

Thresholdを含むRuleの完全な構造同一性を識別する。

### Semantic Descriptor

次の意味軸を持つ。

```text
mechanism_class
capture_archetype
path_archetype
direction
horizon_bucket
observable_set
lane_specific_structure
threshold_bins
```

これは最終Cluster IDではなく、Cluster候補を作るDescriptorである。

### Provenance Signature

```text
source_lane
producer/version
run_config_hash
source_snapshot_hashes
parent_seed_ids
payload_hash
```

同じExact RuleをTechnicalとMLが発見した場合、Exact Signatureは一致し得るが、Record IDとProvenanceは異なる。

## A2.6 Canonicalization契約

`seed-domain-canonicalization-v1`を定義する。

- Dict Keyは安定Sort。
- Listは原則順序保持。
- `parent_seed_ids`、`observable_proxies`などField定義上Setであるものだけ、正規化後Sort/Deduplicateする。
- DecimalはCanonical String。
- FloatのNaN/Infinityを拒否。
- TimestampはUTC Zへ正規化。
- PathはRepo相対POSIX。
- Display TextをExact Signatureから除外する。
- Canonicalization VersionをHash入力に含める。

`json.dumps(sort_keys=True)`を標準準拠Canonicalizationと呼ばない。

## A2.7 Storage契約

```text
archive/
├── runs/<run-id>/
│   ├── workers/<worker-id>/
│   │   ├── attempts-00000.parquet
│   │   ├── seeds-00000.parquet
│   │   └── fragment_manifest.json
│   ├── reduced/
│   │   ├── attempts.parquet
│   │   ├── seeds.parquet
│   │   ├── exact_groups.parquet
│   │   ├── reduce_manifest.json
│   │   └── seed_index.duckdb
│   └── run_state.json
└── archive_manifest.json
```

Rules:

1. Workerは自身のDirectory以外へ書かない。
2. 複数Processが同じDuckDBへ書かない。
3. Reducerは単一Process。
4. DuckDBはParquetから再生成可能。
5. Manifestは同一DirectoryのTemp Fileへ書き、`fsync`後に`os.replace`する。
6. 完了ManifestはArtifact Hashを持つ。
7. Fragmentは一度CompleteになったらImmutable。

## A2.8 Run KeyとIdempotency

Run Key入力:

```text
command_id
producer_version
canonicalization_version
normalized_config_hash
source_artifact_hashes
code_git_sha
payload_schema_versions
```

除外:

```text
absolute output path
run start timestamp
host name
PID
```

同一Run KeyでComplete Artifactがある場合は既定で再利用し、`COMPLETED_RUN_REUSED`を記録する。

## A2.9 Resume

Run State:

```yaml
run_status: PARTIAL
run_key:
config_hash:
source_hashes:
completed_fragment_ids:
failed_fragment_ids:
next_cursor:
producer_version:
```

Resume時:

1. Run Keyを再計算する。
2. Config/Source/Producerの一致を確認する。
3. Complete FragmentをSkipする。
4. Failed Fragmentだけ再実行する。
5. Reducerを再実行し、重複をSignatureで除く。
6. Clean Runと同じ意味的結果になることを検査する。

## A2.10 詳細タスク

| ID | タスク |
|---|---|
| A2-01 | Canonicalization Policyをコードと文書で固定 |
| A2-02 | Identity ProtocolとTechnical Canonicalizerを実装 |
| A2-03 | Record/Exact/Semantic/Provenanceを分離 |
| A2-04 | Fragment/Run State/Archive Schemaを追加 |
| A2-05 | Atomic Writerを実装 |
| A2-06 | Worker Fragment Writerを実装 |
| A2-07 | Single Reducerを実装 |
| A2-08 | ParquetからDuckDB Indexを再構築 |
| A2-09 | Run Key/Idempotencyを実装 |
| A2-10 | Resume Cursor/Retryを実装 |
| A2-11 | A1を新Storageへ接続 |
| A2-12 | 破損、順序、Crash、10k Record Testを追加 |

## A2.11 Test方針

- Title変更でExact Signature不変。
- AND条件順序変更でExact Signature不変。
- Threshold変更でExact Signature変化。
- Direction/Horizon変更でSemantic Descriptor変化。
- Source Lane変更でProvenance変化。
- Worker順序変更でReducer結果不変。
- 10,000 AttemptをStreaming Reduce。
- Temp File途中失敗でFinal Manifestが出ない。
- Fragment Hash不一致を拒否。
- Complete RunをReuse。
- Config/Source変更Resumeを拒否。
- Clean RunとResume Runの正規化結果が一致。
- DuckDB削除後にParquetから再構築可能。

## A2.12 完了条件

### `IMPLEMENTATION_COMPLETE`

- A1 Runを新Archiveへ移行できる。
- 同一Run再実行でSeed数を水増ししない。
- Complete/Partial/Failedを区別できる。
- Worker FragmentとSingle Reducerが動作する。
- Clean/Resumeが意味的に一致する。
- DuckDBが正本でないことをTestで証明する。

### `CURRENT_DATA_OPERATIONAL`

- Local Source RunをArchiveへ取り込める。
- 再実行がReuseまたは新Provenanceとして正しく記録される。
- Artifact件数とManifestが一致する。

## A2.13 停止・再設計条件

- Common CanonicalizerがTechnical ASTを必須とする。
- 全Recordを一つのJSONへ保存する。
- Shared DuckDB/JSONLへ複数Workerが書く。
- Reducer順序で結果が変わる。
- Absolute PathまたはTimestampでIDが変わる。
- 再実行と再発見を区別できない。

## A2.14 Gate G2

```text
CONTINUE_A3_A5
REVISE_A2
STOP_FOUNDRY_EXPANSION
```

Identity、Storage、Resumeに不整合がある状態でML/LLM大量生成へ進まない。
