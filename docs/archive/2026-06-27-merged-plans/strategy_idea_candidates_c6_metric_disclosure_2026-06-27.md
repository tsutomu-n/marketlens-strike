<!--
作成日: 2026-06-27_11:47 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidates C6 Metric Disclosure Plan

## チェックポイントID

C6 `Raw Metric Disclosure`

## 目的

raw metrics と selection-adjusted metrics status を Markdown reports 上で明確に分け、raw metric や shortlist が alpha proof / profit proof と誤読されないようにする。

## 現状

model は `raw_validation_metrics` と `selection_adjusted_metrics_status` を分けているが、candidate set Markdown の列名が `raw metrics status` と誤解を招く。operator review も status counts を明示していない。

## 制約

- selection-adjusted metrics engine は実装しない。
- 新依存、統計補正、外部 API、実データ evaluation は追加しない。
- `NOT_IMPLEMENTED` を proof の代替として扱わない。

## 対象ファイル

- `src/sis/strategy_idea_candidates/rendering.py`
- `src/sis/strategy_idea_candidates/operator_review.py`
- `tests/strategy_idea_candidates/test_candidate_operator_review.py`
- `tests/strategy_idea_candidates/test_candidate_set_writer.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`

## 実装方針

candidate set Markdown の列名を `selection-adjusted status` に直す。operator review Markdown に metric disclosure section を追加し、status counts と no-proof notice を表示する。

## 実装手順

1. focused assertions を追加する。
2. renderer と operator review を更新する。
3. docs を更新する。
4. focused tests、current docs、CLI catalog、`git diff --check` を実行する。

## テスト方針

- operator review に `selection_adjusted_metrics_status` と `NOT_IMPLEMENTED` が出る。
- no alpha/profit proof notice が出る。
- candidate set Markdown の列名が誤解を招かない。

## 完了条件

Reports が raw metrics と selection-adjusted status を混同せず、未実装 status を明示すること。

## 失敗条件

- raw metric を proof と呼ぶ。
- selection-adjusted metrics が実装済みであるかのように見せる。
- 新依存や実データ evaluation が必要になる。

## 影響範囲

Markdown rendering/tests/docs のみ。

## ロールバック方針

Renderer / operator review / tests / docs の C6 変更を revert する。

## 代替案

metric engine を先に作る案は scope が広く、artifact/ledger の安全境界より先行するため採用しない。

## 未解決事項

本物の selection-adjusted metric engine は後続。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/strategy-idea-candidates-20260627-1116`

## 移行手順

なし。
