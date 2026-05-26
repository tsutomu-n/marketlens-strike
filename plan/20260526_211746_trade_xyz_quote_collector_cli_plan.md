# Trade[XYZ] Quote Collector CLI Plan

Timestamp: 2026-05-26 21:17:46 JST

## 結論

`src/sis/cli.py` のリファクタリングが完了した後に、`trade_xyz` quote collector を public CLI として追加する。
この文書は、その時点で読み直して実装判断を再開するための decision memo である。

## いま実装しない理由

- 現在の `src/sis/cli.py` は command registration と helper が一枚に寄っており、これから行うリファクタリングで構造が変わる可能性が高い。
- `trade_xyz` collector の CLI 化は、command 追加だけではなく、registry 読込、出力先、normalize 実行、recommended read order 出力まで触る可能性がある。
- 先に CLI 化すると、直後のリファクタリングと衝突して差分が二度手間になりやすい。

## リファクタ後に最初に確認すること

1. `src/sis/cli.py` がどう分割されたか
2. 既存 command の共通 helper がどこへ移ったか
3. `probe trade-xyz` が返す registry artifact と、その読み直し経路
4. quote collection 系 command を追加するなら、どの module / command group に置くのが自然か
5. `recommended_read_order` 出力の共通化方法

## 実装方針

優先方針:

- `gtrade` 専用の `log-quotes` を無理に汎用化しない
- `trade_xyz` 向けには別 command を追加する
- command 名は `collect-trade-xyz-quotes` を第一候補にする

この方針を優先する理由:

- 既存 `log-quotes` は sidecar replay 前提であり、`trade_xyz` の live API collection と責務が異なる
- 同じ command 名に混在させると option shape と help text が不自然になりやすい
- refactor 後の CLI 構造でも、独立 command のほうが tests と docs の保守が簡単

## 想定 command contract

第一候補:

```bash
uv run sis collect-trade-xyz-quotes
```

候補 options:

- `--registry-path`: default は `data/registry/trade_xyz_instrument_registry.json`
- `--normalize/--no-normalize`: default は `--normalize`
- `--date`: 必要なら明示、未指定なら当日UTC

やらないこと:

- `log-quotes --venue trade_xyz` への相乗り
- micro live や paper cycle をこの command から直接呼ぶこと
- real market / tracking artifact の自動再生成まで広げること

## 想定動作

1. Trade[XYZ] registry を読む
2. active instruments のみ collect する
3. `data/raw/quotes/trade_xyz/<YYYY-MM-DD>.jsonl` に保存する
4. `--normalize` 有効時は `data/normalized/quotes.parquet` と `data/normalized/sis.duckdb` を更新する
5. 終了時に件数と artifact path を出す
6. 他の CLI と同様に `recommended_read_order_*` を出す

## エラー方針

- registry file が無い: exit code 2
- registry に active `trade_xyz` instruments が無い: exit code 2
- API fetch 失敗は collector 既存挙動を尊重し、各 symbol を fail-closed quote として保存する
- command 全体が完全失敗した場合だけ non-zero exit

## 実装対象

- `src/sis/cli.py` またはリファクタ後の CLI module
- 必要なら CLI helper module
- `tests/test_cli_smoke.py`
- 必要なら collector command 専用 test file
- `README.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/CURRENT_STATE.md`

## テスト計画

最小:

- command が exit 0 で動く
- `recommended_read_order_1=docs/CURRENT_STATE.md` を出す
- raw quote JSONL が生成される
- `--normalize` default で normalized artifacts が更新される

追加:

- `--no-normalize` で normalize を呼ばない
- registry missing で exit 2
- inactive / non-orderable symbol を混ぜても active target のみ処理する
- API error payload 時も collector 既存 fail-closed 挙動を壊さない

## docs 更新方針

CLI 化の実装後に次を更新する:

- `README.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/CURRENT_STATE.md`
- 必要なら `docs/CODE_STATUS.md` ではなく generated source `src/sis/reports/implementation_status.py`

## 完了条件

- public CLI から Trade[XYZ] quote collection を実行できる
- docs に unsupported command が残らない
- `./scripts/check` が通る
- `trade_xyz` collector が code/test surface だけでなく operator-facing CLI surface に昇格したと説明できる
