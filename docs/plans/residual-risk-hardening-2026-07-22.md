<!--
作成日: 2026-07-22_06:44 JST
更新日: 2026-07-22_06:44 JST
-->

# Residual Risk Hardening Plan

## チェックポイントID

RISK-HARDENING-2026-07-22

## 目的

整理済みrepositoryに残る誤push、archive tag消失、local evidenceの来歴不明、復旧不能、Graphify再肥大化のリスクを、GitHub側の強制設定と再実行可能なlocal監査手順で管理可能にする。

## 現状

- GitHub repositoryはpublicで、実行者はADMIN権限を持つ。
- mainにbranch protectionとrepository rulesetはなかった。
- CIの必須check候補はGitHub Actionsの check、app ID 15368。
- archive tagは3本、local complete bundleは3個。
- .tmp/archiveは約815 MiB、data/rawは約2.0 GiB。
- Graphifyは約51 MiBをlocal-onlyで保持している。

## 制約

- solo運用なのでPR承認者を必須にしない。
- PR、CI成功、未解決review thread解消、linear historyは必須にする。
- archive tagは作成後の更新と削除を禁止する。
- local raw/archiveの内容をGitへ追加しない。
- 外部backup先を推測してデータを送信しない。
- archive実装をmainへ再統合しない。

## 対象

- GitHub repository ruleset 2件
- scripts/audit_local_retention.py
- tests/test_audit_local_retention.py
- docs/runbooks/LOCAL_ARTIFACT_RETENTION_AND_RECOVERY.md
- docs/720-info/REPOSITORY_CLEANUP_CURRENT_STATUS_2026-07-21.md
- local-only retention manifest 2件

## 実装方針

1. main用rulesetでPR、CI check、linear history、削除・force push禁止を強制する。
2. archive tag用rulesetで更新、削除、force updateを禁止する。
3. local directoryをstreaming SHA-256で台帳化・再検証できるscriptをTDDで追加する。
4. .tmp/archiveとdata/rawにGit管理外manifestを生成し、生成直後にverifyする。
5. 3 bundleを一時repositoryへfetchし、tag targetとgit fsckを確認する。
6. 運用runbookと現況文書へ設定、復旧、保存期限判断を記録する。
7. PRをCI成功後にReadyへ変更し、squash mergeする。

## 実装手順

1. GitHub APIのcurrent ruleset schemaとCI contextを確認する。
2. active rulesetを作成し、effective configurationをread-backする。
3. manifest scriptの失敗testを書く。
4. build/verify、symlink拒否、manifest自己除外、drift検出を実装する。
5. focused test、Ruff、current-docs checkを実行する。
6. local manifest生成とbundle restore drillを実行する。
7. docsを更新し、full quality gateを実行する。
8. commit、push、draft PR、CI、Ready、merge、最終監査を行う。

## テスト方針

- unit testで安定sort、SHA-256、出力自己除外、追加・変更・削除drift、symlink fail-closedを確認する。
- local manifestはbuild直後にverifyする。
- bundleはgit bundle verifyだけでなく、一時repositoryへのfetch、git fsck、tag target確認を行う。
- GitHub rulesetは作成後のAPI read-backでtarget、condition、rule parameterを確認する。
- repository全体はscripts/checkとGitHub CIで検証する。

## 完了条件

- mainとarchive tagにactive rulesetが適用されている。
- local manifest 2件が生成・verify済みでGit対象外。
- 3 bundleが実際にfetch可能で、期待tag targetへ到達する。
- runbookと現況文書が現在の設定を説明する。
- PRがCI成功後にmergeされ、mainがclean。

## 失敗条件

- rulesetに管理者の恒久bypassを設ける。
- CI contextを推測で設定する。
- raw/archive内容またはmanifestをGitへ追加する。
- 一意性未確認データを削除する。
- 外部backup先へ無断で送信する。
- archive tagまたはbundleの存在だけで復旧可能と断定する。

## 影響範囲

GitHubのmerge/ref更新条件、local-only監査artifact、運用文書に限定する。取引、research、paper/live、schema、public CLIの挙動は変更しない。

## ロールバック方針

- rulesetはGitHub repository settingsまたはAPIでdisabledへ変更できる。
- manifest scriptは通常のcommit revertで除去できる。
- local manifestは生成物なので削除・再生成できる。
- archive tagとbundle本体は変更しない。

## 代替案

従来branch protectionだけを使う案はarchive tagを同じ仕組みで保護できないため不採用。外部storageを自動作成する案は保存先、課金、credentialが未指定なので不採用。

## 未解決事項

bundleと一意raw dataの別媒体保存先、暗号化鍵、保存年限は利用者のstorage方針が必要である。今回の作業では、移送可能な検証済みmanifestとrunbookまで完成させる。

## 破壊的変更

mainへの直接push、force push、branch削除、archive tagの更新・削除をGitHub側で拒否する。意図した運用強化であり、rulesetをdisabledにすれば戻せる。

## ブランチ

ai/harden-residual-risks-20260722-0644

## 移行手順

今後は作業branchからPRを作り、CI成功後にsquashまたはrebaseでmainへ統合する。archive tagを更新する必要が生じた場合は、既存tagを書き換えず新しいversioned archive tagを作る。
