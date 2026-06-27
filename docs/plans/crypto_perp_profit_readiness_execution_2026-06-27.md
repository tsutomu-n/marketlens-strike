<!--
作成日: 2026-06-27_19:01 JST
更新日: 2026-06-27_19:01 JST
-->

# Crypto Perp Profit-Readiness Execution Plan

## チェックポイントID

`PR-00` through `PR-F`

## 目的

Crypto Perp Truth-Cycle MVP の既存artifact chainを再実装せず、利益判断用の source availability、replay slice、feature pack、deterministic edge scoring、cost-aware tournament rows、bias guard、operator decision surface、tiny-live shadow を追加する。

## 現状

- `crypto_perp_tournament_rows_preview.v1` は outcome before-cost proxy を3action rowsへ変換する。
- `crypto_perp_tournament_report.v1` は `actual_cash_result_usd` primaryで同一event setを比較できる。
- preview由来の不足は known gaps として gate へ渡るが、cost-adjusted estimate 専用surfaceはまだない。
- source availability、minimal replay slice、edge scorer、tiny-live shadow artifact は未実装。

## 制約

- 依存追加なし。
- 外部API送信、credential生成・変更、exchange write、live orderなし。
- `actual_cash_result_usd` と estimate/proxy を混同しない。
- `NO_TRADE` を失敗扱いしない。
- 欠損 source を0埋めしない。

## 対象ファイル

- `docs/crypto_perp/`
- `docs/plans/`
- `docs/CURRENT_STATE.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `scripts/check_current_docs.py`
- `src/sis/crypto_perp/`
- `src/sis/commands/`
- `schemas/crypto_perp_*.schema.json`
- `tests/crypto_perp/`

## 実装方針

既存 v1 artifactを壊さず、profit-readiness用の追加artifactを隣接実装する。operator-facing surfaceには追加artifactの要約だけ出し、live permission や actual cash claim に昇格させない。

## 実装手順

1. PR-00 docsを追加し、current docs checkerの対象に入れる。
2. Source Availability Matrixを追加する。
3. Replay SliceとFeature Packを追加する。
4. Deterministic Edge Scorerを追加する。
5. Cost-aware Tournament Rows v2を追加する。
6. Bias Guard reportを追加する。
7. Event Card / Truth-Cycle Status / Workbench Bridgeへ追加summaryを反映する。
8. Tiny-live Shadow artifactを追加する。
9. Focused tests、CLI catalog、current docs、full checkを実行する。

## テスト方針

- `uv run pytest tests/crypto_perp -q`
- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `./scripts/check`
- `git diff --check`

## 完了条件

本計画の完了条件は [../crypto_perp/PROFIT_READINESS_EVIDENCE_PLAN_2026-06-27.md](../crypto_perp/PROFIT_READINESS_EVIDENCE_PLAN_2026-06-27.md) に従う。

## 失敗条件

- estimate/proxy を actual cash として出す。
- source欠損を0埋めする。
- live order / exchange write に到達する。
- tests または docs checker が現行仕様と矛盾する。

## 影響範囲

Crypto Perp local artifact chain、CLI catalog、current docs のみ。Paper/live execution、wallet/signing、外部送信は対象外。

## ロールバック方針

追加ファイルと追加fieldを戻す。既存 v1 tournament/report path は互換を保つため、既存利用者は旧surfaceへ戻せる。

## 代替案

既存 `tournament_report.v1` を直接 cost-aware primary に変更する案は、既存 actual cash semantics を壊しやすいため採用しない。

## 未解決事項

なし。実cash ledgerとの接続は、cash ledger/live measurement artifactがある時だけ別途扱う。

## 破壊的変更の有無

なし。既存surfaceは維持し、profit-readiness v1/v2追加で対応する。

## ブランチ名

`ai/crypto-perp-profit-readiness-20260627-1901`

## 移行手順

既存 rows preview は継続利用可。利益判断用には `crypto_perp_tournament_rows.v2` と `crypto_perp_bias_guard.v1` を併用する。
