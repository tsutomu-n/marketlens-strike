<!--
作成日: 2026-06-27_16:21 JST
更新日: 2026-06-27_16:21 JST
-->

# PR-AI-LOOP-00: Safe AI Review Context Sections

## チェックポイントID

CP1

## 目的

`strategy-ai-review-packet-build` で、AI に渡してよい安全な `context_sections` を packet に追加する。

## 現状

`strategy_ai_review_packet.v1` は `source_summaries` を持ち、full source payload は含めない。`strategy_case_lite.v1` の `summary` や件数は packet には入っていない。

## 制約

- `strategy-ai-review-note-record` は今回の実行対象外。
- 外部AI API呼び出し、自動プロンプト実行、自動修正はしない。
- 新依存は追加しない。
- `context_sections` は known schema allowlist からだけ作る。
- full source payload は packet に入れない。
- secret / credential / wallet / exchange write 系が見つかったら `BLOCKED_SENSITIVE_SOURCE`。
- `paper_execution_allowed=false`、`live_allowed=false`、`permission_allowed=false`、`auto_applied=false` は維持する。

## 対象ファイル

- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `schemas/strategy_ai_review_packet.v1.schema.json`
- `tests/strategy_ai_review/test_strategy_ai_review.py`
- `tests/strategy_ai_review/test_strategy_ai_review_cli.py`
- `docs/strategy_ai_review/README.md`

## 実装方針

`source_summaries` は provenance 用に残し、AI-facing context は別フィールド `context_sections` として追加する。最初の allowlist は `strategy_case_lite.v1` のみとし、以下の安全な summary 値だけを使う。

- `strategy_id`
- `case_id`
- `updated_at`
- `summary.artifact_count`
- `summary.timeline_count`
- `summary.latest_status`
- `summary.open_actions`
- `summary.blocked_reasons`

`source_artifacts`、`timeline`、任意の unknown schema payload は展開しない。

## 実装手順

1. packet model/schema に `context_sections` と section model を追加する。
2. `strategy_case_lite.v1` 用 allowlist extractor を追加する。
3. `ai_input_hash` に `context_sections` を含める。
4. Markdown report に `Context Sections` を表示する。
5. テストで full payload 非混入、allowlist 生成、sensitive block を確認する。
6. README を current behavior に更新する。

## テスト方針

- `uv run pytest tests/strategy_ai_review -q`
- `uv run sis strategy-ai-review-packet-build --help`
- 必要なら最小 fixture で `strategy-ai-review-packet-build` を実行する。
- `uv run python scripts/check_current_docs.py`

## 完了条件

- packet JSON が schema validation を通る。
- `context_sections` は allowlisted field のみを含む。
- full source payload と sensitive value が packet に入らない。
- sensitive source では ready state にならない。
- permission flags が false のまま。

## 失敗条件

- unknown schema から任意 payload を取り込む。
- `source_artifacts` / `timeline` の raw payload を入れる。
- sensitive source を `READY_FOR_AI_REVIEW` にする。
- note record や外部AI実行に範囲が広がる。

## 影響範囲

`strategy_ai_review_packet.v1` の additive field 追加と packet build output。note record は regression 対象のみ。

## ロールバック方針

`context_sections` model/schema/service/rendering/tests/docs の差分を戻す。

## 代替案

- `source_summaries` に summary field を足す案: provenance と AI-facing context が混ざるため採用しない。
- unknown schema も浅く要約する案: allowlist 条件に反するため採用しない。

## 未解決事項

なし。

## 破壊的変更の有無

なし。packet schema の additive field 追加。

## ブランチ名

`ai/strategy-idea-candidates-20260627-1116`

## 移行手順

なし。

## Critique

この計画は `packet build` だけに限定されている。最も大きいリスクは `context_sections` が raw payload の別名になることだが、schema allowlist と field-level tests で防ぐ。`strategy_case_lite.v1` 以外は context を出さず、source summary だけに留めるため、未知 artifact の過剰開示を避けられる。
