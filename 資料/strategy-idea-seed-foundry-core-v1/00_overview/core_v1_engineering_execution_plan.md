<!--
作成日: 2026-07-16_13:39 JST
更新日: 2026-07-16_13:39 JST
-->

# MarketLens Strike Strategy Idea Seed Foundry Core v1
# A1～A8 エンジニアリング実行計画

- 対象Repo: `tsutomu-n/marketlens-strike`
- 調査時の確認HEAD: `6a9fe3273bbd53923ffec836a31bf383631bfdbd`
- 計画種別: 実装担当SEへ渡す正本候補
- 現在スコープ: Seedの生成、記録、統合、Cluster化、人間向けReviewまで
- 明示的対象外: Candidate自動変換、Backtest、利益採否、資金管理、Paper、Live、注文、Wallet、Signing、Exchange Write
- 最終完了状態: `SEED_FOUNDRY_CORE_V1_OPERATIONAL`

## 0. 最終決定

Seed Foundry Core v1は、次の8チャンクで実装する。

```text
A1 Technical Walking Product
  ↓
A2 Identity / Archive / Storage Foundation
  ├─────────────────┐
  ↓                 ↓
A3 ML Data Truth    A5 LLM Seed Lane
  ↓                 │
A4 ML Discovery     │
  └────────┬────────┘
           ↓
A6 Mutation / Counterfactual / Cross-lane
           ↓
A7 Unified Archive / Review Product
           ↓
A8 Operational Release
```

各チャンクのゴールは「コードを追加すること」ではない。完了時に、前段にはなかった一つの運用能力が、FixtureとArtifactによって再現可能になることをゴールとする。

A1～A8で完成するのは、三つの生成レーンと共通Archiveを持つ拡張可能なCore v1である。これまで議論したすべての市場メカニズム、数学Operator、データCollector、高度探索アルゴリズムを実装する計画ではない。

初期実装対象の利益メカニズムは次に限定する。

```text
Funding Crowding
Volatility Compression / Release
```

その他のMechanismは、Catalog登録、`DATA_REQUIRED` Seed、LLM Wild Mechanismとして表現可能にするが、専用GeneratorやHistorical Collectorの完成をCore v1の条件にしない。

## 1. 事実、判断、仮定、未確認事項

### 1.1 Repoから確認済みの事実

1. 現行`strategy_idea_candidates`は各Candidateに`SHORTLISTED`または`REJECTED`を要求し、Seedのような合否なしの仮説資産とは責務が異なる。
2. 現行Candidate Generatorは固定Familyと有限Parameter Gridを列挙する。PurgeとEmbargoは現時点では実処理ではなく記録用文字列である。
3. 現行Bitget Public Sourceは5分足、Historical Funding、Ticker Snapshot、Contract情報を保存できる。
4. Historical Fundingにはイベント時刻と`available_at_ms`がある。
5. TickerのMark、Index、Open Interest、Bid/AskはSnapshot中心であり、Historical Featureとして使用できる保証はない。
6. Historical Order Book、Trade Tape、Liquidation、Measured Slippage、Deep Backfillは現行Sourceにない。
7. 現行`strategy_model_loop`はTrialを記録するArtifact面であり、XGBoostまたはLightGBMを学習するRunnerではない。
8. Core CIは`./scripts/check`を実行する。Public CLI追加時はCLI Catalogとの一致が必要である。

### 1.2 この計画で採用する設計判断

1. Seed層は`src/sis/strategy_idea_seeds/`として独立させる。
2. Common Seed Envelopeとレーン固有Payloadを別Artifactにする。
3. Seedの同一性は、Record、Exact Rule、Semantic Cluster、Provenanceへ分離する。
4. Source CapabilityはSeed生成の合否Gateではなく、どのレーンで何に使用できるかを示すRouterとする。
5. 大量Recordの正本はImmutable FragmentとParquet/JSONLに置く。DuckDBは再構築可能なQuery Indexに限定する。
6. MLは「データ真実性」と「Model/Rule発見」を別チャンクにする。
7. LLMはManual Packet方式とし、外部APIをCore v1に含めない。
8. Reviewは単一の利益らしさScoreを使わず、Descriptor Bucketと決定論的Round-robinを使う。
9. Candidate、Backtest、Paper、LiveへはCore v1から接続しない。

### 1.3 明示的な仮定

1. 初期SymbolはFixtureで2銘柄以上、Manual Smokeでは`BTCUSDT`、`ETHUSDT`、必要に応じて`SOLUSDT`を使う。
2. 初期Base Timeframeは5分足とする。
3. 初期Horizonは`1h`、`4h`、`1d`とする。`7d`は履歴長が足りる場合だけ有効化する。
4. Technical Laneは実データから利益を評価せず、Source CapabilityとMechanism Packから仮説を列挙する。
5. ML Laneの初期Historical FeatureはCandle、Historical Funding、Calendarに限定する。
6. LLM回答はJSONとして人間が保存し、Importerが検査する。

### 1.4 実装時に確認する未確認事項

1. Bitget Candleの`ts`がOpen Timeであることを、公式仕様と実Fixtureの両方で確認する。
2. Local Source Rootに存在するCandle/Funding期間、行数、欠損率を測定する。
3. Python 3.13で解決可能なXGBoost/LightGBMのWheel、Version、Tree Dump形式をProbeする。
4. Rule TrialとMutation Attemptの最大件数をFixtureおよび小規模実Runで測定する。
5. Review Packetを人間が一度に読める件数を運用テストで確認する。
6. LLM Wild Mechanismの重複率、Schema不正率、外部事実幻覚率をFixture ResponseとManual Runで測定する。

未確認事項は推測で固定しない。各チャンクのEntry Gateまたは停止条件として扱う。

## 2. Core v1共通契約

### 2.1 三層の記録

```text
Generation Attempt
  生成を試みたすべての組合せ、Model Trial、Rule、Mutation

Materialized Seed
  Seed最低契約を満たした未検証仮説

Review Representative
  Clusterを代表して人間へ表示するSeed
```

「後段でKillする」ことを理由に、壊れたAST、単位不明、方向不明、必要Source不明のAttemptをSeedへ昇格させない。これらはAttempt Ledgerに残す。

### 2.2 Seed最低契約

Materialized Seedは最低限、次を持つ。

- 安定した`seed_record_id`
- `source_lane`
- `UNVERIFIED_SEED`
- 明確なタイトルと仮説
- Profit Mechanism Class
- Capture Archetype
- Direction Hint
- Horizon Hint
- Observable Proxy
- Required Source
- Known Gap
- Falsification Question
- Lineage
- Payload Reference
- すべてFalseのBoundary

利益、勝率、Sharpe、Support、Backtest結果はSeed化の必須条件にしない。

### 2.3 Common EnvelopeはPayloadを参照する

Common EnvelopeへTechnical、ML、LLM固有Fieldを直接追加しない。

```yaml
payload:
  kind: TECHNICAL
  schema_version: strategy_idea_seed_technical_payload.v1
  path: data/...
  sha256: sha256:...
  record_key: technical-payload-...
```

レーン固有PayloadのSchemaは各Laneのチャンクで追加する。Common Envelopeの変更を最小化する。

### 2.4 Boundary

全SeedとSeed Setで次を`Literal[False]`へ固定する。

```text
backtest_evaluated
execution_evaluated
cost_evaluated
profit_claimed
auto_shortlisted
permits_candidate_export
permits_paper_candidate
paper_execution_allowed
live_allowed
wallet_used
signing_used
exchange_write_used
```

### 2.5 正本形式

| 情報 | 正本形式 |
|---|---|
| Run/Artifact/Review Manifest | JSON |
| Seed Set、Cluster Set | JSON |
| 低～中規模Event Ledger | JSONL Fragment |
| 大量Trial、Feature、Path Primitive、Raw Rule | Parquet |
| Query/Inspection Index | 再構築可能なDuckDB |
| 人間向け表示 | Markdown |

### 2.6 完了状態

各チャンクは二つの状態を別々に記録する。

```text
IMPLEMENTATION_COMPLETE
  Code、Schema、Fixture、Test、CLI、Artifact契約が完成

CURRENT_DATA_OPERATIONAL
  現在のLocal Sourceでも推測なしに実行可能
```

Fixtureだけ動く状態をCurrent Data Operationalとは呼ばない。現在データ不足をCode不完成とも呼ばない。

## 3. 外部一次情報を反映した実装判断

### 3.1 Schema

- JSON Schema Draft 2020-12の`$ref`を使い、個別Seed、Seed Set、Payload、Manifestを分割する。
- PydanticのDiscriminatorは同一Artifact内のPayload Unionにのみ使用する。Common Envelopeは外部Payload Referenceを使う。
- JSON SchemaとPydanticの両方で同じFixtureを検証する。

### 3.2 Canonicalization

RFC 8785はJSONの標準的Canonicalizationを定義するが、Pythonの`json.dumps(sort_keys=True)`だけでは完全準拠ではない。Core v1は次のDomain Canonicalizationを明示的にVersion管理する。

```text
object key: Unicode code point順
array: 原則順序保持
set-like field: Field定義に基づき正規化後Sort
datetime: UTC Z、秒精度
decimal: 指数表記を避けたCanonical String
NaN/Infinity: 拒否
path: Repo相対POSIXへ正規化
```

名称は`seed-domain-canonicalization-v1`とし、完全なRFC 8785準拠を主張しない。

### 3.3 Polars

- Parquetは`scan_parquet`を使い、Projection/Predicate Pushdownを利用する。
- FundingのPoint-in-time結合は`join_asof(strategy="backward")`を使う。
- Join前にSymbolごとにTimestampを明示Sortする。
- ToleranceはConfig必須とし、Join後に`funding_age_seconds`を保存する。
- Source TimeとDecision Timeを両方残す。

### 3.4 Atomic WriteとConcurrency

- Manifest/JSONは同一Directory内の一時Fileへ書き、flush、`fsync`、`os.replace`で公開する。
- 複数Processが同じJSONLまたはDuckDBへ書かない。
- Workerは個別Fragmentへ書き、単一Reducerが集約する。
- DuckDBはParquetから再生成可能なRead Indexとし、唯一の正本にしない。

### 3.5 ML依存

- XGBoostとLightGBMはOptional Extraへ置く。
- VersionはCP0 Probe後にLockする。
- Model本体は各Engineの正式な保存形式で保存する。
- Tree Dumpは説明・Rule抽出用であり、Model再読込用とみなさない。
- ParserはEngine VersionとParser VersionをManifestへ保存する。
- LightGBMはCPU、`deterministic=true`、明示Seed、明示Thread数、`force_col_wise`または`force_row_wise`を使う。
- 同一Locked Environment内の意味的再現性を要求する。異OS/異BuildのByte一致は要求しない。

### 3.6 LLM入力

- 外部文書、論文、Web内容、親Seedの自然言語はすべて非信頼データとして扱う。
- LLM出力からCommand、File Path操作、Network操作を実行しない。
- ResponseはJSON Schema、Prompt Hash、Semantic Validatorを通す。
- 人間承認なしにCandidate、Paper、Liveへ進めない。

### 3.7 Diversity

MAP-Elitesの考え方は「単一の最高点ではなく、異なるBehavior Descriptorごとに候補を保持する」点だけを採用する。Core v1ではFull MAP-Elitesを実装しない。

Descriptor:

```text
source_lane
mechanism_class
capture_archetype
path_archetype
direction
horizon
required_source_bundle
```

各CellからRepresentative、Challenger、必要に応じてWildcardを選ぶ。

## 4. Roadmapと依存関係

| チャンク | 新たに利用可能になる能力 | 必須前提 |
|---|---|---|
| A1 | 現行Source形式からTechnical Seedを生成しArtifact化 | Repo preflight |
| A2 | 大量生成を受ける同一性・Archive・Resume基盤 | A1 |
| A3 | LeakageなしのML DatasetとPath Label | A2、Source履歴 |
| A4 | XGBoost/LightGBMからML Seedを生成 | A3 |
| A5 | Manual LLM Packetと安全なSeed Import | A2、A1 Seed Archive |
| A6 | Evidence非継承のMutation/Counterfactual/Cross-lane Request | A4、A5 |
| A7 | 三レーン統合Archiveと人間向けReview Product | A6 |
| A8 | Orchestrator、CI、Resume E2E、Release | A7 |

A3→A4とA5はA2完了後に並行可能である。A6以降はA4とA5の両方を前提とする。

# A1～A8 チャンク文書

- [A1 Technical Walking Product](../A1_technical_walking_product/README.md)
- [A2 Identity / Archive / Storage](../A2_identity_archive_storage/README.md)
- [A3 ML Data Truth](../A3_ml_data_truth/README.md)
- [A4 ML Discovery Lane](../A4_ml_discovery_lane/README.md)
- [A5 LLM Seed Lane](../A5_llm_seed_lane/README.md)
- [A6 Mutation / Counterfactual / Cross-lane](../A6_mutation_counterfactual_cross_lane/README.md)
- [A7 Unified Archive / Review](../A7_unified_archive_review/README.md)
- [A8 Operational Release](../A8_operational_release/README.md)

# 5. チャンク横断のテスト戦略

## 5.1 Test Pyramid

```text
Model/Schema Unit
  ↓
Pure Domain Property Test
  ↓
Artifact Contract Test
  ↓
Fixture Integration
  ↓
Lane E2E
  ↓
Full Orchestrator E2E
```

Live APIをCIで呼ばない。

## 5.2 Property Test対象

- Canonicalizationの冪等性。
- 条件順序変更で同一Signature。
- Direction Flipを2回行うと元へ戻る。
- Resume結果とClean結果の意味一致。
- Long/Short Labelの対称性。
- Source追加が無関係SymbolのFeatureを変えない。
- Mutationが親Evidenceを持たない。

## 5.3 Hostile Test対象

- Future Feature。
- Same-bar Dual Barrier。
- Stale Funding。
- Corrupt Fragment。
- Hash不一致。
- Lineage Cycle。
- Prompt Injection。
- Unknown Operator。
- Boundary True。
- Shared Output Collision。
- Interrupted Atomic Write。
- Null ML Dataset。
- Cluster Over-merge。

## 5.4 Test Evidence

各PRは次を記録する。

```text
実行Command
Exit Code
Test Summary
Artifact Path
Artifact SHA
Known Gap
未実行理由
```

固定のPass件数を長期Docsへ書かない。

# 6. チャンク横断のReason Code

## Input/Source

```text
SOURCE_ROOT_MISSING
SOURCE_MANIFEST_MISSING
SOURCE_MANIFEST_INVALID
SOURCE_HASH_MISMATCH
SOURCE_SNAPSHOT_ONLY
SOURCE_FORWARD_ONLY
SOURCE_HISTORY_MISSING
TIMESTAMP_SEMANTICS_UNKNOWN
FUNDING_STALE
```

## Attempt/Seed

```text
INVALID_AST
INVALID_TYPE
INVALID_UNIT
MISSING_DIRECTION
MISSING_HORIZON
MISSING_OBSERVABLE_PROXY
MISSING_SOURCE_REQUIREMENT
DUPLICATE_EXACT_ATTEMPT
PRUNED_BUDGET
SEED_MATERIALIZED
```

## Storage

```text
FRAGMENT_HASH_MISMATCH
FRAGMENT_SCHEMA_INVALID
REDUCER_DUPLICATE_RECORD
RUN_REUSED
RESUME_CONFIG_MISMATCH
RESUME_SOURCE_MISMATCH
FAILED_FRAGMENT_RETRY
ATOMIC_WRITE_FAILED
```

## ML

```text
ML_DEPENDENCY_UNAVAILABLE
ML_DATA_INSUFFICIENT
MODEL_TRIAL_FAILED
TREE_DUMP_PARSE_FAILED
RULE_SUPPORT_ZERO
SMALL_SAMPLE
COMPLEX_RULE
IN_SAMPLE_DISCOVERY_ONLY
NULL_CONTROL_DISCOVERY
ENGINE_DISAGREEMENT
```

## LLM

```text
LLM_PROMPT_HASH_MISMATCH
LLM_RESPONSE_SCHEMA_INVALID
LLM_LINEAGE_CYCLE
LLM_PERMISSION_CLAIM
LLM_UNKNOWN_OPERATOR
LLM_DATA_REQUIRED
LLM_GROUNDING_UNVERIFIED
LLM_DUPLICATE
LLM_PARENT_EVIDENCE_COPY
```

## Review/Release

```text
CLUSTER_POLICY_UNCERTAIN
CLUSTER_OVERMERGE_GUARD
REVIEW_LIMIT_EXCEEDED
DATA_ACQUISITION_REQUIRED
BOUNDARY_VIOLATION
RELEASE_ARTIFACT_INCONSISTENT
CURRENT_DATA_PARTIAL
```

# 7. 最終受入マトリクス

| 能力 | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Technical Seed | 完成 | 保管強化 | - | - | Packet入力 | Mutation対象 | 統合 | 運用 |
| Identity/Storage | 最小 | 完成 | 使用 | 使用 | 使用 | 使用 | 使用 | Hardening |
| ML Dataset | - | - | 完成 | 使用 | - | Request対象 | 統合 | 運用 |
| ML Seed | - | - | - | 完成 | Packet入力 | Mutation対象 | 統合 | 運用 |
| LLM Seed | - | - | - | - | 完成 | Mutation対象 | 統合 | 運用 |
| Cross-lane | - | 契約基礎 | - | - | - | 完成 | 統合 | 運用 |
| Review Product | 最小Markdown | Inspector基礎 | - | - | - | - | 完成 | Release |
| Candidate接続 | 対象外 | 対象外 | 対象外 | 対象外 | 対象外 | 対象外 | 対象外 | 対象外 |

# 8. 外部一次情報と採用箇所

1. Pydantic Discriminated Unions  
   https://docs.pydantic.dev/latest/concepts/unions/  
   採用: レーン固有Model内の型安全なUnion。Common Envelopeは外部Payload Refとする。

2. JSON Schema Draft 2020-12  
   https://json-schema.org/draft/2020-12  
   採用: Schema分割、`$ref`、個別Seed/Seed Set/Payload契約。

3. RFC 8785 JSON Canonicalization Scheme  
   https://www.rfc-editor.org/rfc/rfc8785  
   採用: Canonicalizationの必要性。Core v1はDomain固有規則をVersion管理し、完全準拠を偽称しない。

4. Polars `join_asof`  
   https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.join_asof.html  
   採用: Symbol単位のBackward As-of Join、Sortedness、Tolerance。

5. Polars Lazy API / `scan_parquet`  
   https://docs.pola.rs/user-guide/lazy/using/  
   https://docs.pola.rs/api/python/stable/reference/api/polars.scan_parquet.html  
   採用: Projection/Predicate Pushdown、大量ParquetのLazy処理。

6. Python `os.replace`  
   https://docs.python.org/3/library/os.html#os.replace  
   採用: 同一Filesystem上のAtomic Publish。Temp File、flush、fsyncを併用。

7. DuckDB Concurrency  
   https://duckdb.org/docs/stable/connect/concurrency  
   採用: 複数Process共有Writerを避け、Worker Fragment＋Single Reducerとする。

8. Python Packaging Optional Dependencies  
   https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras  
   採用: XGBoost/LightGBMをOptional Extraへ分離。

9. XGBoost Python API `get_dump`  
   https://xgboost.readthedocs.io/en/stable/python/python_api.html  
   採用: Tree Dumpは解釈用。Loadable Modelを別保存。

10. LightGBM Parameters / Python API `dump_model`  
    https://lightgbm.readthedocs.io/en/latest/Parameters.html  
    https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.Booster.html  
    採用: CPU Determinism設定、Dump ParserのVersion管理。

11. scikit-learn `TimeSeriesSplit`  
    https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html  
    採用: 時系列順とGapの考え方。Core v1はさらに`label_end_at`によるCustom Purgeを行う。

12. OWASP Prompt Injection Prevention Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html  
    採用: 外部文書を非信頼データとして分離、出力検証、最小権限、Human-in-the-loop。

13. GitHub Actions Workflow Syntax / Concurrency  
    https://docs.github.com/actions/writing-workflows/workflow-syntax-for-github-actions  
    https://docs.github.com/actions/using-jobs/using-concurrency  
    採用: Core/ML Job分離、Timeout、同一Branchの古いRun Cancel。

14. MAP-Elites  
    https://arxiv.org/abs/1504.04909  
    採用: Descriptorごとの多様な候補保持という発想のみ。Core v1でFull Algorithmは実装しない。

# 9. 実装開始時の最終指示

1. A1以外を先行実装しない。
2. A1で実Seedが出なければA2へ進まない。
3. 各チャンクを一つのIssue/Branch/PRとして扱う。
4. PRは対象チャンク外のリファクタを含めない。
5. 各PRで`IMPLEMENTATION_COMPLETE`と`CURRENT_DATA_OPERATIONAL`を別々に報告する。
6. Current Data不足をFixture成功で隠さない。
7. 0 Seed、0 Rule、Data不足は正規の結果としてArtifact化する。
8. Candidate、Backtest、Paper、Liveのコードへ変更を入れない。
9. 実装中に契約変更が必要になった場合、後続チャンクを黙って先取りせず、Decision Recordを作成する。
10. A8まで完了しても、全Mechanism/全Operator/全Collectorが完成したとは報告しない。
