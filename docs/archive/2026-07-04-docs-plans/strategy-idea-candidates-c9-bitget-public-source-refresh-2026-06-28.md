<!--
作成日: 2026-06-28_10:54 JST
更新日: 2026-06-28_10:54 JST
-->

# C9 Repo-Native Bitget Public Source Refresh

## チェックポイントID

C9-bitget-public-source-refresh-2026-06-28

## 目的

`prep-watchdeck` に runtime 依存せず、この repo だけで Bitget public REST から `USDT-FUTURES` の contracts / tickers / 5m candles を取得し、既存 C9 `strategy-idea-candidates-authoring-bridge` が読める互換 source root を生成する。

## 現状

- C9 authoring bridge は `--prep-watchdeck-root` として `data/scanner.duckdb`、`data/candles_5m/date=*/candles.parquet`、`var/snapshots/latest.json` を読む。
- 既存 `BitgetPublicClient` は httpx ベースの public GET client として存在する。
- repo-native な C9 source root 生成 CLI はまだ無い。

## 制約

- private API、wallet、signing、注文、position、balance endpoint は使わない。
- network 実行は `SIS_ALLOW_PUBLIC_NETWORK=1` または `--network` の明示 opt-in がある時だけ許可する。
- 新依存は追加しない。既存 `httpx`、`polars`、`duckdb` を使う。
- 初期対象は Bitget `USDT-FUTURES`、REST public endpoint、5m candles のみ。
- WebSocket、常駐 service、deep backfill、orderbook depth、実測 slippage は対象外。
- 出力は `--out/source_root/` に隔離し、global `data/research` に混ぜない。

## 対象ファイル

- `src/sis/crypto_perp/bitget/public_api.py`
- `src/sis/crypto_perp/bitget/normalizers.py`
- `src/sis/strategy_idea_candidates/bitget_public_source.py`
- `src/sis/commands/strategy_idea_candidates.py`
- `tests/strategy_idea_candidates/test_bitget_public_source.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `.ai-work/state.md`

## 実装方針

1. Bitget mix public endpoint 用の thin API method と normalizer を追加する。
2. `refresh_bitget_public_source()` で contracts / tickers / paginated history candles を取得する。
3. open candle は current bucket 以上の timestamp を除外する。
4. `scanner.duckdb`、partitioned 5m parquet、latest snapshot、manifest を `--out/source_root/` 配下へ書く。
5. CLI `strategy-idea-candidates-bitget-source-refresh` を追加し、network opt-in が無い場合は出力前に exit 2 にする。

## テスト方針

- `httpx.MockTransport` で contracts / tickers / history-candles を固定応答にする。
- limit が Bitget history-candles page cap を超える時、複数 request になることを確認する。
- open candle が出力に入らないことを確認する。
- 生成された source root を `load_prep_watchdeck_source()` と C9 authoring bridge が読めることを確認する。
- CLI は opt-in 無しで exit 2 になり、出力を書かないことを確認する。

## 完了条件

- この repo だけで C9 bridge 用 Bitget public source root を生成できる。
- 生成 root は既存 `load_prep_watchdeck_source()` で読める。
- 生成 root を `strategy-idea-candidates-authoring-bridge --prep-watchdeck-root` に渡せる。
- artifact と CLI stdout に network / credential / exchange-write 境界が残る。

## 失敗条件

- network opt-in 無しで request または出力が発生する。
- private / credentialed / exchange write endpoint を使う。
- generated source root が既存 C9 bridge reader で読めない。

## 影響範囲

`strategy_idea_candidates` の C9 source generation surface と Bitget public normalizer/API の追加に限定する。既存 authoring bridge の `--prep-watchdeck-root` 名は互換 root 入力として維持する。

## ロールバック方針

新規 `bitget_public_source.py` とテストを削除し、`public_api.py` / `normalizers.py` / command / docs の追加分だけを戻す。既存 C9 authoring bridge はそのまま残せる。

## 代替案

- `prep-watchdeck` を submodule / runtime dependency にする: repo 単独運用と依存境界が悪くなるため不採用。
- C9 bridge の `--prep-watchdeck-root` を rename する: 既存 CLI 互換を壊すため不採用。
- WebSocket / deep backfill まで移植する: 初期 C9 source root 生成には過剰なため不採用。

## 未解決事項

- 実測 slippage、orderbook depth、actual cash proof、paper/live permission は別 scope。

## 破壊的変更の有無

なし。新規 CLI と source writer の追加で、既存 bridge 入力名は維持する。

## ブランチ名

`ai/c9-prep-watchdeck-bridge-20260628-1016`
