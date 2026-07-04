<!--
作成日: 2026-07-05_00:12 JST
更新日: 2026-07-05_00:12 JST
-->

# Crypto Perp Backtest Candidate Pack v1 Plan

## チェックポイントID

C1

## 目的

`actual cash` なしの次期終着点を `Pre Actual Cash Evidence Gate` から `Crypto Perp Backtest Candidate Pack v1` へ進める。目的は利益証明ではなく、既存 local artifact から timestamp-safe な simulation evidence pack を作り、候補を次の4択へ分類すること。

- `BACKTEST_REJECT`
- `BACKTEST_REVISE`
- `BACKTEST_COLLECT_MORE_DATA`
- `BACKTEST_CANDIDATE_HOLD`

`BACKTEST_PROMOTE_TO_LIVE` は作らない。

## 現状

- `main` は `origin/main` と一致し、直近 commit は ticker coverage metadata の修正済み。
- `crypto_perp` には event、outcome、source availability、replay slice、feature pack、edge score、cost-aware tournament rows、bias guard、pre-actual-cash aggregation がある。
- `strategy-backtest-*` は Strategy Authoring spec / parquet / metrics 前提で、Crypto Perp の event/outcome artifact を直接食べる surface ではない。
- ticker source metadata は `crypto-perp-profit-readiness-run-local --ticker-manifest` で source availability へ渡せる。

## 制約

- actual cash、cash ledger、actual-cash rows、tiny-live、live order、ML/LLM trade decision は扱わない。
- 外部サービス送信、課金、秘密情報変更、不可逆削除、本番反映は禁止。
- 既存 generic backtest surface を壊さない。
- zero-cost simulation は禁止。初期値でも fee と slippage を非ゼロにする。
- small sample や missing data を pass と誤読させない。

## 対象ファイル

- 追加: `src/sis/crypto_perp/backtest_candidate_pack.py`
- 追加: `src/sis/commands/crypto_perp_backtest_candidate_pack.py`
- 更新: `src/sis/commands/crypto_perp.py`
- 追加: `schemas/crypto_perp_backtest_candidate_pack.v1.schema.json`
- 追加: `tests/crypto_perp/test_backtest_candidate_pack.py`
- 更新: `docs/final-summary.md`

## 実装方針

既存の `pre_actual_cash` 集約を参考にしつつ、Crypto Perp 専用の pack builder を追加する。入力は local `data_dir` 配下の event/outcome/source artifacts とし、出力は要求どおり `data/crypto_perp/backtest_candidate_pack/latest/` に置く。

出力予定:

- `signal_rows.jsonl`
- `data_availability_ledger.json`
- `execution_assumptions.json`
- `no_lookahead_report.json`
- `backtest_result.json`
- `stress_result.json`
- `regime_split_result.json`
- `rolling_stability_result.json`
- `decision.json`
- `decision.md`

## 実装手順

1. `backtest_candidate_pack.py` に pydantic model、artifact builder、markdown renderer、writer を追加する。
2. 既存 inventory から event/outcome pair を選ぶ。
3. 既存 source/feature/edge/rows/bias guard があれば使い、なければ minimal recompute し、origin を artifact に残す。
4. `signal_rows.jsonl` に `timestamp`, `symbol`, `information_cutoff_at`, `source_availability_id`, `feature_pack_id`, `edge_score_id`, `selected_action`, `signal_score`, `entry_allowed`, `no_trade_reason` を出す。
5. `data_availability_ledger.json` に source status、available_at、used_at、missing_reason、staleness_seconds を出す。
6. `execution_assumptions.json` に entry/exit/fee/slippage/funding/holding/position/no-fill policy を固定する。
7. no-lookahead report は signal cutoff、source used_at、ticker metadata window、outcome non-use を明示的に検査する。
8. backtest result は selected action と matured outcome を使って cost-adjusted simulated result を計算する。`UNKNOWN` は no-fill/blocked、`NO_TRADE` は有効 baseline として扱う。
9. stress/regime/rolling は小サンプルでも artifact を出し、sample不足は status/reason に残す。
10. decision を4択へ分類する。
11. CLI `crypto-perp-backtest-candidate-pack` を追加し、boundary stdout を出す。
12. focused tests と schema validation を追加する。

## テスト方針

- Unit: builder が signal rows、ledger、assumptions、no-lookahead、backtest、decision を生成する。
- Unit: source不足や `UNKNOWN` 過多では `BACKTEST_COLLECT_MORE_DATA` になる。
- Unit: zero fee/slippage を拒否または non-zero default にする。
- CLI: command registration/help と最小生成を確認する。
- Schema: `decision.json` を `crypto_perp_backtest_candidate_pack.v1` schema で検証する。

## 完了条件

- CLI が required artifact names を生成する。
- `decision.json` が4択のいずれかを返す。
- artifact が actual cash / live readiness を claim しない。
- focused pytest が pass する。
- 最小 CLI generation が pass する。

## 失敗条件

- 実データ fetch や外部送信が必要になる。
- Generic Strategy Backtest を壊す。
- actual cash / tiny-live / live readiness に読める label を出す。
- no-lookahead が outcome 由来の未来情報混入を検知できない。

## 影響範囲

新規 Crypto Perp surface と command registration のみ。既存 artifact schema や既存 CLI の互換性は変えない。

## ロールバック方針

追加ファイルと `src/sis/commands/crypto_perp.py` の登録行を revert する。既存 schema/data migration は不要。

## 代替案

- Generic `strategy-backtest-*` へ変換して流す: authoring spec/parquet 前提が強く、今回の event/outcome artifact と責任境界がずれるため採用しない。
- `pre_actual_cash.py` に全機能を追加: ファイル肥大化と語彙混同が強いため採用しない。
- actual cash gate を延長: objective と非目標に反するため採用しない。

## 未解決事項

- この実装では fresh public data fetch はしない。既存 local data が薄い場合は `BACKTEST_COLLECT_MORE_DATA` が正しい結果になる。
- 30 event 以上の統計的安定性は、この checkpoint の完了条件ではなく decision reason として残す。

## 破壊的変更の有無

なし。新規 surface の追加。

## ブランチ名

`ai/crypto-perp-backtest-pack-20260705-0011`

## 移行手順

なし。既存 artifacts はそのまま読み取り対象として使える。新 pack は `uv run sis crypto-perp-backtest-candidate-pack` で生成する。

## Critique 1

- ゴール直結性: signal rows、ledger、assumptions、no-lookahead、backtest、stress、decision を同一 pack で生成するため直結している。
- ご都合主義リスク: small sample でも artifact が出るため、decision と reason に sample不足、missing source、UNKNOWN を必ず出す。
- 破壊リスク: existing Strategy Backtest と pre-actual-cash の semantics を変えず、新規 module に隔離する。
- 代替単純化: pre-actual-cash の helper を直接 import する誘惑はあるが、private helper 依存が増える。必要最低限だけ local helper として再実装する。

## Critique 2

- 抜け: `G1 ticker source artifact` の fresh collection は今回実装しないが、base commit で ticker manifest metadata は読める。pack 側は source availability metadata を評価できればよい。
- 抜け: `selected_action=UNKNOWN` 改善確認は pack の summary/decision で数える。新規 fetch がないため改善そのものを捏造しない。
- 誤謬リスク: Backtest という名前が profit proof に見えるため、schema/markdown/stdout に `profit_proven=false`, `permits_live_order=false` を固定する。
- Better: output schema を1つに詰め込まず、required artifact set を生成する。schema は decision/manifest に寄せ、サブartifactは追加プロパティを許容して進化余地を残す。
