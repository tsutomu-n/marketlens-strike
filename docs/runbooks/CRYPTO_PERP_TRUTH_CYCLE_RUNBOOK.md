<!--
作成日: 2026-06-21_18:29 JST
更新日: 2026-06-21_19:02 JST
-->

# Crypto Perp Truth-Cycle Runbook

Crypto Perp Truth-Cycle の post-MVP 実務runbookです。目的は、candidate event を勝ち筋の物語に変えず、prospective decision、matured outcome、tournament report まで同じ手順で再生成することです。

このrunbookは自動売買、wallet、signing、exchange write、tiny live measurementの承認ではありません。

## 正本

- `src/sis/crypto_perp/`
- `src/sis/commands/crypto_perp.py`
- `src/sis/commands/crypto_perp_live.py`
- `schemas/crypto_perp_*.schema.json`
- `tests/crypto_perp/`
- `uv run sis --help`
- [../CURRENT_STATE.md](../CURRENT_STATE.md)
- [../IMPLEMENTED_SURFACES.md](../IMPLEMENTED_SURFACES.md)
- [../NEXT_DIRECTION_CURRENT.md](../NEXT_DIRECTION_CURRENT.md)

## P00: tournament rows からreportを再生成する

既存の rows JSON / JSONL がある場合、まずtournament reportだけを再生成します。

```bash
uv run sis crypto-perp-tournament-report \
  --rows data/crypto_perp/tournament/rows.jsonl \
  --out data/crypto_perp/tournament/latest \
  --report-id crypto-perp-tournament-latest \
  --min-events 10
```

見るもの:

- `tournament_status`
- `leader_action`
- `primary_metric=actual_cash_result_usd`
- `event_count`
- `inconclusive_reasons`
- 各actionの `largest_loss_usd`
- `profit_concentration`
- `operator_time_minutes`

止める条件:

- `tournament_status=INCONCLUSIVE_DATA`
- event set が action 間で一致しない
- `NO_TRADE` を失敗扱いしている
- `REVERSAL_SHORT` だけを勝ち前提にしている
- actual cash ではなく勝率だけで判断している

## P01: candidate event からprospective decisionを記録する

event cardを先に読みます。

```bash
uv run sis crypto-perp-watchdeck \
  --event data/crypto_perp/events/<event-id>/event.json
```

outcome を見る前に decision を記録します。

```bash
uv run sis crypto-perp-decision-record \
  --event data/crypto_perp/events/<event-id>/event.json \
  --action NO_TRADE \
  --out data/crypto_perp/decisions/<event-id> \
  --actor-type human \
  --actor-id operator \
  --size-cap-usd 0 \
  --reason-code insufficient_evidence \
  --notes "prospective decision before outcome"
```

action候補:

- `REVERSAL_SHORT`
- `CONTINUATION_LONG`
- `NO_TRADE`
- `UNKNOWN`
- `CAPTURE_ONLY`

注意:

- `decision_at` は `information_cutoff_at` 以後でなければならない。
- decision artifact は outcome / pnl を含まない。
- `size_cap_usd` は上限記録であり、order permissionではない。
- `UNKNOWN` や `NO_TRADE` は失敗ではなく、証拠不足や見送りを明示するための選択肢。

## P02: public probe後にevent候補へ進めるか検査する

public network probeは明示的な人間承認と環境変数opt-inがある時だけ実行します。

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-probe \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --out data/crypto_perp/provider_probe/latest \
  --raw-root data/crypto_perp/raw \
  --network
```

probe後は、event候補へ進める前にauditします。

```bash
uv run sis crypto-perp-probe-audit \
  --probe data/crypto_perp/provider_probe/latest/provider_probe.json \
  --out data/crypto_perp/probe_audit/latest
```

見るもの:

- `audit_status`
- `missing_endpoints`
- `zero_row_endpoints`
- `failed_endpoints`
- `missing_capabilities`
- `missing_raw_snapshot_paths`
- `known_gaps`
- `next_actions`

進める条件:

- `audit_status=READY_FOR_EVENT_REFRESH`
- `network_attempted=true` のprobe artifactである
- `credentials_used=false`
- `instruments`、`tickers`、`candles` が存在し、row_countが0ではない
- raw snapshot pathが存在する

止める条件:

- `audit_status=BLOCKED_PROBE_QUALITY`
- raw snapshotが欠けている
- tickers / candles が0行
- endpoint errorがある
- credentialsを使ったartifactが混ざっている
- auditを通さずevent候補を増やす

## P03: audit済みraw snapshotからsnapshot / event候補を再生成する

`crypto-perp-probe-audit` が `READY_FOR_EVENT_REFRESH` の時だけ実行します。

```bash
uv run sis crypto-perp-raw-refresh \
  --probe data/crypto_perp/provider_probe/latest/provider_probe.json \
  --probe-audit data/crypto_perp/probe_audit/latest/probe_audit.json \
  --out data/crypto_perp/raw_refresh/latest
```

生成物:

- `raw_refresh.json`
- `raw_refresh.md`
- `universe_snapshot.json`
- `market_snapshot.json`
- `candle_quality.json`
- `events/<event-id>.json`。eventが無い場合は0件として残す。

見るもの:

- `event_count`
- `known_gaps`
- `universe_instrument_count`
- `market_ticker_count`
- `candle_bar_count`

止める条件:

- probe audit が `READY_FOR_EVENT_REFRESH` ではない
- `probe_id` が probe と audit で一致しない
- raw snapshot が欠けている
- candle qualityに `GAP_DETECTED` / `NON_FINAL_BAR` / `INVALID_OHLC` がある
- `NO_EVENT_DETECTED` を無理にevent化する

## P04: matured outcomeを記録する

観察窓が成熟したあとで outcome を記録します。

```bash
uv run sis crypto-perp-outcome-record \
  --event data/crypto_perp/events/<event-id>/event.json \
  --out data/crypto_perp/outcomes/<event-id> \
  --horizon-minutes 60 \
  --reference-price 100 \
  --close-price 105 \
  --high-price 110 \
  --low-price 95 \
  --market-return 0
```

高解像度の順序証拠がある場合だけ、次を追加します。

```bash
--observed-high-low-order HIGH_FIRST
```

順序が分からない場合は指定しません。その場合、OHLC内の high / low 順序は `AMBIGUOUS` として残します。

止める条件:

- horizonが未成熟なのに `--matured` として記録する
- high / low の順序を証拠なしに決める
- books / trades の欠落を `--known-gap` に残さない
- outcomeをdecision前に見てdecisionを作る

## P05: tournament rowsを作る

outcome artifactから、tournament reportへ渡す3action rowsのpreviewを作れます。

```bash
uv run sis crypto-perp-tournament-rows-preview \
  --outcome data/crypto_perp/outcomes/<event-id>/<outcome-id>.json \
  --out data/crypto_perp/tournament_rows_preview/<event-id> \
  --notional-usd 25 \
  --operator-time-minutes 2
```

生成物:

- `tournament_rows_preview.json`
- `tournament_rows.jsonl`
- `tournament_rows_preview.md`

注意:

- これは `outcome_before_cost_proxy` です。実約定、fee、funding、slippage込みのactual cashではありません。
- `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` と `FEES_FUNDING_AND_FILL_SLIPPAGE_NOT_INCLUDED` をknown gapとして残します。
- `NO_TRADE` はcash 0として明示します。失敗扱いしません。
- `tournament_rows_preview.json` を `crypto-perp-tournament-report --rows` に渡すと、previewのknown gapsはreportへ継承されます。

手で作る場合も、winnerだけを保存しません。各eventについて、同じevent setで次の3actionをそろえます。

```json
{"event_id":"event-1","action":"REVERSAL_SHORT","actual_cash_result_usd":"-1.20","market_adjusted_return":"-0.02","operator_time_minutes":"3","near_miss":false}
{"event_id":"event-1","action":"CONTINUATION_LONG","actual_cash_result_usd":"0.80","market_adjusted_return":"0.01","operator_time_minutes":"3","near_miss":false}
{"event_id":"event-1","action":"NO_TRADE","actual_cash_result_usd":"0","market_adjusted_return":"0","operator_time_minutes":"0","near_miss":false}
```

入力制約:

- 1 event につき `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を1行ずつ入れる。
- `actual_cash_result_usd` をprimary metricにする。
- fee、funding、ruined pod、infra costがある場合はcash側に含める。
- データ不足は行を消して隠すのではなく、reportの `INCONCLUSIVE_DATA` または `known_gaps` に残す。
- before-cost proxy rowsを実cashとして扱わない。

## P06: reportから次 action を決める

```bash
uv run sis crypto-perp-tournament-report \
  --rows data/crypto_perp/tournament_rows_preview/<event-id>/tournament_rows_preview.json \
  --out data/crypto_perp/tournament/<report-id> \
  --report-id <report-id> \
  --min-events 10 \
  --known-gap books15_missing
```

進める条件:

- `tournament_status=COMPLETE`
- event set が3actionで一致している
- `actual_cash_result_usd` がprimary metric
- `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` が残っているreportをactual cash evidenceとして扱っていない
- largest loss が許容範囲
- profit concentration が極端ではない
- operator time が継続可能

戻す条件:

- `INCONCLUSIVE_DATA`
- leaderが出ない
- 1 event へのprofit集中が強すぎる
- `NO_TRADE` がactual cash basisで最良
- fill / fee / funding / cash attributionが不明
- high / low ordering ambiguity がdecisionを左右している

次に、reportをgateに通します。

```bash
uv run sis crypto-perp-tournament-gate \
  --report data/crypto_perp/tournament/<report-id>/tournament_report.json \
  --out data/crypto_perp/tournament_gate/<report-id> \
  --max-largest-loss-usd 25 \
  --max-profit-concentration 0.60 \
  --max-operator-time-minutes 120
```

見るもの:

- `gate_status`
- `recommended_action`
- `failed_conditions`
- `known_gaps`

`READY_FOR_HUMAN_TINY_LIVE_REVIEW` は承認準備の入口です。live実行許可ではありません。

## tiny live measurementへ進む前の境界

tiny live measurement はこのrunbookの範囲外です。進むには別の明示承認が必要です。

最低条件:

- `SIS_ENABLE_TINY_LIVE_MEASUREMENT=1`
- `--confirm-live`
- confirmation phrase
- isolated margin
- withdrawal disabled API key
- IP restriction
- max notional 25 USD
- max open positions 1
- no existing position
- no existing open order
- reduce-only close
- flat reconciliation

## 検証

このrunbookや関連CLIを変更した時は次を実行します。

```bash
uv run pytest tests/crypto_perp/test_provider_probe.py tests/crypto_perp/test_raw_refresh.py tests/crypto_perp/test_decisions.py tests/crypto_perp/test_outcomes.py tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_gate.py -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```
