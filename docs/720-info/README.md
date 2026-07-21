<!--
作成日: 2026-07-20_19:33 JST
更新日: 2026-07-21_19:24 JST
-->

# 720 Info

## 結論

このフォルダーは、`marketlens-strike`をコード、テスト、schema、設定、CLI、Git、runtime artifact、HANDOFF、Graphify graphから調査した結果を集約する。

現在のGit、GitHub、worktree、Graphify、整理状態は、先に次を読む。

- [Repository Cleanup Current Status 2026-07-21](REPOSITORY_CLEANUP_CURRENT_STATUS_2026-07-21.md)

repo全体の詳細調査は次にまとめる。Git状態とworktree状態は2026-07-20時点のhistorical snapshotであり、現状判断には上の2026-07-21文書を使う。

- [MarketLens Strike Repository Understanding 2026-07-20](MARKETLENS_STRIKE_REPOSITORY_UNDERSTANDING_2026-07-20.md)

## 読み方

最初に2026-07-21の現行状態文書を読み、その後、詳細文書の「最重要結論」「安全境界」「検証結果」と必要なdomainの章へ進む。

このフォルダーは実装の正本ではない。判断時の優先順位は次のとおり。

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`
2. `pyproject.toml`, `.python-version`, `uv.lock`, `.github/workflows/ci.yml`
3. `uv run sis --help`
4. 対象commandが生成した`data/`配下のartifact
5. current docs
6. historical planとarchive

## 重要な注意

2026-07-20の詳細文書にあるlocal `main`のahead / behind、A1 worktree、root HANDOFFの記述は、統合前のhistorical snapshotである。2026-07-21時点では`main`と`origin/main`のcommitは一致し、A1 worktreeと古いroot HANDOFFは整理済みである。

ただし、root working treeには`.serena/project.yml`の未コミット変更があり、BT0とProfit Coreのworktreeには未統合作業が残る。commit一致をrepo全体のclean状態と混同しない。
