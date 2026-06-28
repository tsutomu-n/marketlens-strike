<!--
作成日: 2026-06-28_17:12 JST
更新日: 2026-06-28_17:12 JST
-->

# Non-Technical Strategy Idea Overview Plan 2026-06-28

## チェックポイントID

CP1

## 目的

戦略アイディアを発想する仕組みを、非技術者が読める日本語の資料としてまとめる。

## 現状

技術資料は `docs/strategy_idea_candidates/README.md`、`docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`、`docs/STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md`、`docs/STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md` に分散している。

## 制約

- 既存の専門用語をそのまま並べず、平易な日本語へ置き換える。
- 利益証明、実運用許可、注文許可と誤読される表現を避ける。
- コード、schema、依存関係、CLI は変更しない。
- 既存の未コミット変更 `docs/REALISTIC_ROADMAP_CURRENT_2026-06-28.md` には触れない。

## 対象ファイル

- `docs/strategy_idea_candidates/NON_TECHNICAL_OVERVIEW_2026-06-28.md`
- `README.md`
- `docs/CURRENT_STATE.md`

## 実装方針

新規文書を `docs/strategy_idea_candidates/` に作成し、技術資料への入口ではなく、非技術者向けの説明本文として完結させる。既存入口からリンクする。

## 実装手順

1. 新規文書を作成する。
2. `README.md` の Read First に追加する。
3. `docs/CURRENT_STATE.md` の結論、目的別表、Recommended Read Order に追加する。
4. current-docs check と whitespace check を実行する。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `git diff --check`

## 完了条件

- 非技術者向け文書が存在する。
- 入口文書から辿れる。
- 検証結果を記録する。

## 失敗条件

- 専門用語の説明に寄りすぎ、非技術者が読みにくい。
- 候補生成を利益証明や実運用許可のように読める。
- pre-existing dirty file を巻き込む。

## 影響範囲

Docs only.

## ロールバック方針

新規文書と README / CURRENT_STATE のリンク追加を戻す。

## 代替案

既存 README に追記するだけの案もあるが、長くなり入口文書として読みにくくなるため採用しない。

## 未解決事項

なし。

## 破壊的変更の有無

なし。

## ブランチ名

`main`。docs-only で、専用ブランチ必須条件には該当しない。

## 移行手順

なし。
