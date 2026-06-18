<!--
作成日: 2026-06-19_01:17 JST
更新日: 2026-06-19_01:17 JST
-->

# Strategy AI Review

## 結論

Strategy AI Review は、LLM に渡してよい最小限の source summary packet を作り、AI の回答を human review 用 note として記録する first slice です。

AI は proposal / critique の補助であり、採用、paper execution、live execution、Strategy Authoring YAML 自動編集を許可しません。

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

Packet は full source payload を入れません。source path、sha256、schema_version、strategy_id、status、action の summary だけを含めます。

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

## 境界

- AI note は human review input であり、採用判定ではない。
- 複数 AI の意見が一致しても自動採用しない。差異は `disagreements` に残す。
- paper order、live order、wallet、signing、exchange write は使わない。

## Verification

```bash
uv run pytest tests/strategy_ai_review -q
uv run sis strategy-ai-review-packet-build --help
uv run sis strategy-ai-review-note-record --help
uv run python scripts/check_current_docs.py
```
