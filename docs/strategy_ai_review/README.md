<!--
作成日: 2026-06-19_01:17 JST
更新日: 2026-07-01_23:09 JST
-->

# Strategy AI Review

## 結論

Strategy AI Review は、LLM に渡してよい最小限の source summary と allowlisted context sections を作り、AI の回答を human review 用 note として記録する first slice です。

AI は proposal / critique の補助であり、採用、paper execution、live execution、Strategy Authoring YAML 自動編集を許可しません。

完了済みの AI-in-the-loop control layer 実装計画は [../archive/2026-06-28-merged-plans/AI_IN_THE_LOOP_CONTROL_LAYER_IMPLEMENTATION_PLAN_2026-06-27.md](../archive/2026-06-28-merged-plans/AI_IN_THE_LOOP_CONTROL_LAYER_IMPLEMENTATION_PLAN_2026-06-27.md) に移動済みです。現在の利用入口はこの README、CLI help、schema、tests です。

## Commands

```bash
uv run sis strategy-ai-review-packet-build \
  --source data/strategy_cases/<strategy-id>/strategy_case_lite.json \
  --review-question "What should a human inspect next?" \
  --out data/strategy_ai_reviews/<strategy-id>

uv run sis strategy-ai-review-note-record \
  --packet data/strategy_ai_reviews/<strategy-id>/strategy_ai_review_packet.json \
  --provider openai \
  --model gpt-5.5 \
  --model-reasoning-effort xhigh \
  --prompt-hash sha256:<64hex> \
  --finding "Return drift should be reviewed by a human." \
  --limitation "AI did not inspect raw market data." \
  --recommendation REVISE

uv run sis strategy-ai-review-findings-structure \
  --note data/strategy_ai_reviews/<strategy-id>/strategy_ai_review_note.json \
  --structured-finding-json docs/tmp/ai_structured_findings_input.json
```

## Artifacts

- `strategy_ai_review_packet.json`
- `strategy_ai_review_packet.md`
- `strategy_ai_review_note.json`
- `strategy_ai_review_note.md`
- `strategy_ai_review_structured_findings.json`
- `strategy_ai_review_structured_findings.md`

Packet は full source payload を入れません。source path、sha256、schema_version、strategy_id、status、action の summary と、known schema allowlist から作る `context_sections` だけを含めます。

新規生成 packet は `context_sections` を出します。ただし `strategy_ai_review_packet.v1` schema では、古い v1 artifact の再検証互換のため `context_sections` は required ではありません。欠けている場合は空の allowlisted context と同じ扱いで読みます。

現時点の `context_sections` allowlist は `strategy_case_lite.v1` の summary section だけです。含める値は次に限定します。

- strategy_id
- case_id
- updated_at
- artifact_count
- timeline_count
- latest_status
- open_actions
- blocked_reasons

`source_artifacts`、`timeline`、`latest_source_hashes`、unknown schema の任意 payload は `context_sections` に入れません。

secret / credential / account detail / wallet / exchange write 系の source が見つかった場合、packet は `BLOCKED_SENSITIVE_SOURCE` になり、AI に渡す ready state にはしません。

Note は次を必須にします。

- provider
- model
- prompt / review 時の reasoning effort は、使った場合のみ `model_reasoning_effort` に記録する
- prompt hash
- input hash
- limitations
- findings
- recommendation
- disagreements
- `auto_applied=false`
- `permission_allowed=false`

`model` には `gpt-5.5` のような model id を入れ、`medium` / `xhigh` は `--model-reasoning-effort` で分けます。通常の packet 確認や note record は `medium`、schema / boundary / omission risk review は `xhigh` を使います。

Structured findings は、既存 note を壊さない companion artifact です。`--structured-finding-json` で渡された人間作成の JSON 配列だけを記録し、AI回答の自動分類、自動プロンプト実行、自動修正はしません。

Structured finding は次を持ちます。

- `finding_id`
- `finding_type`
- `severity`
- `review_impact`
- `statement`
- `evidence_refs`
- `recommended_next_action`
- `limitations`

`evidence_refs` は string path や任意 JSON pointer ではなく、typed object だけを許可します。

```json
{
  "ref_type": "packet_context_entry",
  "index": 0,
  "entry_key": "open_actions"
}
```

許可する `ref_type` は次だけです。

- `note_finding`
- `note_limitation`
- `packet_source_summary`
- `packet_context_section`
- `packet_context_entry`

Structured findings 作成時は、note sha256、packet sha256、`note.input_hash == packet.ai_input_hash` を検証します。`source_note.path` は入力 note artifact path を指し、raw source artifact path ではありません。`source_note` には provider、model、prompt_hash、input_hash、recommendation を保存します。`model_reasoning_effort` は note にある場合だけ optional metadata としてコピーします。

## Implemented AI-in-the-loop hardening

実装済みの強化:

```text
PR-AI-LOOP-00
  Safe AI Review Context Sections

PR-AI-LOOP-01
  Structured AI Review Findings
```

`PR-AI-LOOP-00` は、既存 packet の `source_summaries` を壊さず、known schema allowlist から短い `context_sections` を作ります。unknown schema は source summary のみに留め、secret / credential / wallet / exchange write 系 source は `BLOCKED_SENSITIVE_SOURCE` のまま止めます。

`PR-AI-LOOP-01` は、AI回答後に作った note を入力にして、human review 用の structured findings companion artifact を作ります。operator decision、stage decision、paper permission、live permission には接続しません。

`strategy_ai_review_structured_findings.v1` は、Strategy Case Lite では known artifact type、Strategy Daily Brief では `ai_review_follow_up`、Strategy Workbench Viewer では compact summary として表示できます。これは human inspection の導線であり、AI recommendation の採用、paper execution、live execution、operator decision ではありません。

## 境界

- AI note は human review input であり、採用判定ではない。
- 複数 AI の意見が一致しても自動採用しない。差異は `disagreements` に残す。
- paper order、live order、wallet、signing、exchange write は使わない。
- AI recommendation は operator decision、stage decision、paper permission、live permission ではない。
- AI packet / note は Strategy Authoring YAML を自動編集しない。

## Verification

```bash
uv run pytest tests/strategy_ai_review -q
uv run sis strategy-ai-review-packet-build --help
uv run sis strategy-ai-review-note-record --help
uv run sis strategy-ai-review-findings-structure --help
uv run python scripts/check_current_docs.py
```
