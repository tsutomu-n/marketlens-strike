<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# Goal and scope

## Goal

Implement the next NDX research gate after Layer 2.5 so approved residual-derived Strategy Lab signals can progress to limited local paper observation, while preserving a hard boundary against live trading.

The implementation must let a developer run a deterministic local chain:

```bash
uv run sis research-ndx-paper-observation-gate --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports --quotes-path data/normalized/quotes.parquet
uv run sis research-ndx-operator-promotion --data-dir data --artifact-dir data/research/ndx --decision promote_to_paper_observation --reviewer local_operator --approval-reason "paper_observation_gate_reviewed"
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision promote
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

After this chain, NDX/QQQ paper intent preview and paper observation ledger may be non-empty only for paper observation. No live order path is created.

## In scope

- New pure module under `src/sis/research/ndx/` for Layer 2.6 paper-observation acceptance.
- New pure module under `src/sis/research/ndx/` for Layer 2.7 operator promotion.
- New CLI commands in the existing research command registration surface:
  - `research-ndx-paper-observation-gate`
  - `research-ndx-operator-promotion`
- New JSON schemas:
  - `schemas/ndx_paper_observation_gate_decision.v1.schema.json`
  - `schemas/ndx_operator_promotion_decision.v1.schema.json`
- Narrow evidence-aware override for NDX/QQQ paper-candidate and paper-intent suitability.
- Focused pytest coverage for approval, rejection, stale artifact, hash mismatch, quote availability, paper broker revalidation, downstream candidate unlock, paper intent preview unlock, and live non-permission.
- Minimal active docs updates after code is implemented.

## Out of scope

- Live trading.
- Wallet, signing, exchange write, or public live CLI.
- Production Bitget, Hyperliquid, MT5, IC Markets, CFD, options, or gamma inputs.
- Widening `VenueId` beyond the currently supported ids.
- Claiming alpha, profitability proof, paper-ready proof, or live-ready proof.
- Replacing existing Strategy Lab paper models wholesale.
- Allowing raw JSON bypass into paper execution without model validation.

## Required input state

Layer 2.6 may run only when all of these are true:

- Layer 2.5 export manifest exists.
- Layer 2.5 manifest has `research_only: true`.
- Layer 2.5 manifest has `permits_backtest: false`, `permits_paper_candidate: false`, `permits_paper_intent_preview: false`, and `permits_live_order: false`.
- `data/research/strategy_signals.parquet` and `data/research/strategy_signal_manifest.json` exist and match the Layer 2.5 manifest hashes.
- Layer 2.4 decision and summary exist and match the Layer 2.5 source lineage.
- The backtest input panel is local, deterministic, and does not fetch external market data during the command.
- `data/normalized/quotes.parquet` exists or an explicit `--quotes-path` is provided.
- The quotes contain a current local paper quote for `trade_xyz` / `XYZ100`; otherwise Layer 2.6 may write a non-approve decision but must not permit promotion.
- The decision records whether evidence is `fixture_only`, `historical_local`, or `paper_observation_dry_run`. The default fixture path must not be described as robust out-of-sample proof.

Layer 2.7 may run only when all of these are true:

- Layer 2.6 decision exists and is `APPROVE_PAPER_OBSERVATION_REVIEW`.
- Layer 2.6 decision source hashes match the current Layer 2.5 export.
- A reviewer and approval reason are provided.
- The requested decision is paper-observation only.

## Stop conditions

Stop implementation and return to planning if any of these are needed:

- Live order, wallet, signing, or exchange write code.
- A public live or micro-live Strategy Lab command.
- New production venue id or schema enum widening.
- External API access during tests or default command runs.
- Claim fields such as `paper_ready_claimed=true`, `tiny_live_ready_claimed=true`, or `live_ready_claimed=true`.
- Removing `requires_revalidation=true`, `paper_only=true`, or `live_conversion_allowed=false` from `PaperIntentPreview`.
- Making NDX/QQQ paper path pass without a matching Layer 2.6 and Layer 2.7 artifact.
- Making paper observation pass without local quote revalidation.
- Treating the current 84-signal fixture as statistical proof of alpha or robust backtest performance.
