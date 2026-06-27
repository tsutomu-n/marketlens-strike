<!--
作成日: 2026-06-27_17:25 JST
更新日: 2026-06-27_17:25 JST
-->

# AI-in-the-loop Control Layer Implementation Plan 2026-06-27

## 結論

現時点で追加すべき AI-in-the-loop は、外部 LLM API を呼び出す実行機構ではない。既存の `strategy-ai-review-packet-build` / `strategy-ai-review-note-record` を土台に、AI に渡してよい安全な context packet、プロンプト契約、AI note の検証・記録・表示導線を強化する。

目的は、AI に戦略を採用させることではなく、人間が Strategy Review / Case / Candidate / Drift / Daily Brief を読む前に、見落としや過剰主張、boundary 誤読、missing artifact を発見しやすくすることである。

最初の実装単位は次の 3 PR に分ける。

```text
PR-AI-LOOP-00
  Safe AI Review Context Sections

PR-AI-LOOP-01
  Structured AI Review Findings

PR-AI-LOOP-02
  AI Review Notes into Case / Daily Brief / Workbench Viewer
```

この計画では、public network call、外部 AI API 呼び出し、自動プロンプト実行、自動修正、paper / live permission、Strategy Authoring YAML 自動編集を実装しない。

---

## 背景

現行 Repo にはすでに `strategy_ai_review` first slice がある。

- `strategy-ai-review-packet-build` は、LLM に渡してよい最小 source summary packet を作る。
- `strategy-ai-review-note-record` は、AI の回答を human review 用 note として記録する。
- packet は full source payload を入れず、source path、sha256、schema version、strategy id、status、action の summary を持つ。
- secret / credential / account detail / wallet / exchange write 系 source が見つかった場合、packet は `BLOCKED_SENSITIVE_SOURCE` になる。
- AI note は `auto_applied=false`、`permission_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false` を固定する。

現行の弱点は、AI packet が安全すぎて文脈が薄いこと。path / hash / status だけでは、AI が有益な戦略レビュー補助をしにくい。したがって、次に作るべきものは AI 実行ではなく、AI に渡してよい安全な context extraction である。

---

## 外部調査からの設計判断

### NIST AI RMF からの反映

NIST AI RMF は、AI のリスクを個人・組織・社会への影響として管理し、設計・開発・利用・評価へ trustworthiness considerations を組み込むことを目的にしている。MarketLens では、AI を意思決定者ではなく、リスク・見落とし・誤読検出の補助として扱う。

反映すること:

- AI output は permission artifact ではない。
- AI note は risk / limitation / uncertainty を必須化する。
- AI packet / note は path / hash / schema version / prompt hash / input hash を持つ。
- 評価・利用・記録を分け、AI note と human operator review を混同しない。

### OWASP LLM Top 10 からの反映

OWASP LLM Top 10 は prompt injection、sensitive information disclosure、excessive agency、overreliance などを LLM application の主要リスクとして扱う。

反映すること:

- source artifact の full payload を AI に渡さない。
- secret / credential / wallet / account / exchange write 系 source は packet block にする。
- AI output を downstream command として実行しない。
- AI note を validation / permission / approval の代替にしない。
- prompt / input / output の hash を記録する。

### OpenAI Evals / LangSmith evaluation からの反映

LLM system は、prompt / input / output / evaluator / dataset を固定しないと再現性が落ちる。MarketLens では、AI note の良し悪しをすぐ自動評価するのではなく、まず deterministic artifact contract と golden fixture で「安全に渡したか」「期待する構造で記録したか」を検査する。

反映すること:

- prompt template id / prompt hash / input hash を artifact に残す。
- AI note は finding、limitation、disagreement、recommendation を分ける。
- human review に渡す前に schema validation を通す。
- 後段で eval fixture を作るが、現段階では LLM API を呼ばない。

---

## 最終ゴール

この AI-in-the-loop layer の最終ゴールは次の状態。

```text
safe source artifacts
  ↓
strategy-ai-review-packet-build
  ↓
AI-safe context packet
  ↓
人間が外部 AI / ローカル LLM / ChatGPT 等へ手動投入
  ↓
strategy-ai-review-note-record
  ↓
structured AI review note
  ↓
Strategy Case Lite / Case Index / Daily Brief / Workbench Viewer に参考情報として表示
  ↓
人間の operator review / stage decision / revision request の補助
```

AI は次をしてよい。

- missing / invalid / blocked artifact の見落とし指摘。
- readiness proof と誤読されやすい表現の指摘。
- backtest / drift / candidate selection の過剰主張リスク指摘。
- human reviewer が次に確認すべき source artifact の提案。
- `REVISE`、`EXTEND_OBSERVATION`、`HUMAN_REVIEW_REQUIRED` などの参考 recommendation の記録。

AI は次をしてはいけない。

- Strategy Authoring YAML を編集する。
- Strategy Idea Candidate を shortlist / reject へ変更する。
- operator_review.yaml を代筆して承認する。
- paper / live / micro live / next scale を許可する。
- exchange write / wallet / signing / credentialed API を呼ぶ。
- source artifact の full payload や raw market data を無制限に読む。

---

## 用語

| 用語 | 固定する意味 | 使ってはいけない意味 |
|---|---|---|
| AI Review Packet | AI に渡してよい source summary と context section の artifact | full source dump |
| AI Context Section | 既知 schema から抽出した短い安全文脈 | raw artifact 本文 |
| AI Review Note | AI の回答を人間レビュー用に記録した artifact | 採用判断、paper / live permission |
| Structured Finding | AI note 内の source_refs 付き指摘 | 自動修正命令 |
| Prompt Card | prompt template、目的、禁止事項、hash 対象を定義する artifact | 任意の自由プロンプト |
| AI Recommendation | 人間が読む参考分類 | operator decision |
| AI Input Hash | AI に渡した summary payload の hash | source artifact hash の代替 |

---

## 制約

### 絶対制約

- `paper_execution_allowed=false`。
- `live_allowed=false`。
- `permission_allowed=false`。
- `auto_applied=false`。
- AI note は human review input であり、operator decision ではない。
- 外部 LLM API を呼ばない。
- 新依存を追加しない。
- Strategy Authoring YAML を自動編集しない。
- source artifact をコピーしない。
- hidden mutable state を持たない。

### path / source 制約

- repo-relative POSIX path のみ許可する。
- absolute path、`..`、backslash、URL scheme、hidden segment、secret path segment は拒否する。
- full source payload は packet に入れない。
- context excerpt は既知 schema の allowlist extractor からだけ作る。
- unknown schema は source summary のみで context section を作らない。

### LLM 依存制約

- 既定は manual mode。
- AI packet を作り、人間が任意の AI に渡し、結果を `strategy-ai-review-note-record` で記録する。
- API 呼び出し、tool call、agent execution、automatic rerun は別計画まで禁止。

---

## 実装方針

## PR-AI-LOOP-00: Safe AI Review Context Sections

### 目的

既存 `strategy-ai-review-packet-build` に、AI に渡してよい短い context sections を追加する。

現在の `source_summaries` は維持する。新規に `context_sections` を optional field として追加する。既存 packet を壊さないため、schema version は `strategy_ai_review_packet.v1` のまま、後方互換の optional field とする。

### 対象ファイル

```text
src/sis/strategy_ai_review/models.py
src/sis/strategy_ai_review/service.py
src/sis/strategy_ai_review/rendering.py
src/sis/strategy_ai_review/context_extractors.py        # 新規
src/sis/strategy_ai_review/redaction.py                 # 新規
src/sis/strategy_ai_review/prompt_templates.py          # 新規、必要なら
schemas/strategy_ai_review_packet.v1.schema.json
tests/strategy_ai_review/test_ai_review_context_extractors.py
tests/strategy_ai_review/test_ai_review_packet_context_sections.py
tests/strategy_ai_review/test_ai_review_sensitive_context_redaction.py
docs/strategy_ai_review/AI_REVIEW_QUESTION_TEMPLATES.md # 新規
```

### モデル追加

`src/sis/strategy_ai_review/models.py` に追加する。

```python
class AIReviewContextSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    title: str
    source_path: str
    source_sha256: str
    source_schema_version: str | None = None
    excerpt: str
    excerpt_sha256: str
    char_count: int = Field(ge=0)
    redaction_count: int = Field(ge=0, default=0)
    limitation: str | None = None
```

`StrategyAIReviewPacket` に追加する。

```python
context_sections: list[AIReviewContextSection] = Field(default_factory=list)
context_section_count: int = Field(ge=0, default=0)
```

validator:

```text
context_section_count == len(context_sections)
packet_status=BLOCKED_SENSITIVE_SOURCE の場合 context_sections は空または redacted-only にする
ai_input_hash は source_summaries + context_sections + review_questions から作る
```

### `context_extractors.py`

責務:

```text
既知 schema の artifact payload から、AI に渡せる短い summary excerpt を作る。
```

関数案:

```python
def context_sections_for_source(path: Path, payload: dict[str, Any]) -> list[AIReviewContextSection]: ...
```

初期対応 schema:

```text
strategy_review_manifest.v1
operator_strategy_review.v1
strategy_idea_candidate_set.v1
strategy_idea_candidate_export_manifest.v1
strategy_case_lite.v1
strategy_case_index.v1
strategy_daily_brief.v1
paper_vs_backtest_drift_review.v1
crypto_perp_tournament_report.v1
crypto_perp_tournament_gate.v1
crypto_perp_truth_cycle_status.v1
strategy_workbench_viewer.v1
```

各 extractor は次だけを出す。

- status / decision / recommendation。
- missing / invalid / blocked count。
- candidate count / shortlist count / rejected count。
- known gaps。
- first open action。
- first blocked reason。
- no-fill / blocked / spread / drift summary。
- readiness proof ではない旨。

出してはいけないもの。

- raw market rows。
- credential / account / wallet / address details。
- full Markdown。
- raw source artifact 全体。
- 注文 payload。

### `redaction.py`

責務:

```text
AI context excerpt に入れる文字列から、secret / credential / account / wallet / key / token / signature 系の値を除去する。
```

初期実装:

```text
- key 名に secret / credential / private_key / api_key / token / signature / wallet / account / address / client_oid / order_id が含まれる場合は value を [REDACTED] にする。
- 64文字以上の hex/base64 風 token は [REDACTED_LONG_TOKEN] にする。
- excerpt section は 2,000 chars 上限。
- packet 全体の context excerpt 合計は 12,000 chars 上限。
- redaction_count を残す。
```

### `service.py` 変更

現行 `build_ai_review_packet` の流れを次に変える。

```text
1. source path を読む。
2. missing source は既存どおり fail。
3. sensitive source を検出。
4. sensitive_count > 0 なら packet_status=BLOCKED_SENSITIVE_SOURCE。
5. sensitive_count == 0 の場合のみ context_extractors を呼ぶ。
6. source_summaries + context_sections + review_questions で ai_input_hash を作る。
7. packet JSON / Markdown を出す。
```

`--with-context/--no-context` option は追加してよい。既定は `--with-context` とする。ただし、互換性が心配なら既定 `--no-context` にして docs で opt-in とする。推奨は `--with-context`。理由は、この PR の目的が context 追加だから。

### `rendering.py` 変更

packet Markdown に次を追加する。

```text
## Context Sections

| section_id | source | schema | chars | redactions | limitation |

各 excerpt を折りたたみ風の Markdown section として表示。
```

固定文:

```text
This packet is AI review input only. It is not an approval, permission, strategy recommendation, paper execution proof, live readiness proof, or auto-apply instruction.
```

### docs追加

`docs/strategy_ai_review/AI_REVIEW_QUESTION_TEMPLATES.md`

初期質問:

```text
Q1. この packet で人間が最初に確認すべき未解決事項は何か。
Q2. readiness proof と誤読されやすい箇所は何か。
Q3. missing / invalid / blocked artifact のうち、次に直すべきものは何か。
Q4. candidate selection / backtest / drift review に過剰主張があるか。
Q5. paper / live permission と誤読される文言があるか。
Q6. 次に進むより、前段に戻るべき箇所はあるか。
```

### テスト方針

```bash
uv run pytest tests/strategy_ai_review -q
uv run sis strategy-ai-review-packet-build --help
uv run sis strategy-ai-review-note-record --help
uv run python scripts/check_current_docs.py
git diff --check
```

追加テスト:

```text
test_context_sections_for_strategy_review_manifest
  strategy_review_manifest.v1 から review_status / source_safety / missing count が excerpt に入る。

test_context_sections_for_candidate_set
  candidate count / shortlisted / rejected / selection_adjusted_metrics_status / known gaps が excerpt に入る。

test_sensitive_source_blocks_context
  secret / credential / wallet / exchange write source は BLOCKED_SENSITIVE_SOURCE になり context_sections を出さない。

test_context_hash_changes_when_excerpt_changes
  excerpt が変われば ai_input_hash が変わる。

test_packet_permissions_false
  paper_execution_allowed=false / live_allowed=false / permission_allowed=false を維持する。
```

### 完了条件

- `StrategyAIReviewPacket` が `context_sections` を持てる。
- 既存 packet without context fixture が壊れない。
- context excerpt は known schema allowlist からだけ作られる。
- sensitive source は `BLOCKED_SENSITIVE_SOURCE`。
- `ai_input_hash` が context を含む。
- Markdown report に context section と limitation が出る。
- 外部 AI API を呼ばない。
- new dependency なし。
- `./scripts/check` が通る、または失敗理由と未検証範囲を PR に明記する。

### Stop conditions

- source full payload を packet に入れないと成立しない。
- secret redaction が不十分。
- AI output を自動実行したくなる。
- context section が 12,000 chars を超える。
- prompt / input hash なしで note を記録する必要が出る。

---

## PR-AI-LOOP-01: Structured AI Review Findings

### 目的

AI note を文字列 list だけでなく、source_refs / category / severity 付きの structured findings として記録できるようにする。

### 対象ファイル

```text
src/sis/strategy_ai_review/models.py
src/sis/strategy_ai_review/service.py
src/sis/strategy_ai_review/rendering.py
schemas/strategy_ai_review_note.v1.schema.json
tests/strategy_ai_review/test_ai_review_note_structured_findings.py
```

### モデル追加

```python
class AIReviewFindingCategory(StrEnum):
    MISSING_ARTIFACT = "missing_artifact"
    BOUNDARY_RISK = "boundary_risk"
    OVERCLAIM_RISK = "overclaim_risk"
    DATA_QUALITY = "data_quality"
    BACKTEST_RISK = "backtest_risk"
    CANDIDATE_SELECTION_RISK = "candidate_selection_risk"
    PAPER_DRIFT_RISK = "paper_drift_risk"
    DOCUMENTATION_GAP = "documentation_gap"

class AIReviewFindingSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class AIReviewStructuredFinding(BaseModel):
    finding_id: str
    category: AIReviewFindingCategory
    severity: AIReviewFindingSeverity
    text: str
    source_refs: list[str]
```

`StrategyAIReviewNote` に追加:

```python
structured_findings: list[AIReviewStructuredFinding] = Field(default_factory=list)
```

既存 `findings: list[str]` は互換のため維持する。

### CLI変更

最初は CLI に複雑な nested option を入れない。

方針:

- `--finding` は従来通り文字列。
- `--structured-finding-json` を optional path として追加する。
- 指定があれば JSON array を読み structured_findings に入れる。

### テスト

```text
structured finding JSON が schema-valid。
source_refs が empty の finding は invalid。
severity/category enum が固定。
recommendation は permission ではない。
auto_applied=false / permission_allowed=false を維持。
```

### 完了条件

- 既存 `strategy-ai-review-note-record --finding ...` が壊れない。
- structured findings を別 JSON から取り込める。
- Markdown note に structured findings table が出る。
- `recommendation` は operator decision ではないと固定文が出る。

---

## PR-AI-LOOP-02: AI Notes into Case / Daily Brief / Workbench Viewer

### 目的

AI note を既存の運用索引に参考情報として流す。

### 対象ファイル

```text
src/sis/strategy_case_lite/
src/sis/strategy_case_index/
src/sis/strategy_daily_brief/
src/sis/strategy_workbench_viewer/
tests/strategy_case_lite/
tests/strategy_case_index/
tests/strategy_daily_brief/
tests/strategy_workbench_viewer/
docs/strategy_ai_review/README.md
docs/strategy_workbench_viewer/README.md
```

### 追加表示

Case Lite / Index / Daily Brief / Viewer で次だけ表示する。

```text
ai_note_count
highest_ai_finding_severity
first_ai_finding
ai_recommendation
limitation_count
disagreement_count
auto_applied=false
permission_allowed=false
```

### 境界

- AI note は blocked reason ではなく review support item。
- HIGH severity finding があっても自動停止しない。ただし Daily Brief では high-priority item として表示できる。
- AI recommendation を stage decision に変換しない。

### 完了条件

- AI note artifact を `strategy-case-lite-update --artifact` で拾える。
- Case Index に AI note summary が出る。
- Daily Brief に AI follow-up item が出る。
- Workbench Viewer に AI note compact summary が出る。
- paper / live permission flag は false のまま。

---

## まだ実装しないこと

### 外部 AI API 呼び出し

理由:

- provider / model version / prompt / cost / retry / rate limit / PII handling の contract が未定。
- 現時点では manual packet → manual AI → note record で十分。

### 自動プロンプト実行

理由:

- prompt injection / data exfiltration / overreliance risk が高い。
- まず prompt card と input hash を固定する必要がある。

### AI による自動修正

理由:

- 現行設計では Strategy Learning / Revision Request / Authoring Update Handoff も `auto_applied=false`。
- AI が YAML を編集すると、人間レビュー境界が崩れる。

### AI recommendation による stage decision

理由:

- stage decision は policy / source artifact / human evidence を読む artifact。
- AI note は参考情報であり policy evidence ではない。

### RAG / vector database

理由:

- artifact path / hash / schema を正本にする設計と相性が悪い。
- まず safe extractor / context section で足りる。

### Svelte UI 連携

理由:

- 現行 static Workbench Viewer がある。
- AI context / structured findings の contract が安定してからでよい。

---

## 実装順序

```text
1. PR-AI-LOOP-00
   Safe AI Review Context Sections

2. Dogfood
   review_manifest / candidate_set / drift_review / case_lite / daily_brief を source に packet を作り、AI に手動投入して note を記録する。

3. PR-AI-LOOP-01
   Structured AI Review Findings

4. PR-AI-LOOP-02
   Case / Daily Brief / Workbench Viewer summary

5. その後に C9 bridge / Daily Cycle Runbook を再検討する。
```

---

## Dogfood 手順

```bash
uv run sis strategy-ai-review-packet-build \
  --source data/strategy_reviews/<review-id>/review_manifest.json \
  --source data/strategy_cases/<strategy-id>/strategy_case_lite.json \
  --review-question "What should a human inspect next, without treating any result as paper/live permission?" \
  --out data/strategy_ai_reviews/<strategy-id> \
  --replace-existing
```

人間が AI へ packet Markdown を渡す。

AI 回答から note を記録する。

```bash
uv run sis strategy-ai-review-note-record \
  --packet data/strategy_ai_reviews/<strategy-id>/strategy_ai_review_packet.json \
  --provider manual-chatgpt \
  --model gpt-reviewer \
  --prompt-hash sha256:<64hex> \
  --finding "Review status is incomplete; lifecycle review should be checked before paper smoke planning." \
  --limitation "AI did not inspect raw market data or source JSON payloads." \
  --recommendation HUMAN_REVIEW_REQUIRED \
  --replace-existing
```

確認すること:

- packet が full payload を含んでいない。
- context section が短く、既知 schema summary だけである。
- `ai_input_hash` が変化を反映する。
- note に limitation が入る。
- AI note が permission として表示されない。

---

## 実装者向け最小チェックリスト

```text
[ ] context_sections model を追加した。
[ ] context_extractors.py を追加した。
[ ] redaction.py を追加した。
[ ] known schema allowlist を作った。
[ ] unknown schema は source summary のみにした。
[ ] sensitive source は BLOCKED_SENSITIVE_SOURCE にした。
[ ] ai_input_hash が context_sections を含む。
[ ] packet Markdown に context section と disclaimer が出る。
[ ] tests/strategy_ai_review を追加・更新した。
[ ] docs/strategy_ai_review/AI_REVIEW_QUESTION_TEMPLATES.md を追加した。
[ ] docs/strategy_ai_review/README.md を必要最小限更新した。
[ ] current-docs と CLI catalog を確認した。
[ ] paper/live/wallet/signing/exchange write に触れていない。
```

---

## 誤謬リスクと対策

| リスク | 対策 |
|---|---|
| AI note が operator decision に見える | note Markdown に `not permission / not decision` 固定文を出す |
| AI packet が source leak になる | full payload 禁止、known extractor allowlist、redaction_count 記録 |
| prompt injection | packet は untrusted source summary として扱い、AI output を実行しない |
| AI の過剰確信 | limitations / disagreements / source_refs を必須化する |
| provider/model差分 | provider、model、prompt_hash、input_hash を必須化する |
| replay不能 | packet path/hash、input hash、prompt hash、note hash を保存する |
| surface増殖 | AI layer は `strategy_ai_review` 内に閉じ、既存 viewer / case / brief には summary だけ渡す |

---

## 最終判断

surface を増やす前に AI-in-the-loop を加える判断は正しい。ただし、実装すべきものは AI 実行ではない。

今の正しい次手は次である。

```text
PR-AI-LOOP-00: Safe AI Review Context Sections
```

これは、既存 `strategy_ai_review` を壊さず、AI に渡せる安全な context packet を作るための最小実装である。これが入ると、今後の C9 bridge、daily cycle runbook、case index、workbench viewer に AI critique を安全に組み込める。
