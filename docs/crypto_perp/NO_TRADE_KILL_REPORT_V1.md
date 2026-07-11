<!--
作成日: 2026-07-09_20:05 JST
更新日: 2026-07-11_19:42 JST
-->

# NO_TRADE Kill Report V1

## 結論

`crypto-perp-no-trade-kill-report` は、no-cash gate の判定を必須入力とし、上流が HOLD の場合だけ `NO_TRADE`、after-cost、stress、集中リスクを評価する local review artifact です。

これは Paper Observation permission、paper order permission、profit proof、actual cash readiness、live readiness ではありません。

## CLI

```bash
uv run sis crypto-perp-no-trade-kill-report \
  --gate data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json \
  --signal-rows data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/signal_rows.jsonl \
  --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json \
  --tournament-rows data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/tournament_rows_v2.json \
  --out data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest
```

`--gate`と`--tournament-rows`は必須です。どちらか未指定ならCLIはexit code 2で失敗し、gate/derived rowsなしのHOLD経路を作りません。

## Upstream Routing

- `NO_CASH_BACKTEST_REJECT` -> `KILL_UPSTREAM_GATE_REJECTED`
- `NO_CASH_BACKTEST_REVISE` -> `REVISE_SOURCE_OR_SIGNAL`
- `NO_CASH_BACKTEST_COLLECT_MORE_DATA` -> `COLLECT_MORE_DATA`
- missing / unknown -> `COLLECT_MORE_DATA`
- `NO_CASH_BACKTEST_HOLD` -> local kill checksを実行

出力は`upstream_gate_decision`、`upstream_reason_codes`、`upstream_blockers`を保持します。gateがHOLDの場合もrows modelを検証し、leader_actionがderived rowsに存在しない、未知、不正ならbuilderは`COLLECT_MORE_DATA`へ落とします。

## Market Episode Profit Concentration

trade row単位の利益集中だけでなくmarket episode単位でも集中を検査します。Kill Reportは必須pack-local tournament rowsの`summary.execution_windows`とbacktest simulated resultsからepisode cluster/totalsを再計算します。`backtest.summary.profit_robustness.market_episode_totals_usd`は、その再計算値と順序・件数・値が完全一致する場合だけ採用します。

- missing、非array、bool/non-numeric、非有限値を含む場合: `episode_concentration_estimated=false`、concentration出力は`null`、local decisionは`COLLECT_MORE_DATA`、reasonは`EPISODE_PROFIT_CONCENTRATION_NOT_ESTIMABLE`
- execution window欠損/不正、duplicate result event、derived/reported totals不一致も同じNOT_ESTIMABLE/COLLECT
- largest positive episode share `> 0.60`またはtop-2 positive episode share `> 0.80`: local decisionは`REVISE_SOURCE_OR_SIGNAL`、reasonは`EPISODE_PROFIT_CONCENTRATION_HIGH`
- 閾値は既存trade concentrationの`0.60 / 0.80`を再利用し、別の都合のよいepisode閾値を増やしません。

新規出力は`episode_concentration_estimated`、`episode_largest_win_concentration`、`episode_top2_win_concentration`です。現30-event backtestのepisode totalsではlargestは約`0.716`、top-2は約`0.997`で両閾値を超えます。ただし現在は上流gate `NO_CASH_BACKTEST_REJECT`が優先され、kill decisionは`KILL_UPSTREAM_GATE_REJECTED`のままです。上流が将来HOLDになっても、この集中を無視してleaderboard HOLDへ進めません。

## Current Runtime Result

現在のgateは`NO_CASH_BACKTEST_REJECT`なので、kill reportはlocal NO_TRADE checksへ進まず`KILL_UPSTREAM_GATE_REJECTED`です。guard sample不足、candidate reject、position overlap、episode不足、static benchmark未達、PBO not estimableを`upstream_reason_codes` / `upstream_blockers`へ伝播します。

pack-local rowsを入力し、source refsにはsignal、backtest、stress、rows、gateのraw SHA-256を記録します。名目`+3.042366783076564551621614274 USD`でも上流REJECTを`HOLD_FOR_LEADERBOARD`へ戻しません。

## Boundary

Paper、actual cash、wallet、signing、exchange write、live orderの全flagはfalseです。
