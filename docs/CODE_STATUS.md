# Code Status

この文書は current codebase を PR-00 から PR-08 の migration 軸で読むための要約です。実装の正本はコードと tests です。

## Summary

| PR | Title | Status | Evidence |
|---|---|---|---|
| PR-00 | Python 3.13 migration | DONE | `pyproject.toml`, `.python-version`, `uv.lock`, `.github/workflows/ci.yml`, `scripts/check` |
| PR-01 | Archive legacy venues | DONE | `archive/legacy_sidecars/`, `src/sis/venues/archive/`, `src/sis/execution/archive/`, `pyproject.toml` no longer depends on `ostium-python-sdk` |
| PR-02 | Generalize models and schemas | DONE | `src/sis/models.py`, `schemas/`, `configs/*.yaml`, `configs/instrument_registry.seed.json` |
| PR-03 | Build Trade[XYZ] universe mapping | DONE | `src/sis/venues/trade_xyz/registry.py`, `report.py`, `tests/test_trade_xyz_registry.py` |
| PR-04 | Add Trade[XYZ] read-only collector | DONE | `src/sis/venues/trade_xyz/collector.py`, `normalizer.py`, `tests/test_trade_xyz_collector.py` |
| PR-05 | Add real market data layer | DONE | `src/sis/real_market/*`, `tests/test_real_market_models.py`, `tests/test_real_market_quality.py`, `tests/test_real_market_features.py` |
| PR-06 | Add real vs venue tracking | DONE | `src/sis/tracking/*`, `tests/test_tracking_models.py`, `tests/test_real_vs_venue_tracking.py`, `tests/test_lead_lag.py` |
| PR-07 | Gate paper execution by venue quality | DONE | `src/sis/paper/*`, `src/sis/core/execution_plan.py`, `tests/test_paper_trading.py`, `tests/test_paper_runner.py` |
| PR-08 | Add Trade[XYZ] micro live safety canary | DONE | `src/sis/execution/trade_xyz_adapter.py`, `live_order_policy.py`, `micro_live_canary.py`, dedicated PR-08 tests |

## Current Operational Interpretation

- migration 実装は完了している。
- ただし operator-facing runtime artifact chain は一部 legacy collector surface をまだ利用する。
- そのため「code complete」と「operationally cut over」は分けて扱う。

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
- `trade_xyz` を主軸にした operations chain への全面移行

## Verification

2026-05-26 current verification:

- `uv run python -V`: pass
- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass
- `uv run pytest -q`: 297 passed
- `./scripts/check`: pass

## Reading Pointers

- migration contract: `plan/PR-00_to_PR-08_implementation_plan.md`
- runtime status: `docs/CURRENT_STATE.md`
- operator procedure: `docs/OPERATIONS_RUNBOOK.md`
- architecture and boundaries: `docs/ARCHITECTURE_AND_PHASES.md`
