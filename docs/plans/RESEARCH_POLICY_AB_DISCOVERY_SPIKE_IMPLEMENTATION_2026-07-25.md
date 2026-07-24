<!--
作成日: 2026-07-25_00:52 JST
更新日: 2026-07-25_00:52 JST
-->

# Research Policy A/B Discovery Spike Implementation Plan

## Checkpoint ID

`RPAB-0`

## Status

```text
DOCUMENT_STATUS=PLAN_ONLY
IMPLEMENTATION_STARTED=false
SPIKE_OPERATIONAL=false
CORE_INTEGRATION_PERMISSION=false
ORCHESTRATOR_PERMISSION=false
PAPER_PERMISSION=false
LIVE_PERMISSION=false
ACTUAL_CASH_PERMISSION=false
```

## 結論

最初の実装は、既存Pipelineを変更しない独立Spikeとする。

```text
tools/research_spikes/research_policy_ab/
```

このSpikeは、同じFrozen Evidenceに対する次の三方式を比較する。

```text
B0: 現行Instructionの最初の一回
B1: 現行Instructionを3回実行し、Blind reviewで選ぶ
P1: 現行Instruction + Research Policy v0を3回実行し、Blind reviewで選ぶ
```

Policyの価値は`P1 > B1`でのみ主張できる。`P1 > B0`だけでは、単にSampling数が増えた効果と区別できない。

モデル実行はRepo内部から自動化しない。Spikeは、Evidence bundleとPromptをExportし、外部で実行したJSON結果をImport、検証、Blind review、Decision化する。

## 現Checkpointで答える問い

> 同一Model、同一Evidence、同等の実行条件で、Research Policy v0は単純Repeated Samplingより、Evidenceに接地し、実行可能で、主要な競合説明を区別する次実験を選べるか。

このCheckpointでは、利益戦略発見、Multi-Agent、Long-term memory、A2 Archive、Provider API自動化を検証しない。

## 実装境界

### 許可する変更

- `tools/research_spikes/research_policy_ab/**`
- このPlan
- [Alpha Strike / Research Foundry Operating Model](ALPHA_STRIKE_RESEARCH_FOUNDRY_OPERATING_MODEL_2026-07-25.md)
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`の導線追加

### 禁止する変更

- `src/**`
- `schemas/**`
- `configs/**`
- `uv.lock`
- `pyproject.toml`
- Public CLI
- Candidate Pack / Kill Report / Strategy Reviewの既存Decision logic
- Paper / live / actual cash系Surface
- Provider credential、API key、外部送信設定

既存Dependencyのみを使う。新規Dependencyが必要になった時点で、Checkpointを停止しPlanを再審査する。

## 実装構成

```text
tools/research_spikes/research_policy_ab/
├── README.md
├── __init__.py
├── canonical.py
├── models.py
├── build_packet.py
├── validate_result.py
├── build_blind_review.py
├── decide.py
├── policies/
│   └── research_policy_v0.md
├── examples/
│   └── case_manifest.example.yaml
└── tests/
    ├── __init__.py
    ├── fixtures.py
    ├── test_models.py
    ├── test_build_packet.py
    ├── test_validate_result.py
    ├── test_blind_review.py
    └── test_decide.py
```

最初からGeneric workflow engine、Database、DuckDB index、Resume、Plugin systemを作らない。

## Runtime Artifact

RuntimeはGit管理しない。

```text
data/research_spikes/research_policy_ab/<spike-id>/
├── experiment_manifest.json
├── cases/
│   └── <case-id>/
│       ├── frozen_case.json
│       ├── evidence_catalog.json
│       ├── freeze_manifest.json
│       └── evidence/
├── runs/
│   └── <run-id>/
│       ├── prompt.md
│       ├── input.json
│       ├── result_schema.json
│       ├── run_manifest.json
│       └── raw_result.json
├── normalized/
│   ├── accepted_results.jsonl
│   ├── rejected_results.jsonl
│   └── import_summary.json
├── blind_review/
│   ├── review_items.json
│   ├── review_key.json
│   ├── human_review.template.json
│   └── human_review.json
├── prospective/
│   ├── outcome.template.json
│   └── outcome.json
└── decision/
    ├── decision.json
    └── decision.md
```

## Case契約

### 最初に必要なCase

Operational completionには、最低限次を要求する。

1. **Archived diagnostic case**: 人間が後から見逃しまたは早期終了を修正したCase。
2. **Archived correct-stop case**: 深掘りせず停止するのが妥当だったCase。
3. **Current / Prospective case**: Policy freeze後に選定、または新しいEvidenceを含むCase。

3件は統計的証明用ではなく、Policyの一方向偏り、未来情報、Archived暗記を検出する工学的最小値である。

### `case_manifest.v0`

```yaml
schema_version: research_policy_ab_case.v0
case_id:
case_kind: ARCHIVED_DIAGNOSTIC | ARCHIVED_CORRECT_STOP | CURRENT_PROSPECTIVE
campaign_id:
failure_archetype:
information_cutoff_at:
research_question:
current_hypothesis:
allowed_roots:
completed_experiments:
data_catalog:
evidence:
reference:
```

`reference`はHuman evaluation用であり、Model bundleへ含めない。

### Evidence entry

```yaml
- evidence_id: EVIDENCE.DECISION
  path: data/...
  available_at: "2026-07-25T00:00:00Z"
  role: CURRENT_DECISION
```

### Data catalog entry

```yaml
- data_id: DATA.ORDER_BOOK
  status: AVAILABLE | MISSING | UNKNOWN | INACCESSIBLE
```

## Packet freeze

`build_packet.py`は、Case manifestとEvidence Artifactを検査し、Bundleを生成する。

### 必須検査

- Evidence pathが`allowed_roots`配下
- Symlink拒否
- Regular fileのみ
- File hash保存
- `available_at <= information_cutoff_at`
- `.env`、secret、credential file拒否
- Binary / Parquetの直接投入拒否
- `reference`除外
- Arm間でEvidence hash、Input hash、Output schemaが一致

### 初期Size ceiling

```text
single evidence file <= 2 MiB
case bundle total <= 8 MiB
```

これは工学的初期値であり、超過時はRaw dataを渡さず、既存Summary Artifactを使う。Ceilingを上げて解決しない。

## ArmとRun

```text
BASELINE-001
BASELINE-002
BASELINE-003
POLICY-001
POLICY-002
POLICY-003
```

`samples_per_arm=3`はSampling varianceと明白な不安定性を見る初期上限であり、統計的有意性を主張しない。

### Arm間で固定するもの

- Model / Model version
- Reasoning設定
- Evidence bundle
- Output schema
- Tool access
- Network access
- 実行Timeout
- Reviewer rubric

変更するのはResearch Policy文面の有無だけとする。

Model version、Tool、Network、EvidenceがArm間で一致しない場合は`INVALID_EXPERIMENT`とする。

## Model実行

Model実行は手動またはRepo外の既存Harnessで行う。

Modelへ見せるもの:

```text
prompt.md
input.json
result_schema.json
evidence/
```

見せないもの:

```text
reference
他Armの結果
review_key.json
human review
他Case
Repo全体
```

Run manifestには最低限次を記録する。

```yaml
provider:
model:
model_version:
model_version_verified:
invocation:
reasoning_effort:
temperature:
network_access:
tool_access:
started_at:
finished_at:
input_tokens:
output_tokens:
provider_cost_jpy:
wall_time_ms:
tool_call_count:
```

取得できない値は`null`で保存し、推測値を入れない。Cost比較不能なら最終Decisionは`INCONCLUSIVE`または定性的Pareto比較に限定する。

## Research Policy v0

Policyは短くし、既存Schemaや一般的な金融注意事項を重複記載しない。

```markdown
# Research Policy v0

1. 集計上の不採用と仮説全体の不採用を区別する。
2. 支持証拠、反証証拠、欠落Dataを分離する。
3. 条件付き生存、符号反転、裾、期間・Symbol・Side集中を確認する。
4. 未説明Residualは最大3件とする。
5. 各Residualに競合説明を最大3件置く。
6. 次実験は競合説明を最小費用で区別する一件だけを選ぶ。
7. 既実施、実行不能、取得不能Data前提の実験を提案しない。
8. DEEPEN、BRANCH、PIVOT、PARK、KILL、DEFER_DATAから一つを選ぶ。
9. 有用な次実験がなければKILLまたはPARKを選ぶ。
10. 事実、推論、仮定、未確認を分ける。
```

## Proposal契約

```yaml
schema_version: research_policy_ab_proposal.v0
run_id:
case_id:
pack_hash:
current_hypothesis:
current_verdict:
supporting_evidence_refs:
contradicting_evidence_refs:
missing_data_refs:
rejected_explanations:
unresolved_residuals:
recommended_action: DEEPEN | BRANCH | PIVOT | PARK | KILL | DEFER_DATA
next_experiment:
uncertainties:
boundary:
reviewer:
```

### 制約

- Residualは最大3件
- Competing explanationは各Residual最大3件
- Recommended actionは一つ
- Next experimentは最大一つ
- DEEPEN / BRANCH / PIVOT / DEFER_DATAならNext experiment必須
- KILL / PARKならNext experiment省略可
- DEFER_DATAなら`MISSING | UNKNOWN | INACCESSIBLE`のData ref必須
- Stop condition必須
- Estimated cost必須
- Completed experimentの同一ID再提案禁止
- Boundaryは全て`false`

Boundary:

```yaml
permits_core_integration: false
permits_candidate_promotion: false
permits_paper: false
permits_live: false
actual_cash_used: false
profit_proven: false
```

## Result import / Hard Gate

`validate_result.py`は全Attemptを保存し、成功結果だけを選別しない。

Attempt status:

```text
ERROR
TIMEOUT
INVALID_JSON
SCHEMA_REJECT
HARD_GATE_REJECT
COMPLETE
```

Retryは新Attempt IDとし、上書きしない。

Hard Gate:

- Case / Run / Pack / Policy hash一致
- Unknown Evidence ref拒否
- Unknown Data ref拒否
- Evidence hash drift拒否
- Future Evidence拒否
- Output limit検査
- Action / Next experiment整合
- Boundary false
- Model identity記録

Evidenceの意味的整合性は完全な自動判定を主張しない。参照存在はHard Gate、内容整合はBlind human reviewで扱う。

## Blind review

`build_blind_review.py`はArm、Run ID、Provider、Model、Sample番号、Policy versionを除外し、順序を固定SeedでRandomizeする。

Human rubricは各軸0-2点。

| 軸 | 0 | 1 | 2 |
|---|---|---|---|
| Evidence整合 | 根拠なし・矛盾 | 一部接地 | 主要主張が接地 |
| 実行可能性 | 実行不能 | 条件付き可能 | 現環境で実行可能 |
| 識別力 | 競合を区別しない | 一部区別 | 主要競合を区別 |
| 増分情報 | 既実施の反復 | 一部新規 | 明確な新情報 |
| 経済的重要性 | 利益判断と無関係 | 間接的 | 直接影響 |
| 費用対効果 | 過大 | 不明 | 妥当 |

Critical reject:

```text
UNSUPPORTED_EVIDENCE
FUTURE_INFORMATION
SEMANTIC_DUPLICATE_EXPERIMENT
UNAVAILABLE_DATA_TREATED_AS_AVAILABLE
BOUNDARY_VIOLATION
NON_FALSIFIABLE_EXPERIMENT
```

Arm内のBest proposalを選んだ後、B1対P1を次で評価する。

```text
LEFT_WIN
RIGHT_WIN
TIE
BOTH_REJECT
```

LLM Judgeを最終採用判定に使わない。

## Prospective outcome

Policy freeze後のCaseで、勝ったProposalの次実験を一件だけ実行し、結果を記録する。

Outcome:

```text
COMPETING_EXPLANATION_REJECTED
HYPOTHESIS_SCOPE_NARROWED
DATA_GAP_CONFIRMED
CORRECT_STOP_CONFIRMED
NO_NEW_INFORMATION
INVALID_EXECUTION
```

利益が見つからなくても、不確実性低下、正しいKill、Data gap特定、高価な実験回避は有効結果とする。

## Decision

### `PROMOTE_THIN_HARNESS`

全て満たす場合。

- P1がB1よりBlind reviewで優れる
- 改善が一つのArchived caseだけに集中しない
- Critical regressionなし
- Hard Gate違反が増えていない
- Current / Prospective caseで提案を実行できた
- 実験により判断または不確実性が変わった
- Cost差が記録され、追加費用に見合う

許可するのはThin Harnessの別Checkpoint検討だけであり、Core統合を許可しない。

### `REVISE_POLICY_ONCE`

- Archived caseにRepairあり
- RegressionまたはProspective不成立あり
- Critical regressionなし

Policy修正は一回だけ。新しい未知Caseがないまま同じCaseで再評価しない。

### `KEEP_MANUAL_BASELINE`

- B1がP1以上
- Policy差が文章量だけ
- PolicyがEvidence解釈を阻害
- Repeated Samplingで十分

### `INCONCLUSIVE`

- Cost比較不能
- Current / Prospective caseなし
- Human reviewが不安定
- Case coverageが一方向のみ

### `INVALID_EXPERIMENT`

- Policy途中変更
- 成功RunだけImport
- Arm間のInput / Model / Tool差
- Future leakage
- Hash drift
- Blind key漏洩

## TASKS

- [ ] RPAB-01: Pydantic ContractとCanonical hashを実装する。
- [ ] RPAB-02: Case manifest読込、Evidence検査、Bundle freezeを実装する。
- [ ] RPAB-03: BASELINE / POLICY各3 RunのScheduleとPromptを生成する。
- [ ] RPAB-04: Result import、Attempt ledger、Hard Gateを実装する。
- [ ] RPAB-05: Blind review packetとHuman review schemaを実装する。
- [ ] RPAB-06: Prospective outcome schemaとDecision reducerを実装する。
- [ ] RPAB-07: Synthetic CaseでFreezeからDecisionまでE2E Testを通す。
- [ ] RPAB-08: Archived diagnostic、Archived correct-stop、Current / Prospectiveの3 Caseを準備する。
- [ ] RPAB-09: External Model runを各Arm3回実行し、全AttemptをImportする。
- [ ] RPAB-10: Blind review、Prospective experiment、最終Decisionを完了する。

## Test

Focused:

```bash
uv run pytest tools/research_spikes/research_policy_ab/tests -q
```

Repository gate:

```bash
./scripts/check
```

## Implementation completion

```text
SPIKE_IMPLEMENTATION_COMPLETE=true
```

と判定できる条件:

- Synthetic E2Eが通る
- Arm間差分がPolicyだけ
- Future Evidence、Unknown Evidence、Hash driftを拒否
- Blind packetからArm情報が消える
- Error / RetryをAttempt ledgerへ残せる
- `./scripts/check`が通る
- `src/`、`schemas/`、Public CLIを変更していない

## Operational completion

```text
SPIKE_OPERATIONAL_COMPLETE=true
```

と判定できる条件:

- 必須3 Caseを実行
- 各Arm3 Run
- Blind review完了
- Current / Prospective caseの次実験を一件実行
- 最終Decisionが5状態のいずれかに到達

## Stop conditions

次のいずれかで実装を停止し、Planを再審査する。

- 新Dependencyが必要
- Provider API自動化が必要
- `src/`変更なしでは実装不能
- CaseをFreezeできない
- 同一Model / Tool条件を作れない
- Cost / Usageを一切記録できない
- Blind reviewを成立させられない
- Current / Prospective caseを確保できない
- Spike実装量が既存Portfolio Capacity Spikeを大幅に超える

## 事実・推論・仮定・未確認

### 事実

- Repoには独立Discovery Spikeとmanual LLM review export / importの前例がある。
- Research Policyの増分価値は未証明である。
- Runtime `data/`はGit管理対象外である。

### 推論

- External Model invocationを分離すると、Provider integrationより先にPolicy効果を測定できる。
- `tools/`隔離は失敗時のRollback costを下げる。
- B1対P1を比較しないとPolicy効果を主張できない。

### 仮定

- 同一Model条件で各Arm3 Runを実行できる。
- Human blind reviewが可能である。
- 少なくとも3種類のCaseを用意できる。

### 未確認

- 最初のCurrent / Prospective caseの具体的Artifact path。
- Model Token / Cost取得可否。
- Human reviewの再現性。
- Policy効果のModel間転移。
