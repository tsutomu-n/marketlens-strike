<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# Acceptance and verification

## Acceptance

The implementation is complete only when all of these are true:

- `uv run sis research-ndx-paper-observation-gate --help` shows the new command and options.
- `uv run sis research-ndx-operator-promotion --help` shows the new command and options.
- Approved Layer 2.5 artifacts can produce `APPROVE_PAPER_OBSERVATION_REVIEW`.
- Non-approved, missing, or hash-mismatched Layer 2.5 artifacts fail closed.
- Missing or stale local quote evidence produces non-approve or blocked paper-observation readiness.
- Layer 2.6 records `sample_scope`, `evidence_tier`, `quotes_hash`, and `paper_observation_dry_run_ready`.
- Layer 2.6 decision validates against `schemas/ndx_paper_observation_gate_decision.v1.schema.json`.
- Layer 2.6 decision records no external API, credential, wallet, venue write, paper intent, or live order permission.
- Valid Layer 2.6 approval plus explicit reviewer approval can produce `promote_to_paper_observation`.
- Hold/reject Layer 2.7 decisions do not unlock candidate or paper intent generation.
- Layer 2.7 decision validates against `schemas/ndx_operator_promotion_decision.v1.schema.json`.
- Layer 2.7 decision records `permits_live_order=false`, `live_conversion_allowed=false`, `wallet_used=false`, and `venue_write_used=false`.
- Without valid Layer 2.7 evidence, NDX/QQQ paper candidate and paper intent paths remain fail-closed.
- With valid Layer 2.7 evidence, NDX/QQQ candidate selection may succeed for paper observation.
- With valid Layer 2.7 evidence and standard `PromotionDecision --decision promote`, `build-paper-intent-preview` may emit NDX/QQQ paper-only intents.
- `paper-from-intents` revalidates those intents against local quotes and paper broker state before writing paper artifacts.
- Raw JSON bypass without valid promotion evidence is rejected by validation.
- Live suitability remains blocked.
- No dependency additions or lockfile churn occur.
- `./scripts/check` passes.

## Required verification commands

```bash
uv run sis research-ndx-paper-observation-gate --help
uv run sis research-ndx-operator-promotion --help
uv run sis research-ndx-paper-observation-gate --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports --quotes-path data/normalized/quotes.parquet
uv run sis research-ndx-operator-promotion --data-dir data --artifact-dir data/research/ndx --decision promote_to_paper_observation --reviewer local_operator --approval-reason "paper_observation_gate_reviewed"
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision promote
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
uv run pytest tests/research/test_ndx_layer26_paper_observation_gate.py tests/research/test_ndx_layer27_operator_promotion.py -q
uv run python scripts/check_current_docs.py
./scripts/check
```

## Diff checks

Before final report, inspect:

```bash
git diff -- src/sis/research/ndx src/sis/commands/research.py src/sis/venues/suitability.py src/sis/research/strategy_lab schemas tests docs/research/ndx docs/strategy_research_lab docs/CURRENT_STATE.md docs/CODE_STATUS.md
git diff -- pyproject.toml uv.lock
```

Expected dependency diff:

- no `pyproject.toml` dependency addition
- no `uv.lock` dependency churn

## Residual risk after completion

Even after acceptance passes:

- Layer 2.6 is not alpha proof.
- Layer 2.6 is not robust out-of-sample proof when evidence is fixture-only.
- Layer 2.7 is not live readiness.
- Paper observation can still lose money.
- The NDX/QQQ venue proxy remains a paper observation surface, not a production live venue.
- Live trading requires a separate plan for credentials, wallet/signing, exchange writes, live risk, and operator controls.
