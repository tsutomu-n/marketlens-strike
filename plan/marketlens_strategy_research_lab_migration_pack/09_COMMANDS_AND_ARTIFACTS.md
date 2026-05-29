# 09 Commands And Artifacts

## Existing Commands To Keep

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run sis bot-preview
uv run sis paper-operations-cycle
```

## New Commands

### strategy-preview

```bash
uv run sis strategy-preview \
  --spec configs/strategies/equity_index_momentum_v0.yaml \
  --evaluation-plan configs/evaluation/initial_walkforward.yaml
```

Outputs:

```text
data/research/strategy_signals.parquet
data/research/strategy_signals.jsonl
data/reports/strategy_signals_preview.md
```

### evaluate-strategy-lab

```bash
uv run sis evaluate-strategy-lab \
  --spec configs/strategies/equity_index_momentum_v0.yaml \
  --evaluation-plan configs/evaluation/initial_walkforward.yaml
```

Outputs:

```text
data/research/trial_ledger.jsonl
data/reports/strategy_trial_report.md
```

### build-paper-candidate-pack

```bash
uv run sis build-paper-candidate-pack \
  --trial-ledger data/research/trial_ledger.jsonl
```

Outputs:

```text
data/research/paper_candidate_pack.json
data/reports/paper_candidate_pack.md
```

### promotion-decision

```bash
uv run sis promotion-decision \
  --source-pack data/research/paper_candidate_pack.json \
  --decision hold
```

Outputs:

```text
data/research/promotion_decision.json
data/reports/promotion_decision.md
```

### build-paper-intent-preview

```bash
uv run sis build-paper-intent-preview \
  --source-pack data/research/paper_candidate_pack.json \
  --promotion-decision data/research/promotion_decision.json
```

Outputs:

```text
data/bot/paper_intent_preview.json
data/reports/paper_intent_preview.md
```

### paper-from-intents

```bash
uv run sis paper-from-intents \
  --intents-path data/bot/paper_intent_preview.json
```

Outputs:

```text
data/paper/orders.parquet
data/paper/fills.parquet
data/paper/positions.parquet
data/paper/paper_observation_ledger.jsonl
data/reports/daily_paper_report.md
```
