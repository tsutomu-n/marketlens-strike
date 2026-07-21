<!--
作成日: 2026-07-22_06:49 JST
更新日: 2026-07-22_06:49 JST
-->

# Local Artifact Retention And Recovery Runbook

## 1. 結論

local raw data、historical archive、Git bundle、Graphify artifactはGitへ追加しない。削除前にSHA-256台帳と復旧経路を確認し、archive Git履歴は保護済みremote tagと検証済みbundleの二経路で保持する。

## 2. GitHub側の強制設定

### 2.1 Main delivery

- ruleset: Protect main delivery
- ruleset ID: 19483352
- target: default branch
- enforcement: active
- bypass actor: なし
- Pull Request: 必須
- 必須status check: check
- GitHub Actions app ID: 15368
- latest mainとの同期: 必須
- unresolved review thread: merge前に解消必須
- approving review: 0。solo運用のため第三者承認は要求しない
- merge方式: squashまたはrebase
- branch削除、force push、non-linear history: 禁止

設定確認:

    gh api repos/tsutomu-n/marketlens-strike/rulesets/19483352
    gh api repos/tsutomu-n/marketlens-strike/rules/branches/main

### 2.2 Archive tags

- ruleset: Protect archive tags
- ruleset ID: 19483353
- target pattern: refs/tags/archive/*
- enforcement: active
- bypass actor: なし
- tag新規作成: 許可
- 既存tag更新、削除、force update: 禁止

設定確認:

    gh api repos/tsutomu-n/marketlens-strike/rulesets/19483353

既存archive tagを書き換えない。内容更新が必要なら、日付またはversionを含む新しいarchive tagを作る。

## 3. Local retention manifest

### 3.1 対象

| Root | Classification | Git |
|---|---|---|
| .tmp/archive | historical-archive | .tmp/*で除外 |
| data/raw | unique-raw-evidence | data/で除外 |

manifest名は各root直下のLOCAL_RETENTION_MANIFEST.jsonである。manifest自体は台帳対象から除外される。

### 3.2 生成

    uv run python scripts/audit_local_retention.py build \
      --root .tmp/archive \
      --classification historical-archive

    uv run python scripts/audit_local_retention.py build \
      --root data/raw \
      --classification unique-raw-evidence

manifestはpath、size、mtime、SHA-256を記録する。symlinkと特殊ファイルは追跡せず、エラーで停止する。

### 3.3 検証

    uv run python scripts/audit_local_retention.py verify --root .tmp/archive
    uv run python scripts/audit_local_retention.py verify --root data/raw

exit code:

- 0: path集合と内容hashが一致
- 1: file追加、変更、削除を検出
- 2: manifest不正、root不一致、symlink、特殊file、I/O error

mtimeだけの変化は内容破損にしない。削除判断にはpathとSHA-256を使う。

## 4. 保存分類

### 再生成可能

生成command、input、versionが残っているもの。容量が必要な場合は、再生成確認後に削除できる。

### 検証証跡

PR、実験、調査の判断根拠。関連判断が有効な間は保持する。保存期限を設定する場合も、期限だけで自動削除せずmanifest差分をreviewする。

### 唯一のraw data

再取得不能または取得条件不明のもの。別媒体backupとchecksum照合が終わるまで削除禁止。

## 5. Git bundle復旧

### 5.1 現在の対応表

| Bundle | Bundle内ref | Remote archive tag | Expected commit |
|---|---|---|---|
| crypto-perp-portfolio-replay-20260716.bundle | refs/remotes/origin/ai/crypto-perp-portfolio-replay-20260716-2204 | archive/crypto-perp-portfolio-replay-20260716 | 50ff4790f0b43bf9080f2adb02c5cfaa31cfa8e5 |
| profit-core-branch-set-20260721.bundle | refs/tags/archive/profit-core-branch-set-20260721 | archive/profit-core-branch-set-20260721 | 6f3d7a2c4109f9e730194b498aad037e42fb8b8f |
| legacy-branch-set-20260721.bundle | refs/tags/archive/legacy-branch-set-20260721 | archive/legacy-branch-set-20260721 | fbe65b32f5d45774b08e3d453cb02f24852857b0 |

Execution Replay bundleだけはbundle内refがarchive tagではなく旧remote tracking refである。復旧可能性には影響しないが、source refを推測してはいけない。

### 5.2 復旧test

最低限、次をbundleごとに行う。

1. git bundle verify
2. 空のbare repositoryを作る
3. git bundle list-headsで確認したrefをfetchする
4. git fsck --full --no-dangling
5. fetched refをpeeled commitへ解決する
6. remote archive tagのpeeled commitと一致させる

2026-07-22の実測では3 bundleすべてfetch、fsck、expected commit、remote tag一致に成功した。

## 6. 別媒体backup

保存先、課金、credential、暗号化鍵はrepoから決めない。利用者が管理する暗号化済みvolumeまたはbackup serviceを選び、次の順で複製する。

1. local manifestをverifyする。
2. 3 bundleと2 manifestを保存先へ複製する。
3. 保存先でSHA-256を再計算する。
4. local manifestまたは既存bundle checksumと一致させる。
5. 復元用のGit binary versionと復旧test日を記録する。

保存先が未指定の状態で、cloud storage、外付け媒体、第三者serviceへ自動送信しない。

## 7. Archiveコードの再利用

archive tagまたはbundle全体をmainへmergeしない。

1. 現行mainから専用branchを作る。
2. 必要なfileまたはcommitだけを抽出する。
3. 現行schema、安全境界、product軸へ適合させる。
4. focused testとscripts/checkを実行する。
5. PR、CI成功、Ready、mergeの順で統合する。

Profit Coreのactual-cash経路は、archiveから直接再有効化しない。

## 8. Graphify

- graphify-outはGit対象外。
- コード変更後にgraphify update .を実行する。
- active graph.json、manifest、report、label情報は保持する。
- update/query後に増えた日付backup、cache、rebuild lockは、active graph確認後に整理する。
- watch daemonやGraphify artifactの自動commitは使用しない。

## 9. Stop condition

次の場合は削除、移動、上書きを中止する。

- manifest verifyが失敗する
- bundle fetch、fsck、expected commit照合が失敗する
- remote archive tagが存在しない
- symlinkまたは特殊fileを検出する
- 保存先の暗号化、容量、checksum照合方法が不明
- 対象が現行test、CI、runbookから参照されている

## 10. 実行タイミング

- raw/archiveへfileを追加・変更・削除した直後
- 新しいarchive bundle/tagを作った直後
- 別媒体へ複製した直後
- archiveから実装を取り出す直前
- それ以外は定期cronを増やさず、重要なcleanup前に手動実行する
