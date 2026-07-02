<!--
作成日: 2026-07-02_00:00 JST
更新日: 2026-07-02_00:00 JST
-->

# Test And Acceptance Plan: Profit Core Smart Priors

## 結論

この計画のテスト目的は、利益が出ることを証明することではない。候補生成・探索会計・kill gate・virtual gate が、false positive、検証渋滞、実行不能候補、actual cash誤読を増やさないことを確認する。

## テスト階層

### L0: Schema validation

目的: JSON SchemaとPydantic modelの契約が一致していることを確認する。

対象:

- `smart_candidate_prior_report.v1`
- `edge_candidate_search_ledger.v1`
- `trial_multiplicity_account.v1`
- `backtest_kill_gate.v1`
- `virtual_execution_gate.v1`
- `llm_adversarial_evidence_review.v1`

必須テスト:

```text
valid minimal payload passes
extra field fails
permission true flag fails
missing source refs fail when required
virtual actual_cash=true fails
LLM approval override fails
```

想定ファイル:

```text
tests/edge_candidate_factory/test_schema_validation.py
tests/edge_candidate_factory/test_models.py
```

### L1: Smart Prior unit tests

目的: flow cause based priorが、feature listだけの候補にならないことを確認する。

必須テスト:

```text
each family has cause_prior
each family has mechanism_card
each family has required_sources
each family has kill_conditions
volatility compression is regime/statistical state, not standalone forced-flow cause
spread widening can generate NO_TRADE/filter candidate
funding candidate requires basis/cost/funding source fields
liquidation candidate includes reversal and continuation counter hypothesis
```

想定ファイル:

```text
tests/edge_candidate_factory/test_smart_priors.py
```

### L2: Generator determinism tests

目的: 同じ入力とconfigから同じcandidate inventoryが再生成されることを確認する。

必須テスト:

```text
same source and config produces same candidate ids
candidate cap produces cap rejection rows
near duplicate produces duplicate rejection rows
missing source produces blocker, not success
selected-only output is impossible
candidate_prior_score is present but proof_status remains not_alpha_or_profit_proof
```

想定ファイル:

```text
tests/edge_candidate_factory/test_generator.py
```

### L3: Ledger and multiplicity tests

目的: 大量探索を会計なしに進めないことを確認する。

必須テスト:

```text
candidate_count_total equals generated + rejected
family_trial_counts sum to total
validation_peek_count is persisted
rerank_count is persisted
sealed_test_used_for_selection=true fails
success_only_reporting=true fails
effective_trial_count_status can be NOT_ESTIMABLE and is not hidden
candidate_cluster_count is persisted
```

想定ファイル:

```text
tests/edge_candidate_factory/test_multiplicity.py
tests/edge_candidate_factory/test_ledger.py
```

### L4: Backtest Kill Gate tests

目的: backtestがattack permissionではなくkill deviceとして動くことを確認する。

必須テスト:

```text
backtest pass alone does not produce SHORTLIST_FOR_VIRTUAL
NO_TRADE leader blocks or kills candidate
missing source results INCONCLUSIVE_DATA
technical bridge only does not equal economic pass
rare event family can be RESEARCH_ONLY instead of immediate KILL
large loss exceeds limit -> KILL
profit concentration exceeds limit -> KILL
multiplicity account missing -> INCONCLUSIVE_DATA
sealed test used for selection -> KILL or hard block
```

想定ファイル:

```text
tests/edge_candidate_factory/test_backtest_kill_gate.py
```

### L5: Virtual Execution Gate tests

目的: virtual forwardがPnLではなくexecution lifecycleを検証することを確認する。

必須テスト:

```text
fixture order accepted -> lifecycle pass
reject reason captured -> no crash
partial fill handled
cancel handled
reduce-only close checked
flat reconciliation mismatch -> VIRTUAL_FAILED_RECONCILIATION
actual_cash=true in virtual artifact fails
production_exchange_write_used=true fails
virtual PnL cannot be consumed by actual cash report gate
duplicate client_oid blocked
```

想定ファイル:

```text
tests/edge_candidate_factory/test_virtual_execution_gate.py
```

### L6: C9 bridge compatibility tests

目的: technical bridge statusをeconomic passと誤読しないことを確認する。

対象:

- `tests/strategy_idea_candidates/test_authoring_bridge.py`

追加テスト:

```text
BRIDGED summary records bridge_success_semantics=technical_only
min_trade_count=0 marks economic_gate_status=NOT_EVALUATED
pass_thresholds={} marks economic_gate_status=NOT_EVALUATED
candidate scoped paths remain present
unsupported family still writes blocker
source missing still writes blocker
```

### L7: LLM Adversarial Evidence Review tests

目的: LLM reviewがapprovalではなくnegative-vetoに限定されることを確認する。

必須テスト:

```text
manual AI response saying APPROVE does not set permission
missing artifact finding is persisted
overclaim flag is persisted
actual_cash_confusion finding is persisted
machine_checkable=true hard blocker can block
non-machine-checkable finding remains soft warning
```

想定ファイル:

```text
tests/edge_candidate_factory/test_adversarial_review.py
```

### L8: CLI tests

目的: public commandsがoperatorに危険な誤読をさせないstdoutを出すことを確認する。

必須テスト:

```text
edge-candidate-factory-run --help works
edge-candidate-backtest-kill-gate --help works
edge-candidate-artifact-summary --help works
network_attempted=false emitted in local mode
production_exchange_write_used=false emitted before virtual network mode
live_order_submitted=false emitted
status field emitted
artifact paths emitted
known_gap_count emitted
```

想定ファイル:

```text
tests/edge_candidate_factory/test_cli.py
```

## Fixture strategy

### Fixture source root

新規fixture root:

```text
tests/fixtures/edge_candidate_factory/prep_watchdeck_source_root/
```

最低限含めるもの:

```text
data/scanner.duckdb
data/candles_5m/date=YYYY-MM-DD/candles.parquet
var/snapshots/latest.json
```

このfixtureは、既存 `strategy_idea_candidates` の prep-watchdeck compatible source fixture と重複しすぎないようにする。共通化できる場合はhelperを使う。

### Fixture scenarios

最低限次を用意する。

1. normal BTCUSDT source with funding and candles。
2. missing funding source。
3. missing candles source。
4. high spread source。
5. duplicate candidate parameter source。
6. virtual execution normal lifecycle。
7. virtual execution reconciliation mismatch。
8. LLM adversarial response with overclaim。

## Acceptance matrix

| Area | Acceptance | Required test |
|---|---|---|
| Schema | all new schema validate minimal and reject unsafe flags | L0 |
| Smart Prior | all candidates have cause prior, mechanism, sources, kill conditions | L1 |
| Generator | deterministic, full inventory, no selected-only output | L2 |
| Ledger | all trials and rejections accounted | L3 |
| Multiplicity | sealed test and success-only reporting cannot pass | L3 |
| Backtest Kill Gate | backtest pass alone cannot advance | L4 |
| Bridge | technical bridge not economic pass | L6 |
| Virtual Gate | lifecycle pass is not profit proof | L5 |
| LLM Review | LLM cannot approve or override gate | L7 |
| CLI | safe stdout fields emitted | L8 |

## Definition of Done by task

### T1 done

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run ruff check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py
```

### T2 done

```bash
uv run pytest tests/edge_candidate_factory/test_models.py -q
uv run pytest tests/edge_candidate_factory/test_schema_validation.py -q
```

### T3 done

```bash
uv run pytest tests/edge_candidate_factory/test_smart_priors.py -q
```

### T4 done

```bash
uv run pytest tests/edge_candidate_factory/test_generator.py -q
uv run pytest tests/edge_candidate_factory/test_cli.py -q
```

### T5 done

```bash
uv run pytest tests/edge_candidate_factory/test_multiplicity.py -q
uv run pytest tests/edge_candidate_factory/test_ledger.py -q
```

### T6 done

```bash
uv run pytest tests/edge_candidate_factory/test_backtest_kill_gate.py -q
```

### T7 done

```bash
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
```

### T8 done

```bash
uv run pytest tests/edge_candidate_factory/test_virtual_execution_gate.py -q
```

### T9 done

```bash
uv run pytest tests/edge_candidate_factory/test_adversarial_review.py -q
```

### Final done

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run ty check src --python-version 3.13 --output-format concise
uv run pytest -q
./scripts/check
```

固定pass countはこの文書に書かない。

## Hard blockers

次が1つでもあれば、実装は未完了。

- candidate generation outputがshortlistだけ。
- rejection ledgerがない。
- validation peek countが保存されない。
- sealed testをselectionに使っている。
- C9 technical bridgeをeconomic passにしている。
- virtual PnLをactual cashにしている。
- virtual gateがflat reconciliationを見ていない。
- LLM outputがpermissionやgate overrideを持つ。
- Addon resultがCore statusを上書きする。
- `./scripts/check` が通らない。

## Manual review checklist

コードレビュー時は次を確認する。

1. 新artifactのboundary fieldがfalse固定か。
2. `actual_cash` と `virtual_exchange` が混ざっていないか。
3. `BRIDGED` の意味がtechnical-onlyとして保存されているか。
4. source refs path/hashが残るか。
5. candidate idがbridge、kill gate、virtual gate、risk reviewまで失われないか。
6. NO_TRADE比較が欠けた候補を前進させていないか。
7. operator timeやunexecutable reasonがcandidate priorに入っているか。
8. LLM reviewがapprovalやscore補正をしていないか。
9. external networkを使うcommandが明示opt-inなしに動かないか。
10. docsが未実装のものを実装済みと書いていないか。
