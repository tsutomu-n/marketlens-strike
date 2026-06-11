<!--
作成日: 2026-06-11_14:29 JST
更新日: 2026-06-11_14:29 JST
-->

# Layer 2.7 NDX Operator Promotion

Layer 2.7 records an explicit operator decision to allow Layer 2.5 NDX/QQQ signals into paper observation after Layer 2.6 approves paper-observation review.

## Command

```bash
uv run sis research-ndx-operator-promotion \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --decision promote_to_paper_observation \
  --reviewer local_operator \
  --approval-reason paper_observation_gate_reviewed
```

## Outputs

- `data/research/ndx/operator_promotion_decision.json`
- `data/reports/ndx_operator_promotion_report.md`

## Boundary

Layer 2.7 promotion can unlock NDX/QQQ `trade_xyz` paper candidate and `PaperIntentPreview` generation only when its artifact hash and source Layer 2.6 gate hash match. Without valid evidence, existing NDX/QQQ venue suitability blocks remain active.

Layer 2.7 does not permit live orders. Generated `PaperIntentPreview` rows remain paper-only and must pass `paper-from-intents` revalidation against local quotes and paper broker state before paper artifacts are written.
