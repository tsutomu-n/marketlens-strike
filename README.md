<!--
作成日: 2026-05-22_09:50 JST
更新日: 2026-07-05_13:26 JST
-->

# marketlens-strike

`marketlens-strike` is a Python 3.13 CLI workspace for backtest-first strategy research, local evidence packs, Strategy Research Lab workflows, paper-operation artifacts, NDX local research gates, and safety/readiness boundaries.

The code is the source of truth. Current docs are entry points only; generated files under `data/` may be absent in a fresh checkout until commands are run.

## Read First

1. [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
2. [docs/CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](docs/CURRENT_GOAL_AND_DIRECTION_2026-07-05.md)
3. [docs/CURRENT_DOCS_INDEX_2026-07-05.md](docs/CURRENT_DOCS_INDEX_2026-07-05.md)
4. [docs/IMPLEMENTED_SURFACES.md](docs/IMPLEMENTED_SURFACES.md)
5. [docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md)
6. [docs/strategy_idea_candidates/README.md](docs/strategy_idea_candidates/README.md)
7. [docs/backtest/README.md](docs/backtest/README.md)
8. [docs/strategy_review/README.md](docs/strategy_review/README.md)
9. [docs/research/ndx/README.md](docs/research/ndx/README.md)
10. [docs/runbooks/README.md](docs/runbooks/README.md)

Historical docs are not current proof. If history is needed, start from [docs/archive/README.md](docs/archive/README.md) or [plan/README.md](plan/README.md) after checking code and CLI help.

## Current Direction

The practical next direction is evidence quality, not live execution.

- Keep the default axis backtest-first and venue-neutral.
- Use C9 bridge only as a fail-closed artifact connection from shortlisted candidates to candidate-scoped Strategy Authoring / backtest pack outputs.
- Use Bitget public source refresh and ticker-aware source availability as local source inputs, not actual cash evidence.
- Use `crypto-perp-backtest-candidate-pack` as the no-actual-cash short-term Crypto Perp endpoint.
- Treat `NO_TRADE` as a valid action.
- Treat missing source, small samples, blocked family mapping, and unsupported product mapping as valid stop results.

No-cash goal progress is tracked in [docs/NO_CASH_GOAL_PROGRESS_2026-07-05.md](docs/NO_CASH_GOAL_PROGRESS_2026-07-05.md). Current practical reading: implementation/routing is around 70%, evidence quality is around 50%, and overall no-cash progress is 60-65%.

This repo does not currently prove profit, actual cash readiness, tiny-live readiness, live readiness, wallet readiness, signing readiness, or exchange-write readiness.

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

## Main Commands

Aggregate local gate:

```bash
./scripts/check
```

Current docs and CLI catalog:

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
```

Crypto Perp no-actual-cash backtest candidate pack:

```bash
uv run sis crypto-perp-backtest-candidate-pack
```

Strategy backtest HTML report:

```bash
uv run sis strategy-backtest-html-report
```

Strategy Idea Candidate C9 bridge helpers:

```bash
uv run sis strategy-idea-candidates-bitget-source-refresh --help
uv run sis strategy-idea-candidates-authoring-bridge --help
```

Strategy Review:

```bash
uv run sis strategy-review-build --help
uv run sis strategy-review-record --help
```

NDX Layer 2.2 local DAG foundation and review gate:

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import \
  --pack data/research/ndx/review/llm_review_input.json \
  --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate \
  --root configs/research_layer_2_2/ndx \
  --pack data/research/ndx/review/llm_review_input.json \
  --review data/research/ndx/review/normalized_review.json \
  --out data/research/ndx/review
```

Operations and status artifacts:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

## Human-Facing Guides

Trade[XYZ] guides are current only as read-only / historical venue context. They are not the default product axis, current next action, or live readiness path.

- [docs/trade_xyz_bot_beginner_guide.md](docs/trade_xyz_bot_beginner_guide.md) - Trade[XYZ] read-only / historical venue companion
- [docs/trade_xyz_bot_beginner_guide.html](docs/trade_xyz_bot_beginner_guide.html) - same guide as browser-friendly HTML
- [docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md](docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md)
- [docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html](docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html)
- [docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.md](docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.md)
- [docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html](docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html)

## Current Boundaries

- `VenueId` currently allows `trade_xyz` and `bitget_demo`.
- `bitget_futures` and `hyperliquid_perp` are catalog-only / disabled for current Strategy Lab schemas.
- Trade[XYZ] is implemented code and historical/read-only venue context, but it is not the default product axis or current order-entry bottleneck.
- `bitget_demo` is a demo execution surface. It is not production Bitget readiness.
- `READ_ONLY_GO`, `PASS`, `READY_FOR_HUMAN_REVIEW`, and `BACKTEST_CANDIDATE_HOLD` are not paper/live permission.
- `strategy-review-build` and `strategy-review-record` create human-review artifacts only.
- NDX Layer 2.2-2.8 gates are local research / paper-observation gates. They do not prove alpha or live readiness.
- `crypto-perp-backtest-candidate-pack` creates local simulation artifacts only. It does not create actual cash evidence.
- `docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md` is a historical implementation record, not a current hash or pass-count source.
- wallet secrets, signing, exchange writes, and production live trading remain out of scope.
- `data/` is git-ignored runtime state.

## Source Of Truth

Priority:

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`
2. CLI help: `uv run sis --help`
3. generated runtime artifacts under `data/`
4. tracked current docs under `docs/`
5. `plan/` historical planning records
6. `docs/archive/` and `plan/archive/`

## Verification

Do not copy fixed pass counts into this file. Rerun the commands for the current checkout.

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```
