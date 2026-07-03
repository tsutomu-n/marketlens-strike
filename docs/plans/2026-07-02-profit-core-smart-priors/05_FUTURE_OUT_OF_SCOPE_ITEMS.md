<!--
作成日: 2026-07-03_07:19 JST
更新日: 2026-07-03_08:20 JST
-->

# Future Out-of-Scope Items: Profit-First Stop Conditions

## 結論

この文書の4項目は実装キューではない。actual cash ledger / live measurement、assignment、event universe が揃わない限り、demo / testnet 実行、外部LLM API、actual-cash gate 実行を進めても profit-readiness は上がらない。

正しい結果は `BLOCKED_NEEDS_ACTUAL_CASH_ROWS`、または既存CLI上の `BLOCKED_MISSING_EVENT_OR_OUTCOME` / `NEEDS_ACTUAL_CASH` で止めることです。ここに書く内容は、実行済み証跡ではなく、止まる順序と読みに行く既存CLIを固定するための境界です。

- demo / testnet は execution lifecycle evidence であり、profit evidence ではない。
- external LLM API は review automation であり、profit evidence ではない。
- actual-cash gate 実行の価値は rows の品質に依存する。rows が無ければ実行しないことが正しい。
- virtual / backtest / estimate / LLM output は actual cash rows に変換できない。
- dogfood / status / viewer artifacts は profit evidence ではない。
- actual cash rows は cash ledger + explicit assignment からだけ作る。

## 共通境界

すべての項目に次を適用する。

- production live trading を許可しない。
- wallet / signing / production exchange write を標準operator pathへ昇格しない。
- virtual / backtest / estimate / LLM output を actual cash evidence として扱わない。
- LLM output を approval、paper permission、live permission、gate override として扱わない。
- `data/` に生成されるruntime artifactをtracked source of truthにしない。
- 外部API、credential、exchange write、actual cash rows、risk gate実行は、それぞれ別PRまたは別作業単位で明示scopeにする。

## Profit-First Gate Order

demo / testnet や外部LLM APIより先に、次の順番で止まる。新規audit CLIを作るのではなく、既存CLIの出力を読む。

1. `crypto-perp-profit-readiness-inventory`
   - real event と matured outcome が無ければ `BLOCKED_MISSING_EVENT_OR_OUTCOME`。
   - dogfood / status / viewer artifacts は profit evidence ではない。
2. `crypto-perp-source-availability`
   - `can_compute_actual_cash=false` なら actual cash rows へ進まない。
   - `cash_ledger` または `live_measurement` が必要。
3. `crypto-perp-truth-cycle-status`
   - `stop_reasons` と `stage_checklist.blocks_progress=true` を先に読む。
   - `NEEDS_ACTUAL_CASH` なら actual cash basis で作り直す。
4. `crypto-perp-actual-cash-rows-build`
   - cash ledger + explicit assignment からだけ rows を作る。
5. `crypto-perp-actual-cash-report-gate`
   - actual cash rows がある場合だけ実行候補にする。

## 現実的な優先順位

1. Existing artifact inventory / status review
   - 最初にやる。既存CLIで足りる。ここで event / outcome が無ければ止める。
2. Source availability actual-cash check
   - `can_compute_actual_cash` が現実判定。`cash_ledger` または `live_measurement` が無ければ止める。
3. Actual cash rows handoff integration
   - ledger + assignment がある時だけ価値がある。入力条件の検証が主作業。
4. Actual cash report gate execution
   - actual cash rows がある時だけ価値がある。rows なし実行は儀式。
5. Demo / testnet virtual execution
   - actual cash 投入直前の execution risk check。profit evidence ではない。
6. External LLM API
   - manual review が詰まるまで不要。API化は運用自動化であり profit evidence ではない。

## 1. Actual Cash Source Availability

### 現在の扱い

まず既存artifact inventoryを読む。real event と matured outcome が無いなら、dogfood/status/viewerが揃っていても profit-readiness は止まる。

```bash
uv run sis crypto-perp-profit-readiness-inventory \
  --data-dir data/crypto_perp \
  --out data/crypto_perp/artifact_inventory/latest
```

見るもの:

- `inventory_status`
- real event の有無
- matured outcome の有無
- dogfood/status/viewer artifacts しか無い状態になっていないか

`inventory_status=BLOCKED_MISSING_EVENT_OR_OUTCOME` なら止める。次に進む理由は無い。

event がある場合だけ、source availability を読む。

```bash
uv run sis crypto-perp-source-availability \
  --event data/crypto_perp/events/<event-id>/event.json \
  --out data/crypto_perp/source_availability/<event-id>
```

見るもの:

- `can_compute_actual_cash`
- `source_statuses` の `source_id=cash_ledger`
- `source_statuses` の `source_id=live_measurement`
- source refs
- row counts
- `known_gaps`

`can_compute_actual_cash=false` なら actual cash rows / actual-cash gate は不可。`known_gaps` の `ACTUAL_CASH_SOURCE_MISSING` を停止理由として扱う。

truth-cycle status が既にある場合は、次に欠けているlocal stepを読む。

```bash
uv run sis crypto-perp-truth-cycle-status \
  --event data/crypto_perp/events/<event-id>/event.json \
  --source-availability data/crypto_perp/source_availability/<event-id>/source_availability.json \
  --out data/crypto_perp/truth_cycle_status/<event-id>
```

見るもの:

- `next_steps`
- `stage_checklist`
- `stage_checklist[].blocks_progress`
- `stop_reasons`
- `known_gaps`
- `cycle_status`

`stage_checklist.blocks_progress=true` が残っている間は、次の勝ち筋、tiny live、gate 実行へ進まない。`cycle_status=NEEDS_ACTUAL_CASH` なら actual cash basis の証跡を用意し直す。

### 停止条件

- real event が無い。
- matured outcome が無い。
- `cash_ledger` と `live_measurement` が両方無い。
- source refs / row counts が無い。
- dogfood/status/viewer artifacts しか無い。
- source availability を作らず rows / gate へ進もうとしている。

### 受入条件

- inventory が `BLOCKED_MISSING_EVENT_OR_OUTCOME` の時に後続実行へ進まない。
- source availability の `can_compute_actual_cash=false` を停止結果として読める。
- `ACTUAL_CASH_SOURCE_MISSING` を gap ではなく停止理由として扱う。
- 既存CLIの読み方だけを固定し、新規audit CLIを作らない。

## 2. Actual Cash Rows Generation

### 現在の扱い

actual cash rows は「生成」ではなく、実cash証跡の写像です。入力は cash ledger + explicit assignment のみ。preview / estimate / backtest / virtual / dogfood から rows を作らない。

既存入口:

```bash
uv run sis crypto-perp-actual-cash-rows-build \
  --ledger data/crypto_perp/cash_ledger/<ledger-id>/cash_ledger.json \
  --assignment data/crypto_perp/cash/assignment.json \
  --out data/crypto_perp/tournament/<report-id>/actual_cash_rows
```

assignment は `event_id`、`action`、`pod_id` を明示する。`NO_TRADE` は `pod_id=null` と cash 0 を許可する。`REVERSAL_SHORT` / `CONTINUATION_LONG` のような trade action は、対応する ledger entry が無ければ失敗する。欠損 ledger entry を cash 0 で埋めない。

### 必須条件

- ledger artifact と assignment file の source refs を保存する。
- assignment は `event_id`、`action`、`pod_id` を明示する。
- trade action の `pod_id` は ledger entry と対応する。
- `NO_TRADE` だけが `pod_id=null` と cash 0 を許される。
- rows は `cash_metric_basis=actual_cash` を満たす。
- `actual_cash_result_usd` は actual cash basis の時だけ使う。
- fee / funding / fill / partial close の扱いを source refs または `known_gaps` に残す。

### 停止条件

- ledger が無い。
- assignment が無い。
- assignment の `pod_id` に対応する ledger entry が無い。
- `cash_metric_basis=actual_cash` を満たさない。
- `actual_cash_result_usd` を non-actual basis で埋めようとしている。
- fee / funding / fill / partial close の扱いを source refs / `known_gaps` に残せない。
- virtual / backtest / estimate / dogfood を rows source にしようとしている。

### 受入条件

- `actual_cash_rows_summary.json` と `actual_cash_rows.jsonl` の source refs に ledger と assignment が含まれる。
- trade action は ledger entry 欠損で失敗し、0埋めしない。
- `NO_TRADE` は同一event set比較の一部として cash 0 を明示できる。
- `crypto-perp-actual-cash-report-gate` に渡せる rows 形式であることを確認できる。

## 3. Risk / Actual-Cash Gate Execution

### 現在の扱い

gate 実行自体は価値ではない。gate の価値は actual cash rows の品質に依存する。rows が無ければ、実行しないことが正しい。

`crypto-perp-risk-taker-review` は human risk review artifact であり、live permission ではない。`crypto-perp-actual-cash-report-gate` は actual cash rows を読むが、ready status を live permission にしない。

既存入口:

```bash
uv run sis crypto-perp-actual-cash-report-gate \
  --rows data/crypto_perp/tournament/<report-id>/actual_cash_rows/actual_cash_rows.jsonl \
  --report-id <report-id> \
  --min-events 10 \
  --out data/crypto_perp/tournament/<report-id>/report_gate
```

human risk review を別に作る場合も、live permission ではなく local review artifact として読む。

```bash
uv run sis crypto-perp-risk-taker-review \
  --rows-v2 <crypto_perp_tournament_rows.v2.json> \
  --source-availability <crypto_perp_source_availability.v1.json> \
  --bias-guard <crypto_perp_bias_guard.v1.json> \
  --operator-jurisdiction-status <allowed|prohibited|unknown> \
  --source-freshness-status <fresh|stale|unknown> \
  --out <risk_review_dir>
```

### 必須条件

- actual cash rows ref とそのhashが存在する。
- rows は actual cash basis である。
- source availability と bias guard が同じ candidate / event universe を指す。
- operator jurisdiction と venue terms status を明示する。
- gate outputを human review 用として扱い、live permissionへ直結しない。
- `NO_TRADE` を失敗扱いしない。

### 停止条件

- rows が無い。
- rows が actual cash basis ではない。
- source availability / bias guard が同じ universe を指さない。
- `NO_TRADE` を失敗扱いしている。
- event count が不足している。
- jurisdiction / venue terms / source freshness が unknown のまま ready扱いになる。
- gate result を live readiness / auto trade / tiny live permission に接続しようとしている。

### 受入条件

- rows なしなら gate を実行しないことを acceptance にする。
- actual-cash report gate artifactが rows source refs を保持する。
- ready になっても `permits_live_order=false` の境界を崩さない。
- final summary は gate status と known gaps を表示するが、live order permissionを表示しない。

## 4. Demo / Testnet Execution

### 現在の扱い

demo / testnet は actual cash source availability より前にやらない。demo / testnet pass は edge、profit、actual cash を証明しない。価値は order accepted / rejected、partial fill、cancel、reduce-only close、flat reconciliation の確認だけです。

`Virtual Execution Gate v0` は、まず fixture / mock mode で order lifecycle と reconciliation を検査する計画です。実際の demo / testnet order lifecycle 実行は今回の範囲外です。

既存 `bitget-demo-smoke` は read-only smoke であり、`external_write_enabled=false`、`exchange_write_used=false` を出す。これは demo order lifecycle 実行ではない。

### 将来の入口

最初の将来PRは、1 venue だけに限定する。Bitget demo、Hyperliquid testnet、GRVT testnet を同時に入れない。actual cash 投入直前の execution risk check として扱う。

想定対象:

```text
src/sis/edge_candidate_factory/virtual_execution_gate.py
src/sis/execution/bitget_demo_virtual.py
tests/edge_candidate_factory/test_virtual_execution_gate.py
tests/execution/test_bitget_demo_virtual.py
```

### 必須条件

- 明示opt-in flagなしでは network / exchange write を試みない。
- `execution_environment=demo` または `execution_environment=testnet` を保存する。
- `exchange_write_used=true` になっても、`production_exchange_write_used=false`、`actual_cash=false`、`cash_metric_basis=virtual_exchange` を固定する。
- production endpoint と demo / testnet endpoint をartifactで区別できる。
- client order id の重複防止を実装する。
- order accepted、reject reason、partial fill、cancel、reduce-only close、flat reconciliation を保存する。
- fee-like fields と funding-like fields は actual cash ではなく virtual exchange metadata として扱う。

### 停止条件

- production endpoint に書き込みが必要。
- credential が未設定、またはenv名が文書化されていない。
- cancel / reduce-only close / flat reconciliation を検証できない。
- demo / testnet pass を candidate promotion に使う。
- demo / testnet PnL を actual cash rows に混ぜる。
- production endpoint と demo / testnet endpoint をartifactで区別できない。
- `production_exchange_write_used=false` を保存できない。
- source refs や request / response hash を残せない。

### 受入条件

- 正常系、reject、partial fill、cancel、reconciliation mismatch のfixture testがある。
- demo / testnet opt-in testで `production_exchange_write_used=false` を検証する。
- artifactが `virtual_execution_gate.v1` を満たす。
- stdoutに `actual_cash=false`、`cash_metric_basis=virtual_exchange`、`permits_live_order=false` が出る。

## 5. External LLM API

### 現在の扱い

external LLM API は初期Coreには不要。manual packet / manual import で詰まるまで入れない。API化は profit evidence ではなく運用自動化です。

今回の `LLM Adversarial Evidence Review v0` は manual packet / manual import 方式です。外部LLM APIは呼ばない。

既存 `strategy-ai-review-packet-build`、`strategy-ai-review-note-record`、`strategy-ai-review-findings-structure` も、人間レビュー支援用のlocal artifact経路であり、permissionやlive readinessを出さない。

provider response は反対尋問材料であり、判断者ではない。既存 `strategy-ai-review-*` と同じく permission / live readiness は出さない。

### 将来の入口

外部LLM APIを入れる場合は、manual review が運用ボトルネックになった場合だけにする。`llm_adversarial_evidence_review.v1` の前段に provider adapter と redaction / cost / timeout / retry policy を追加する。

想定対象:

```text
src/sis/edge_candidate_factory/adversarial_review.py
src/sis/edge_candidate_factory/llm_provider.py
tests/edge_candidate_factory/test_adversarial_review.py
tests/edge_candidate_factory/test_llm_provider.py
```

### 必須条件

- 明示opt-in flagなしでは外部APIを呼ばない。
- prompt packet、redaction report、request hash、response hash、provider、model、timeout、cost cap をartifactへ残す。
- secrets、credentials、raw private payload、未許可sourceをpromptへ入れない。
- API failure は review unavailable / blocked として扱い、approval扱いにしない。
- LLMが `APPROVE`、`PASS`、`PROMOTE`、`LIVE_READY` を返しても無視する。

### 停止条件

- actual cash source 不足を LLMで補おうとしている。
- LLM response を score補正、candidate promotion、gate override に使う。
- redaction / prompt provenance / response hash / cost cap が無い。
- provider failure を human approval や soft pass として扱う。
- LLMがmissing artifactを補完する設計になる。

### 受入条件

- external API未使用のlocal/manual pathが引き続き動く。
- external API adapterは opt-in disabled で network未試行になる。
- overclaim、missing artifact、actual cash confusion、contradiction がfindingとして保存される。
- `llm_approval_ignored=true`、`gate_override_allowed=false`、`actual_cash_decision_allowed=false` を検証する。

## 推奨PR分割

将来実装する場合は、次の順に分ける。

1. Existing artifact inventory and source availability doc/runbook alignment
   - 新規CLIは作らない。
   - `crypto-perp-profit-readiness-inventory`、`crypto-perp-source-availability`、`crypto-perp-truth-cycle-status` の読み方を文書化する。
2. Actual cash rows handoff integration
   - 既存 rows builder の入力条件を Edge Candidate handoff 側で検証する。
   - ledger + assignment 以外を拒否する。
3. Actual cash report gate execution
   - actual cash rows がある場合だけ gate実行対象にする。
   - rowsなしなら実行しないことを acceptance にする。
4. Demo / testnet virtual execution
   - actual cash 投入直前の execution lifecycle check。
   - profit evidence として扱わない。
5. External LLM API
   - manual review が運用ボトルネックになった場合だけ。
   - 初期Coreでは原則やらない。

## 誤謬リスク

- ロードマップ誤謬: 並べた項目を順に作れば進むように見える。
- 再実装誤謬: 既存 `inventory` / `source_availability` / `truth_cycle_status` を見ずに新auditを作る。
- 技術達成誤謬: demo / testnet、LLM API、gate artifact を profit evidence と誤読する。
- 証跡変換誤謬: virtual / backtest / estimate を actual cash rows に変換できるように見せる。
- gate儀式化リスク: 入力が弱いのに gate status で安心する。
- LLM権威化リスク: もっともらしいAPI応答を判断に昇格する。
- testnet過大評価リスク: demo / testnet は本番の流動性、latency、slippage、panic挙動を代表しない。
- NO_TRADE誤読リスク: `NO_TRADE` を失敗扱いし、同一event set比較を壊す。
- 0埋め誤謬: missing ledger entry を cash 0 として扱う。許される cash 0 は明示的な `NO_TRADE` だけ。
- current-doc drift risk: archive docs の古い手順をcurrent pathとして読ませる。

## 最低検証

docsだけを更新する場合:

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

将来実装する場合は、変更範囲に応じて最低限次を追加する。

```bash
uv run pytest tests/edge_candidate_factory/test_virtual_execution_gate.py -q
uv run pytest tests/edge_candidate_factory/test_adversarial_review.py -q
uv run pytest tests/edge_candidate_factory/test_risk_actual_cash_handoff.py -q
uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q
uv run python scripts/check_cli_catalog.py
./scripts/check
```
