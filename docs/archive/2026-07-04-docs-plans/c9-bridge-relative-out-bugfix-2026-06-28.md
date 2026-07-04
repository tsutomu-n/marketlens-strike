<!--
作成日: 2026-06-28_14:14 JST
更新日: 2026-06-28_14:14 JST
-->

# C9 Bridge Relative Out Bug Fix

## チェックポイントID

C9-REL-OUT-01

## 目的

`strategy-idea-candidates-authoring-bridge` が相対 `--out` で生成した C9 対応候補を `BRIDGED` にできるようにする。

## 現状

`_write_bridged_candidate_artifacts()` は相対 `out_dir` から作った `candidate_dir` を `_authoring_spec()` に渡している。`run_strategy_backtest_pack()` は repo root へ `chdir` して実行されるため、spec 内の裸の相対 data path が repo root 相対として解決され、生成済み parquet/csv を見つけられない。

## 制約

- 公開 CLI、schema、manifest field は変更しない。
- Strategy Authoring 全体の path resolver は変更しない。
- C9 bridge 生成物の spec path 表現だけを局所的に変える。
- 成功候補に古い `bridge_blocker.json` を残さない。

## 対象ファイル

- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`

## 実装方針

`feature_panel.parquet`、`quotes.parquet`、`venue_cost_matrix.csv` の実体を書いた後、それぞれの absolute path を `_authoring_spec()` に渡し、spec の `data.*_path` に absolute POSIX string を書く。`BRIDGED` 成功後は同じ candidate directory の stale `bridge_blocker.json` を削除する。

## 実装手順

1. 相対 `out_dir=Path("bridge_out")` で C9 対応 candidate が `BRIDGED` になる回帰テストを追加する。
2. テスト内で spec の data paths が absolute path かつ存在することを確認する。
3. stale `bridge_blocker.json` を事前に置き、成功後に削除されることを確認する。
4. `_authoring_spec()` の引数を artifact paths に変更する。
5. `_write_bridged_candidate_artifacts()` で `Path.resolve()` 済み path を spec に渡す。
6. 成功 artifact 書き込み後に stale blocker を削除する。

## テスト方針

- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py`
- `uv run pytest tests/strategy_idea_candidates/test_bitget_public_source.py::test_generated_source_root_can_feed_authoring_bridge`

## 完了条件

- 相対 `out_dir` の C9 対応 candidate が `BRIDGED` になる。
- `backtest_pack/strategy_backtest_pack.json` と validation JSON が生成される。
- spec の data paths は absolute path で実ファイルを指す。
- `BRIDGED` candidate に stale `bridge_blocker.json` が残らない。

## 失敗条件

- 相対 `out_dir` で `BLOCKED_BACKTEST_PACK` になる。
- Strategy Authoring の汎用 resolver や公開 CLI を変更する必要が出る。
- BLOCKED candidate の blocker 出力が消える。

## 影響範囲

C9 authoring bridge の生成 spec と成功 candidate directory の stale blocker cleanup に限定する。

## ロールバック方針

本変更を戻せば従来の相対 path spec 生成に戻る。schema や CLI 変更はないため追加 migration は不要。

## 代替案

- Strategy Authoring resolver を spec file 相対に変える案は、既存 authoring workflow へ波及するため採用しない。
- basename だけを書く案は、repo root 相対解決に引きずられるため不十分。

## 未解決事項

なし。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/post-c9-bitget-source-20260628-1113`

## 移行手順

不要。
