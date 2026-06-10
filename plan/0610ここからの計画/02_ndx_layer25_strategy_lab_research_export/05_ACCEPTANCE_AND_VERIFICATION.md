<!--
作成日: 2026-06-10_12:02 JST
更新日: 2026-06-10_15:55 JST
-->

# Acceptance and verification

## Acceptance

The implementation is complete only when all of these are true:

- `uv run sis research-ndx-strategy-lab-export --help` shows the new command and options.
- The command defaults to `data_dir/research` for canonical Strategy Lab artifacts and `data/reports` for residual diagnostics.
- Approved synthetic Layer 2.4 artifacts produce canonical Strategy Lab signal artifact and manifest.
- Existing Strategy Lab signal artifacts cause fail-closed behavior unless `--replace-existing` is passed.
- `--replace-existing` overwrites only after recording previous Strategy Lab artifact hashes in the export manifest.
- Rejected or non-approved Layer 2.4 artifacts produce no Strategy Lab signal artifact.
- Missing or hash-mismatched inputs produce no Strategy Lab signal artifact.
- Layer 2.5 export manifest validates against `schemas/ndx_strategy_lab_research_export_manifest.v1.schema.json`.
- Exported signal frame validates through existing Strategy Lab signal validation.
- Signal rows include `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED` in `block_reasons`.
- `export_id` is stable across repeated exports from identical source artifacts.
- `evaluate-strategy-lab` can consume the exported artifact.
- Selected signal `block_reasons` are present in `TradeCandidate.block_reasons`.
- `build-paper-candidate-pack` does not select NDX/QQQ candidates for paper.
- `build-paper-intent-preview` remains empty for NDX/QQQ even after a manual promote decision.
- No external API, credential, wallet, venue write, paper order, or live order path is added.
- `./scripts/check` passes.

## Required verification commands

```bash
uv run sis research-ndx-strategy-lab-export --help
uv run sis research-ndx-strategy-lab-export --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
uv run pytest tests/research/test_ndx_layer25_strategy_lab_export.py
uv run python scripts/check_current_docs.py
./scripts/check
```

## Diff checks

Before final report, inspect:

```bash
git diff -- src/sis/research/ndx src/sis/commands/research.py schemas tests/research docs/research/ndx
git diff -- pyproject.toml uv.lock
```

Expected dependency diff:

- no `pyproject.toml` dependency addition
- no `uv.lock` dependency churn

## Residual risk after completion

Even after acceptance passes:

- Layer 2.5 remains research-only.
- No paper/live readiness is established.
- The residual model may still be economically useless.
- Backtest readiness remains a separate future gate.
- Operator promotion remains blocked for NDX/QQQ under current venue suitability behavior.
