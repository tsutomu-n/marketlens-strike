<!--
作成日: 2026-06-10_12:02 JST
更新日: 2026-06-10_15:06 JST
-->

# Implementation tasks

## Task 1: RED tests for Layer 2.5 approval and fail-closed behavior

Files:

- `tests/research/test_ndx_layer25_strategy_lab_export.py`

Add fixture helpers adapted from `tests/research/test_ndx_layer24_residual_validation.py`.

Required failing tests:

- approved Layer 2.4 artifacts write Strategy Lab signal artifact, Strategy Lab manifest, Layer 2.5 export manifest, and report.
- the command default reads `reports-dir=data/reports` and writes canonical artifacts under `data_dir/research/`.
- non-approved Layer 2.4 decision exits non-zero and writes no Strategy Lab signal artifact.
- missing required input exits non-zero and writes no Strategy Lab signal artifact.
- hash mismatch exits non-zero and writes no Strategy Lab signal artifact.
- emitted signal frame passes `validate_strategy_signal_frame`.
- emitted rows use `feature_ts` as `ts_signal` and preserve NDX lineage in `feature_snapshot_ref`.
- repeated export on identical source artifacts produces the same `export_id`.

## Task 2: RED tests for downstream safety boundary

Files:

- `tests/research/test_ndx_layer25_strategy_lab_export.py`
- existing Strategy Lab command helpers if needed.

Required failing tests:

- after Layer 2.5 export, `evaluate-strategy-lab` can read the canonical artifact.
- selected signal `block_reasons` propagate into `TradeCandidate.block_reasons`.
- after `evaluate-strategy-lab`, `build-paper-candidate-pack` blocks NDX/QQQ candidate with venue suitability and/or research-only block reason.
- after a manual `promotion-decision --decision promote`, `build-paper-intent-preview` writes an empty intent list for NDX/QQQ.

## Task 3: implement pure export module

Files:

- `src/sis/research/ndx/strategy_lab_export.py`

Responsibilities:

- load and validate Layer 2.4 decision and summary;
- validate required input paths and hashes;
- read `ndx_feature_panel.parquet`, `open_gap_residuals.parquet`, and `neutralized_residuals.parquet`;
- join by `date`;
- build `StrategySignalRecord` rows;
- cast to `STRATEGY_SIGNAL_SCHEMA`;
- validate with `validate_strategy_signal_frame`;
- write canonical Strategy Lab artifact and manifest with existing `write_strategy_signal_manifest`;
- write Layer 2.5 export manifest and report.
- compute `export_id` from a timestamp-excluded stable payload and record `hash_excludes`.

Do not put this logic in the command wrapper.

## Task 4: propagate selected signal block reasons into candidate pack

Files:

- `src/sis/commands/research.py`
- `tests/research/test_ndx_layer25_strategy_lab_export.py`

Responsibilities:

- for selected signal rows, merge `signal.get("block_reasons")` into candidate block reasons before selected/rejected ids are decided;
- preserve existing venue suitability block behavior;
- preserve existing behavior for blocked/no-signal trial records.

## Task 5: add schema

Files:

- `schemas/ndx_strategy_lab_research_export_manifest.v1.schema.json`
- relevant schema inventory test if one exists for NDX schemas.

The schema must encode research-only booleans as constants where possible.

## Task 6: add CLI command

Files:

- `src/sis/commands/research.py`

Add command:

- `research-ndx-strategy-lab-export`

The command should call the pure module and use Typer exit code 2 for fail-closed validation errors.

## Task 7: docs after code passes

Files:

- `docs/research/ndx/README.md`
- `docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md`
- new or existing Layer 2.5 doc under `docs/research/ndx/`

Docs must say:

- Layer 2.5 writes Strategy Lab research signals only after Layer 2.4 approval.
- Layer 2.5 does not permit backtest, paper candidate, PaperIntentPreview, live order, external API, credentials, wallet, or venue write.
- Layer 2.5 does not prove alpha.

Update hidden metadata timestamps on edited Markdown files.

## Task 8: final verification

Run targeted tests first, then full check:

```bash
uv run pytest tests/research/test_ndx_layer25_strategy_lab_export.py
uv run python scripts/check_current_docs.py
./scripts/check
```
