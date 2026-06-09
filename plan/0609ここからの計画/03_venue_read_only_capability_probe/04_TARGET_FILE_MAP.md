<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Target File Map

## Add

- `src/sis/venues/read_only_probe.py`
  - pure local model/builders for venue read-only probe summaries
  - no network client
  - no env secret values in returned data
- `schemas/venue_read_only_probe_summary.v1.schema.json`
  - JSON Schema for the generated summary artifact
- `tests/test_venue_read_only_probe.py`
  - pure unit tests for builders and schema validation
- `tests/test_venue_read_only_probe_cli.py`
  - CLI tests for default fixture-first behavior
- `docs/venues/read_only_capability_probe.md`
  - current doc explaining what the probe does and does not prove

## Modify

- `src/sis/commands/execution.py`
  - add CLI command `venue-read-only-probe`
  - write:
    - `data/ops/venue_read_only_probe_summary.json`
    - `data/reports/venue_read_only_probe.md`
- `src/sis/cli.py`
  - only if command registration wiring requires a new injected writer; prefer
    keeping the writer in `src/sis/commands/execution.py` if small enough
- `src/sis/venues/capabilities.py`
  - only if helper functions are needed, for example
    `read_only_probe_candidate_venue_ids()`
- `tests/test_venue_capabilities.py`
  - add drift tests only if not covered by the new probe tests
- `tests/test_strategy_lab_schemas.py`
  - keep or extend guards proving future venues are not in Strategy Lab schemas
- `README.md`
  - add doc link and one boundary bullet
- `docs/CURRENT_STATE.md`
  - add current state summary
- `docs/CODE_STATUS.md`
  - add implemented surface row after implementation
- `scripts/check_current_docs.py`
  - only if `docs/venues` is not already included; current code already
    includes it

## Must Not Modify

- `src/sis/venues/ids.py`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/evaluation_plan.mls.v1.schema.json`
- `src/sis/research/strategy_lab/specs.py`
- `src/sis/research/strategy_lab/evaluation_plan.py`
- `src/sis/research/strategy_lab/candidates.py`
- `src/sis/research/strategy_lab/paper_intent_preview.py`
- `src/sis/paper/runner.py`
- `pyproject.toml`
- `uv.lock`

