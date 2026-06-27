<!--
作成日: 2026-06-27_11:47 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidates C11 Fixture E2E Plan

## チェックポイントID

C11 `Fixture E2E`

## 目的

fixture input evidence から candidate set、policy validation、operator review、shortlist export、`strategy-intake-validate` 相当の intake validation までを 1 本の regression test で通す。

## 現状

個別 tests はあるが、C4/C5/C8/C10 を連結した fixture E2E はない。

## 制約

- public CLI は追加しない。
- 実 market data、外部 API、新依存、paper/live behavior は使わない。
- `strategy_idea.v1` schema は拡張しない。

## 対象ファイル

- `tests/strategy_idea_candidates/test_candidate_pipeline_e2e.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`

## 実装方針

既存 fixture と Python API を使って、source file と validation artifact を tmp path に作り、candidate set write、policy validation、operator review write、shortlist export、intake validation を実行する。

## 実装手順

1. E2E test を追加する。
2. docs を更新する。
3. focused tests、current docs、CLI catalog、`git diff --check` を実行する。

## テスト方針

- candidate set JSON / Markdown が書ける。
- policy validation が pass する。
- operator review Markdown が書ける。
- shortlist export が strict `strategy_idea.v1` と sidecar manifest を書く。
- intake validation が `READY_FOR_AUTHORING_DRAFT` を返す。

## 完了条件

C11 fixture E2E が deterministic に通り、paper/live/alpha claims を追加しないこと。

## 失敗条件

- fixture が実データや外部 API に依存する。
- E2E が public CLI 追加を要求する。
- provenance を `strategy_idea.v1` に押し込む。

## 影響範囲

Tests/docs のみ。

## ロールバック方針

E2E test と docs 更新を revert する。

## 代替案

CLI E2E を先に作る案は、public surface を広げるため採用しない。

## 未解決事項

C6 selection-adjusted metrics と C9 Strategy Lab / backtest bridge は後続。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/strategy-idea-candidates-20260627-1116`

## 移行手順

なし。
