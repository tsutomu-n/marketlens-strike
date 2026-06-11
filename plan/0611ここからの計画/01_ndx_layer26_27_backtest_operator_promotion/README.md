<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# NDX Layer 2.6/2.7 paper-observation gate and operator promotion plan

## 結論

Layer 2.6/2.7 は、Layer 2.5 の research-only NDX signals を限定的な paper observation へ進めるための別計画である。

実装対象は次の 2 gate までに限定する。

1. Layer 2.6: paper-observation acceptance gate
2. Layer 2.7: operator promotion to paper observation

この計画は live trading、wallet、signing、exchange write、public live CLI、production venue enablement を許可しない。live は Layer 2.8 以降の別計画に分ける。

重要: Layer 2.6 は、84 本程度の fixture-derived signal だけで alpha や robust backtest を認定しない。Layer 2.6 が許可できるのは、local artifact lineage、signal/quote revalidation、paper broker dry-run feasibility、operator review に足る最低限の evidence が揃った場合の paper-observation review だけである。

## Read order

1. `01_GOAL_AND_SCOPE.md`
2. `02_CODE_TRUTH_AND_RISK_AUDIT.md`
3. `03_ARTIFACT_CONTRACT.md`
4. `04_IMPLEMENTATION_TASKS.md`
5. `05_ACCEPTANCE_AND_VERIFICATION.md`
6. `06_CODER_HANDOFF_PROMPT.md`
7. `07_STOP_CONDITIONS.md`

## Implementation target

Add two explicit CLI paths:

```bash
uv run sis research-ndx-paper-observation-gate \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --quotes-path data/normalized/quotes.parquet

uv run sis research-ndx-operator-promotion \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --decision promote_to_paper_observation \
  --reviewer local_operator \
  --approval-reason "paper_observation_gate_reviewed"
```

Expected write surface:

- `data/research/ndx/paper_observation_gate_decision.json`
- `data/reports/ndx_paper_observation_gate_report.md`
- `data/research/ndx/operator_promotion_decision.json`
- `data/reports/ndx_operator_promotion_report.md`

Expected downstream behavior after valid promotion:

- `build-paper-candidate-pack` may select NDX/QQQ candidates for paper observation only when the Layer 2.7 artifact is valid and matches the current Layer 2.5 export.
- `build-paper-intent-preview` may emit paper-only NDX/QQQ `PaperIntentPreview` rows only when candidate selection and the Layer 2.7 artifact are valid.
- `paper-from-intents` must still revalidate the preview against latest local quotes and paper broker state before writing paper orders/fills.
- `PaperIntentPreview` must keep `requires_revalidation=true`, `paper_only=true`, `live_conversion_allowed=false`, `wallet_used=false`, and `exchange_write_used=false`.

## Boundary

Layer 2.6 approval is not alpha proof and not a robust out-of-sample backtest claim. It only allows an operator promotion review for paper observation.

Layer 2.7 promotion is not live readiness. It only allows paper observation preview generation for the approved Layer 2.5 export and Layer 2.6 decision.
