<!--
作成日: 2026-05-22_09:50 JST
更新日: 2026-06-27_10:59 JST
-->

# marketlens-strike

`marketlens-strike` is a Python 3.13 CLI workspace for backtest-first strategy
research, NDX Layer 2.2/2.3/2.4 local research gates, Strategy Research Lab
workflows, paper operations, venue-neutral execution contracts, and safety
gates.

The code is the source of truth. Current docs summarize the implemented surfaces
and the latest verified snapshots; generated files under `data/` may be absent
in a fresh checkout until commands are run.

## Read First

1. [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
2. [docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md](docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md)
3. [docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md](docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md)
4. [docs/AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](docs/AI_AGENT_STRATEGY_BACKTEST_GUIDE.md)
5. [docs/STRATEGY_AND_BACKTEST_USER_GUIDE.md](docs/STRATEGY_AND_BACKTEST_USER_GUIDE.md)
6. [docs/FEATURE_CAPABILITY_SUMMARY_2026-06-27.md](docs/FEATURE_CAPABILITY_SUMMARY_2026-06-27.md)
7. [docs/STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md](docs/STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md)
8. [docs/STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](docs/STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md)
9. [docs/STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md](docs/STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md)
10. [docs/STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md](docs/STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md)
11. [docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md)
12. [docs/CODE_STATUS.md](docs/CODE_STATUS.md)
13. [docs/IMPLEMENTED_SURFACES.md](docs/IMPLEMENTED_SURFACES.md)
14. [docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md](docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md)
15. [docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md](docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md)
16. [docs/NEXT_DIRECTION_CURRENT.md](docs/NEXT_DIRECTION_CURRENT.md)
17. [docs/research/ndx/README.md](docs/research/ndx/README.md)
18. [docs/research/ndx/09_LLM_REVIEW_GATE.md](docs/research/ndx/09_LLM_REVIEW_GATE.md)
19. [docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md](docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md)
20. [docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md](docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md)
21. [docs/backtest/README.md](docs/backtest/README.md)
22. [docs/strategy_review/README.md](docs/strategy_review/README.md)
23. [docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md](docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md)
24. [docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md](docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md)
25. [docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md](docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md)
26. [docs/venues/bitget_hyperliquid_capability_gate.md](docs/venues/bitget_hyperliquid_capability_gate.md)
27. [docs/venues/read_only_capability_probe.md](docs/venues/read_only_capability_probe.md)
28. [docs/strategy_research_lab/README.md](docs/strategy_research_lab/README.md)
29. [docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md](docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md)
30. [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md)
31. [docs/runbooks/README.md](docs/runbooks/README.md)
32. [docs/ARCHITECTURE_AND_PHASES.md](docs/ARCHITECTURE_AND_PHASES.md)
33. [docs/trade_xyz_bot_beginner_guide.md](docs/trade_xyz_bot_beginner_guide.md)

## Judgment Notes

These are not source-of-truth docs. Use them only to avoid optimistic
misreadings after checking code, tests, schemas, CLI help, and current artifacts.

- [docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md](docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md) - 正本ではない個人トレーダー目線の評価
- [docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md](docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md) - 正本ではない利益目線の判断メモ

The visual companion for the Trade[XYZ] beginner guide is
[docs/trade_xyz_bot_beginner_guide.html](docs/trade_xyz_bot_beginner_guide.html).

If Trade[XYZ] public user address, Bitget demo credentials, or new normal
paper-observation evidence arrives, use the `External Input Restart Checklist`
in [docs/NEXT_DIRECTION_CURRENT.md](docs/NEXT_DIRECTION_CURRENT.md). Those
checks are read-only / observation checks, not paper or live execution
permission.

## Historical References

These documents are useful for implementation history and audit provenance.
They are not the first source for current readiness or permission decisions.

1. [docs/MIGRATION_HISTORY.md](docs/MIGRATION_HISTORY.md)
2. [docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md](docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md)
3. [docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md](docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md)
4. [docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md](docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md)
5. [docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md](docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md)
6. [plan/archive/PR-00_to_PR-08_implementation_plan.md](plan/archive/PR-00_to_PR-08_implementation_plan.md)

## Setup

```bash
uv python install 3.13
uv sync --dev --locked
uv run python -V
uv run sis --help
```

Only update the lockfile when dependencies change:

```bash
uv lock --python /usr/bin/python3.13
```

Run the aggregate local gate:

```bash
./scripts/check
```

`./scripts/check` runs locked sync, Python version check, Ruff lint and format
check, current-docs lint, Pyrefly, ty, and Pytest.

## Main Flows

Operations and status artifacts:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

Venue capability boundary probe:

```bash
uv run sis venue-read-only-probe
```

Trade[XYZ] read-only refresh:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run sis bot-preview
```

Useful quote collection variants:

```bash
uv run sis collect-trade-xyz-quotes --symbols SP500,NVDA --duration-minutes 5 --interval-seconds 60
uv run sis collect-trade-xyz-quotes --no-normalize --write-summary --write-report
uv run sis collect-trade-xyz-quotes --dry-run --max-symbols 3
```

Paper operations:

```bash
uv run sis paper-operations-cycle
```

Strategy Research Lab to paper-only preview:

```bash
uv run sis strategy-preview
uv run sis strategy-experiment-run --spec path/to/strategy_experiment.yaml
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

Strategy authoring YAML to paper-only preview:

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-author-train-model --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --target-column research_return_1d --feature-column research_return_4h --feature-column vix_level
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
```

Strategy review packet for human review:

```bash
uv run sis strategy-review-build \
  --review-id local-review-001 \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --lifecycle-review data/research/strategy_lifecycle/strategy_lifecycle_review.json
```

This creates `review.md` and `review_manifest.json` for human review only. It
does not prove alpha, paper readiness, live readiness, or paper execution
permission. See [docs/strategy_review/README.md](docs/strategy_review/README.md).

Record and revalidate a human Strategy Review decision:

```bash
uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/local-review-001 \
  --decision REVIEWED_FOR_CONTEXT \
  --reviewer operator-name \
  --rationale "review.md and review_manifest.json were reviewed as context"

uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/local-review-001 \
  --validate-existing
```

This writes `operator_review.yaml` as `operator_strategy_review.v1`. It records
path/hash lineage for the current `review.md` and `review_manifest.json`; it
does not authorize paper execution or live trading.

NDX Layer 2.2 local DAG foundation and review gate:

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
```

This Layer 2.2 gate is local/manual review plumbing only. It does not fetch
market data, calculate residuals, export Strategy Lab artifacts, backtest, or
connect paper/live order paths.

NDX Layer 2.3 fixture-first preflight and residual artifacts:

```bash
uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-ndx-feature-panel --root configs/research_layer_2_2/ndx --input-root tests/fixtures/ndx --out data/research/ndx
uv run sis research-ndx-residual --feature-panel data/research/ndx/ndx_feature_panel.parquet --out data/research/ndx
uv run sis research-ndx-diagnostics --residuals data/research/ndx/open_gap_residuals.parquet --out data/reports
```

NDX Layer 2.4 residual validation gate:

```bash
uv run sis research-ndx-residual-validate --root configs/research_layer_2_2/ndx --artifact-dir data/research/ndx --reports-dir data/reports --out data/research/ndx
```

Layer 2.3/2.4 are also local research gates. Layer 2.4 may approve only the
Layer 2.5 research-only export bridge. That approval does not prove alpha,
backtest readiness, paper readiness, or live readiness.

NDX Layer 2.5 research-only export through Layer 2.8 paper observation review:

```bash
uv run sis research-ndx-strategy-lab-export --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
uv run sis research-ndx-paper-observation-gate --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports --quotes-path data/normalized/quotes.parquet
uv run sis research-ndx-operator-promotion --data-dir data --artifact-dir data/research/ndx --decision promote_to_paper_observation --reviewer local_operator --approval-reason paper_observation_gate_reviewed
uv run sis research-ndx-paper-observation-review --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
```

These commands remain local artifact gates. They do not call external APIs, use
credentials, write exchange state, or authorize live order paths.

Trade[XYZ] pure backtest v0.1:

```bash
uv run pytest -q tests/backtest
```

The pure backtest engine is currently a Python API surface under
`src/sis/backtest/engine/` and `src/sis/backtest/trade_xyz/`; it is not exposed
as a public CLI command. See [docs/backtest/README.md](docs/backtest/README.md).

Strategy Lab details live in [docs/strategy_research_lab/README.md](docs/strategy_research_lab/README.md).
The author-facing capability list is
[docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md](docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md),
with command-level detail at
[docs/strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md](docs/strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md),
with a plain-Japanese explanation source at
[docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.md](docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.md),
and a visual HTML companion at
[docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html](docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html).
Strategy idea preparation starts at
[docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md](docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md),
with a visual HTML companion at
[docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html](docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html).

## Current Boundaries

- Current development is backtest-first and venue-neutral. Trade[XYZ] is an implemented venue and future order-entry candidate, not the current order-entry bottleneck.
- `VenueId` currently allows `trade_xyz` and `bitget_demo`.
- `bitget_futures` and `hyperliquid_perp` are suitability/capability catalog entries only; they are not current `VenueId` values and are not accepted by Strategy Lab artifact schemas.
- `src/sis/venues/capabilities.py` records venue capability state. It makes `bitget_futures` and `hyperliquid_perp` known but schema-disabled, paper-disabled, network-disabled, and live-disabled.
- `venue-read-only-probe` writes fixture-first local artifacts for these venue boundaries. It does not use external APIs, credentials, wallet, signing, exchange writes, live orders, or network attempts.
- `bitget_demo` is accepted by execution-venue schemas, but `evaluation_plan.mls.v1` still fixes `target_venue` to `trade_xyz`; do not treat `bitget_demo` as a complete Strategy Lab evaluation target.
- `trade_xyz`, `bitget_demo`, `real_market`, `tracking`, `paper`, and `micro_live` code surfaces exist.
- `src/sis/cli.py` builds the root Typer app; command implementations live under `src/sis/commands/`.
- `collect-trade-xyz-quotes` is a public CLI command.
- `bitget-demo-smoke` is a local/mock-first smoke. `status=configured` means the three local Bitget demo env values are present; it does not prove network connectivity, account readiness, order submit readiness, or fill sync.
- `bitget_demo` is a crypto fixture/demo paper surface. It is not an NDX/QQQ execution venue.
- micro live is a code/test safety surface, not a public operator command.
- `bot-preview` writes read-only HOLD preview artifacts when run; it does not use wallet secrets, signing, or exchange writes.
- `check-go-no-go` and `build-evidence-card` are supplemental reports. Use `phase-gate-review` for the current Trade[XYZ] decision.
- `data/research/strategy_signals.parquet` is the canonical Strategy Lab signal artifact. `data/research/signals.csv` is a legacy export.
- NDX Layer 2.2 DAG and manual review gate code lives under `configs/research_layer_2_2/ndx/`, `src/sis/research/dag/`, `schemas/layer_2_2_*.schema.json`, and `schemas/llm_dag_review.v1.schema.json`.
- NDX Layer 2.3/2.4 local preflight, residual, diagnostics, and validation gate code lives under `src/sis/research/ndx/`, `src/sis/commands/research.py`, `configs/research_layer_2_3/ndx/`, `configs/research_layer_2_4/ndx/`, `schemas/ndx_*.schema.json`, and `tests/research/`.
- NDX/QQQ records may be retained for research and backtests, but they are blocked from `selected_candidate_ids`, `PaperIntentPreview`, and legacy `paper-step` order generation unless valid residual validation, venue suitability, and operator promotion evidence is present for that path.
- `PaperIntentPreview` is paper-only. Do not convert it to live orders.
- Trade[XYZ] pure backtest v0.1 is separate from `build-backtest` and Strategy
  Authoring fixed-horizon backtest.
- `strategy-review-build` reads existing backtest / validation / optional
  authoring / lifecycle artifacts and writes a human-review packet. It is not a
  paper or live permission gate.
- `strategy-review-record` writes and validates `operator_review.yaml` for the
  review packet. `live_allowed=false` and `paper_execution_allowed=false` are
  fixed.
- Strategy Lab runtime validation lives in Pydantic models; tracked JSON Schema files are thin guards for interoperability.
- wallet secrets, signing, exchange writes, and production live trading remain out of scope.
- `data/` is git-ignored runtime state.

## Current Verification

Run these commands for current verification instead of copying old pass counts from generated or historical docs:

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

2026-06-06 docs-only spot check:

- `uv run python scripts/check_current_docs.py`: pass, current-doc allowlist checked successfully

2026-06-15 historical local documentation snapshot:

- `research-layer22-review-pack`, `research-layer22-review-import`, `research-layer22-exit-gate`, `research-ndx-source-resolve`, `research-ndx-feature-panel`, `research-ndx-residual`, `research-ndx-diagnostics`, `research-ndx-residual-validate`, `research-ndx-strategy-lab-export`, `research-ndx-paper-observation-gate`, `research-ndx-operator-promotion`, and `research-ndx-paper-observation-review` are registered CLI commands.
- `uv run python scripts/check_current_docs.py`: current-docs check passed; rerun for the current checked-doc count.
- Layer 2.2 historical implementation record is frozen in [docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md](docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md). For the current local exit decision and pack hash, rerun the Layer 2.2 commands above and inspect `data/research/ndx/review/layer_2_2_exit_decision.json`.
- Non-approve exit-gate runs remove stale `layer_2_2_freeze_manifest.json` from the same output directory.
- Current Layer 2.4 default artifact decision is `APPROVE_STRATEGY_LAB_EXPORT`; this is only permission for Layer 2.5 research-only export and is not alpha, backtest, paper, or live readiness proof.
- `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md` records a historical code-truth docs cleanup checklist.

Runtime validation readback:

- Run `uv run sis validate-artifacts --strict` for strict artifact validation.
- Run `uv run sis phase-gate-review` for the read-only / paper gate decision.
- Run `uv run sis execution-drift-overview` and `uv run sis execution-snapshot --venue trade_xyz` for execution-readiness gaps.
- Run `uv run sis readiness-snapshot` and inspect `data/manifests/trade_xyz_data_readiness_manifest.json` only as runtime artifacts, not as tracked-doc proof.
- `docs/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` records the current code-truth documentation checklist and the 2026-06-22 doc/archive routing cleanup.
- `docs/archive/2026-06-22-doc-routing/DOCUMENT_AUDIT_2026-06-17_CODE_TRUTH_CHECKLIST.md` records the previous historical docs checklist.

`READ_ONLY_GO` means the read-only / paper gate is clear. It does not mean
production live trading is ready.

## Legacy Notes

gTrade / Ostium source, sidecars, raw data, registry files, and dedicated tests
were compressed into `archive/gtrade_ostium_legacy_archive_*.zip`. The active
repo tree keeps Trade[XYZ] as an implemented read-only / research venue. Current
strategy work should start from backtest-first and venue-neutral docs before
returning to Trade[XYZ] readiness work.
