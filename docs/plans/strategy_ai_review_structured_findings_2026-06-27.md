<!--
作成日: 2026-06-27_18:09 JST
更新日: 2026-06-27_18:18 JST
-->

# Strategy AI Review Structured Findings Plan

## チェックポイントID

PR-AI-LOOP-01

## 目的

`strategy-ai-review-note-record` で記録した AI review note を、人間レビュー用の structured findings artifact に変換・記録できるようにする。

目的は、AI回答の自由文を downstream automation に接続することではない。人間が次に確認すべき source artifact、boundary risk、context gap、overclaim risk を読みやすい構造にすることである。

## 現状

実装済み:

- `strategy-ai-review-packet-build` は `strategy_case_lite.v1` の allowlist から `context_sections` を作る。
- `strategy-ai-review-note-record` は provider、model、prompt hash、input hash、limitations、findings、recommendation を記録する。
- AI review note は `auto_applied=false`、`permission_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false` を維持する。

未実装:

- note の `findings: list[str]` を typed finding として分類する artifact。
- finding ごとの severity、review impact、typed evidence refs、recommended next action。
- structured finding schema / CLI / tests / docs。

## 制約

- 外部AI API呼び出しは実装しない。
- 自動プロンプト実行は実装しない。
- 自動修正は実装しない。
- Strategy Authoring YAML を編集しない。
- operator decision / stage decision / paper permission / live permission に接続しない。
- `strategy_ai_review_note.v1` は壊さない。
- source artifact full payload は読まない・コピーしない。
- structured finding の evidence ref は typed object とし、packet summary / context section / note finding index への参照だけにする。
- secret / credential / wallet / signing / exchange write 系の情報を新 artifact に入れない。
- 新依存は追加しない。
- `model_reasoning_effort` は PR-AI-LOOP-01 の必須前提にしない。現行 main の `strategy_ai_review_note.v1` に無い前提で扱い、PR-AI-LOOP-01 では note schema を追加拡張しない。別ブランチや将来版 note に optional metadata として存在する場合だけ、互換的に copy してよい。

## 対象ファイル

- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `schemas/strategy_ai_review_structured_findings.v1.schema.json`
- `tests/strategy_ai_review/test_strategy_ai_review_structured_findings.py`
- `tests/strategy_ai_review/test_strategy_ai_review_cli.py`
- `docs/strategy_ai_review/README.md`

## 実装方針

既存 `strategy_ai_review_note.v1` を変更せず、companion artifact として `strategy_ai_review_structured_findings.v1` を追加する。

新CLIは次の名前にする。

```bash
uv run sis strategy-ai-review-findings-structure \
  --note data/strategy_ai_reviews/<strategy-id>/strategy_ai_review_note.json \
  --structured-finding-json docs/tmp/ai_structured_findings_input.json
```

このCLIは、AI回答を生成しない。既存 note を読み、JSON で渡された structured findings を schema-valid artifact として保存するだけにする。1件だけを CLI option で作る補助導線は将来追加してよいが、主導線は `--structured-finding-json` とする。

入力 JSON 例:

```json
[
  {
    "finding_type": "SOURCE_ARTIFACT_REVIEW",
    "severity": "MEDIUM",
    "review_impact": "HUMAN_REVIEW_REQUIRED",
    "statement": "Inspect the referenced strategy_case_lite.v1 source artifact.",
    "evidence_refs": [
      {"ref_type": "note_finding", "index": 0},
      {"ref_type": "packet_context_entry", "index": 0, "entry_key": "open_actions"}
    ],
    "recommended_next_action": "INSPECT_SOURCE_ARTIFACT",
    "limitations": ["AI did not inspect raw market data."]
  }
]
```

## Artifact

出力ファイル:

- `strategy_ai_review_structured_findings.json`
- `strategy_ai_review_structured_findings.md`

schema version:

```text
strategy_ai_review_structured_findings.v1
```

## Schema案

top-level:

```text
schema_version
finding_set_id
recorded_at
producer
finding_set_status
source_note
source_packet
findings
auto_applied=false
permission_allowed=false
paper_execution_allowed=false
live_allowed=false
boundary
```

`source_note`:

```text
path
sha256
input_hash
prompt_hash
provider
model
recommendation
```

`source_note.path` は structured findings の入力に使った note artifact path を指す。raw source artifact path ではない。

`source_packet`:

```text
path
sha256
ai_input_hash
```

`finding`:

```text
finding_id
finding_type
severity
review_impact
statement
evidence_refs
recommended_next_action
limitations
```

## Enum案

`finding_type`:

- `SOURCE_ARTIFACT_REVIEW`
- `OPEN_ACTION_REVIEW`
- `CONTEXT_INSUFFICIENT`
- `SAFETY_BOUNDARY`
- `OVERCLAIM_RISK`
- `OTHER`

`severity`:

- `INFO`
- `LOW`
- `MEDIUM`
- `HIGH`

`review_impact`:

- `INFORMATION_ONLY`
- `HUMAN_REVIEW_REQUIRED`
- `BLOCKING_CONTEXT_GAP`

`recommended_next_action`:

- `INSPECT_SOURCE_ARTIFACT`
- `INSPECT_DRIFT_EVIDENCE`
- `ADD_ALLOWLISTED_CONTEXT`
- `RECORD_HUMAN_REVIEW`
- `NO_ACTION`

## Evidence Ref 方針

`evidence_refs` は string pattern ではなく typed object にする。

```text
ref_type
index
entry_key
```

`ref_type`:

- `note_finding`
- `note_limitation`
- `packet_source_summary`
- `packet_context_section`
- `packet_context_entry`

validation rule:

```text
note_finding:
  index < len(note.findings)
  entry_key must be None

note_limitation:
  index < len(note.limitations)
  entry_key must be None

packet_source_summary:
  index < len(packet.source_summaries)
  entry_key must be None

packet_context_section:
  index < len(packet.context_sections)
  entry_key must be None

packet_context_entry:
  index < len(packet.context_sections)
  entry_key in packet.context_sections[index].entries
```

禁止する参照:

- raw source artifact path の内部 field
- absolute path
- URL
- hidden path segment
- `..`
- secret / credential / wallet / signing / exchange write 系 path
- arbitrary JSON pointer

## Source Lineage Validation

structured findings 作成時に必ず検査する。

```text
1. note file exists
2. note sha256 を計算する
3. note.source_packet.path の packet file exists
4. packet sha256 が note.source_packet.sha256 と一致する
5. note.input_hash == packet.ai_input_hash
6. output source_note.input_hash == note.input_hash
7. output source_packet.ai_input_hash == packet.ai_input_hash
```

この検査に失敗した場合、success artifact は作らない。

## 実装手順

1. `schemas/strategy_ai_review_structured_findings.v1.schema.json` を追加する。
2. `models.py` に structured findings 用 Pydantic models / enums を追加する。
3. service に `record_structured_findings(...)` を追加する。
4. rendering に JSON companion Markdown renderer を追加する。
5. command に `strategy-ai-review-findings-structure` を追加する。
6. `--structured-finding-json` 入力 parser と validation を追加する。
7. tests に dogfood note fixture から structured findings を作る path を追加する。
8. README に structured findings の境界とコマンド例を追記する。

## テスト方針

- `uv run pytest tests/strategy_ai_review -q`
- `uv run sis strategy-ai-review-findings-structure --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- 変更後に必要なら `./scripts/check`

最小テスト:

- existing note から structured findings artifact を作れる。
- schema validation が通る。
- `model_reasoning_effort` が無くても structured findings artifact を作れる。
- `source_note` は未知 field を必須要求しない。
- `finding_set_status=RECORDED` が保存される。
- `auto_applied=false`、`permission_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false`。
- typed `evidence_refs` が note / packet の実在要素だけを参照できる。
- arbitrary JSON pointer 形式や範囲外 index は fail。
- note hash / packet hash / input hash lineage mismatch は fail。
- raw source payload を出力しない。
- `finding_id` 未指定なら `finding-001`、`finding-002` のように自動採番される。

## 完了条件

- structured findings artifact が note と packet の hash lineage を持つ。
- finding が typed enum / severity / review impact / evidence refs / recommended action を持つ。
- 既存 `strategy_ai_review_note.v1` 互換を壊さない。
- CLI help、schema validation、focused tests が通る。
- external AI API、自動修正、paper/live permission が追加されない。

## 失敗条件

- AI回答を自動生成する。
- AI finding を operator decision として扱う。
- finding recommendation を paper/live permission へ接続する。
- Strategy Authoring YAML を編集する。
- source artifact full payload を structured findings にコピーする。
- evidence ref が arbitrary path / arbitrary JSON pointer になる。
- `recommended_next_action` に `REVISE` のような判断語を入れる。

## 影響範囲

Strategy AI Review の note 後段だけ。packet build、note record、Strategy Case Lite、Daily Brief、Workbench Viewer への表示連携はこの PR では変更しない。

## ロールバック方針

`strategy_ai_review_structured_findings.v1` schema、models/service/rendering/command/tests/docs の追加分を戻す。既存 packet / note artifact には migration 不要。

## 代替案

- 既存 `strategy_ai_review_note.v1` の `findings` を object array に変える案: 既存 note 互換を壊すため採用しない。
- structured finding を packet に入れる案: AI input と AI output が混ざるため採用しない。
- AI回答から自動分類する案: 外部AI/API/自動実行の境界に踏み込むためこの PR では採用しない。

## 未解決事項

なし。実装時の固定方針は次の通り。

- `evidence_refs` は typed object にする。
- `finding_id` は未指定なら自動採番する。
- `recommended_next_action` に `REVISE` は入れない。
- `model_reasoning_effort` は PR-AI-LOOP-01 の必須要件から外す。別ブランチや将来版 note に optional metadata として存在する場合だけ copy してよい。

## 破壊的変更の有無

なし。companion artifact と CLI の追加のみ。

## ブランチ作業の要否

実装時は専用ブランチが必要。想定ブランチ:

```text
ai/strategy-ai-review-structured-findings-YYYYMMDD-HHMM
```

## 移行手順

なし。既存 `strategy_ai_review_note.v1` はそのまま有効。

## Critique

この計画の最大リスクは、structured findings が permission artifact に見えること。対策として、artifact 名・enum・CLI・Markdown に human review input であることを明記し、permission flags を false 固定にする。もう一つのリスクは evidence ref が raw source payload の抜け道になること。対策として、typed evidence ref を note / packet の既存 summary 領域に限定し、lineage validation を必須にする。

実装時は `--structured-finding-json` を主導線にし、CLI 引数で1件ずつ作る導線は後回しでよい。複数 finding を安全に扱うには JSON input の方が再現性と reviewability が高い。
