<!--
作成日: 2026-07-09_22:02 JST
更新日: 2026-07-11_18:35 JST
-->

# Crypto Perp Human Review Packet V1

## 結論

`crypto-perp-human-review-packet`はno-cash判定チェーンの12入力を同一runとして検証し、人間レビュー用に束ねるlocal artifactです。schema、raw file SHA-256、event/outcome pair、execution window、component refs、上流decision、再帰的boundaryのいずれかが不整合ならREADYへ進めません。

現在のartifactは`READY_FOR_HUMAN_REVIEW_PLANNING`ではなく`BLOCKED_BY_BIAS_GUARD`です。pack defaultの`fold_count=0`ではPBO入力条件を満たさず、guardが`BIAS_GUARD_FAILED_sample_sufficient_for_pbo`で`BLOCKED`になっています。candidate以降はREJECT/KILLを維持し、next actionは`FIX_REVIEW_PACKET_BLOCKERS`です。

## Command

```bash
uv run sis crypto-perp-human-review-packet \
  --selection-manifest data/crypto_perp/real_market_no_cash/ticker_required/selection_manifest.json \
  --decision data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json \
  --tournament-rows data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/tournament_rows_v2.json \
  --bias-guard data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/bias_guard.json \
  --data-availability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/data_availability_ledger.json \
  --signal-rows data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/signal_rows.jsonl \
  --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/rolling_stability_result.json \
  --gate data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json \
  --kill-report data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json \
  --leaderboard data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest/candidate_leaderboard.json \
  --out data/crypto_perp/real_market_no_cash/human_review_packet/latest
```

## v2 input contract and lineage

新規生成packetは`input_contract_version=crypto_perp_human_review_packet_inputs.v2`を持ち、入力名・順序・件数を次の12件へ固定します。

1. selection manifest
2. candidate decision
3. tournament rows
4. bias guard
5. data availability ledger
6. signal rows
7. backtest result
8. stress result
9. rolling stability result
10. no-cash gate
11. NO_TRADE kill report
12. candidate leaderboard

12入力はdefault pathでも省略される検証対象ではありません。各JSONと各signal JSONL rowを対応schemaで検査し、unknown field、必須field欠損、型不正を`BLOCKED_BY_ARTIFACT_LINEAGE`へ落とします。selection manifest、rows、signal、backtest、stress間のevent/outcome pair、`information_cutoff_at < entry_at < settled_at`、entry/horizon、30件のevent/outcome countも一致が必要です。

source refsと`decision.summary.pack_component_refs`はpath、schema version、実ファイルのraw SHA-256を照合します。異なるrun、同じpathで内容だけ変わったartifact、古いhash、欠落ref、余分な入力はfail-closedです。禁止flagはtop levelだけでなく全入力のnested mappingを再帰的に走査し、Paper、actual cash、wallet、signing、exchange write、live order関連が明示的な`false`以外なら停止します。

出力schema名はreader互換のため`crypto_perp_human_review_packet.v1`を維持します。`input_contract_version`がある新規packetにはstrict 12-input条件を適用し、このfieldを持たない既存v1 artifactは従来required fieldで読めるconditional migrationです。旧artifactを新規生成物と同じ強度のlineage証拠とは扱いません。

## Decisions

判定優先順位は次です。

1. `BLOCKED_BY_BOUNDARY_VIOLATION`
2. `BLOCKED_BY_ARTIFACT_LINEAGE`
3. `BLOCKED_BY_BIAS_GUARD`
4. `BLOCKED_BY_PBO`
5. `BLOCKED_BY_CANDIDATE`
6. `BLOCKED_BY_GATE`
7. `BLOCKED_BY_KILL_REPORT`
8. `BLOCKED_BY_LEADERBOARD`
9. 全条件を満たす場合だけ`READY_FOR_HUMAN_REVIEW_PLANNING`

PBOは`COMPUTED_PASS`というstatus文字列だけでは通過できません。専用PBO計算artifactとlineageを検証するproducerが未実装のため、現在のbuilderは`pbo_evidence_verified=false`を固定し、guardがPASSでも`PBO_COMPUTATION_EVIDENCE_MISSING`で停止します。つまり、statusの手書き差し替えでREADYを偽造できません。

## Current Runtime Result

```text
input_contract_version=crypto_perp_human_review_packet_inputs.v2
review_input_count=12
packet_decision=BLOCKED_BY_BIAS_GUARD
next_action=FIX_REVIEW_PACKET_BLOCKERS
artifact_lineage_status=PASS
bias_guard_status=BLOCKED
bias_guard_stop_reason=BIAS_GUARD_FAILED_sample_sufficient_for_pbo
pbo_status=NOT_ESTIMABLE
pbo_computed=false
pbo_evidence_verified=false
candidate_decision=BACKTEST_REJECT
gate_decision=NO_CASH_BACKTEST_REJECT
kill_decision=KILL_UPSTREAM_GATE_REJECTED
leaderboard_top_next_action=KILL
```

30 events / 14 simulated trades / 10 winsの名目after-cost totalは`3.042366783076564551621614274 USD`、stress totalは`2.762366783076564551621614274 USD`です。ただしpeak concurrent positionsは6、market episodesは5（勝ち3）、single-position totalは`-0.4618201695034107750204885438 USD`です。always-longは`5.816219911337534249441041925 USD`でselectorより高く、score/result correlationは`-0.2902937515082110915592253119`、shortは2/2敗で`-0.4939911498820537167728313263 USD`です。

trade単位ではnaive iid t=`2.0179`、one-sided sign p=`0.0898`、iid bootstrap total 95% interval=`[+0.1069,+5.7882]`と見えます。しかし重複依存を無視しています。5 episodeを単位にしたbootstrap total 95% intervalは`[-1.9182,+9.2413]`で0を跨ぐため、利益の再現性は未証明です。

## Boundary

このpacketはPaper Observationを開始せず、paper order、profit proof、actual cash、wallet、signing、exchange write、live orderを許可しません。現在の全安全flagはfalseです。guard/PBO、position overlap、独立episode、selector benchmark、source/約定条件のblockerを解消しても、自動的にPaperまたはlive permissionへ変わりません。
