<!--
作成日: 2026-06-10_12:02 JST
更新日: 2026-06-10_12:02 JST
-->

# Goal and scope

## Goal

Implement NDX Layer 2.5 as a research-only export from approved Layer 2.4 residual validation artifacts into the existing Strategy Lab signal artifact contract.

The implementation must let a developer run a single command after an approved Layer 2.4 result and receive a Strategy Lab-compatible signal artifact with complete lineage.

## In scope

- New pure module under `src/sis/research/ndx/` for Layer 2.5 export logic.
- New Typer command in the existing research command registration surface.
- New JSON schema for the Layer 2.5 export manifest.
- Focused pytest coverage for approval, rejection, lineage, schema validation, signal-frame validation, and paper/live non-permission.
- Minimal docs update to the active NDX research status docs after code is implemented.

## Out of scope

- New package root such as `src/strat_tool/`.
- New dependency such as VectorBT.
- New notebook-first workflow.
- New venue, order, wallet, account, credential, or exchange write path.
- Backtest execution.
- Paper candidate or PaperIntentPreview creation.
- Live trading, paper trading, or operator promotion.
- Claims that Layer 2.4 approval proves alpha.

## Required input state

Layer 2.5 may run only when all of these are true:

- `residual_validation_decision.json` exists.
- The decision has `decision: "APPROVE_STRATEGY_LAB_EXPORT"`.
- The decision has `permits_strategy_lab_research_only_export: true`.
- The decision has `permits_backtest: false`, `permits_paper_candidate: false`, `permits_paper_intent_preview: false`, and `permits_live_order: false`.
- `residual_validation_summary.json`, `ndx_feature_panel.parquet`, `ndx_feature_manifest.json`, `open_gap_residuals.parquet`, `open_gap_residual_manifest.json`, and `reports/neutralized_residuals.parquet` exist and match their recorded hashes where hashes exist.

## Stop conditions

Stop implementation and return to planning if any of these are needed:

- Adding a new execution venue enum.
- Changing `strategy_signal.v1` required fields.
- Allowing NDX/QQQ to pass paper candidate suitability.
- Introducing paper/live writes.
- Fetching market data during export.
- Using non-fixture external services in tests.
- Making side or sizing rules depend on undocumented discretionary assumptions.
