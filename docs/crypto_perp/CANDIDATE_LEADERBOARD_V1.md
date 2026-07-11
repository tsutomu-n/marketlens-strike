<!--
作成日: 2026-07-09_20:05 JST
更新日: 2026-07-11_18:35 JST
-->

# Candidate Leaderboard V1

## 結論

`crypto-perp-candidate-leaderboard`はno-cash候補を人間レビュー用に順位付けるlocal artifactです。kill reportだけでなくno-cash gateを直接再検査し、上流停止をHOLDへ戻しません。

## CLI

```bash
uv run sis crypto-perp-candidate-leaderboard \
  --decision data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json \
  --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json \
  --kill-report data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json \
  --gate data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json \
  --signal-rows data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/signal_rows.jsonl \
  --out data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest
```

## Fail-Closed Routing

- gate reject -> `KILL`
- gate revise -> `REVISE_SIGNAL`
- gate collect / missing / unknown -> `COLLECT_MORE_DATA`
- gate HOLD -> kill reportから通常判定

source refsにはdecision、backtest、stress、kill report、gate、signal rowsのraw file SHA-256を記録し、Human Review Packetが実ファイルとのlineageを再検証します。

## Current Runtime Result

```text
gate_decision=NO_CASH_BACKTEST_REJECT
kill_decision=KILL_UPSTREAM_GATE_REJECTED
next_action=KILL
reason_codes=UPSTREAM_GATE_REJECTED,BIAS_GUARD_BLOCKED,BIAS_GUARD_FAILED_sample_sufficient_for_pbo,BACKTEST_CANDIDATE_PACK_REJECT,POSITION_OVERLAP_NOT_ACCOUNTED,INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET,SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION,PBO_NOT_ESTIMABLE_OR_MISSING
```

表示上のcost-adjusted totalは`3.042366783076564551621614274 USD`、stressは`2.762366783076564551621614274 USD`ですが、gate rejectを直接再検査して順位をKILLへ固定します。

## Boundary

`HOLD_FOR_HUMAN_REVIEW`でもPaper permissionではありません。Paper、actual cash、wallet、signing、exchange write、live orderの全flagはfalseです。
