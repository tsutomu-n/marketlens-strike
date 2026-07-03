<!--
作成日: 2026-07-03_10:10 JST
更新日: 2026-07-03_12:41 JST
-->

# Blocker Taxonomy

## 結論

Reality Check Sprint の目的は、利益候補を探すことではなく、既存pipelineの詰まりを分類し、次に直す1箇所を決めることです。

この文書は blocker name、意味、原因、次actionを固定する。

## Blocker severity

```text
HARD_BLOCKER: 次段へ進めない。
SOFT_BLOCKER: 進めるが、profit evidenceとしては読まない。
INFO: 境界メモ。進行判定には使わない。
```

## Stage: Candidate Generation

### CANDIDATE_SET_MISSING

Severity: HARD_BLOCKER

意味: candidate set artifact が無い。

次action:

```text
strategy-idea-candidates-build を再実行する。
input contract / validation のpathを確認する。
```

### SEARCH_LEDGER_MISSING

Severity: HARD_BLOCKER

意味: search ledger が無い。探索全量を検証できない。

次action:

```text
candidate generation outputを確認する。
search_ledger.jsonl を出さない古いrunは使わない。
```

### EXPORT_MANIFEST_MISSING

Severity: HARD_BLOCKER

意味: shortlistを次段へ渡すsidecarが無い。

次action:

```text
--export-shortlist が有効か確認する。
exported_strategy_ideas/strategy_idea_candidate_export_manifest.json を確認する。
```

### SUCCESS_ONLY_REPORTING_DETECTED

Severity: HARD_BLOCKER

意味: shortlistだけが残り、rejected candidates が無い。

次action:

```text
そのrunは使わない。
全candidate inventoryとrejection reasonを出すrunに戻す。
```

### SEALED_TEST_USED_FOR_SELECTION

Severity: HARD_BLOCKER

意味: sealed test を候補選択に使っている。

次action:

```text
runを破棄する。
sealed test non-use を満たす設定で再生成する。
```

### NO_SHORTLISTED_CANDIDATES

Severity: SOFT_BLOCKER

意味: 候補は出たが、shortlistが無い。

次action:

```text
rejection reasonを読む。
source不足、cap、risk field不足、selection policyを確認する。
```

## Stage: Authoring Bridge

### AUTHORING_BRIDGE_MISSING

Severity: HARD_BLOCKER

意味: C9 bridge manifestが無い。

次action:

```text
strategy-idea-candidates-authoring-bridge を実行する。
source_root、candidate_set、export_manifest、ledger pathを確認する。
```

### BRIDGE_ALL_BLOCKED

Severity: HARD_BLOCKER

意味: bridge対象候補が全てblocked。

次action:

```text
status_countsを読む。
一番多いblockerを次PR対象にする。
```

### UNSUPPORTED_FAMILY_DOMINATES

Severity: HARD_BLOCKER

意味: `BLOCKED_UNSUPPORTED_FAMILY_MAPPING` が最多。

次action:

```text
C9 bridgeのblocked_by_family / blocked_reason_countsを読み、実artifactで支配的なfamilyを1つだけ扱う。
source不足やside_bias不足が見えている場合は、成功扱いにせず precise blocker へ分解する。
全family対応はしない。
```

### UNSUPPORTED_SIDE_BIAS_DOMINATES

Severity: HARD_BLOCKER

意味: `both`、`no_trade` などがC9で止まっている。

次action:

```text
C9側で both/no_trade の扱いを定義する。
no_tradeは売買specではなくfilter / blocker / no-trade candidateとして扱う。
```

### NO_SYMBOL_DATA_DOMINATES

Severity: HARD_BLOCKER

意味: symbolのcandle/quoteがsource rootに無い。

次action:

```text
source refresh条件を修正する。
symbol list、product type、granularity、source root pathを確認する。
```

### MISSING_SOURCE_COLUMNS_DOMINATES

Severity: HARD_BLOCKER

意味: familyが必要とする列がsourceに無い。

次action:

```text
source adapterを直す。
不足列をestimateで埋める場合は estimate_only known gap を明示する。
```

### BRIDGED_TECHNICAL_ONLY

Severity: SOFT_BLOCKER

意味: bridgeは通ったが、economic passではない。

次action:

```text
bridge_success_semantics=technical_only を表示する。
economic_gate_status=NOT_EVALUATED として読む。
backtest passやBRIDGEDだけで進めない。
```

## Stage: Profit Readiness

### PROFIT_READINESS_INVENTORY_MISSING

Severity: SOFT_BLOCKER

意味: inventory artifactが無い。

次action:

```text
crypto-perp-profit-readiness-inventory を実行する。
ただし、missing artifactを自動生成しない。
```

### BLOCKED_MISSING_EVENT_OR_OUTCOME

Severity: HARD_BLOCKER

意味: real eventまたはmatured outcomeが不足。

次action:

```text
truth-cycle artifactsを作る。
dogfood/status/viewer artifactだけで解除しない。
```

### ACTUAL_CASH_SOURCE_MISSING

Severity: HARD_BLOCKER

意味: cash ledgerまたはlive measurementが無い。

次action:

```text
actual cash sourceを用意する。
preview、estimate、virtual outputで代用しない。
```

### MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES

Severity: HARD_BLOCKER

意味: 自動選択すると誤る可能性がある。

次action:

```text
operatorがevent/outcomeを明示指定する。
auto-selectしない。
```

## Stage: Risk Review

### RISK_REVIEW_MISSING

Severity: SOFT_BLOCKER

意味: risk-taker review artifactが無い。

次action:

```text
rows-v2、source availability、bias guardがあるか確認する。
揃う場合だけ crypto-perp-risk-taker-review を実行する。
```

### BLOCKED_BY_VENUE

Severity: HARD_BLOCKER

意味: operator jurisdiction または venue constraint が通っていない。

次action:

```text
venue terms、jurisdiction、credential scopeを確認する。
KEEP_RESEARCH_LOCALとして扱う。
```

### INCONCLUSIVE_DATA

Severity: SOFT_BLOCKER

意味: source freshness、cost source、liquidation buffer、leaderなどが不足。

次action:

```text
missing sourceを確認する。
source不足ならsource pipelineを直す。
leaderなしならNO_ACTION。
```

### KILL

Severity: FINAL_STOP

意味: NO_TRADE leader、after-cost negative、stress negative、largest loss、profit concentration、operator timeなどで落ちた。

次action:

```text
候補を殺す。
同じ候補をparameter微調整して再提出しない。
family-level learningだけ残す。
```

### NEEDS_ACTUAL_CASH

Severity: HARD_BLOCKER

意味: estimate上は進める余地があるが、actual cash evidenceが無い。

次action:

```text
cash ledger + assignment を用意する。
virtual outputで代替しない。
```

## Stage: Actual Cash

### ACTUAL_CASH_ROWS_MISSING

Severity: HARD_BLOCKER

意味: actual cash rowsが無い。

次action:

```text
cash ledger + explicit assignment がある場合だけ rows buildを実行する。
```

### CASH_LEDGER_MISSING

Severity: HARD_BLOCKER

意味: cash ledgerが無い。

次action:

```text
実cash証跡を作る。
estimateやbacktestからledgerを作らない。
```

### ASSIGNMENT_MISSING

Severity: HARD_BLOCKER

意味: ledger entryとevent/actionの対応が無い。

次action:

```text
assignmentを明示する。
NO_TRADEはpod_id null可。
trade actionはpod_id必須。
```

### TRADE_ACTION_LEDGER_ENTRY_MISSING

Severity: HARD_BLOCKER

意味: trade actionに対応するledger entryが無い。

次action:

```text
失敗として扱う。
0埋め禁止。
```

### ACTUAL_CASH_REPORT_GATE_MISSING

Severity: SOFT_BLOCKER

意味: rowsはあるがgateが無い。

次action:

```text
actual cash rowsがある場合だけ gate を実行する。
```

## Next action mapping

```text
UNSUPPORTED_FAMILY_DOMINATES -> add one C9 family mapping
UNSUPPORTED_SIDE_BIAS_DOMINATES -> define both/no_trade bridge behavior
NO_SYMBOL_DATA_DOMINATES -> fix source refresh/source root
MISSING_SOURCE_COLUMNS_DOMINATES -> fix source adapter
BLOCKED_MISSING_EVENT_OR_OUTCOME -> run truth-cycle event/outcome steps
ACTUAL_CASH_SOURCE_MISSING -> prepare cash ledger / assignment path
NEEDS_ACTUAL_CASH -> build actual cash rows only from ledger + assignment
KILL -> reject candidate/family variant
INCONCLUSIVE_DATA -> collect missing source or stop
```

## Better option rule

If two blockers tie, choose the one that unlocks the most existing artifacts without adding a new subsystem.

Priority preference:

1. Source/path/hash/lineage repair.
2. C9 bridge blocker with existing family.
3. Actual cash input handoff.
4. Fixture-only virtual lifecycle.
5. New Smart Prior / ML / LLM only after the above fail to move throughput.
