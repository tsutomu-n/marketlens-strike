<!--
作成日: 2026-06-28_18:57 JST
更新日: 2026-06-28_18:57 JST
-->

# Risk-Taker Review Artifact 実装計画

## チェックポイントID

CP1 risk-taker review artifact

## 目的

`crypto_perp_tournament_rows.v2`、`crypto_perp_source_availability.v1`、`crypto_perp_bias_guard.v1` を読み、候補を実行前に `READY_FOR_HUMAN_RISK_REVIEW`、`NEEDS_ACTUAL_CASH`、`BLOCKED_BY_VENUE`、`INCONCLUSIVE_DATA`、`KILL` へ分類する local-only review artifact を追加する。

## 現状

- `crypto-perp-profit-readiness-run-local` は source availability、cost-aware rows、bias guard を local artifact として生成できる。
- `crypto-perp-tournament-gate` は actual-cash tournament report 用の gate で、非 actual cash を `NEEDS_ACTUAL_CASH` に止める。
- `CryptoPerpBoundary` は live order、wallet、signing、exchange write、live order submitted を false 固定にできる共通モデル。
- current docs は CLI catalog と implemented/current-state docs の整合検査対象。

## 制約

- external API、wallet、signing、exchange write、live order、tiny-live measurement は使わない。
- `actual_cash_result_usd=null` の estimate を actual cash proof と読まない。
- `operator_jurisdiction_status != allowed` は live / credential / tiny-live へ進めない。
- `NO_TRADE` leader は trade action 採用不可。
- 既存 `crypto-perp-tournament-gate` の責務を増やさない。
- public CLI / schema 追加なので専用ブランチ上で実装する。

## 対象ファイル

- `src/sis/crypto_perp/risk_taker_review.py`
- `src/sis/commands/crypto_perp_risk_taker_review.py`
- `src/sis/commands/crypto_perp.py`
- `schemas/crypto_perp_risk_taker_review.v1.schema.json`
- `tests/crypto_perp/test_risk_taker_review.py`
- `tests/crypto_perp/test_risk_taker_review_command_registration.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/CURRENT_STATE.md`
- `docs/final-summary.md`

## 実装方針

- Pydantic model と判定ロジックは `src/sis/crypto_perp/risk_taker_review.py` に置く。
- Typer wrapper は thin command として `src/sis/commands/crypto_perp_risk_taker_review.py` に置く。
- rows は action ごとに集約し、`NO_TRADE` total と比較する。
- source availability、bias guard、operator jurisdiction、source freshness、liquidation buffer を条件化する。
- 条件は `conditions` に全件残し、失敗理由と `known_gaps` を artifact に残す。
- どの status でも boundary は false のままにする。

## 実装手順

1. `risk_taker_review.py` に schema version、status/action literal、condition model、summary model、`build_risk_taker_review()` を追加する。
2. JSON schema を Pydantic dump に合う形で追加する。
3. CLI を追加し、入力 artifact を validate して JSON / Markdown を書く。
4. `register_crypto_perp_commands()` に CLI 登録を追加する。
5. focused tests と command registration tests を追加する。
6. current docs と CLI catalog を更新する。
7. focused tests、CLI help、catalog/current-doc checks、whitespace check を実行する。

## テスト方針

- model tests:
  - allowed + fresh + positive stress edge + actual cash available で `READY_FOR_HUMAN_RISK_REVIEW`
  - prohibited / unknown jurisdiction で `BLOCKED_BY_VENUE`
  - stale / unknown source freshness で `INCONCLUSIVE_DATA`
  - estimate-only positive edge で `NEEDS_ACTUAL_CASH`
  - `NO_TRADE` leader、negative stress edge、bias guard blocked で `KILL`
  - schema validation passes with `Draft202012Validator`
- CLI tests:
  - JSON / Markdown を書く
  - stdout に false permission boundary が出る
  - `--help` に required options が出る
  - invalid artifact schema は exit 2
- regression:
  - `crypto-perp-tournament-report` は estimate rows を引き続き拒否する
  - existing tournament gate tests を変えずに通す

## 完了条件

- `crypto-perp-risk-taker-review` が public CLI に登録される。
- `crypto_perp_risk_taker_review.v1` schema が artifact を validate する。
- artifact が jurisdiction、source freshness、NO_TRADE 比較、after-cost edge、stress edge、operator time、tail risk、known gaps を出す。
- actual cash が無い estimate は `READY_FOR_HUMAN_RISK_REVIEW` にならない。
- live / credential / exchange-write / tiny-live permission を出さない。
- focused tests、CLI catalog、current docs、whitespace check が通る。

## 失敗条件

- existing tournament gate の semantics を変える。
- estimate-only を human risk review ready にする。
- false-only boundary 以外を出す。
- 外部 network / credential / exchange write / live order に触れる。

## 影響範囲

新規 standalone CLI と schema の追加、crypto-perp docs の current surface 記述更新。既存 artifact builder と actual-cash gate は変更しない。

## ロールバック方針

新規 model、command、schema、tests、docs 追記を取り除き、`src/sis/commands/crypto_perp.py` の登録行を戻す。既存 runtime data や dependency lock は変更しない。

## 代替案

- `crypto-perp-tournament-gate` に組み込む案: actual-cash gate と risk-taker research review の責務が混ざるため採用しない。
- profit-readiness run-local に組み込む案: jurisdiction / freshness の明示入力と human review artifact の独立性が弱くなるため、v1 では standalone CLI にする。

## 未解決事項

なし。threshold は existing tournament gate の近い値を conservative default として使う。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/risk-taker-review-artifact-20260628-1721`

## 移行手順

なし。新規 CLI のみ。

## 実装前 Critique

- 用語衝突: `READY_FOR_HUMAN_RISK_REVIEW` は live / tiny-live readiness ではない。stdout と Markdown に `permits_live_order=false` を必ず出す。
- 責任境界: actual-cash tournament gate は触らず、risk-taker review は local research artifact として置く。
- 仕様リスク: source freshness は自動判定せず CLI option として受ける。Bitget Terms や fee の live fetch はしない。
- テストで見るべき破壊: estimate-only positive edge、NO_TRADE leader、bias guard blocked、schema invalid input exit 2。
- readiness: ready with assumptions.
