<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA1部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A1 — 実Source接続Technical Seed Walking Product

## A1.1 ゴール定義

現行RepoのSource Rootまたはそれを忠実に模したFixtureを入力とし、Funding CrowdingとVolatility Compression/ReleaseのTechnical Seedを生成し、Attempt Ledger、Seed Set、Run Manifest、Markdownまで一度通す。

A1完了時に証明するものは次の三点である。

1. Seed DomainがCandidate Domainから独立して成立する。
2. Common EnvelopeがTechnical固有実装に依存しすぎない。
3. 「データがある仮説」と「データ収集が必要な仮説」を同じSeed Setで表現できる。

A1はFoundry全体を完成させない。最小経路を実Seedによって検証するWalking Productである。

## A1.2 Entry Criteria

- `git status --short`と`git diff --stat`を記録済み。
- 専用Branchを作成済み。
- `uv run python -V`がPython 3.13を示す。
- `./scripts/check`が開始時点で成功する。
- 現行Bitget Source FixtureのDirectory/Manifest構造を確認済み。
- Candidate、Backtest、Paper、Liveを変更対象外として記録済み。

## A1.3 対象範囲

### 実装する

- Common Seed Envelope
- Technical Payload
- Profit Mechanism Catalog最小版
- Operator Catalog最小版
- Source Probe最小版
- Technical Axis Generator
- Generation AttemptとSeed Materializationの分離
- JSON/JSONL Artifact
- Markdown Renderer
- Public CLI 1本
- Schema、Fixture、Focused Test

### 実装しない

- ML Payload詳細
- LLM Payload詳細
- Cross-run Archive
- Near Clustering
- Candidate Materializer
- Backtestまたは利益評価
- Current Market Signal生成

## A1.4 対象ファイル

### 新規

```text
src/sis/strategy_idea_seeds/__init__.py

src/sis/strategy_idea_seeds/common/__init__.py
src/sis/strategy_idea_seeds/common/models.py
src/sis/strategy_idea_seeds/common/boundary.py
src/sis/strategy_idea_seeds/common/artifact_refs.py
src/sis/strategy_idea_seeds/common/canonical_json.py
src/sis/strategy_idea_seeds/common/ids.py
src/sis/strategy_idea_seeds/common/errors.py

src/sis/strategy_idea_seeds/source/__init__.py
src/sis/strategy_idea_seeds/source/models.py
src/sis/strategy_idea_seeds/source/probe.py

src/sis/strategy_idea_seeds/technical/__init__.py
src/sis/strategy_idea_seeds/technical/models.py
src/sis/strategy_idea_seeds/technical/catalog.py
src/sis/strategy_idea_seeds/technical/generator.py

src/sis/strategy_idea_seeds/storage/__init__.py
src/sis/strategy_idea_seeds/storage/attempt_writer.py
src/sis/strategy_idea_seeds/storage/artifact_writer.py

src/sis/strategy_idea_seeds/rendering.py
src/sis/strategy_idea_seeds/service.py
src/sis/commands/strategy_idea_seeds.py

schemas/strategy_idea_seed.v1.schema.json
schemas/strategy_idea_seed_set.v1.schema.json
schemas/strategy_idea_seed_technical_payload.v1.schema.json
schemas/strategy_idea_seed_attempt.v1.schema.json
schemas/strategy_idea_seed_run_manifest.v1.schema.json

configs/strategy_idea_seeds/operator_catalog_v1.yaml
configs/strategy_idea_seeds/mechanisms/crowding_volatility_release_v1.yaml

tests/strategy_idea_seeds/
tests/fixtures/strategy_idea_seeds/a1_source_root/
```

### 変更

```text
src/sis/cli.py
docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md
```

### 変更禁止

```text
src/sis/strategy_idea_candidates/
schemas/strategy_idea_candidate_set.v1.schema.json
schemas/strategy_idea.v1.schema.json
src/sis/backtest/
src/sis/paper/
src/sis/crypto_perp/live*
```

## A1.5 Common Envelope契約

```yaml
schema_version: strategy_idea_seed.v1
seed_record_id:
created_at:
producer:
source_lane: TECHNICAL
status: UNVERIFIED_SEED

title:
hypothesis:

profit_intent:
  mechanism_class:
  capture_archetype:
  path_archetype:
  direction_hint:
  horizon_hint:
  affected_actor_or_constraint:
  observable_proxies:
  hypothesized_persistence:
  alternative_explanations:

required_sources:
known_gaps:
falsification_question:
next_research_question:

lineage:
  parent_seed_ids: []
  generation_depth: 0
  mutation_operators: []

payload:
  kind: TECHNICAL
  schema_version: strategy_idea_seed_technical_payload.v1
  path:
  sha256:
  record_key:

provenance_signature:
boundary:
```

Common Envelopeは`signal_expression`、`parameter_grid`、`model_support`などを持たない。

## A1.6 Technical Payload契約

Technical Payloadは次を持つ。

- `mechanism_template_id`
- `operator_ast`
- `generation_axes`
- `parameter_values`
- `technical_exact_signature`
- `technical_semantic_descriptor`
- `source_capability_snapshot_ref`
- `authoring_compatibility`

`authoring_compatibility`は将来の変換可能性を示すMetadataであり、Authoring Codeを呼び出さない。

## A1.7 Profit Mechanism Catalog最小版

初期Templateは二つに限定する。

### Funding Crowding

```text
Actor/Constraint:
  Funding負担を受ける混雑Position

Observable:
  Historical Funding
  Price Return
  Volume/Turnover
  Volatility

Capture:
  Continuation
  Reversal
  Squeeze

Direction:
  Long
  Short
```

### Volatility Compression/Release

```text
Actor/Constraint:
  低Volatility後に発生するPosition再構築と流動性変化

Observable:
  Range Compression
  Realized Volatility
  Volume/Turnover
  Price Breakout

Capture:
  Continuation
  Failed Breakout Reversal
  Two-sided Expansion
```

Mechanismの因果は証明済みとしない。`mechanism_status=HYPOTHESIZED_NOT_CAUSALLY_VERIFIED`を固定する。

## A1.8 Source Probe

Probeは値を使った利益判定をしない。存在、期間、列、Manifest、利用用途を分類する。

```text
HISTORICAL
SNAPSHOT_ONLY
FORWARD_ONLY
MISSING
INVALID
UNKNOWN
```

初期Source Key:

```text
candles_5m
funding_rows
ticker_rows
mark_index_history
open_interest_history
trade_tape_history
order_book_history
liquidation_history
```

`usable_for`を別々に記録する。

```yaml
usable_for:
  technical_concept_generation:
  ml_historical_feature:
  llm_context:
  direct_evidence_claim:
```

Ticker SnapshotがあることをHistorical Mark/Index/OIがあることとして扱わない。

## A1.9 Technical Generation手順

1. Mechanism PackをSchema検証する。
2. Operator CatalogをSchema検証する。
3. Source Capabilityを読み込む。
4. Templateを安定順序で列挙する。
5. Direction、Capture、Horizon、Threshold、Lookback、Source Requirementを安定順序で展開する。
6. 各組合せを`GenerationAttempt`として記録する。
7. AST、型、単位、Direction、Horizon、Observable、Required Sourceを検証する。
8. 最低契約を満たすAttemptだけをSeedへMaterializeする。
9. Exact Duplicate AttemptもLedgerへ残す。
10. Budget超過は`PRUNED_BUDGET`として残し、次Cursorを記録する。

初期Fixtureで最低限、次の形を通す。

- Long Continuation
- Short Continuation
- Long Reversal
- Short Reversal
- Historical Sourceを使用するSeed
- `DATA_REQUIRED` Seed

## A1.10 IDとHash

### `seed_record_id`

次をCanonicalizeしてHash化する。

```text
source_lane
producer_id/version
mechanism_template_id
technical_payload_hash
parent_seed_ids
```

現在時刻、出力Directory、Title、Markdownは含めない。

### `provenance_signature`

次を含める。

```text
producer version
config hash
source capability snapshot hash
parent ids
payload hash
```

A1では共通Semantic Cluster IDを完成させない。Technical Payload内のDescriptorだけを保存する。

## A1.11 Artifact

```text
<out>/
├── seed_run_manifest.json
├── source_capabilities.json
├── technical/
│   ├── technical_attempts.jsonl
│   └── technical_payloads.jsonl
└── review/
    ├── strategy_idea_seed_set.json
    └── strategy_idea_seed_set.md
```

Manifestは以下を持つ。

- Input path/hash
- Config path/hash
- Producer version
- Git SHA
- Attempt count
- Seed count
- Reason count
- Artifact path/hash
- Boundary summary
- Known gaps
- Run status

## A1.12 Public CLI

```bash
uv run sis strategy-idea-seeds-technical-build   --source-root <path>   --mechanism-pack <path>   --operator-catalog <path>   --out <path>
```

CLIはPath解決、Model読込、Service呼出し、Summary出力、Exit Code変換だけを担当する。

既存Repoの慣例に合わせる。

```text
成功: exit 0, status=pass
入力/契約/出力衝突: exit 2, status=fail
```

Seed 0件は正常完了である。

## A1.13 詳細タスク

| ID | タスク | 成果物 |
|---|---|---|
| A1-01 | Repo状態、初期Test、Branchを記録 | `.ai-work/state.md` |
| A1-02 | Common ModelとBoundaryを実装 | Pydantic Model |
| A1-03 | 個別Seed/Seed Set/Payload Schemaを実装 | JSON Schema |
| A1-04 | Domain Canonical JSONとID生成を実装 | `canonical_json.py`, `ids.py` |
| A1-05 | Source ProbeとCapability Modelを実装 | `source_capabilities.json` |
| A1-06 | 最小Operator/Mechanism Configを実装 | YAML |
| A1-07 | Axis GeneratorとAttempt Modelを実装 | Attempt JSONL |
| A1-08 | Seed Materializerを実装 | Seed Set |
| A1-09 | Artifact WriterとRendererを実装 | JSON/Markdown |
| A1-10 | CLIを登録 | Public CLI |
| A1-11 | Fixture、Schema、Property、CLI Testを追加 | Pytest |
| A1-12 | CLI Catalogを更新し`./scripts/check`を実行 | Verification記録 |

## A1.14 Test方針

### Unit

- Canonical Objectから安定IDが生成される。
- BoundaryにTrueを入れると拒否する。
- Direction/Horizon/Observable/Required Source欠落をAttempt止まりにする。
- Invalid Unit/TypeをSeed化しない。
- Title変更でSeed IDが変わらない。
- Axis入力順序を変えてもSeed集合が変わらない。

### Schema

- Individual SeedとSeed SetをJSON Schema/Pydantic両方で検証する。
- Payload SHA不正、Path不正、Duplicate IDを拒否する。

### Fixture E2E

- Historical Funding SeedとData Required Seedが同時に出る。
- Ticker SnapshotをHistorical Featureとして表示しない。
- Candidate Artifactが生成されない。

### Regression

```bash
uv run pytest tests/strategy_idea_seeds -q
uv run python scripts/check_cli_catalog.py
./scripts/check
```

## A1.15 完了条件

### `IMPLEMENTATION_COMPLETE`

- 忠実なFixtureからSeedを生成する。
- Attempt数、Seed数、Reason数がManifestと一致する。
- 同一入力でSeed IDと意味的Payloadが一致する。
- Boundaryが全件False。
- Candidate PackageをImportしない。
- CLI、Schema、Focused Test、`./scripts/check`が成功する。

### `CURRENT_DATA_OPERATIONAL`

- Local Source RootをProbeし、推測なしで完走する。
- Source不足時も`DATA_REQUIRED`または0件正常終了となる。
- Source Manifestと実Fileに矛盾があれば`INVALID`として止まる。

## A1.16 停止・再設計条件

- Common ModelへTechnical専用Fieldが増える。
- Seedがハードコード済みJSONの返却にすぎない。
- Mechanism、方向、Horizon、Observableの具体性がない。
- Candidate/Backtest型なしでは実装できない。
- Source SnapshotをHistoricalとして誤使用する。
- 利益ScoreまたはShortlistを追加しようとする。

## A1.17 Gate G1

次のいずれかを記録する。

```text
CONTINUE_A2
REVISE_A1
STOP_FOUNDRY_EXPANSION
```

`CONTINUE_A2`には、少なくとも一つのHistorical Seed、一つのData Required Seed、追跡可能なLedgerが必要である。
