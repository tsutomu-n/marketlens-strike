<!--
作成日: 2026-07-20_19:33 JST
更新日: 2026-07-20_19:40 JST
-->

# 720 Info

## 結論

このフォルダーは、2026-07-20時点で`marketlens-strike`をコード、テスト、schema、設定、CLI、Git、runtime artifact、HANDOFF、graphify graphから調査した結果を集約する。

詳細は次の1文書にまとめる。

- [MarketLens Strike Repository Understanding 2026-07-20](MARKETLENS_STRIKE_REPOSITORY_UNDERSTANDING_2026-07-20.md)

## 読み方

最初に詳細文書の「最重要結論」「現在のGit状態」「安全境界」「検証結果」を読む。その後、必要なdomainの章へ進む。

このフォルダーは実装の正本ではない。判断時の優先順位は次のとおり。

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`
2. `pyproject.toml`, `.python-version`, `uv.lock`, `.github/workflows/ci.yml`
3. `uv run sis --help`
4. 対象commandが生成した`data/`配下のartifact
5. current docs
6. historical planとarchive

## 重要な注意

この調査時点のlocal `main`は`origin/main`に対してahead 3 / behind 2である。local `main`と`origin/main`は異なる変更を持ち、Seed Foundry A1は`origin/main`にのみ存在する。両者を同一のcurrent codeとして読まない。
