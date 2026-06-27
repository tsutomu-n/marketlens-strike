<!--
作成日: 2026-06-27_11:47 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidates C4 Generator Plan

## チェックポイントID

C4 `Deterministic Candidate Generator v0`

## 目的

`PASS` 済み input evidence と generator config を受け取り、fixed candidate family、finite parameter grid、candidate cap、duplicate rejection rule から、同じ入力で同じ `strategy_idea_candidate_set.v1` を生成する。

## 現状

C1/C2/C3/C8 は実装済み。candidate set model、canonical JSON / Markdown writer、blocked input evidence builder、shortlist export と sidecar manifest がある。C4 の deterministic generator は未実装。

## 制約

- public CLI は追加しない。
- 新依存は追加しない。
- 外部 API、LLM、ML optimizer、実 market data fetch は使わない。
- `strategy_idea.v1` schema は拡張しない。
- 出力は常に `UNVERIFIED_CANDIDATE` で、alpha proof / paper permission / live readiness を主張しない。

## 対象ファイル

- `src/sis/strategy_idea_candidates/generator.py`
- `src/sis/strategy_idea_candidates/models.py`
- `src/sis/strategy_idea_candidates/__init__.py`
- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `tests/strategy_idea_candidates/test_candidate_generator.py`
- `tests/strategy_idea_candidates/fixtures.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`

## 実装方針

Generator は Python API とする。`StrategyInputContract`、`StrategyInputContractValidation`、validation path、generator config を入力し、validation が non-PASS の場合は既存 blocked builder を使う。PASS の場合だけ fixed family templates と finite grid を展開する。

Candidate set には `parameter_grids`、`candidate_cap`、`cap_rejection_count` を保存する。duplicate は candidate inventory に `REJECTED` として残し、`duplicate_rejection_count` と `rejection_reason` で追跡する。

## 実装手順

1. generator の focused tests を追加する。
2. candidate set model/schema/fixture に C4 で必要な grid/cap fields を追加する。
3. `generator.py` に config、family template、build function、stable grid hash を実装する。
4. docs と `.ai-work` を更新する。
5. focused tests、current docs、CLI catalog、`git diff --check` を実行する。

## テスト方針

- 同じ入力と config で同じ JSON content / hash になること。
- fixed family IDs が artifact に出ること。
- `parameter_grids` と `parameter_grid_hash` が安定すること。
- duplicate parameter set が silent drop されず rejected inventory に残ること。
- candidate cap 超過が rejected inventory と summary に残ること。
- non-PASS input validation が `BLOCKED_INPUT_EVIDENCE` になること。
- writer と export が既存通り動くこと。

## 完了条件

上記テストが通り、`strategy_idea.v1` schema、public CLI、新依存、paper/live 境界に変更がないこと。

## 失敗条件

- source hash、available-at、max observed timestamp、label window、prediction horizon を candidate set に残せない。
- selected-only artifact になる。
- duplicate/cap rejection が silent drop になる。
- raw metrics を proof として扱う必要が出る。
- C4 に新依存または外部 API が必要になる。

## 影響範囲

`strategy_idea_candidates` package とその schema/tests/docs のみ。既存 Strategy Intake と export は sidecar方式のまま。

## ロールバック方針

`generator.py`、C4 tests、candidate set schema/model の C4 fields、docs 更新を revert すれば C1/C2/C3/C8 の状態に戻せる。

## 代替案

Grid を candidate ごとの `parameter_set` だけに残す案は、探索空間全体の保存が弱いため採用しない。

## 未解決事項

C5 split engine、C6 selection-adjusted metrics、C9 bridge、C10 operator review surface、C11 CLI/E2E は後続。

## 破壊的変更の有無

なし。candidate set v1 への C4 fields 追加は同ブランチ内の未公開 artifact contract の拡張。

## ブランチ名

`ai/strategy-idea-candidates-20260627-1116`

## 移行手順

なし。
