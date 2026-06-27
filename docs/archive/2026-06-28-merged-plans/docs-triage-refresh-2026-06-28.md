<!--
作成日: 2026-06-28_06:36 JST
更新日: 2026-06-28_06:38 JST
-->

# Docs Triage Refresh Plan 2026-06-28

## チェックポイントID

DOCS-TRIAGE-REFRESH-2026-06-28

## 目的

`docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` を、現行コード、CLI、schema、tests、docs checker を根拠にした docs triage checklist として更新する。

## 現状

- `main` は作業開始時点で未コミット変更なし。
- 作業開始時の `uv run python scripts/check_current_docs.py` は current docs 173 件を検査済み。checkpoint plan 追加後の検証では 174 件。
- `uv run python scripts/check_cli_catalog.py` は public CLI 216 件を Typer 登録と照合済み。
- 既存 triage は分類表を持つが、判定基準と次 cleanup 候補を明示する余地がある。

## 制約

- 削除、移動、archive 変更はこの checkpoint では行わない。
- `docs/archive/**` と `plan/archive/**` は historical context として扱い、current proof に戻さない。
- runtime artifact 値、branch 状態、pass count、hash は固定の current truth として書かない。

## 対象ファイル

- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/plans/docs-triage-refresh-2026-06-28.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## 実装方針

- 既存 triage doc を正本として更新し、競合する新規 audit は作らない。
- 分類表の前に判定基準を追加する。
- cleanup 候補は実行せず、次に進める場合の条件と最小確認だけを記録する。
- 抜け・漏れ・誤謬リスクを、docs checker / CLI catalog / archive / runtime artifact / low-level helper の限界に寄せて明示する。

## 実装手順

1. baseline checks と CLI help を再実行する。
2. checker allowlist、既存 triage、implemented surfaces、CLI catalog を読む。
3. triage doc の timestamp、確認時点、判定基準、cleanup 候補、risk pass を更新する。
4. docs checker、CLI catalog checker、`git diff --check` を実行する。
5. final summary と `.ai-work/` を更新する。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

`./scripts/check` は docs routing / checker allowlist / code behavior を変更していないため必須にしない。

## 完了条件

- 既存 triage doc が四分類、判定基準、cleanup 候補、risk pass を持つ。
- current docs checker と CLI catalog checker が通る。
- whitespace diff check が通る。
- 削除・移動が発生していない。

## 失敗条件

- current docs checker が失敗する。
- CLI catalog checker が失敗する。
- archive docs を current proof として再導線化する。
- runtime snapshot を固定の current truth として書く。

## 影響範囲

docs triage と作業記録のみ。実装コード、schema、CLI registration、runtime artifact には影響しない。

## ロールバック方針

この checkpoint の docs 変更を revert する。削除・移動は行わないため、ファイル復旧作業は不要。

## 代替案

- 新しい audit doc を作る案: 既存 triage と競合するため採用しない。
- archive cleanup まで実行する案: 今回の依頼は triage refresh であり、別タスクに分ける。

## 未解決事項

なし。

## 破壊的変更の有無

なし。

## ブランチ名

`main`。docs の局所更新であり、専用ブランチが必要な破壊的変更、依存変更、構成変更、API/schema 変更には該当しない。

## 移行手順

不要。
