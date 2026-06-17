<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Target File Map

## Design-Gate Files To Add

- `src/sis/venues/capabilities.py`
- `tests/test_venue_capabilities.py`
- `docs/venues/bitget_hyperliquid_capability_gate.md`

## Existing Files To Review Before Any Code Change

- `src/sis/venues/ids.py`
- `src/sis/venues/suitability.py`
- `src/sis/execution/base.py`
- `src/sis/execution/bitget_demo_adapter.py`
- `src/sis/commands/execution.py`
- `src/sis/commands/execution_artifacts.py`
- `src/sis/research/strategy_lab/specs.py`
- `src/sis/research/strategy_lab/evaluation_plan.py`
- `src/sis/research/strategy_lab/candidates.py`
- `src/sis/research/strategy_lab/paper_intent_preview.py`
- `src/sis/paper/runner.py`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/evaluation_plan.mls.v1.schema.json`

## Files Not To Modify In The First Slice

- `src/sis/venues/ids.py`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/evaluation_plan.mls.v1.schema.json`
- `pyproject.toml`
- `uv.lock`

## Future Schema-Widening Slice

Only a later slice may modify:

- `src/sis/venues/ids.py`
- Strategy Lab Pydantic venue fields
- Strategy Lab JSON schemas
- `schemas/evaluation_plan.mls.v1.schema.json`
- tests that assert current enum values
