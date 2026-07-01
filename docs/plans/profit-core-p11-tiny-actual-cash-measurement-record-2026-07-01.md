<!--
作成日: 2026-07-01_17:15 JST
更新日: 2026-07-01_17:15 JST
-->

# Profit Core P11 Tiny Actual-Cash Measurement Record Plan

## チェックポイントID

P11: Tiny Actual-Cash Measurement

## 目的

human approval 済みの tiny actual-cash sample について、実 order intent、submitted order、fills、fees、funding、cash ledger、flat reconciliation、stop condition、NO_TRADE comparison を Profit Core candidate lineage に接続する。

この実装は actual-cash execution ではない。既にユーザー側で発生した実約定と ledger 証跡を local artifact として検証・記録するだけで、credential、order submit、exchange write、wallet、signing、external network は行わない。

## 現状

- P9 `profit_core_actual_cash_readiness_packet.v1` は actual cash 実行前の条件固定 packet であり、実行許可そのものではない。
- P10 `profit_core_external_venue_adapter_run.v1` は Bitget public read-only external adapter evidence であり、actual cash や order permission ではない。
- Crypto Perp 側には `crypto_perp_cash_ledger.v1` と `crypto_perp_actual_cash_rows_summary.v1` / actual cash rows JSONL がある。
- P12 actual cash report gate は後段で、P11 は candidate lineage に実 cash sample を接続する thin record とする。

## 制約

- CLI は外部 network、credential、order submit、exchange write、wallet、signing、live order を実行しない。
- paper/demo/testnet/estimate を actual cash として扱わない。
- `cash_metric_basis=actual_cash` かつ `actual_cash_result_usd` が実 ledger に接続している rows だけを actual cash とする。
- `NO_TRADE` comparison は同一 event set に必須。
- flat reconciliation と stop condition が欠ける場合は complete にしない。
- human approval artifact がない、または approved でない場合は complete にしない。

## 対象ファイル

- `schemas/profit_core_tiny_actual_cash_measurement.v1.schema.json`
- `src/sis/edge_candidates/tiny_actual_cash_measurement.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_tiny_actual_cash_measurement.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`

## 実装方針

`edge-candidate-tiny-actual-cash-measurement-record` を追加する。

入力:

- `--readiness-packet`: P9 readiness packet
- `--external-venue-adapter`: P10 adapter record
- `--human-approval`: user-provided approval artifact
- `--order-intent`: user-provided actual order intent artifact
- `--submitted-order`: user-provided submitted order artifact
- `--fills`: user-provided actual fills artifact
- `--fee-funding`: user-provided fee/funding evidence artifact
- `--cash-ledger`: `crypto_perp_cash_ledger.v1`
- `--actual-cash-rows`: actual cash rows JSONL or JSON array
- `--flat-reconciliation`: user-provided flat reconciliation proof
- `--stop-condition`: user-provided stop condition proof

出力:

- `profit_core_tiny_actual_cash_measurement.json`

status:

- `RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE`
- `BLOCKED_HUMAN_APPROVAL`
- `BLOCKED_UPSTREAM`
- `BLOCKED_NON_ACTUAL_CASH_BASIS`
- `BLOCKED_MISSING_NO_TRADE_COMPARISON`
- `BLOCKED_FLAT_RECONCILIATION`
- `BLOCKED_STOP_CONDITION`
- `BLOCKED_CANDIDATE_LINEAGE`

## 実装手順

1. RED tests を追加する。
2. schema と Pydantic model を追加する。
3. P9/P10 upstream status、candidate id、approval、order/fill/fee/funding evidence を検査する。
4. cash ledger と actual-cash rows を読み、同一 event set と `NO_TRADE` を検査する。
5. flat reconciliation と stop condition を検査する。
6. CLI command を追加する。
7. CLI catalog と final summary を更新する。
8. focused tests、ruff、CLI catalog、current docs、full check を実行する。

## テスト方針

- complete artifact で `RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE` になる。
- human approval がない、または approved でない時は `BLOCKED_HUMAN_APPROVAL`。
- actual cash rows が `cash_metric_basis=actual_cash` でない時は `BLOCKED_NON_ACTUAL_CASH_BASIS`。
- `NO_TRADE` が同一 event set にない時は `BLOCKED_MISSING_NO_TRADE_COMPARISON`。
- flat reconciliation が false の時は `BLOCKED_FLAT_RECONCILIATION`。
- stop condition が未定義の時は `BLOCKED_STOP_CONDITION`。
- CLI stdout は `network_attempted=false`、`exchange_write_used=false`、`live_order_submitted=false` を出す。
- schema validation が通る。

## 完了条件

- P11 schema/model/CLI がある。
- P9/P10/upstream/user evidence refs と sha256 を持つ。
- actual-cash result が actual cash rows と cash ledger から出る。
- `NO_TRADE` comparison、flat reconciliation、stop condition を complete 条件にする。
- この CLI が actual-cash execution を実行しないことを boundary で固定する。
- focused tests、CLI catalog、current docs、full check が通る。

## 失敗条件

- この CLI が order submit、credential use、exchange write、wallet、signing、external network を実行する。
- demo/testnet/paper/estimate を actual cash と扱う。
- `NO_TRADE`、flat reconciliation、stop condition が欠けても complete status を出す。
- cash ledger と rows の actual cash result がつながらない。

## 影響範囲

Profit Core edge candidate workflow の artifact surface と CLI catalog に限定する。Crypto Perp cash ledger / actual-cash report gate、external venue order path、credential handling は変更しない。

## ロールバック方針

追加した schema、module、test、CLI registration、docs addendum を削除または revert する。既存 P9/P10 artifacts と Crypto Perp actual cash ledger/report gate は変更対象外。

## 代替案

- 実 order submit を CLI に含める案: この `Go` だけでは明示承認・credential・法務/venue condition が足りず、repo stop condition に反するため却下。
- P12 report gate に統合する案: P12 は report/gate で、P11 は order/fill/ledger lineage record なので分ける。

## 未解決事項

なし。実取引の実行可否はこの artifact の範囲外。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-p11-tiny-actual-cash-record-20260701-1712`

## 移行手順

なし。
