<!--
作成日: 2026-06-19_01:17 JST
更新日: 2026-06-27_17:04 JST
-->

# Strategy AI Review

## 結論

Strategy AI Review は、LLM に渡してよい最小限の source summary と allowlisted context sections を作り、AI の回答を human review 用 note として記録する first slice です。

AI は proposal / critique の補助であり、採用、paper execution、live execution、Strategy Authoring YAML 自動編集を許可しません。

次に強化する AI-in-the-loop control layer の実装計画は [AI_IN_THE_LOOP_CONTROL_LAYER_IMPLEMENTATION_PLAN_2026-06-27.md](AI_IN_THE_LOOP_CONTROL_LAYER_IMPLEMENTATION_PLAN_2026-06-27.md) を読む。この計画は、外部 LLM API 実行ではなく、AI に渡してよい安全な context packet、prompt / input hash、structured finding、AI note の表示導線を追加するための coder handoff です。

## Commands

```bash
uv run sis strategy-ai-review-packet-build \
  --source data/strategy_cases/<strategy-id>/strategy_case_lite.json \
  --review-question "What should a human inspect next?" \
  --out data/strategy_ai_reviews/<strategy-id>

uv run sis strategy-ai-review-note-record \
  --packet data/strategy_ai_reviews/<strategy-id>/strategy_ai_review_packet.json \
  --provider openai \
  --model gpt-reviewer \
  --prompt-hash sha256:<64hex> \
  --finding "Return drift should be reviewed by a human." \
  --limitation "AI did not inspect raw market data." \
  --recommendation REVISE
```

## Artifacts

- `strategy_ai_review_packet.json`
- `strategy_ai_review_packet.md`
- `strategy_ai_review_note.json`
- `strategy_ai_review_note.md`

Packet は full source payload を入れません。source path、sha256、schema_version、strategy_id、status、action の summary と、known schema allowlist から作る `context_sections` だけを含めます。

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
- prompt hash
- input hash
- limitations
- findings
- recommendation
- disagreements
- `auto_applied=false`
- `permission_allowed=false`

## Planned AI-in-the-loop hardening

実装計画の順序:

```text
PR-AI-LOOP-00
  Safe AI Review Context Sections

PR-AI-LOOP-01
  Structured AI Review Findings

PR-AI-LOOP-02
  AI Review Notes into Case / Daily Brief / Workbench Viewer
```

最初に実装する `PR-AI-LOOP-00` では、既存 packet の `source_summaries` を壊さず、known schema allowlist から短い `context_sections` を作ります。unknown schema は source summary のみに留め、secret / credential / wallet / exchange write 系 source は `BLOCKED_SENSITIVE_SOURCE` のまま止めます。

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
uv run python scripts/check_current_docs.py
```
