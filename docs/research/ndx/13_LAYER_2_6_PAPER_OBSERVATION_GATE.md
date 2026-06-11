<!--
作成日: 2026-06-11_14:29 JST
更新日: 2026-06-11_14:29 JST
-->

# Layer 2.6 NDX Paper Observation Gate

Layer 2.6 checks whether the Layer 2.5 research-only Strategy Lab export has enough local evidence to request operator review for paper observation.

## Command

```bash
uv run sis research-ndx-paper-observation-gate \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --quotes-path data/normalized/quotes.parquet
```

## Outputs

- `data/research/ndx/paper_observation_gate_decision.json`
- `data/reports/ndx_paper_observation_gate_report.md`

## Boundary

Layer 2.6 validates Layer 2.5 artifact hashes, signal counts, era counts, tested variant count, and local `trade_xyz` / `XYZ100` quote availability. It records `sample_scope`, `evidence_tier`, `quotes_hash`, and `paper_observation_dry_run_ready`.

Layer 2.6 does not prove alpha, robust out-of-sample performance, paper readiness, live readiness, wallet readiness, or exchange-write readiness. Even `APPROVE_PAPER_OBSERVATION_REVIEW` only permits a Layer 2.7 operator promotion review.
