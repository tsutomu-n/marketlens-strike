<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# Artifact contract

## Layer 2.6 command

```bash
uv run sis research-ndx-paper-observation-gate \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --quotes-path data/normalized/quotes.parquet
```

Options:

- `--data-dir`: project runtime data root. Default from settings, normally `data`.
- `--artifact-dir`: NDX Layer 2.4 / 2.5 artifact directory. Default `data/research/ndx`.
- `--reports-dir`: report directory. Default `data/reports`.
- `--quotes-path`: local quote parquet used to prove paper observation can be revalidated. Default `data/normalized/quotes.parquet`.
- `--min-era-count`: minimum era count for promotion review. Default must be documented and must not silently approve a one-era fixture.
- `--min-signal-count`: minimum signal count for promotion review. Default must be documented and must not be presented as statistical proof.
- `--max-tested-variant-count`: maximum accepted variant count. Default `1`.
- `--fixture-evidence-policy`: `warn` or `reject`. Default `warn` is allowed only for local paper observation; production or live gates must reject fixture-only evidence.

Outputs:

- `artifact-dir/paper_observation_gate_decision.json`
- `reports-dir/ndx_paper_observation_gate_report.md`

Decision values:

- `APPROVE_PAPER_OBSERVATION_REVIEW`
- `REVISE_2_5`
- `REJECT_PAPER_OBSERVATION_GATE`

Required manifest fields:

- `schema_version: "ndx_paper_observation_gate_decision.v1"`
- `decision`
- `decision_id`
- `created_at`
- `source_layer25_export_id`
- `source_layer25_export_manifest_path`
- `source_layer25_export_manifest_hash`
- `strategy_signals_path`
- `strategy_signals_hash`
- `strategy_signal_manifest_path`
- `strategy_signal_manifest_hash`
- `signal_count`
- `era_count`
- `sample_scope`
- `evidence_tier`
- `quotes_path`
- `quotes_hash`
- `paper_quote_available`
- `paper_quote_latest_ts`
- `paper_observation_dry_run_ready`
- `split_method`
- `tested_variant_count`
- `acceptance_thresholds`
- `metrics`
- `reason_codes`
- `block_reasons`
- `permits_operator_promotion_review`
- `permits_paper_observation_review`
- `permits_paper_candidate: false`
- `permits_paper_intent_preview: false`
- `permits_live_order: false`
- `external_api_used: false`
- `credentials_used: false`
- `wallet_used: false`
- `venue_write_used: false`

## Layer 2.7 command

```bash
uv run sis research-ndx-operator-promotion \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --decision promote_to_paper_observation \
  --reviewer local_operator \
  --approval-reason "paper_observation_gate_reviewed"
```

Options:

- `--data-dir`: project runtime data root. Default from settings, normally `data`.
- `--artifact-dir`: NDX Layer 2.6 artifact directory. Default `data/research/ndx`.
- `--decision`: `promote_to_paper_observation`, `hold`, or `reject`.
- `--reviewer`: non-empty reviewer id for promote.
- `--approval-reason`: repeatable or comma-separated approval reason for promote.
- `--rejection-reason`: repeatable or comma-separated rejection reason for hold/reject.

Outputs:

- `artifact-dir/operator_promotion_decision.json`
- `data-dir/reports/ndx_operator_promotion_report.md`

Required manifest fields:

- `schema_version: "ndx_operator_promotion_decision.v1"`
- `promotion_id`
- `created_at`
- `decision`
- `reviewer`
- `approval_reasons`
- `rejection_reasons`
- `source_paper_observation_gate_decision_id`
- `source_paper_observation_gate_path`
- `source_paper_observation_gate_hash`
- `source_layer25_export_id`
- `source_layer25_export_manifest_path`
- `source_layer25_export_manifest_hash`
- `strategy_signals_hash`
- `required_evidence`
- `observed_evidence`
- `permits_paper_candidate`
- `permits_paper_intent_preview`
- `permits_paper_observation`
- `permits_live_order: false`
- `live_conversion_allowed: false`
- `external_api_used: false`
- `credentials_used: false`
- `wallet_used: false`
- `venue_write_used: false`

## Downstream evidence contract

Candidate and paper-intent generation may treat NDX/QQQ `trade_xyz` as suitable for paper observation only when all of these are true:

- `operator_promotion_decision.json` exists.
- `decision` is `promote_to_paper_observation`.
- `permits_paper_candidate=true`.
- `permits_paper_intent_preview=true`.
- `permits_live_order=false`.
- The recorded Layer 2.5 export id and signal hashes match the current artifacts.
- The recorded Layer 2.6 decision is `APPROVE_PAPER_OBSERVATION_REVIEW`.
- The recorded Layer 2.6 decision has `paper_observation_dry_run_ready=true`.
- The local quote evidence recorded by Layer 2.6 still matches or is fresher than the evidence used by the downstream paper run.

This evidence must not affect live suitability.
