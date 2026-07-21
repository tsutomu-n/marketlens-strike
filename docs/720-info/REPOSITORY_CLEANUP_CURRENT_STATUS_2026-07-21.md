<!--
作成日: 2026-07-21_19:24 JST
更新日: 2026-07-22_06:53 JST
-->

# Repository Cleanup Current Status 2026-07-21

## 1. 結論

2026-07-22_06:49 JST時点で、保留されていたBT0、Execution Replay、Profit Core、その他の旧branchはすべて「mainへ限定統合」または「復旧可能なarchiveへ退避」のどちらかに分類済みである。さらにmainとarchive tagをGitHub rulesetで保護し、local evidenceをSHA-256台帳化した。

- mainへ統合: repo現況文書、Crypto Perp Portfolio CapacityのPR-BT0 discovery spike
- 未統合: Execution Replay、Profit Core、旧Strategy AI Review、旧計画branch
- local/remoteの通常branch: mainだけ
- worktree: root checkoutだけ
- open PR: この文書用PRを作る前は0件
- root working tree: この文書作成前はclean
- Graphify: 約51 MiBのactive artifactだけをローカル保持し、Git対象外

未統合branchを誤ってpushまたはmergeするリスクは解消した。履歴は削除せず、remote archive tagとlocal Git bundleで復旧可能にしている。

## 1.1 2026-07-22 hardening

- Protect main delivery、ruleset ID 19483352、active
- Protect archive tags、ruleset ID 19483353、active
- main: PR、check、最新mainとの同期、linear history、review thread解消を必須化
- main: branch削除とforce pushを禁止
- archive/*: 既存tagの更新、削除、force updateを禁止
- .tmp/archive: 958 files、850,136,529 bytesをSHA-256台帳化・verify済み
- data/raw: 109 files、2,096,766,465 bytesをSHA-256台帳化・verify済み
- 3 bundle: 空repositoryへのfetch、git fsck、expected commit、remote tag一致を確認

手順の正本は[Local Artifact Retention And Recovery Runbook](../runbooks/LOCAL_ARTIFACT_RETENTION_AND_RECOVERY.md)である。

## 2. mainへ反映した内容

### 2.1 現況文書

- PR #50: docs: refresh repository cleanup status
- CI成功後にReadyへ変更し、squash merge
- merge commit: 4e3ae49ac34daeb00514c5283b88acd03b6ce545

### 2.2 Portfolio Capacity PR-BT0

- PR #51: research: add portfolio capacity discovery spike
- CI成功後にReadyへ変更し、squash merge
- merge commit: 9fcffb351ca339c75366e69412b90597f0061ce0
- 統合範囲: tools/backtest_spikes/crypto_perp_portfolio_capacity/ 配下の15ファイルだけ
- 非対象: src、public CLI、schema、依存、lockfile、production execution

元worktreeの未追跡15ファイルは、commit fe03934ae310febb7e5013b51212524585f45712 として先に保護した。cleanなorigin/mainから作った統合branchへcherry-pickし、full quality gateを通してからPR化した。

## 3. 検証結果

Portfolio CapacityのVectorBT込みfocused testは31 passed。clean-main統合worktreeで scripts/check を実行し、次を確認した。

- Ruff lint / format check: success
- current-docs / CLI catalog: success
- Pyrefly: 0 errors
- ty: success
- Pytest: 3185 passed, 2 skipped in 118.87s

最初のfull checkでは、repo内の.worktrees配下をPyreflyが除外したためsourceを発見できなかった。コード不良ではなく検証配置の問題だったため、統合worktreeをrepo外へ移し、Python 3.13のvenvを作り直して再実行した。

## 4. 未統合履歴の処理

### 4.1 Execution Replay

旧branchはmainにない実装17ファイル、18 commit、約3,388行の追加を持っていたが、branch固有のtestと現行設計文書がなく、Trade[XYZ]を標準軸へ戻す内容を含むためmergeしていない。

- 保存tag: archive/crypto-perp-portfolio-replay-20260716
- 保存bundle: .tmp/archive/git-bundles/crypto-perp-portfolio-replay-20260716.bundle
- bundle SHA-256: 9b4660fdf02d78ff98bbc631b8a226f876ae92a494c8155c06dda292f30ae28d
- 元branch: local/remoteとも削除済み

Portfolio Capacityとして再利用できる狭い部分だけをPR-BT0として統合した。

### 4.2 Profit Core

15 local branchと14 remote branchを監査した。各predecessorの変更pathはすべて最終tipにも存在したが、履歴は単純な祖先関係ではなく、blobも完全一致しなかった。そのため15 tipすべてをparentに持つarchive anchorを作った。

- archive anchor: 6f3d7a2c4109f9e730194b498aad037e42fb8b8f
- 保存tag: archive/profit-core-branch-set-20260721
- 保存bundle: .tmp/archive/git-bundles/profit-core-branch-set-20260721.bundle
- bundle SHA-256: 492615e45d734d7011cf9460eb495adc23fccb6cc7c569de94093a36665467d7
- archive前focused test: 81 passed
- 元branch: local/remoteとも0本
- 元worktree: clean確認後に削除

Profit Coreは現行mainへ戻していない。特にactual cash関連をarchiveからそのまま再有効化してはならない。

### 4.3 その他の旧branch

Portfolio Capacityの2 branch、旧repo hygiene、旧Strategy AI Review、旧roadmap、旧Profit Core reality-checkの6 tipを1つのarchive anchorへ集約した。

- 保存tag: archive/legacy-branch-set-20260721
- peeled target: fbe65b32f5d45774b08e3d453cb02f24852857b0
- 保存bundle: .tmp/archive/git-bundles/legacy-branch-set-20260721.bundle
- bundle SHA-256: b733705943af0957b433c82c050fede671f17e78706161d4b369140aa12f7d1c
- bundle検証: complete history
- 元branch: local/remoteとも削除済み

## 5. 現在のGitとworktree

- local branch: mainだけ
- remote tracking branch: origin/mainだけ
- worktree: /home/tn/projects/marketlens-strike だけ
- stash: なし
- .serena/project.yml: main版へ復元済み

Serena差分は別versionが生成したcomment/template driftで、採用根拠がなかった。差分と同じ内容はBT0の保護commitにも残るため、rootではmain版へ戻した。

## 6. Archiveと復旧

復旧用tagはremoteへpush済みで、bundleはGit管理外のlocal backupである。

| tag | 主な内容 | bundle |
|---|---|---:|
| archive/crypto-perp-portfolio-replay-20260716 | Execution Replay全履歴 | 約30 MiB |
| archive/profit-core-branch-set-20260721 | Profit Core 15 tip全履歴 | 約30 MiB |
| archive/legacy-branch-set-20260721 | その他6 tip全履歴 | 約31 MiB |

archive tagは保存用であり、そのままmainへmergeする入口ではない。再利用時は必要なfile/commitだけを現行mainから作った専用branchへ抽出し、現行testと安全境界を再適用する。

## 7. Graphify

- active graph.json: 約49 MiB
- graphify-out全体: 約51 MiB
- .gitignoreのgraphify-out/で除外
- Git追跡なし、local-only方針を継続

graphify update . を実行し、47,964 nodes、68,212 edgesへ更新した。更新時に生成された約60 MiBのcacheは再生成可能なため削除し、active artifactだけを残した。

## 8. local archiveと一時領域

### 8.1 Refactor cleanup archive

.tmp/archive/refactor_cleanup_2026-06-25_0207/ の大容量4ファイルをSHA-256で比較した。2つのParquetが完全一致したため、代表コピーを残し、recheck_trade_xyz_ws_quotes_24h.parquetだけを削除した。

- 削減: 146,177,670 bytes
- .tmp/archive整理後: 約815 MiB
- hashが異なる、または唯一のDB/Parquetは保持
- local manifest: .tmp/archive/refactor_cleanup_2026-06-25_0207/ARCHIVE_MANIFEST.md

### 8.2 Pytest一時領域

/tmp/pytest-of-tn/garbage-* の74 directory、約5.5 GiBは、過去の別repo test名を含むpytest cleanup失敗物だった。active pytest processがないことを確認し、対象をgarbage-*へ限定して削除した。その後のfocused testでcleanup warningは再発していない。

## 9. 削除対象と復旧性

| 対象 | 理由 | 復旧性 |
|---|---|---|
| 旧local/remote branch | 誤push・誤merge入口を除去 | remote tagとcomplete bundleから復旧可 |
| 不要worktreeとvenv | branch保護後の重複checkout | tag、bundle、mainから再作成可 |
| Graphify backup/cache | active graphから再生成可能 | graphify updateで再生成可 |
| 重複Parquet 1個 | SHA-256完全一致 | 同一hashの代表コピーを保持 |
| pytest garbage 約5.5 GiB | 失敗した一時cleanup物 | 復旧不可、実行成果ではない |

## 10. 残リスク

### R1. 別媒体backup先は未指定

remote archive tagはruleset保護済みで、local bundleは実fetchとfsckまで検証した。ただしbundleと一意raw dataの別媒体保存先、暗号化鍵、保存年限は未指定である。保存先を推測した外部送信は行わず、runbookの複製・checksum手順を使う。

### R2. local-only raw/archive data

一意性が確認できないデータは削除していない。2 rootともpath、size、mtime、SHA-256のlocal-only manifestを生成・verify済みである。保存期限や別媒体方針が決まるまでは、容量だけを理由に一括削除しない。

### R3. archiveコードは現行保証外

archiveは履歴保全であり、alpha、paper/live readiness、安全性、現行schema互換を証明しない。再利用時は現行mainへ部分抽出し、計画、test、review、CIをやり直す。

### R4. Graphifyはsnapshot

将来の変更を自動的に保証しない。コード変更後はgraphify updateを実行し、生成物は引き続きGitへ追加しない。常駐watchと自動commitは採用しない。

## 11. 今後の予定

必須のrepository hardening作業はない。通常開発は保護済みmainを対象とするPRから開始できる。

利用者が別媒体保存先を決めた場合だけ、3 bundleと2 manifestを暗号化済み保存先へ複製し、保存先でSHA-256を再照合する。archive実装を再利用する場合は、archive全体ではなく必要部分だけを現行mainから作った新branchへ抽出する。

## 12. 完了判定

BT0保護、限定統合、CI後merge、未統合履歴の監査と退避、通常branch/worktree整理、Serena差分分離、Graphify local-only維持、exact duplicateだけの削除、GitHub ruleset、local SHA-256台帳、bundle restore drillを完了したため、repository cleanupとhardeningは完了と判定する。
