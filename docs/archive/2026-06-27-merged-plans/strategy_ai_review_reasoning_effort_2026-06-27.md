<!--
作成日: 2026-06-27_17:49 JST
更新日: 2026-06-27_17:49 JST
-->

# Strategy AI Review Reasoning Effort Recording

## チェックポイントID

CP1

## 目的

`strategy-ai-review-note-record` で、AI reviewer の model id と reasoning effort を分けて記録できるようにする。

## 現状

`strategy_ai_review_note.v1` は `provider` と `model` を持つが、`gpt-5.5 medium` と `gpt-5.5 xhigh` の違いを専用フィールドで表現できない。

## 制約

- 既存 note artifact を壊さない。
- 外部AI API呼び出し、自動修正、paper/live permission は追加しない。
- `auto_applied=false`、`permission_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false` を維持する。
- `model` は `gpt-5.5` のような model id として残す。

## 対象ファイル

- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `schemas/strategy_ai_review_note.v1.schema.json`
- `tests/strategy_ai_review/test_strategy_ai_review.py`
- `tests/strategy_ai_review/test_strategy_ai_review_cli.py`
- `docs/strategy_ai_review/README.md`

## 実装方針

`model_reasoning_effort` を optional metadata として `strategy_ai_review_note.v1` に追加する。許可値はまず `medium` と `xhigh` に限定する。既存 artifact 互換のため required にはしない。

## 実装手順

1. テストに `model_reasoning_effort` 記録の期待値を追加する。
2. Pydantic model と JSON schema に optional field を追加する。
3. service / CLI に `model_reasoning_effort` 引数を追加する。
4. Markdown rendering に表示を追加する。
5. README に `--model-reasoning-effort` の使い分けを追記する。

## テスト方針

- `uv run pytest tests/strategy_ai_review -q`
- `uv run ruff check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run ruff format --check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run sis strategy-ai-review-note-record --help`
- `uv run python scripts/check_current_docs.py`

## 完了条件

- CLI で `--model-reasoning-effort xhigh` が記録できる。
- option なしの既存テストが通る。
- note JSON/Markdown に reasoning effort が出る。
- schema validation が通る。

## 失敗条件

- `model` に effort を混ぜる。
- 既存 note artifact を required field 不足で壊す。
- AI回答から自動採用や permission へ接続する。

## 影響範囲

Strategy AI Review note artifact と note record CLI の additive metadata。

## ロールバック方針

`model_reasoning_effort` に関する schema/model/service/CLI/rendering/tests/docs の差分を戻す。

## 代替案

- `model` に `gpt-5.5 xhigh` と書く案: model id と実行設定が混ざるため採用しない。
- `provider` に含める案: provider と reasoning effort は責務が異なるため採用しない。

## 未解決事項

なし。

## 破壊的変更の有無

なし。optional field の追加のみ。

## ブランチ名

`ai/strategy-ai-review-reasoning-effort-20260627-1748`

## 移行手順

なし。既存 artifact はそのまま有効。
