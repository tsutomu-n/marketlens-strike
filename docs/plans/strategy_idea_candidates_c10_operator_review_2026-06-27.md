<!--
作成日: 2026-06-27_11:47 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidates C10 Operator Review Plan

## チェックポイントID

C10 `Operator Review Surface`

## 目的

人間が candidate generation の探索量、棄却数、selection policy、known gaps、policy validation、境界 false を 1 つの Markdown surface で読めるようにする。

## 現状

candidate set Markdown はあるが、operator が判断前に読むための dedicated review surface はない。

## 制約

- public CLI は追加しない。
- 新 schema、JSONL / CSV、外部 API、新依存は追加しない。
- review surface は paper/live approval UI ではない。

## 対象ファイル

- `src/sis/strategy_idea_candidates/operator_review.py`
- `src/sis/strategy_idea_candidates/__init__.py`
- `tests/strategy_idea_candidates/test_candidate_operator_review.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`

## 実装方針

`render_strategy_idea_candidate_operator_review_markdown` と `write_strategy_idea_candidate_operator_review` を追加する。入力は `StrategyIdeaCandidateSet` と任意の C5 policy validation result。出力は deterministic Markdown のみ。

## 実装手順

1. focused tests を追加する。
2. render / write API を追加する。
3. `__init__.py` から export する。
4. docs を更新する。
5. focused tests、current docs、CLI catalog、`git diff --check` を実行する。

## テスト方針

- review Markdown に candidate counts、duplicate/cap rejection count、selection policy、known gaps、rejection reasons、policy validation、no paper/live notice が出る。
- 同じ input から同じ review content が出る。
- existing output をデフォルトで上書きしない。

## 完了条件

operator が best candidate だけでなく、探索量と棄却理由を読める Markdown artifact を生成できること。

## 失敗条件

- shortlist だけの成功報告になる。
- paper/live approval と誤読される。
- `strategy_idea.v1` schema に provenance を押し込む。

## 影響範囲

`strategy_idea_candidates` package と tests/docs のみ。

## ロールバック方針

`operator_review.py`、C10 tests、docs 更新を revert する。

## 代替案

candidate set Markdown を兼用する案は、operator review の要点が散るため採用しない。

## 未解決事項

C9 Strategy Lab / backtest bridge、C11 public CLI / fixture E2E は後続。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/strategy-idea-candidates-20260627-1116`

## 移行手順

なし。
