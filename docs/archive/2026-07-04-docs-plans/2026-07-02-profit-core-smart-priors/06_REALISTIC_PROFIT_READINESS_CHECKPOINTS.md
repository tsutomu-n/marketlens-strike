<!--
作成日: 2026-07-03_09:09 JST
更新日: 2026-07-03_11:07 JST
-->

# Realistic Profit-Readiness Checkpoints

## 結論

この文書は、Crypto Perp の profit-readiness を「今できる」「一部だけできる」「入力不足で止める」に分ける実装チェックポイントです。

今回の作業は docs-only。demo / testnet、外部LLM API、actual cash rows build、actual-cash gate 実行へ進まない。既存CLIと手元artifactから、どこまで読めるか、どこで止めるべきかを固定する。

## 目的

- `data/crypto_perp` にある artifact を profit evidence と誤読しない。
- real event、matured outcome、cash ledger、assignment、actual cash rows の有無を先に確認する。
- dogfood / status / viewer artifact だけの状態を profit-readiness と扱わない。
- actual cash basis が無い時は、`BLOCKED_MISSING_EVENT_OR_OUTCOME`、`ACTUAL_CASH_SOURCE_MISSING`、`NEEDS_ACTUAL_CASH` などの停止結果として扱う。
- 既存CLIを前提にし、新規 audit CLI や schema をこのチェックポイント文書から増やさない。

## 制約

- 実装開始時点では docs-only。
- 外部API、demo / testnet order lifecycle、actual cash rows build、actual-cash gate はこの文書作成作業では実行しない。
- `data/` 生成物を tracked source of truth にしない。
- `actual_cash_result_usd` は ledger-connected actual cash basis に限定する。
- preview / estimate / backtest / virtual / dogfood を actual cash rows に変換しない。
- `NO_TRADE` を失敗扱いしない。
- missing ledger entry を cash 0 として扱わない。cash 0 を許すのは明示的な `NO_TRADE` だけ。
- permission boundary は常に `permits_live_order=false` を維持する。

## 対象ファイル

今回の docs-only 作業対象:

- `docs/plans/2026-07-02-profit-core-smart-priors/06_REALISTIC_PROFIT_READINESS_CHECKPOINTS.md`
- `docs/plans/2026-07-02-profit-core-smart-priors/README.md`

この文書が前提にする既存入口:

- `crypto-perp-profit-readiness-inventory`
- `crypto-perp-source-availability`
- `crypto-perp-truth-cycle-status`
- `crypto-perp-actual-cash-rows-build`
- `crypto-perp-actual-cash-report-gate`
- `crypto-perp-risk-taker-review`

変更しないもの:

- `src/`
- `schemas/`
- public CLI registration
- runtime artifacts under `data/`

## テスト方針

この docs-only 作業では次を実行する。

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

確認すること:

- metadata header が作業時点の東京時間になっている。
- README の文書構成に 06 が追加されている。
- 06 が既存CLIを再実装する計画になっていない。
- 「今できる」「一部だけできる」「入力不足で止める」が混ざっていない。
- demo / testnet、外部LLM API、actual cash rows build、gate 実行を実施済みのように読めない。

将来コード実装へ進む場合だけ、変更対象に応じて focused pytest を追加する。

```bash
uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q
uv run pytest tests/crypto_perp/test_risk_taker_review.py -q
uv run pytest tests/crypto_perp/test_truth_cycle_status.py -q
```

## 完了条件

- この文書に目的、制約、対象ファイル、テスト方針、完了条件、現実チェックポイントが含まれる。
- README に 06 の索引が追加される。
- `uv run python scripts/check_current_docs.py` が pass する。
- `git diff --check` が pass する。
- コード、schema、CLI、runtime artifact は変更しない。
- external API、demo / testnet、actual cash rows build、actual-cash gate は実行しない。

## チェックポイント一覧

| ID | 判定 | やること | 止め方 |
| --- | --- | --- | --- |
| C0 | 今できる | Current artifact inventory | real event / matured outcome / ledger / assignment / rows が無ければ profit evidence と扱わない |
| C1 | 今できる | Profit-readiness inventory | `BLOCKED_MISSING_EVENT_OR_OUTCOME` は正常な停止結果 |
| C2 | event がある場合だけ一部できる | Source availability | `can_compute_actual_cash=false` / `ACTUAL_CASH_SOURCE_MISSING` なら rows / gate へ進まない |
| C3 | 既存 artifact がある場合だけできる | Truth-cycle status review | `NEEDS_ACTUAL_CASH` は actual cash basis 作り直しの停止結果 |
| C4 | ledger + assignment がある場合だけできる | Actual cash rows handoff | trade action の missing ledger entry は失敗。0埋め禁止 |
| C5 | actual cash rows がある場合だけできる | Actual-cash report gate | rows が無いなら実行しないことが完了条件 |
| C6 | rows-v2 + source availability + bias guard がある場合だけできる | Risk-taker review | `READY_FOR_HUMAN_RISK_REVIEW` は live permission ではない |
| C7 | 初期計画では未実装・後回し | Demo / testnet execution | profit evidence ではなく execution lifecycle check |
| C8 | 初期計画では未実装・後回し | External LLM API | score補正、promotion、gate override に使わない |

## C0: Current Artifact Inventory

判定: 今できる。

最初に `data/crypto_perp` を棚卸しする。確認対象は real event、matured outcome、cash ledger、assignment、actual cash rows の有無です。

dogfood / status / viewer artifact しか無い場合は、profit evidence と扱わない。これは失敗ではなく、後続の profit-readiness 判定へ進む入力が不足している状態です。

完了条件:

- `data/crypto_perp` の現物から real event、matured outcome、cash ledger、assignment、actual cash rows の有無を説明できる。
- dogfood / status / viewer artifact を profit evidence として数えない。
- 不足している artifact を rows / gate 実行で補おうとしない。

## C1: Profit-Readiness Inventory

判定: 今できる。

最初のCLI確認は既存 inventory です。

```bash
uv run sis crypto-perp-profit-readiness-inventory \
  --data-dir data/crypto_perp
```

`BLOCKED_MISSING_EVENT_OR_OUTCOME` は正常な停止結果として扱う。これは「壊れている」ではなく、real event または matured outcome が不足しており、profit-readiness を主張できないという意味です。

完了条件:

- inventory status を最初に読む。
- `BLOCKED_MISSING_EVENT_OR_OUTCOME` の時は source availability、rows build、gate 実行へ進まない。
- dogfood / status / viewer artifact だけを理由に stop condition を解除しない。

## C2: Source Availability

判定: event がある場合だけ一部できる。

event がある場合だけ、source availability を読む。

```bash
uv run sis crypto-perp-source-availability \
  --event <event.json>
```

見るもの:

- `can_compute_actual_cash`
- cash ledger または live measurement の有無
- source refs
- row counts
- `known_gaps`

`can_compute_actual_cash=false` または `ACTUAL_CASH_SOURCE_MISSING` がある場合は、actual cash rows / actual-cash gate へ進まない。

完了条件:

- event が無い時に source availability を無理に作らない。
- `can_compute_actual_cash=false` を停止結果として扱う。
- cash ledger / live measurement 不足を LLM、backtest、virtual artifact で補わない。

## C3: Truth-Cycle Status Review

判定: 既存 truth-cycle artifact がある場合だけできる。

既存の truth-cycle status artifact がある場合だけ、後続実行より先に status を読む。

見るもの:

- `stage_checklist.blocks_progress=true`
- `stop_reasons`
- `known_gaps`
- `cycle_status`
- `next_steps`

`NEEDS_ACTUAL_CASH` は actual cash basis 作り直しの停止結果です。tiny live、gate、次の勝ち筋へ進む合図ではない。

完了条件:

- `stage_checklist.blocks_progress=true` を無視しない。
- `stop_reasons` と `known_gaps` を先に読む。
- `NEEDS_ACTUAL_CASH` を actual cash rows が必要な停止結果として扱う。

## C4: Actual Cash Rows Handoff

判定: cash ledger + assignment がある場合だけできる。

actual cash rows は cash ledger + explicit assignment からだけ作る。preview / estimate / backtest / virtual / dogfood から rows を作らない。

既存入口:

```bash
uv run sis crypto-perp-actual-cash-rows-build \
  --ledger <cash_ledger.json> \
  --assignment <assignment.json> \
  --out <actual_cash_rows_dir>
```

前提:

- `crypto-perp-actual-cash-rows-build` は ledger + assignment 以外を拒否する前提で扱う。
- trade action の missing ledger entry は失敗。
- missing ledger entry の cash 0 埋めは禁止。
- `NO_TRADE` だけ cash 0 を許可する。

完了条件:

- ledger と assignment が無い時は rows build を実行しない。
- trade action と ledger entry の対応が無い時は失敗として扱う。
- `NO_TRADE` を同一event set比較の一部として cash 0 にできる。

## C5: Actual-Cash Report Gate

判定: actual cash rows がある場合だけできる。

actual-cash report gate は actual cash rows がある場合だけ実行候補にする。

既存入口:

```bash
uv run sis crypto-perp-actual-cash-report-gate \
  --rows <actual_cash_rows.jsonl> \
  --report-id <report-id> \
  --min-events 10 \
  --out <report_gate_dir>
```

rows が無いなら実行しないこと自体を完了条件に含める。gate result を live readiness、auto trade、tiny live permission に接続しない。

完了条件:

- actual cash rows が無い場合は gate を実行しない。
- gate artifact を profit evidence の代替にしない。
- gate result が ready に見えても `permits_live_order=false` の境界を維持する。

## C6: Risk-Taker Review

判定: rows-v2 + source availability + bias guard がある場合だけできる。

既存入口:

```bash
uv run sis crypto-perp-risk-taker-review \
  --rows-v2 <crypto_perp_tournament_rows.v2.json> \
  --source-availability <crypto_perp_source_availability.v1.json> \
  --bias-guard <crypto_perp_bias_guard.v1.json> \
  --operator-jurisdiction-status <allowed|prohibited|unknown> \
  --source-freshness-status <fresh|stale|unknown> \
  --out <risk_review_dir>
```

`READY_FOR_HUMAN_RISK_REVIEW` は live permission ではない。risk-taker review は human review artifact であり、注文許可、tiny live 許可、自動売買許可ではない。

完了条件:

- rows-v2、source availability、bias guard が揃っている場合だけ review を検討する。
- `READY_FOR_HUMAN_RISK_REVIEW` を live permission と読まない。
- `permits_live_order=false` を必ず維持する。

## C7: Demo / Testnet Execution

判定: 初期計画では未実装・後回し。

demo / testnet execution は actual cash source availability より前にやらない。これは profit evidence ではなく、order lifecycle、reject、partial fill、cancel、reduce-only close、flat reconciliation の execution lifecycle check です。

完了条件:

- actual cash source availability の前に demo / testnet 実行を優先しない。
- demo / testnet pass を profit evidence、candidate promotion、gate override に使わない。
- production exchange write、wallet、signing、live order へ接続しない。

## C8: External LLM API

判定: 初期計画では未実装・後回し。

external LLM API は manual review が詰まるまで入れない。LLM output は反対尋問材料であり、score補正、promotion、gate override、paper/live permission に使わない。

完了条件:

- manual review が詰まるまで provider adapter を追加しない。
- LLM output を missing artifact の補完に使わない。
- LLM response を score補正、candidate promotion、gate override、actual cash 判定に使わない。

## 抜け、漏れ、誤謬リスク

- artifact 量を profit evidence と誤読する。
- dogfood / status / viewer artifact を real event / matured outcome と混同する。
- `BLOCKED_MISSING_EVENT_OR_OUTCOME` や `NEEDS_ACTUAL_CASH` を失敗として回避しようとする。
- rows が無いのに gate を実行して、gate artifact の存在で安心する。
- missing ledger entry を cash 0 で埋める。
- `NO_TRADE` を失敗扱いして同一event set比較を壊す。
- demo / testnet を profit proof と誤読する。
- LLM API を判断者に昇格する。
- `permits_live_order=false` の境界を、review ready や gate ready の言葉で曖昧にする。
