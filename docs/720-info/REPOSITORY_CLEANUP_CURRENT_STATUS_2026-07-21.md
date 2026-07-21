<!--
作成日: 2026-07-21_19:24 JST
更新日: 2026-07-21_19:24 JST
-->

# Repository Cleanup Current Status 2026-07-21

## 1. 結論

2026-07-21_19:24 JST時点で、`main`のcommitは`origin/main`と一致し、open PRは0件である。完了済みA1 worktree、誤mergeリスクのあったPR、merge済みbranch、古いHANDOFF、重複Graphify生成物は整理済みである。

一方、root working treeには今回の文書作成前から`.serena/project.yml`の未コミット変更がある。また、BT0 worktreeには未追跡実装15ファイル、Profit Core worktreeにはmain未収録の可能性がある大きな履歴が残る。これらは整理対象ではなく、保全対象である。

## 2. この文書の位置づけ

この文書は、2026-07-20のrepo全体調査後に行ったGit、GitHub、worktree、HANDOFF、Graphify生成物の整理結果と残リスクを記録する現行スナップショットである。

実装や挙動の正本ではない。判断時は、コード、テスト、schema、設定、lockfile、CI、CLI help、Git refを優先する。

## 3. 現在のGit状態

### 3.1 Root checkout

- path: `/home/tn/projects/marketlens-strike`
- branch: `main`
- HEAD: `d717e4b01b63c69996485ee46ff808bb9069c460`
- `origin/main`: `d717e4b01b63c69996485ee46ff808bb9069c460`
- commit relation: 同一
- working tree: cleanではない
- 文書作成前から存在した変更: `.serena/project.yml`

`.serena/project.yml`の差分は、Serenaの生成コメント、利用可能language一覧、workspace folder設定の更新を含む。この文書作成では内容を変更していない。所有者と採用可否を確認せず、他の変更と一緒にcommitしない。

### 3.2 Stash

調査時点でstashは存在しない。

## 4. GitHub状態

### 4.1 Pull Request

- open PR: 0件
- PR #49: repo調査文書とGraphify local-only方針をmainへ統合済み
- PR #48: Seed Foundry A1をmainへ統合済み
- PR #44: 2026-07-21にclose
- PR #46: 2026-07-21にclose

PR #44は、PR内に存在しないZIPを参照するREADMEとchecksumだけを追加する状態だったため、誤merge防止のためcloseした。

PR #46は、Git上はmerge可能だったが、現在のmainより古いSeed Foundry checklistとCI/doc validatorを含み、現行文書を意味的に巻き戻す可能性があったためcloseした。必要な検証は、現行mainから新しいPRとして再設計する。

### 4.2 削除済みremote branch

次の6本は、merge済みまたはclose済みであることを確認して削除した。

- `ai/human-review-packet-20260709-2200`
- `ai/post-merge-doc-status-20260711-2038`
- `ai/seed-foundry-a1-technical-walking-product-20260716-1654`
- `ai/seed-foundry-docs-20260716-1604`
- `ai/add-seed-foundry-archives-20260716-1522`
- `ai/seed-foundry-archive-completeness-20260716-1700`

## 5. Worktree状態

### 5.1 削除済みA1 worktree

次のworktreeは、PR #48でmainへ統合済み、working tree clean、主要変更がmainへ収録済みであることを確認して削除した。

```text
/home/tn/projects/marketlens-strike/.worktrees/marketlens-strike-a1-20260716-1654
```

A1のsmoke artifactとHANDOFFは削除せず、次へ退避した。

```text
/home/tn/projects/marketlens-strike/.tmp/archive/seed-foundry-a1-completed-20260721
```

退避内容は15ファイル、約320 KiBである。

### 5.2 保全中のBT0 worktree

- path: `/home/tn/projects/marketlens-strike/.worktrees/marketlens-strike-bt0-20260716-2325`
- branch: `ai/crypto-perp-portfolio-capacity-bt0-20260716-2325`
- HEAD: `5301bbf1f058b7d77783d725255aac0f35344225`
- upstream: なし
- working tree: 未追跡実装15ファイルあり

未追跡ファイルは`tools/backtest_spikes/crypto_perp_portfolio_capacity/`配下の実装、test、fixtureである。commit、patch、別媒体への退避のいずれもない状態でworktreeを削除してはいけない。

### 5.3 保全中のProfit Core worktree

- path: `/home/tn/projects/marketlens-strike/.worktrees/marketlens-strike-profit-core-impl`
- branch: `ai/profit-core-smart-priors-20260702-1952`
- HEAD: `21c458ad5d678326d627d82bc70dde8fbce24f75`
- upstream: `origin/ai/profit-core-smart-priors-20260702-1952`
- working tree: clean

このbranchはmainに対して長い独立履歴を持つ。先行調査では、branchで扱った57ファイルが現在のmainと異なっていた。PR記録がなく、単純なmerged判定や古さだけで削除できない。

### 5.4 Worktree容量

残る`.worktrees/`全体は約1.5 GiBである。大部分はworktreeごとの`.venv`である可能性が高いが、BT0の未追跡コードとProfit Core履歴を保全したまま、環境だけを削除する場合も事前確認が必要である。

## 6. Graphifyの現在地

### 6.1 保存方針

Graphify artifactはローカル専用で、今後もGit管理対象外とする。`.gitignore`の`graphify-out/`規則で除外されている。

### 6.2 現在残しているもの

- `graphify-out/graph.json`: 約49 MiB
- `graphify-out/manifest.json`
- `graphify-out/GRAPH_REPORT.md`
- community label、interpreter、root、cost情報

`graphify-out/`全体は約50 MiBである。

### 6.3 整理したもの

- `graphify-out/2026-07-20/`: 旧スナップショット
- `graphify-out/cache/`: 再生成可能なAST cache

上記とPytest、Ruff、Hypothesis cacheはデスクトップ環境のゴミ箱へ移動した。Graphify queryは整理後も正常動作を確認した。ゴミ箱を空にするまでは、物理ディスク上の容量が完全には解放されない。

## 7. HANDOFF状態

rootの`.ai_memory/HANDOFF.md`は、完了済みA1 worktreeへ誘導する古いrestart pointerだったため、active位置から除去した。

削除ではなく、A1完了archiveへ退避している。現在rootにactive HANDOFFはない。新しい継続作業を開始する場合は、古いA1 handoffを復活させず、その作業専用のrestart状態を新規作成する。

## 8. ローカル容量と保全判断

2026-07-21_19:24 JST時点の主な容量は次のとおり。

| Path | 容量 | 判断 |
| --- | ---: | --- |
| `graphify-out/` | 約50 MiB | 維持。ローカル専用 |
| `.worktrees/` | 約1.5 GiB | 未統合作業があるため一括削除禁止 |
| `.tmp/archive/seed-foundry-a1-completed-20260721/` | 約320 KiB | A1証跡として維持 |
| `.tmp/archive/refactor_cleanup_2026-06-25_0207/` | 約864 MiB | 一意なDB、Parquet、生ログの可能性があり要確認 |
| `data/raw/` | 約2.0 GiB | 市場観測データ。無条件削除禁止 |

## 9. 残るbranch整理リスク

remoteには、現在のmainへ未収録の可能性があるbranchが残る。

特に次は自動削除しない。

- `origin/ai/crypto-perp-portfolio-replay-20260716-2204`
- `origin/ai/profit-core-smart-priors-20260702-1952`
- Profit Coreの各checkpoint branch
- `origin/ai/refactor-repo-hygiene-20260701-2042`
- `origin/ai/strategy-ai-review-dogfood-route-20260701-2259`
- `origin/docs/crypto-perp-backtest-candidate-roadmap-20260705`
- `origin/docs/profit-core-reality-check-20260703`

Crypto Perp Portfolio Replay branchは、mainと異なる実装ファイルを持つがPRがない。Profit Core系branchは単純な祖先関係になっておらず、tip branchだけ残せば安全とは証明できていない。

## 10. 残リスクと推奨対応

### R1. `.serena/project.yml`の所有権が未確定

- 状態: rootに未コミット差分あり
- リスク: 今回のdocs変更と混ぜてcommitする
- 対応: Serena更新として採用するか、生成差分として戻すかを別タスクで判断する

### R2. BT0の未追跡コード

- 状態: 15ファイルがGit外
- リスク: worktree削除、clean操作、ディスク障害で消失する
- 対応: 内容review後、専用branchへcommitするかpatch/archiveを作る

### R3. Profit Coreの独立履歴

- 状態: cleanだがmain未収録の可能性がある
- リスク: 古いbranchとして一括削除する、または逆に不要なbranchを無期限に残す
- 対応: file単位のmain収録判定、必要機能の選別、保存tipまたはtagの決定を行う

### R4. PRなしremote実装

- 状態: Crypto Perp Portfolio Replay branchにmainと異なる実装がある
- リスク: 意図不明のまま放置、または誤削除
- 対応: test、設計文書、現在のproduct軸との整合をreviewし、PR化、archive、削除のいずれかを決める

### R5. 大きなlocal archive

- 状態: `.tmp/archive`に約864 MiB、`data/raw`に約2.0 GiB
- リスク: 容量圧迫と、根拠データの誤削除
- 対応: hash、生成元、再生成可否、他媒体backupを確認してから保存期限を決める

### R6. Graphの更新時点

- 状態: 現行graphはquery可能だが、この文書追加後のGit文書構成までは反映していない
- リスク: graphにないことをrepoに存在しないと誤認する
- 対応: 次にコードを変更した時、repo規則どおり`graphify update .`を実行する

## 11. 次に整理する場合の順序

1. `.serena/project.yml`差分の所有権と採否を確定する。
2. BT0の未追跡15ファイルをcommitまたはarchiveで保護する。
3. Crypto Perp Portfolio Replay branchをreviewする。
4. Profit Core worktreeと各branchの内容をfile単位で照合する。
5. `.tmp/archive/refactor_cleanup_2026-06-25_0207/`の再生成可否と保存期限を決める。
6. 上記が終わるまで、残る2 worktreeと未merge remote branchを削除しない。

## 12. 確認済みコマンド

主に次を使って現状を確認した。

```bash
git status --short --branch --untracked-files=all
git rev-parse HEAD
git rev-parse origin/main
git worktree list --porcelain
git branch -vv
git branch -r
git stash list
gh pr list --state open
gh pr view 44
gh pr view 46
du -sh graphify-out .worktrees .tmp/archive data/raw
graphify query "repository cleanup current status worktrees branches pull requests graphify artifact residual risks"
```

## 13. 更新条件

次のいずれかが起きた場合、この文書を再検証し、東京時間の`更新日`を更新する。

- mainまたはorigin/mainが進む
- PRを作成、close、mergeする
- worktreeまたはbranchを追加、削除する
- BT0またはProfit Coreをcommit、archive、統合する
- `.serena/project.yml`の扱いを確定する
- Graphify artifactを再生成する
- `.tmp/archive`または`data/raw`を移動、削除する
