<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA8部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A8 — Operational Release

## A8.1 ゴール定義

A1～A7で完成した能力を、第三者がCLIとRunbookだけで再現、停止、再開、監査できる状態にし、Seed Foundry Core v1をRelease可能にする。

A8では新しい生成アルゴリズム、Mechanism、Operatorを追加しない。統合、運用、検証だけを行う。

## A8.2 Entry Criteria

- A1～A7が`IMPLEMENTATION_COMPLETE`。
- Technical/ML/LLM Fixtureが存在。
- Manual LLM Response Fixtureが存在。
- Archive/ResumeがClean Runと一致。
- Review Productが人間に読めることを確認済み。

## A8.3 対象範囲

### 実装する

- 統合Orchestrator
- Run State/Status
- Lane Skip/Pause
- Clean E2E
- Resume E2E
- Failure Isolation
- Public CLI整理
- Core CI
- ML Optional CI
- CLI Catalog
- Current Docs
- Runbook
- Artifact Guide
- Reason Code Guide
- Release Validation
- Performance/Storage Measurement

### 実装しない

- 新Mechanism
- 新Operator
- 自動LLM API
- Candidate Materializer
- Backtest/利益評価
- Data Collector
- Full MAP-Elites
- Vector DB

## A8.4 対象ファイル

```text
src/sis/strategy_idea_seeds/
  orchestrator.py
  run_status.py
  release_validation.py
  inspection.py

src/sis/commands/strategy_idea_seeds.py

schemas/
  strategy_idea_seed_orchestrator_manifest.v1.schema.json
  strategy_idea_seed_release_validation.v1.schema.json

configs/strategy_idea_seeds/core_v1_run.yaml

tests/strategy_idea_seeds/e2e/
tests/strategy_idea_seeds/release/

docs/strategy_idea_seeds/
  README.md
  ARCHITECTURE.md
  CLI.md
  ARTIFACTS.md
  REASON_CODES.md
  OPERATOR_RUNBOOK.md
  CURRENT_LIMITATIONS.md

.github/workflows/ci.yml
docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md
scripts/check_current_docs.py
docs/CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md
docs/IMPLEMENTED_SURFACES.md
```

## A8.5 Orchestrator

```bash
uv run sis strategy-idea-seeds-run   --config configs/strategy_idea_seeds/core_v1_run.yaml   --out data/strategy_idea_seeds/<run-id>
```

処理:

1. Preflight。
2. Source Capability。
3. Technical Lane。
4. ML Dataset。
5. ML DiscoverまたはData不足Skip。
6. LLM Import ArtifactがあればImport。なければPacketだけ生成。
7. Mutation/Cross-lane。
8. Reduce/Archive。
9. Review Build。
10. Release Validation。

各Laneは既存個別CLI/Serviceを呼ぶ。Orchestrator専用の別実装を作らない。

## A8.6 Run Status

```text
PLANNED
RUNNING
PARTIAL
COMPLETE
FAILED
CANCELLED
```

Lane Status:

```text
COMPLETE
SKIPPED_NOT_REQUESTED
PAUSED_DATA_INSUFFICIENT
PAUSED_DEPENDENCY_UNAVAILABLE
FAILED
```

ML Data不足またはManual LLM ResponseなしでCore Implementationを失敗扱いにしない。ただし`CURRENT_DATA_OPERATIONAL`の範囲を明記する。

## A8.7 Clean/Resume E2E

Fixture E2E:

```text
Source Fixture
  → Technical
  → ML Dataset
  → ML Synthetic Discovery
  → Manual LLM Fixture Import
  → Mutation
  → Archive
  → Review
```

Resume Test:

1. ML Trial途中で停止。
2. Partial Fragmentを保存。
3. Resume。
4. Clean Runと正規化結果を比較。

比較から除く:

```text
created_at
duration
host
pid
temporary path
```

比較する:

```text
seed ids
payload hashes
signatures
cluster membership
review selection
reason counts
boundary
```

## A8.8 CI

### Core Job

既存`./scripts/check`を維持する。ML ExtraなしでCommon/Technical/Storage/LLM/Mutation/ReviewのFixture Testを通す。

### ML Job

```bash
uv sync --dev --extra seed-ml --locked
uv run --extra seed-ml pytest tests/strategy_idea_seeds/ml -q
```

Synthetic DataとGolden Dumpだけを使用し、外部Networkを使わない。

### Concurrency

GitHub ActionsのConcurrency Groupを使い、同一Branchの古いJobをCancel可能にする。既存CIの20分Timeoutを不安定化させない。

初期運用Guardrail:

- Core Seed Test: 既存`check`全体の20分以内を維持。
- ML Focused Job: 10分以内を目標とし、20分をHard Timeout。
- Core E2E Fixture: 60秒以内を目標。
- 数値は初回Benchmark後に記録し、根拠なく固定し続けない。

## A8.9 Public CLI整理

最終Public CLI:

```text
strategy-idea-seeds-technical-build
strategy-idea-seeds-archive-reduce
strategy-idea-seeds-ml-dataset-build
strategy-idea-seeds-ml-discover
strategy-idea-seeds-llm-packet-build
strategy-idea-seeds-llm-import
strategy-idea-seeds-expand
strategy-idea-seeds-review-build
strategy-idea-seeds-run
strategy-idea-seeds-validate
strategy-idea-seeds-inspect
```

各CLIに`--help` Testを持つ。

## A8.10 Documentation

Runbookは次を説明する。

- 最小Technical Run
- ML Dataset/Discover
- LLM Manual Packet/Import
- Resume
- Review Build
- Artifactの読み順
- Data不足の扱い
- Boundary
- 0件Run
- Failed Fragment Retry
- Known Limitation

Runtime件数や一時的な結果をTracked Docsの固定正本にしない。

## A8.11 Release Validation

必須検査:

- 全Seed `UNVERIFIED_SEED`
- 全Boundary False
- Candidate Artifact 0
- Paper/Live Artifact 0
- Manifest/Ledger/Parquet件数整合
- Artifact Hash整合
- Clean/Resume意味一致
- CLI Catalog整合
- Current Docs整合
- Core CI成功
- ML CI成功
- No Network Fixture
- Known Gaps記録

## A8.12 詳細タスク

| ID | タスク |
|---|---|
| A8-01 | Orchestrator Config/Manifestを固定 |
| A8-02 | Lane Status/Skip/Pauseを実装 |
| A8-03 | OrchestratorをService再利用で実装 |
| A8-04 | Validate/Inspect CLIを実装 |
| A8-05 | Full Fixture E2Eを追加 |
| A8-06 | Resume E2Eを追加 |
| A8-07 | Failure Isolation Testを追加 |
| A8-08 | Core/ML CIを分離 |
| A8-09 | CLI Catalog/Current Docsを更新 |
| A8-10 | Runbook/Artifact/Reason Code Docsを作成 |
| A8-11 | Performance/Storage Benchmarkを記録 |
| A8-12 | Release Validatorを実行しEvidenceを保存 |

## A8.13 完了条件

### `SEED_FOUNDRY_CORE_V1_IMPLEMENTED`

- A1～A7の全能力がFixtureで完走。
- Orchestratorが既存Serviceを順に実行。
- Clean/Resumeが意味的に一致。
- Core/ML CIが成功。
- CLI/Docs/Runbookが完成。
- 全Boundary False。
- Candidate/Backtest/Paper/Liveへ接続しない。

### `SEED_FOUNDRY_CORE_V1_OPERATIONAL`

上記に加え、現在Local Sourceについて:

- Technical Laneが完走。
- ML LaneはSeed生成または`PAUSED_DATA_INSUFFICIENT`を正しく出す。
- LLM Packetを現在Archiveから生成できる。
- Manual LLM ResponseをImport可能。
- Review Packetを生成可能。
- Known GapとData Backlogを表示可能。

MLがData不足でPauseの場合、状態は次とする。

```text
SEED_FOUNDRY_CORE_V1_IMPLEMENTED_CURRENT_DATA_PARTIAL
```

これを完全Operationalと呼ばない。

## A8.14 Release停止条件

- A8で新しいGenerator/Mechanismを追加し始める。
- Core CIへML依存を混ぜる。
- Clean/ResumeでSeed Setが変わる。
- Candidate Exportが自動発生。
- BoundaryにTrueがある。
- Artifact件数が不整合。
- Runtime Data不足をFixture成功で隠す。
- RunbookなしでOperatorが再現できない。
