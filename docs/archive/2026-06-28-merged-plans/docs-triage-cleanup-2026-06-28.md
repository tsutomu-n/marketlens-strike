<!--
作成日: 2026-06-28_08:08 JST
更新日: 2026-06-28_08:08 JST
-->

# Docs Triage Cleanup 2026-06-28

## チェックポイントID

CP1

## 目的

完了済みの `docs/plans/` 4件を `docs/archive/2026-06-28-merged-plans/` へ移し、current docs triage と archive README と final summary を実態に合わせる。

## 現状

`uv run python scripts/check_current_docs.py` は 2026-06-28_08:08 JST 時点で 177 current docs を検査して通っている。`uv run python scripts/check_cli_catalog.py` は 224 public CLI commands を Typer 登録と照合して通っている。

`docs/plans/` には完了済みの次の4件が残っている。

- `actual-cash-semantic-repair-2026-06-28.md`
- `cash-metric-legacy-migration-2026-06-28.md`
- `crypto-perp-profit-readiness-local-automation-2026-06-28.md`
- `docs-triage-refresh-2026-06-28.md`

## 制約

- 削除しない。archive 移動だけにする。
- Crypto Perp の古い plan 系 docs は参照関係を壊さないため今回は移動しない。
- docs に件数を書く場合は、固定された現在値ではなく確認時点の結果として書く。
- `git push` はしない。

## 対象ファイル

- `docs/plans/*.md` の対象4件
- `docs/archive/README.md`
- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/final-summary.md`

## 実装方針

完了済み plan を `docs/archive/2026-06-28-merged-plans/` に移動し、archive README に移動元を明記する。current docs triage は stale 化しやすい branch 固定文や `docs/plans/` の空前提を避け、完了済み plan を archive へ移す運用として書く。

## 実装手順

1. archive directory を作る。
2. 対象4件を `docs/archive/2026-06-28-merged-plans/` へ移動する。
3. `docs/archive/README.md` の更新日と archive 履歴を更新する。
4. `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` の更新日、件数、plans 記述、cleanup 候補を更新する。
5. `docs/final-summary.md` に今回の addendum を追加する。
6. この計画自体も完了済み plan として archive へ移す。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- `find docs/plans -maxdepth 1 -type f -name '*.md'`

## 完了条件

対象4件とこの計画が archive へ移動済みで、上記確認が通る。

## 失敗条件

- current-doc checker がリンク、metadata、plan routing で失敗する。
- 移動対象以外の docs を不要に変更する。
- Crypto Perp の current runbook 参照を壊す。

## 影響範囲

docs routing と historical plan 配置のみ。コード、schema、CLI 挙動は変更しない。

## ロールバック方針

この checkpoint の docs 差分を revert し、移動した plan を元の `docs/plans/` へ戻す。

## 代替案

`docs/plans/` に active plan として残す案もあるが、今回の目的が完了済み plan の archive 移動なので採用しない。

## 未解決事項

なし。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/docs-triage-cleanup-20260628-0808`

## 移行手順

利用者向け移行は不要。過去計画を読む場合は `docs/archive/2026-06-28-merged-plans/` を見る。
