<!--
作成日: 2026-06-27_11:47 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidates C5 Policy Validation Plan

## チェックポイントID

C5 `Split / Leakage Policy Validation`

## 目的

C4 generator が保存した split / leakage / purge / embargo policy record を、最低限の時刻境界と sealed-test non-use について検査できる Python API を追加する。

## 現状

`StrategyIdeaCandidateSet` は `split_policy` と `leakage_policy` を保存しているが、それらが train / validation / sealed test の順序や candidate label window と整合しているかを検査する専用 API はない。

## 制約

- full split engine は実装しない。
- 実データ row validation、CV、統計補正、外部 API、新依存、CLI は追加しない。
- policy validation は alpha proof、profit proof、paper/live permission ではない。

## 対象ファイル

- `src/sis/strategy_idea_candidates/policies.py`
- `src/sis/strategy_idea_candidates/__init__.py`
- `tests/strategy_idea_candidates/test_candidate_policy_validation.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`

## 実装方針

`validate_split_and_leakage_policy(candidate_set)` を追加し、pass/fail と failure messages を返す。検査対象は time window ordering、sealed test non-use、candidate label / feature windows、source available-at boundary、purge / embargo policy の存在に限定する。

## 実装手順

1. focused tests を追加する。
2. `policies.py` に dataclass result と validation function を追加する。
3. `__init__.py` から export する。
4. docs を更新する。
5. focused tests、current docs、CLI catalog、`git diff --check` を実行する。

## テスト方針

- generator output が policy validation を pass する。
- validation window と sealed test window の overlap を fail にする。
- candidate label window が sealed test window に入る場合を fail にする。
- source max observed timestamp が available-at より後の場合を fail にする。

## 完了条件

policy validation API が deterministic に pass/fail を返し、既存 writer/export/generator と独立して使えること。

## 失敗条件

- full split engine と誤読される。
- raw metrics や shortlist を proof として扱う。
- 実データ row がないと検査できない設計になる。

## 影響範囲

`strategy_idea_candidates` package と tests/docs のみ。

## ロールバック方針

`policies.py`、C5 tests、docs 更新を revert する。

## 代替案

Pydantic model validator にすべて埋め込む案は、blocked artifact や fixture の柔軟性を落としやすいため採用しない。

## 未解決事項

実データ行ベースの purge / embargo engine、selection-adjusted metrics、review/backtest bridge は後続。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/strategy-idea-candidates-20260627-1116`

## 移行手順

なし。
