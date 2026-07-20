<!--
作成日: 2026-07-20_19:49 JST
更新日: 2026-07-20_19:49 JST
-->

# ローカルmain文書統合計画

## チェックポイントID

`DOC-RECONCILE-2026-07-20`

## 目的

`origin/main` のA1実装を正本としつつ、分岐したローカル`main`にのみ存在した有用な調査・設計文書とリポジトリ理解レポートを、誤った現行手順を復活させずに統合する。

## 現状

- ローカル`main` は `origin/main` に対しahead 3 / behind 2だった。
- `origin/main` の統合基準は `427de2b62ebb21a613793aee92b1d49bbe69e09c`。
- ローカル側には仮説探索、Execution Replay、古いSeed Foundry指示、知識グラフがある。
- A1は既に`origin/main`で実装済みであり、A2開始はこの作業範囲外である。

## 制約

- ローカルcommitを一括cherry-pickしない。
- `.serena/project.yml`のtemplateドリフトは移植しない。
- A2、Execution Replay実装、新機能開発を始めない。
- 外部書き込み、push、依存関係変更を行わない。
- コード、テスト、schema、CLI helpを文書より優先する。

## 対象ファイル

- `.gitignore`
- `AGENTS.md`
- `docs/720-info/`
- `docs/plans/HYPOTHESIS_SEARCH_ENGINE_*.md`
- `docs/plans/CRYPTO_PERP_PORTFOLIO_CAPACITY_EXECUTION_REPLAY_2026-07-16.md`
- `plan/archive/2026-07-20-local-main-reconciliation/`
- `graphify-out/`
- `docs/final-summary.md`

## 実装方針と手順

1. リポジトリ理解レポートを専用ブランチでcommitし、消失リスクを先に潰す。
2. `origin/main` から専用統合ブランチとworktreeを作る。
3. 運用上有用な差分だけを選択移植する。
4. Execution Replayは未実装の設計案として`docs/plans/`へ配置する。
5. Seed Foundryのマージ前指示は警告付きで`plan/archive/`へ配置する。
6. 文書経路チェックと全品質ゲートを実行する。
7. 統合後のソースから知識グラフを最後に更新する。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `uv run pytest -q tests/test_docs_current_truth.py`
- `./scripts/check`
- `graphify update .`
- `git diff --check`

## 完了条件

- レポートがcommitで保全されている。
- 統合ブランチが`origin/main` のA1実装を含む。
- 計画文書がcurrent/archiveの境界に従っている。
- 全品質ゲートが成功する。
- 知識グラフが統合後のツリーを反映する。
- A2や新機能の実装が混入していない。

## 失敗条件

- ローカル差分の一括移植でA1実装を巻き戻す。
- 古いPR状態を現行指示として残す。
- 文書チェックまたは全品質ゲートが失敗する。
- ユーザーの既存変更を上書きする。

## 影響範囲

文書経路、作業ガイド、ローカル生成知識グラフに限定する。製品コード、schema、CLI、依存関係、runtime dataは変更しない。

## ロールバック方針

統合ブランチを使用せず`origin/main` の `427de2b`を維持する。元のローカル`main`とレポート保全ブランチは削除しない。

## 代替案

- 3 local commitの一括cherry-pick: A1前の文脈と無関係な設定ドリフトを復活させるため不採用。
- 文書を全廃棄: 調査と設計の資産を失うため不採用。
- 古いSeed指示をcurrent planに置く: 実行誤りのリスクが高いため不採用。

## 未解決事項

- Execution Replay設計を実装するかは未決定。実装する場合は現行コードに対する再設計・再承認が必要。
- A2の開始は本計画では扱わない。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/reconcile-main-20260720-1949`

## 移行手順

必要な場合のみ、検証済み統合ブランチを人間が`main`へ取り込む。この作業でpushやremote branch作成は行わない。
