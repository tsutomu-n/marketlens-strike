<!--
作成日: 2026-07-05_18:55 JST
更新日: 2026-07-06_18:03 JST
-->

# Crypto Perp Evidence Quality Reality Check 2026-07-05

## 結論

この repo の Crypto Perp 系は、まだ開発中の research / evidence pipeline です。

現時点で強いのは、候補、source、backtest、review、blocker を artifact として残す力です。弱いのは、実戦で使える水準の source coverage、sample size、books / trades / replay、measured slippage、actual cash evidence です。

したがって、現行成果は「勝てるBotに近い」ではなく、「勝てる可能性のある仮説を安全に潰すための装置ができ始めている」と読む。

## 読み方の修正

| 読み違い | 現実的な読み |
|---|---|
| CLI / schema / artifact が多いので完成が近い | 構造は増えたが、証拠品質はまだ薄い |
| `BRIDGED` は有望候補 | C9 bridge が変換できた候補。alpha proof ではない |
| `BACKTEST_CANDIDATE_HOLD` は次段階に近い | local simulation に残っただけ。paper / production permission ではない |
| Bitget public source があるので実市場に近い | public REST snapshot / candles 中心。books / trades / replay / measured slippage は不足 |
| cost-adjusted estimate は実現損益に近い | actual cash ではない。cash ledger または measurement artifact が必要 |
| `trade_xyz` authoring venue で Crypto Perp を扱える | 現状は Strategy Lab への proxy 接続。Bitget production execution readiness ではない |

## 開発中として妥当な点

- fail-closed の思想は良い。
- unsupported family、missing source、sample insufficient を止める設計は良い。
- `NO_TRADE` を正式 action として扱う点は良い。
- actual cash や production execution を non-goal としている点は良い。
- public network は opt-in で、暗黙に外部APIへ行かない点は良い。

## まだ弱い点

### 1. source coverage

現在の public source は主に contracts、tickers、history candles です。

不足:

- orderbook depth
- trades
- replay
- measured slippage
- websocket sequence
- deep backfill
- cash ledger
- measurement artifact

この欠損を 0 埋めしてはいけない。欠損として artifact に残す。

### 2. sample size

10 event 程度の local pack は、戦略の優位性を見るには薄い。

PBO、rolling stability、regime split が sample insufficient の場合は、良い候補ではなく、追加データが必要な候補として読む。

### 3. estimate / actual cash の境界

`cost_adjusted_cash_estimate_usd` と `stress_cash_estimate_usd` は estimate です。

actual cash と呼べるのは、cash ledger または measurement artifact と明示的な assignment がある場合だけです。

### 4. cost model の読み方

プロジェクト前提は taker fee 0.04%、funding `0.0001`、slippage `2` bps です。

PR #23 後、対象 local simulation surface の normal default は `src/sis/crypto_perp/cost_model.py` に集約されています。`0.0006` は normal default ではなく、explicit conservative / stress assumption としてのみ読む。

参照設定は [../../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml](../../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml) に置き、config/code alignment test で共有定数と一致させます。

### 5. C9 bridge の proxy venue 問題

C9 bridge は `USDT-FUTURES` 候補を扱いますが、Strategy Authoring へ渡す venue は既存基盤上の `trade_xyz` です。

これは開発中の bridge としては許容できます。ただし、Bitget execution 対応済みと読んではいけない。

## Evidence grade の読み方

`crypto-perp-backtest-candidate-pack` の `decision.json` には `evidence_grade_summary` を置く。

目的は、decision そのものではなく、証拠の強さを一目で誤読しないためです。

| field | 読むこと |
|---|---|
| `overall_grade` | local simulation の証拠強度 |
| `strongest_evidence_level` | 現在の最強証拠。現状は `simulated_estimate` |
| `artifact_origin_counts` | existing と recomputed_minimal の割合 |
| `source_missing_counts` | books / trades / replay などの欠損 |
| `critical_missing_count` | signal に必要な critical source の欠損 |
| `known_limits` | actual cash ではない、production readiness ではない等の限界 |

`evidence_grade_summary` は candidate decision を甘くするためのものではない。むしろ、`decision` の読み間違いを防ぐための現実ラベルです。

`BACKTEST_CANDIDATE_HOLD` でも Paper Observation へ直接進みません。次は `crypto-perp-no-cash-backtest-gate` で blockers を machine-readable にし、その後に human review for paper observation へ渡します。

## 当面の優先順位

1. event / outcome 数を増やし、PBO と rolling stability が評価不能ではない状態にする。
2. books / trades / replay の source missing を減らす。
3. cost model を config から runtime builders へ段階的に接続する。
4. C9 bridge の `trade_xyz` proxy を manifest / docs で明示し続ける。
5. actual cash へ進む前に、estimate と actual cash の境界を再確認する。

## やらないこと

- `BRIDGED` 件数を成功指標にしない。
- `BACKTEST_COLLECT_MORE_DATA` を candidate hold と読まない。
- `BACKTEST_CANDIDATE_HOLD` を paper / production permission と読まない。
- missing source を 0 埋めしない。
- Bitget public REST だけで約定品質を判断しない。
- production order path へ進めない。

## Verification

```bash
uv run pytest tests/crypto_perp/test_backtest_candidate_pack.py
uv run sis crypto-perp-backtest-candidate-pack
jq '{decision, reason_codes, evidence_grade_summary, boundary, non_goal_flags}' data/crypto_perp/backtest_candidate_pack/latest/decision.json
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
```
