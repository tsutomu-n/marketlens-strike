<!--
作成日: 2026-07-21_20:50 JST
更新日: 2026-07-21_20:50 JST
-->

# Repository Residual Risk Cleanup Plan

## チェックポイントID

CLEANUP-2026-07-21-FINAL

## 目的

未保護コード、未統合branch、重複生成物、一時領域、現況文書の不整合を整理し、通常開発をcleanなmainから再開できる状態にする。

## 現状と制約

- Graphify artifactはlocal-onlyのまま保持する。
- 未統合branchは内容確認なしにmergeまたは削除しない。
- Profit Coreのactual cash経路を再有効化しない。
- 一意性が不明なraw dataは削除しない。
- mainへの反映はclean branch、PR、CI成功、Ready、mergeの順に行う。

## 対象

Portfolio Capacity spike、現況文書、Git refs、worktree、graphify-out、.tmp/archive。

## 実装方針と手順

1. BT0の未追跡15ファイルをcommitしてremoteへ保護する。
2. clean mainから限定統合branchを作り、PR-BT0だけをcherry-pickする。
3. focused testとfull quality gateを通し、CI成功後にmergeする。
4. Execution Replay、Profit Core、その他の旧branchを監査する。
5. mergeしない履歴はremote archive tagとcomplete Git bundleへ退避する。
6. clean確認後に旧branch/worktreeを削除する。
7. Graphifyのactive artifactを残し、cache/backupだけを削除する。
8. local archiveはhash一致した重複だけを削除する。
9. 時刻付き現況文書を更新し、doc-only PRをCI成功後にmergeする。

## テスト方針

Portfolio Capacity focused Pytest、scripts/check、current-docs check、GitHub CIを使う。bundleはgit bundle verify、remote tagはgit ls-remoteで確認する。

## 完了条件

通常branchはlocal/remoteともmainだけ、worktreeはrootだけ、open PRは0件、GraphifyはGit対象外、未統合履歴はremote tagとcomplete bundleから復旧可能、root working treeはclean。

## 失敗条件

未保護file/branchの削除、venue-specificまたはactual-cash実装の無検証統合、一意なraw dataの削除、CI失敗中のReady/merge。

## 影響範囲

mainへ入る実装はresearch spike 15ファイルだけ。その他はGit ref、local生成物、文書の整理で、public CLIやproduction executionは変更しない。

## ロールバック方針

main統合はrevert可能。旧branchはarchive tagまたはbundleから再作成可能。Graphify cache/backupは再生成でき、重複Parquetは同一SHA-256の代表コピーから複製できる。

## 代替案

旧branchを残す案は誤操作入口を残すため不採用。全branch mergeは現行product軸、安全境界、test不足に反するため不採用。

## 未解決事項

local-only raw/archive dataの長期保存先と保存期限は運用判断として残る。現行repoの機能やcleanup完了を妨げない。

## 破壊的変更、移行、ブランチ

public API、schema、DBの破壊的変更と利用者向け移行はない。旧branch/worktreeはarchive後に削除する。作業branchは ai/final-cleanup-status-20260721-2050。
