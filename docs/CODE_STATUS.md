# Code Status

この文書は current codebase を PR-00 から PR-08 の migration 軸で読むための要約です。実装の正本はコードと tests です。

## Summary

| PR | Title | Status | Evidence |
|---|---|---|---|
| PR-00 | Python 3.13 migration | DONE | pyproject.toml, .python-version, uv.lock, .github/workflows/ci.yml, scripts/check |
| PR-01 | Archive legacy venues | DONE | archive/gtrade_ostium_legacy_archive_*.zip, package.json legacy note, pyproject.toml without ostium-python-sdk |
| PR-02 | Generalize models and schemas | DONE | src/sis/models.py, schemas/, configs/*.yaml, configs/instrument_registry.seed.json |
| PR-03 | Build Trade[XYZ] universe mapping | DONE | src/sis/venues/trade_xyz/registry.py, src/sis/venues/trade_xyz/report.py, tests/test_trade_xyz_registry.py, `perpDexs` fallback |
| PR-04 | Add Trade[XYZ] read-only collector | DONE | src/sis/venues/trade_xyz/collector.py, src/sis/venues/trade_xyz/normalizer.py, tests/test_trade_xyz_collector.py, quote collection summary/report |
| PR-05 | Add real market data layer | DONE | src/sis/real_market/*, tests/test_real_market_models.py, tests/test_real_market_quality.py, tests/test_real_market_features.py |
| PR-06 | Add real vs venue tracking | DONE | src/sis/tracking/*, tests/test_tracking_models.py, tests/test_real_vs_venue_tracking.py, tests/test_lead_lag.py |
| PR-07 | Gate paper execution by venue quality | DONE | src/sis/paper/*, src/sis/core/execution_plan.py, tests/test_paper_trading.py, tests/test_paper_runner.py |
| PR-08 | Add Trade[XYZ] micro live safety canary | DONE | src/sis/execution/trade_xyz_adapter.py, src/sis/execution/live_order_policy.py, src/sis/execution/micro_live_canary.py, PR-08 tests |

## Post-PR08 / PR9a-PR12 Status

| Slice | Status | Evidence |
|---|---|---|
| PR9a CLI import recovery | DONE | `uv run sis --help`, `uv run python -m sis.cli --help` |
| PR9b HIP-3 mapping and contexts | DONE | `perpDexs` asset-id fallback, `metaAndAssetCtxs` enrichment, `tests/test_trade_xyz_registry.py` |
| PR9c fresh quote window | DONE | `collect-trade-xyz-quotes --duration-minutes --interval-seconds --write-summary --write-report`, `data/ops/trade_xyz_quote_collection_summary.json` |
| PR10 strict validation and diagnostics | DONE | `validate-artifacts --strict`, `diagnose-quotes --venue trade_xyz`, `tests/test_validate_artifacts_trade_xyz.py` |
| PR11 operations cutover | DONE | `phase-gate-review` consumes Trade[XYZ] artifacts and emits `READ_ONLY_GO` / `CONDITIONAL_INDEX_ONLY` / `NO_GO` |
| PR12 fresh read-only smoke | DONE | `data/ops/pr12_fresh_read_only_smoke_summary.json`, `data/reports/pr12_fresh_read_only_smoke_report.md` |

## Current Operational Interpretation

- migration 実装は完了している。
- `src/sis/cli.py` は root Typer app registration と `main()` に近い構成へ分割済み。
- Trade[XYZ] read-only artifacts は strict validation / diagnostics / phase gate に接続済み。
- production live trading は未接続なので、"read-only gate complete" と "live trading ready" は分けて扱う。
- `probe trade-xyz` は live `perpDexs` から `asset_id` を解決できる。解決不能時は従来どおり `api_orderable=false` で fail-closed。

## Verified Acceptance Highlights

PR-07:

- best bid / ask 優先の fill price selection
- tracking / source confidence / venue quality / spread / depth / funding gate
- `configs/fee_model.trade_xyz.yaml` を使う round-trip cost model
- paper report に `source_confidence`, `venue_quality_score`, `block_reasons`, `fee_mode`, `estimated_round_trip_cost_bps`, `fill_price_source`

PR-08:

- disabled micro live, confirm flag, scheduleCancel, market order, notional, leverage, session, event blackout, source confidence, venue quality, open-position gate
- `scheduleCancel -> place limit order -> orderStatus by cloid -> cancelByCloid or reduce-only close`
- `micro_live_safety_report` と audit bundle の生成
- standard verification は mock / fake exchange / dry-run policy tests のみ

## Known Gaps By Design

- manual signing, wallet secrets, exchange write credentials
- public CLI からの micro live 実行 surface
- production live trading
- bot decision / live order preview の正式 artifact surface

## Verification

2026-05-27 current verification:

- `uv run python -V`: pass
- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass
- `uv run pytest -q`: 275 passed
- `./scripts/check`: pass
- targeted PR9a-PR12 tests: 19 passed
- latest strict validation: `checked_files=11`, `issues=0`
- latest phase gate: `READ_ONLY_GO`, `next_actions=[]`

## Reading Pointers

- historical migration contract: `plan/archive/PR-00_to_PR-08_implementation_plan.md`
- runtime status: `docs/CURRENT_STATE.md`
- operator procedure: `docs/OPERATIONS_RUNBOOK.md`
- architecture and boundaries: `docs/ARCHITECTURE_AND_PHASES.md`
