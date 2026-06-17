<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# Implementation tasks

## Task 1: RED tests for Layer 2.6 paper-observation gate

Files:

- `tests/research/test_ndx_layer26_paper_observation_gate.py`

Required failing tests:

- approved Layer 2.5 artifacts produce `APPROVE_PAPER_OBSERVATION_REVIEW`.
- missing Layer 2.5 export manifest exits non-zero and writes no acceptance decision.
- mismatched Strategy Lab signal hash exits non-zero and writes no acceptance decision.
- insufficient era count or signal count produces non-approve decision.
- missing local quote for `trade_xyz` / `XYZ100` produces non-approve decision and does not permit promotion review.
- fixture-only evidence records `evidence_tier=fixture_only` and never claims robust out-of-sample performance.
- decision manifest validates against `schemas/ndx_paper_observation_gate_decision.v1.schema.json`.
- decision records no external API, credentials, wallet, venue write, or live order permission.

## Task 2: implement Layer 2.6 pure module

Files:

- `src/sis/research/ndx/paper_observation_gate.py`

Responsibilities:

- load and validate Layer 2.5 export manifest.
- verify current Strategy Lab signal artifact hashes.
- compute deterministic paper-observation acceptance metrics from local artifacts.
- verify local quote availability for the intended paper observation venue/symbol.
- record split method, era metrics, signal count, variant count, thresholds, and decision.
- record evidence tier, sample scope, quote hash, and dry-run readiness.
- write decision JSON and report.

Do not put core validation logic in the command wrapper.

## Task 3: add Layer 2.6 schema and CLI

Files:

- `schemas/ndx_paper_observation_gate_decision.v1.schema.json`
- `src/sis/commands/research.py`
- schema inventory tests if present.

Add command:

- `research-ndx-paper-observation-gate`

Use exit code 2 for fail-closed validation errors.

## Task 4: RED tests for Layer 2.7 operator promotion

Files:

- `tests/research/test_ndx_layer27_operator_promotion.py`

Required failing tests:

- valid Layer 2.6 approval plus reviewer and approval reason produces `promote_to_paper_observation`.
- hold/reject decisions require rejection reasons.
- promote requires reviewer, approval reason, and matching Layer 2.6 approval.
- stale Layer 2.6 / Layer 2.5 hashes fail closed.
- promotion is rejected when Layer 2.6 did not record `paper_observation_dry_run_ready=true`.
- promotion manifest validates against `schemas/ndx_operator_promotion_decision.v1.schema.json`.
- promotion does not permit live order, wallet, or exchange write.

## Task 5: implement Layer 2.7 pure module

Files:

- `src/sis/research/ndx/operator_promotion.py`

Responsibilities:

- load and validate Layer 2.6 decision.
- verify source Layer 2.5 export and current signal hashes.
- validate reviewer and decision-specific reasons.
- write operator promotion decision JSON and report.
- keep live permissions false.

## Task 6: add evidence-aware NDX paper override

Files:

- `src/sis/venues/suitability.py`
- `src/sis/research/strategy_lab/paper_candidate_pack.py`
- `src/sis/research/strategy_lab/paper_intent_preview.py`
- `src/sis/commands/research.py`

Responsibilities:

- keep default NDX/QQQ paper candidate and paper intent blocks unchanged.
- add a narrow paper-stage override that requires valid Layer 2.7 promotion evidence.
- never apply this override to live stage.
- reject stale or mismatched promotion evidence.
- preserve `PaperIntentPreview` paper-only fields.

## Task 7: downstream paper observation tests

Files:

- `tests/research/test_ndx_layer27_operator_promotion.py`
- `tests/test_venue_suitability.py`
- `tests/test_strategy_lab_candidate_pack.py`
- `tests/test_strategy_lab_paper_intent_preview.py`
- `tests/test_paper_from_intents.py`

Required failing tests:

- without Layer 2.7 evidence, current NDX/QQQ fail-closed behavior remains unchanged.
- with valid Layer 2.7 evidence, `build-paper-candidate-pack` can select the NDX/QQQ candidate.
- with valid Layer 2.7 evidence and existing `PromotionDecision --decision promote`, `build-paper-intent-preview` emits paper-only NDX/QQQ intents.
- `paper-from-intents` can revalidate those intents against a local `trade_xyz` / `XYZ100` quote and either write paper artifacts or record explicit paper-only block reasons.
- generated `PaperIntentPreview` keeps `live_conversion_allowed=false`, `wallet_used=false`, and `exchange_write_used=false`.
- direct raw JSON bypass without valid promotion evidence is rejected.
- raw JSON with valid promotion evidence is still subject to quote availability, expiry, halt policy, and paper broker revalidation.
- live suitability remains blocked for NDX/QQQ.

## Task 8: docs after code passes

Files:

- `docs/research/ndx/README.md`
- `docs/research/ndx/13_LAYER_2_6_BACKTEST_ACCEPTANCE.md`
- `docs/research/ndx/14_LAYER_2_7_OPERATOR_PROMOTION.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/strategy_research_lab/04_PAPER_PROMOTION_AND_INTENT_SPEC.md`

Docs must say:

- Layer 2.6 does not prove alpha.
- Layer 2.7 allows paper observation only.
- Layer 2.7 does not permit live order, wallet, signing, exchange write, or public live CLI.
- PaperIntentPreview remains paper-only and revalidated.

Update hidden metadata timestamps on edited Markdown files.

## Task 9: final verification

Run targeted tests first, then full check:

```bash
uv run sis research-ndx-paper-observation-gate --help
uv run sis research-ndx-operator-promotion --help
uv run sis research-ndx-paper-observation-gate --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports --quotes-path data/normalized/quotes.parquet
uv run pytest tests/research/test_ndx_layer26_paper_observation_gate.py tests/research/test_ndx_layer27_operator_promotion.py -q
uv run python scripts/check_current_docs.py
./scripts/check
```
