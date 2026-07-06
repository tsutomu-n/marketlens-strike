<!--
作成日: 2026-07-06_18:03 JST
更新日: 2026-07-06_18:03 JST
-->

# No-Cash Backtest Gate Plan 2026-07-06

## チェックポイントID

CP-no-cash-backtest-gate-v1

## 目的

`crypto-perp-backtest-candidate-pack` の no-cash backtest evidence を Paper Observation 手前で評価する local gate artifact を追加する。

## 現状

`BACKTEST_CANDIDATE_HOLD` は local simulation に残るだけで、paper permission、actual cash readiness、live readiness ではない。Paper Observation へ進む前に、source、sample、stability、PBO、NO_TRADE 比較の不足を machine-readable に残す gate が必要。

## 制約

- actual cash source を要求しない。
- cash ledger を作らない。
- wallet / signing / exchange write を使わない。
- missing source を 0 埋めしない。
- `NO_TRADE` を trade action に差し替えない。
- Paper Observation への最終許可を出さない。

## 対象ファイル

- `src/sis/crypto_perp/no_cash_backtest_gate.py`
- `src/sis/commands/crypto_perp_no_cash_backtest_gate.py`
- `schemas/crypto_perp_no_cash_backtest_gate.v1.schema.json`
- `tests/crypto_perp/test_no_cash_backtest_gate.py`
- `docs/crypto_perp/NO_CASH_BACKTEST_GATE_V1.md`
- `src/sis/commands/crypto_perp.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- current docs / runbook / final summary

## 実装方針

Typed Pydantic artifact builder を追加し、CLI は既存 pack artifact JSON を読む薄い wrapper にする。Gate decision は `NO_CASH_BACKTEST_COLLECT_MORE_DATA`、`NO_CASH_BACKTEST_REVISE`、`NO_CASH_BACKTEST_REJECT`、`NO_CASH_BACKTEST_HOLD` の4択だけにする。

## 実装手順

1. gate artifact model、threshold constants、builder、writer、markdown renderer を追加する。
2. CLI `crypto-perp-no-cash-backtest-gate` を追加して登録する。
3. JSON schema を追加する。
4. legacy decision、collect/revise/reject/hold、optional source gap、CLI、schema の tests を追加する。
5. docs と CLI catalog を更新する。
6. required checks と `./scripts/check` を実行する。

## テスト方針

- `uv run pytest tests/crypto_perp/test_no_cash_backtest_gate.py -q`
- `uv run pytest tests/crypto_perp/test_backtest_candidate_pack.py -q`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- `./scripts/check`

## 完了条件

新CLIが登録され、schema が出力を検証し、tests/current-docs/catalog/full check が通る。artifact/stdout が profit proof、actual cash readiness、paper execution permission、live readiness、wallet/signing、exchange write を主張しない。

## 失敗条件

Paper permission や live readiness と読める decision name / stdout / artifact field を出す。missing books/trades/replay を pass として隠す。actual cash、wallet、signing、exchange write を前提にする。

## 影響範囲

Crypto Perp no-cash local simulation gate の追加のみ。既存 candidate pack の artifact contract は壊さない。

## ロールバック方針

新規 gate module/CLI/schema/tests/docs の差分を戻す。既存 backtest candidate pack の動作変更は行わない。

## 代替案

`BACKTEST_CANDIDATE_HOLD` を直接 Paper Observation の候補として読む案は、paper permission と誤読されるため採用しない。

## 未解決事項

なし。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/no-cash-backtest-gate-20260706-1758`

## 移行手順

なし。新CLIを必要時に実行するだけ。
