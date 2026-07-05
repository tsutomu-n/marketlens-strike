<!--
作成日: 2026-07-05_11:55 JST
更新日: 2026-07-05_11:55 JST
-->

# Current-Only Docs Refresh Plan

## チェックポイントID

C1/C2 current-only-docs-refresh.

## 目的

現行判断に使う入口 docs を current-only に作り直し、旧 roadmap、dogfood log、古い snapshot は archive/history として隔離する。実装、schema、public CLI behavior、runtime artifact は変えない。

## 現状

- `README.md` と `docs/CURRENT_STATE.md` は current entry だが、dated research docs、old roadmap、archive/history への導線が多い。
- `docs/REALISTIC_ROADMAP_CURRENT_2026-06-28.md` は standalone current roadmap として checker 対象に残っている。
- `plan/2026-06-22-strategy-feedback-case-index/` は 00-33 と dogfood logs 全体が checker の current scope に残っている。
- `scripts/check_current_docs.py` は baseline で green だが、current / historical の意味判定までは十分に縛っていない。

## 制約

- コード、schema、CLI behavior、lockfile、runtime artifact は変更しない。
- 古い資料は削除せず archive へ移す。
- archive 本文は原則書き換えない。更新するのは archive index と current からの導線だけ。
- Markdown を更新する場合は Tokyo time metadata header を更新する。
- `git push` はしない。

## 対象ファイル

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/CURRENT_GOAL_AND_DIRECTION_2026-07-05.md`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/REALISTIC_ROADMAP_CURRENT_2026-06-28.md`
- `plan/README.md`
- `plan/2026-06-22-strategy-feedback-case-index/`
- `scripts/check_current_docs.py`
- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/DOCUMENT_AUDIT_2026-07-05_CODE_TRUTH_DOC_TRIAGE.md`
- `docs/archive/README.md`
- `docs/final-summary.md`

## 実装方針

1. 新しい goal doc に C9 bridge、Bitget public source、ticker-aware source availability、Backtest Candidate Pack、evidence quality 改善を統合する。
2. 新しい docs index で Primary / Domain current / Historical reference を明確に分ける。
3. `NEXT_DIRECTION_CURRENT.md` は互換 redirect にし、旧 roadmap は archive へ移す。
4. active plan package は短い current summary だけ残し、00-33/TASK_CHAIN は archive へ移す。
5. checker は新 docs と plan summary を current scope に入れ、旧 roadmap と plan logs を current scope から外す。

## テスト方針

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
rg -n "docs/archive/|plan/archive/|progress-to-90|Pre Actual Cash Decision Gate|checked [0-9]+ current docs|[0-9]+ passed|origin/main|branch:" README.md docs plan --glob '!docs/archive/**' --glob '!plan/archive/**'
uv run sis --help
```

必要なら最後に `./scripts/check` を実行する。

## 完了条件

- current entry docs が新 goal/index を最初に読む構造になっている。
- old roadmap と plan dogfood logs が current checker scope から外れている。
- checker が新 goal/index と plan summary を検査する。
- current docs に fixed pass count や old progress label を増やしていない。
- 検証結果を `docs/final-summary.md` に記録する。

## 失敗条件

- current docs checker が broken links / missing metadata / semantic drift を出す。
- archive へ移したファイルへの current 入口リンクが壊れる。
- code/schema/CLI behavior/runtime artifact に変更が混ざる。

## 影響範囲

docs と checker routing のみ。runtime behavior への影響なし。

## ロールバック方針

docs と checker の差分を revert すれば戻せる。archive へ移したファイルは削除せず残すため、path revert または archive index 修正で復旧できる。

## 代替案

- `REALISTIC_ROADMAP_CURRENT_2026-06-28.md` を redirect に残し、`NEXT_DIRECTION_CURRENT.md` を archive する案もある。ただし現行 docs からのリンクが多いため、互換 redirect は `NEXT_DIRECTION_CURRENT.md` に残す。

## 未解決事項

なし。current/currentでない判断は code、CLI help、checker、既存 current docs を優先する。

## 破壊的変更の有無

なし。ファイル移動は archive 隔離であり削除ではない。

## ブランチ名

`ai/current-only-docs-refresh-20260705-1155`

## 移行手順

利用者側の移行は不要。旧 `NEXT_DIRECTION_CURRENT.md` のリンクは互換 redirect で新 goal doc に誘導する。
