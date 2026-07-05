<!--
作成日: 2026-07-05_10:08 JST
更新日: 2026-07-05_10:08 JST
-->

# Crypto Perp Backtest Candidate Pack v1

## 結論

actual cash を扱わない短期の Crypto Perp 終着点は、`crypto-perp-backtest-candidate-pack` です。

これは利益証明ではなく、既存 local artifact から timestamp-safe な simulation backtest evidence pack を作り、候補を次の4択へ分類するための current surface です。

- `BACKTEST_REJECT`
- `BACKTEST_REVISE`
- `BACKTEST_COLLECT_MORE_DATA`
- `BACKTEST_CANDIDATE_HOLD`

`BACKTEST_PROMOTE_TO_LIVE` は存在しません。`BACKTEST_CANDIDATE_HOLD` でも、actual cash readiness、paper permission、tiny-live readiness、live readiness、wallet/signing、exchange write、live order permission は出ません。

## 正本

- CLI: `uv run sis crypto-perp-backtest-candidate-pack`
- Builder: `src/sis/crypto_perp/backtest_candidate_pack.py`
- Models: `src/sis/crypto_perp/backtest_candidate_pack_models.py`
- Reports: `src/sis/crypto_perp/backtest_candidate_pack_reports.py`
- Command wrapper: `src/sis/commands/crypto_perp_backtest_candidate_pack.py`
- Registration: `src/sis/commands/crypto_perp.py`
- Schema: `schemas/crypto_perp_backtest_candidate_pack.v1.schema.json`
- Tests: `tests/crypto_perp/test_backtest_candidate_pack.py`
- Local output: `data/crypto_perp/backtest_candidate_pack/latest/`

## 生成する artifact

デフォルトでは `data/crypto_perp/backtest_candidate_pack/latest/` に次を出します。

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

## 実行

```bash
uv run sis crypto-perp-backtest-candidate-pack
```

主な option:

```bash
uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp \
  --out data/crypto_perp/backtest_candidate_pack/latest \
  --notional-usd 100 \
  --min-events 10 \
  --min-events-for-stability 30 \
  --fee-rate 0.0006 \
  --funding-rate 0.0001 \
  --slippage-bps 2
```

zero-cost simulation は禁止です。`fee_rate` と `slippage_bps` は正の値でなければなりません。

## 現在の local result

現在の local 10-event BTCUSDT pack は次の分類です。

- decision: `BACKTEST_COLLECT_MORE_DATA`
- reason codes:
  - `PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT`
  - `ROLLING_STABILITY_SAMPLE_INSUFFICIENT`
- event_count: `10`
- outcome_count: `10`
- selected_action_counts:
  - `NO_TRADE=8`
  - `REVERSAL_SHORT=2`
- selected_action `UNKNOWN`: `0`
- no-lookahead failed: `0`
- no-lookahead unverified: `0`
- executed simulated trades: `2`

この結果は「追加データが必要」という分類です。利益証明ではありません。

## 読み方

| artifact | 読むこと | 読まないこと |
|---|---|---|
| `signal_rows.jsonl` | signal cutoff 時点で選ばれた action、entry allowed、UNKNOWN / NO_TRADE 理由 | outcome を見た後の裁量判断 |
| `data_availability_ledger.json` | source が signal cutoff 以前に利用可能だったか | unavailable source の zero-fill |
| `execution_assumptions.json` | fee、funding、slippage、holding、no-fill policy | 実約定条件や実現損益 |
| `no_lookahead_report.json` | signal/source/feature の timestamp safety | alpha proof |
| `backtest_result.json` | cost-adjusted estimate の local simulation | actual cash profit |
| `stress_result.json` | stress estimate の local simulation | live readiness |
| `regime_split_result.json` | event family ごとの簡易 split | 十分な regime robustness |
| `rolling_stability_result.json` | sample size と cumulative stability | sample 十分性の自動証明 |
| `decision.json` | 4択 decision と reason codes | live / tiny-live / paper permission |

## Pre Actual Cash との関係

2026-07-04 の `Pre Actual Cash Decision Gate` は historical context です。短期の current entry は、この Backtest Candidate Pack v1 です。

古い progress docs、pre-actual-cash gate doc、pre-actual-cash dogfood snapshots、完了済み implementation plans は `docs/archive/2026-07-05-docs-code-truth-cleanup/` へ移動済みです。

## 境界

この command は local artifact を読むだけです。

やらないこと:

- actual cash source 作成
- cash ledger 作成
- actual-cash rows 作成
- actual-cash report gate を通した profit proof
- tiny-live 実行
- live order
- wallet / signing
- exchange write
- ML/LLM trade decision
- `BACKTEST_PROMOTE_TO_LIVE`

## Verification

最小確認:

```bash
uv run pytest tests/crypto_perp/test_backtest_candidate_pack.py
uv run sis crypto-perp-backtest-candidate-pack
jq '{decision, reason_codes, event_count, outcome_count, selected_action_counts: .summary.selected_action_counts, no_lookahead: .summary.no_lookahead, backtest: .summary.backtest, boundary, non_goal_flags}' data/crypto_perp/backtest_candidate_pack/latest/decision.json
```

広い確認:

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
./scripts/check
```
