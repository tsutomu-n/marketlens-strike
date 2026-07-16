
# コーダーへ渡す最終指示

現時点では、**PR #46がOpen・Ready for Review・Merge可能・CI成功・未マージ**です。したがって、A1実装はPR #46を人間レビュー後にマージし、更新された`main`から開始してください。

また、「これまで作ったファイルをすべて格納する」という作業は未完了です。過去生成ファイル原本21件の格納はIssue #47としてOpenです。これはA1実装を技術的にはブロックしませんが、**資料移行完了を宣言する条件**です。

以下をそのままコーダーへ渡してください。

---

# MarketLens Strike — Seed Foundry Core v1 実装指示

## 0. 目的

Strategy Idea Seed Foundry Core v1の実装を開始する。

ただし、現在の作業対象は**A1のみ**とする。

A1の目的は、現行RepoのSource形式またはそれを忠実に再現したFixtureから、次のTechnical Seedを実際に生成し、Attempt Ledger、Seed Set、Run Manifest、Markdownまで一連の処理を完成させることである。

```text
Funding Crowding
Volatility Compression / Release
```

A1では、ML、LLM、Candidate変換、Backtest、利益評価、Paper、Liveへ進まない。

---

# 1. 作業開始前に必ず行うこと

## 1.1 PR #46を先に処理する

対象：

```text
PR #46
docs: harden Seed Foundry plan integrity and archive status
```

確認事項：

```text
state: open
draft: false
mergeable: true
CI: success
merged: false
```

作業手順：

1. PR #46の差分を人間が確認する。
2. 未解決Review Threadがないことを確認する。
3. CI成功を確認する。
4. 権限と承認がある場合のみSquash Mergeする。
5. マージ権限がない場合は、Merge Readyであることを報告し、A1を開始しない。
6. PR #46マージ後の`main`で`./scripts/check`が成功することを確認する。

PR #46がマージされる前にA1を開始してはいけない。旧Checklistには、詳細計画との不一致と存在しない正本参照があったためである。

## 1.2 `main`を更新する

```bash
git switch main
git pull --ff-only
git status --short
git branch --show-current
git rev-parse HEAD
```

期待条件：

```text
current branch = main
working tree = clean
PR #46のmerge commitを含む
```

未コミット変更がある場合は上書きしない。

```bash
git diff --stat
git diff > .ai-work/pre-existing.diff
```

衝突の可能性がある場合は作業を止め、変更内容を報告する。

## 1.3 A1専用ブランチを作る

```bash
git switch -c ai/seed-foundry-a1-technical-walking-product-YYYYMMDD-HHmm
```

A1とIssue #47のArchive作業を同じブランチ・同じPRへ混ぜない。

---

# 2. 実装正本

次の順序で読むこと。

```text
資料/strategy-idea-seed-foundry-core-v1/README.md

資料/strategy-idea-seed-foundry-core-v1/
  00_overview/core_v1_engineering_execution_plan.md

資料/strategy-idea-seed-foundry-core-v1/
  A1_technical_walking_product/README.md

資料/strategy-idea-seed-foundry-core-v1/
  00_overview/core_v1_task_checklist.yaml

資料/strategy-idea-seed-foundry-core-v1/
  00_overview/core_v1_test_matrix.csv

資料/strategy-idea-seed-foundry-core-v1/
  90_reference/README.md
```

正本の役割：

```text
00_overview/core_v1_engineering_execution_plan.md
  横断設計、共通契約、依存関係、Reason Code

A1_technical_walking_product/README.md
  A1の詳細タスク、対象ファイル、テスト、完了条件

core_v1_task_checklist.yaml
  進捗とEvidenceの記録

core_v1_test_matrix.csv
  主要テストの確認
```

次は実装正本として使用しない。

```text
資料/strategy-idea-seed-foundry-core-v1/99_archive/
```

`99_archive`は旧版・却下案・過去生成物の記録であり、現行仕様ではない。

---

# 3. A1のゴール

A1完了時に、次の三点が実証されていること。

1. Seed DomainがCandidate Domainから独立して成立する。
2. Common Seed EnvelopeがTechnical固有実装へ過度に依存していない。
3. Historical Dataで表現可能な仮説と、追加データが必要な仮説を、同じSeed Setへ格納できる。

最低限、以下の形のSeedを生成する。

```text
Long Continuation
Short Continuation
Long Reversal
Short Reversal
Historical Sourceを使用するSeed
DATA_REQUIRED Seed
```

固定済みのSeed JSONを返すだけでは未達である。

Seedは以下から決定論的に生成する。

```text
Source Capability
Profit Mechanism Pack
Operator Catalog
Direction Axis
Capture Archetype Axis
Horizon Axis
Threshold Axis
Lookback Axis
Required Source Axis
```

---

# 4. 今回実装する範囲

## 4.1 実装対象

```text
Common Seed Envelope
Technical Payload
Seed Boundary
Artifact Reference
Source Probe
Source Capability
Profit Mechanism Catalog最小版
Operator Catalog最小版
Technical Axis Generator
Generation Attempt
Seed Materialization
Attempt Ledger
Run Manifest
Seed Set JSON
Markdown Renderer
Public CLI
JSON Schema
Pydantic Model
忠実なSource Fixture
Focused Test
CLI Catalog更新
```

## 4.2 明示的な対象外

```text
ML Payload詳細
ML Dataset
XGBoost
LightGBM
LLM Packet
LLM Import
Mutation
Counterfactual
Cross-lane
Cross-run Archive
Near Clustering
Candidate Materializer
Backtest
利益評価
Position Sizing
Campaign
Paper
Live
注文
Wallet
Signing
Exchange Write
```

A2以降の機能を先回りして実装しない。

---

# 5. 変更禁止範囲

次を変更しない。

```text
src/sis/strategy_idea_candidates/

schemas/strategy_idea_candidate_set.v1.schema.json
schemas/strategy_idea.v1.schema.json

src/sis/backtest/
src/sis/paper/

Live関連コード
注文関連コード
Wallet関連コード
Signing関連コード
Exchange Write関連コード
```

Seed FoundryからCandidate、Backtest、Paper、Liveへの自動出力を作らない。

---

# 6. 推奨する新規ファイル構成

```text
src/sis/strategy_idea_seeds/
├── __init__.py
│
├── common/
│   ├── __init__.py
│   ├── models.py
│   ├── boundary.py
│   ├── artifact_refs.py
│   ├── canonical_json.py
│   ├── ids.py
│   └── errors.py
│
├── source/
│   ├── __init__.py
│   ├── models.py
│   └── probe.py
│
├── technical/
│   ├── __init__.py
│   ├── models.py
│   ├── catalog.py
│   └── generator.py
│
├── storage/
│   ├── __init__.py
│   ├── attempt_writer.py
│   └── artifact_writer.py
│
├── rendering.py
└── service.py

src/sis/commands/
└── strategy_idea_seeds.py

schemas/
├── strategy_idea_seed.v1.schema.json
├── strategy_idea_seed_set.v1.schema.json
├── strategy_idea_seed_technical_payload.v1.schema.json
├── strategy_idea_seed_attempt.v1.schema.json
└── strategy_idea_seed_run_manifest.v1.schema.json

configs/strategy_idea_seeds/
├── operator_catalog_v1.yaml
└── mechanisms/
    └── crowding_volatility_release_v1.yaml

tests/strategy_idea_seeds/
tests/fixtures/strategy_idea_seeds/a1_source_root/
```

既存RepoのModule Boundaryに従い、Command WrapperへDomain Logicを置かない。

CLIは次だけを担当する。

```text
Path解決
入力読込
Service呼出し
結果表示
Exit Code変換
```

---

# 7. Common Seed Envelope

最低限、次を持たせる。

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

Common Envelopeには、次を追加しない。

```text
signal_expression
parameter_grid
model_support
backtest_metrics
profit_score
shortlist_decision
```

---

# 8. Seed Boundary

すべてのSeedについて、以下を`Literal[False]`として型・Schemaの両方で固定する。

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

いずれかが`true`であれば、Artifact生成を失敗させる。

---

# 9. Technical Payload

最低限、次を持たせる。

```text
mechanism_template_id
operator_ast
generation_axes
parameter_values
technical_exact_signature
technical_semantic_descriptor
source_capability_snapshot_ref
authoring_compatibility
```

`authoring_compatibility`はMetadataのみとする。

Strategy Authoring Codeを呼び出したり、Candidateへ自動変換したりしない。

---

# 10. Source Capability

## 10.1 状態

```text
HISTORICAL
SNAPSHOT_ONLY
FORWARD_ONLY
MISSING
INVALID
UNKNOWN
```

## 10.2 初期Source Key

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

## 10.3 利用可能性を用途別に持つ

```yaml
usable_for:
  technical_concept_generation:
  ml_historical_feature:
  llm_context:
  direct_evidence_claim:
```

重要条件：

```text
Ticker Snapshotが存在
≠
Historical Mark/Index/OIが存在
```

SnapshotをHistorical Dataとして扱わない。

不足データがある場合も、全体を失敗させず、Seedへ次のTagを付ける。

```text
DATA_REQUIRED
SOURCE_SNAPSHOT_ONLY
SOURCE_HISTORY_MISSING
FORWARD_COLLECTION_REQUIRED
```

Source Manifestと実ファイルが矛盾する場合は、`INVALID`として処理を停止する。

---

# 11. Profit Mechanism Catalog最小版

## 11.1 Funding Crowding

```text
Actor / Constraint:
Funding負担を受ける混雑Position

Observable:
Historical Funding
Price Return
Volume / Turnover
Volatility

Capture:
Continuation
Reversal
Squeeze

Direction:
Long
Short
```

## 11.2 Volatility Compression / Release

```text
Actor / Constraint:
低Volatility後に生じるPosition再構築・流動性変化

Observable:
Range Compression
Realized Volatility
Volume / Turnover
Price Breakout

Capture:
Continuation
Failed Breakout Reversal
Two-sided Expansion

Direction:
Long
Short
```

これらを因果証明済みとして扱わない。

```text
mechanism_status=HYPOTHESIZED_NOT_CAUSALLY_VERIFIED
```

に固定する。

---

# 12. AttemptとSeedを分離する

すべてのAxis組合せを`GenerationAttempt`として記録する。

以下を満たすAttemptだけをMaterialized Seedへ変換する。

```text
ASTが有効
型が有効
単位が有効
Directionがある
Horizonがある
Observable Proxyがある
Required Sourceがある
Falsification Questionがある
Boundaryがすべてfalse
```

満たさないAttemptを削除しない。

Attempt LedgerへReason Code付きで残す。

初期Reason Code：

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

利益がありそうかどうかでSeed化を判断しない。

---

# 13. 決定論とID

同一入力、同一Config、同一Codeでは、次を一致させる。

```text
seed_record_id
technical_exact_signature
technical_payload_hash
Seed Setの意味内容
```

Hashへ含めるもの：

```text
source_lane
producer_id
producer_version
mechanism_template_id
technical_payload_hash
parent_seed_ids
config_hash
source_capability_snapshot_hash
```

Hashへ含めないもの：

```text
現在時刻
絶対出力Path
PID
Host名
Markdown表示文
実行Directory名
```

Titleのみを変更してもSeed IDが変わらないこと。

AxisのYAML記述順を変えても、生成Seed集合が変わらないこと。

---

# 14. 必須Artifact

```text
<out>/
├── seed_run_manifest.json
├── source_capabilities.json
│
├── technical/
│   ├── technical_attempts.jsonl
│   └── technical_payloads.jsonl
│
└── review/
    ├── strategy_idea_seed_set.json
    └── strategy_idea_seed_set.md
```

Manifestに最低限含める。

```text
Input path/hash
Config path/hash
Producer version
Git SHA

Attempt count
Seed count
Reason count

Artifact path/hash
Boundary summary
Known gaps
Run status
```

Manifest件数とArtifact実件数が一致しなければ完了扱いにしない。

---

# 15. Public CLI

追加するCLI：

```bash
uv run sis strategy-idea-seeds-technical-build \
  --source-root <path> \
  --mechanism-pack <path> \
  --operator-catalog <path> \
  --out <path>
```

期待する標準出力：

```text
status=pass
attempt_count=<n>
seed_count=<n>
data_required_count=<n>
seed_set_path=<path>
ledger_path=<path>
manifest_path=<path>
```

Exit Code：

```text
正常完了: 0
入力不正: 2
契約違反: 2
既存出力衝突: 2
内部予期せぬ例外: 1
```

Seed 0件は契約上正常であれば`status=pass`とする。

ただし、0件理由をManifestへ記録する。

---

# 16. 必須テスト

## 16.1 Unit

```text
Boundary trueを拒否
Title変更でSeed ID不変
Axis順序変更でSeed集合不変
Invalid TypeはAttempt止まり
Invalid UnitはAttempt止まり
Direction欠落はAttempt止まり
Horizon欠落はAttempt止まり
```

## 16.2 Schema

```text
PydanticとJSON Schemaの両方で同じFixtureを検証
不正SHAを拒否
不正Payload Pathを拒否
Duplicate Seed IDを拒否
Boundary trueを拒否
```

## 16.3 Source

```text
CandleをHISTORICALとして分類
Funding RowsをHISTORICALとして分類
Ticker RowsをSNAPSHOT_ONLYとして分類
SnapshotをHistorical Mark/Index/OIとして扱わない
Missing SourceをDATA_REQUIREDへ変換
Manifestと実File矛盾をINVALIDにする
```

## 16.4 Fixture E2E

```text
Long Seedが存在
Short Seedが存在
Continuation Seedが存在
Reversal Seedが存在
Historical Source Seedが存在
DATA_REQUIRED Seedが存在
全AttemptがLedgerに存在
Candidate Artifactが生成されない
```

## 16.5 Determinism

同一Fixtureを二回実行し、次を比較する。

```text
Seed ID
Payload Hash
Technical Signature
Seed Setの正規化内容
```

## 16.6 Regression

```bash
uv run pytest tests/strategy_idea_seeds -q
uv run python scripts/check_seed_foundry_docs.py
uv run python scripts/check_cli_catalog.py
./scripts/check
```

既存Testを変更して通すのではなく、新実装が既存契約へ適合するよう修正する。

---

# 17. A1完了条件

## `IMPLEMENTATION_COMPLETE=true`

以下をすべて満たす場合のみ設定する。

```text
忠実なFixtureからTechnical Seedが生成される
Historical Source Seedが存在する
DATA_REQUIRED Seedが存在する
Long / Shortが存在する
Continuation / Reversalが存在する
全AttemptがLedgerに残る
Manifest件数とArtifact件数が一致する
同一入力でSeed IDが安定する
全Boundaryがfalse
Candidate PackageをImportしない
Candidate Artifactを生成しない
Backtest / Paper / Liveへ接続しない
CLIが動作する
Schema Testが成功する
Focused Testが成功する
./scripts/checkが成功する
```

## `CURRENT_DATA_OPERATIONAL=true`

以下も満たす場合だけ設定する。

```text
Local Source Rootを推測なしにProbeできる
Local Source Runが完走する
Source不足を正しくDATA_REQUIREDへ分類する
Source矛盾をINVALIDとして検出する
```

Fixtureだけが成功した場合：

```text
IMPLEMENTATION_COMPLETE=true
CURRENT_DATA_OPERATIONAL=false
```

と報告する。

---

# 18. 停止・再設計条件

次のいずれかが発生した場合、A2へ進まない。

```text
Common EnvelopeへTechnical専用Fieldを追加しないと成立しない
固定JSONを返すだけになっている
Mechanismが抽象的でObservableへ落ちない
DirectionまたはHorizonが曖昧
Candidate型を使わないと成立しない
Backtest型を使わないと成立しない
SnapshotをHistoricalと誤認する
AttemptとSeedを区別できない
利益Scoreを追加する
Shortlistを追加する
Candidate Artifactを生成する
Boundaryをfalseに固定できない
```

停止時は、A1の完了を宣言せず、次を報告する。

```text
停止したタスクID
発生した事実
破られる契約
合理的な修正案
修正による影響範囲
```

---

# 19. Issue #47の扱い

Issue #47は別ブランチ・別PRで処理する。

```text
Issue #47
Complete exact archive of previously generated Seed Foundry files
```

A1実装PRへ混ぜない。

推奨ブランチ：

```bash
git switch main
git pull --ff-only
git switch -c ai/seed-foundry-archive-completeness-YYYYMMDD-HHmm
```

配置先：

```text
資料/strategy-idea-seed-foundry-core-v1/
└── 99_archive/
    └── generated_files/
```

受入条件：

```text
索引記載21ファイルが原名で存在
各SHA-256が一致
SHA256SUMS.txtが存在
Checksum検証Scriptが存在
旧版・実装正本ではないと明記
ZIPを自動展開しない
現行正本を上書きしない
```

Issue #47はA1実装の技術的ブロッカーではない。

ただし、Issue #47が未完了の間は、

```text
これまで作った全ファイルをGitHubへ格納済み
```

と報告してはいけない。

---

# 20. PR方針

A1は一つの専用PRとする。

PR本文に次を記載する。

```text
目的
A1だけを実装したこと
変更ファイル
追加CLI
生成Artifact
実行したTest
IMPLEMENTATION_COMPLETE
CURRENT_DATA_OPERATIONAL
停止条件への該当有無
Known Gaps
Candidate / Backtest / Paper / Live境界
A2へ進めるか
```

自動レビューThreadを未解決のままマージしない。

CI成功だけで完了判断しない。

```text
CI成功
+
完了条件のEvidence
+
Review Thread解消
+
人間レビュー
```

をマージ条件とする。

---

# 21. 最終報告書式

A1完了時は次の形式で報告する。

```text
## 状態

IMPLEMENTATION_COMPLETE:
CURRENT_DATA_OPERATIONAL:
Gate:
  CONTINUE_A2 | REVISE_A1 | STOP_FOUNDRY_EXPANSION

## Git

branch:
commit:
PR:
base main SHA:

## 変更

新規ファイル:
変更ファイル:
変更禁止範囲の差分: なし

## 実装

生成Mechanism:
生成Direction:
生成Capture:
生成Horizon:
DATA_REQUIRED対応:

## Artifact

run_manifest:
source_capabilities:
attempt_ledger:
technical_payloads:
seed_set_json:
seed_set_markdown:

## 件数

attempt_count:
seed_count:
historical_seed_count:
data_required_seed_count:
reason_counts:

## テスト

実行コマンド:
結果:
CI:
未実行テストと理由:

## 境界

candidate_exported=false
backtest_evaluated=false
paper_execution_allowed=false
live_allowed=false
wallet_used=false
signing_used=false
exchange_write_used=false

## 未確認事項

- ...

## Known Gaps

- ...

## 次判断

A2へ進めるか:
理由:
```

目的またはA1完了条件の変更が必要になった場合だけ、変更前に確認を求めること。

それ以外の実装上の小判断は、既存コード、正本資料、テスト、Repo規約から合理的に判断して進めること。

東京時刻は2026-07-16 23:09:06 JSTです。

07月16日(木)_午後11時09分06秒.
