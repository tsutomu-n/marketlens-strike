<!--
作成日: 2026-06-10_12:02 JST
更新日: 2026-06-10_15:06 JST
-->

# Coder handoff prompt

Implement NDX Layer 2.5 Strategy Lab research-only export in `/home/tn/projects/marketlens-strike`.

Read first:

1. `./.ai_memory/HANDOFF.md`
2. `AGENTS.md`
3. `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/README.md`
4. `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/01_GOAL_AND_SCOPE.md`
5. `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/02_CODE_TRUTH_AND_RISK_AUDIT.md`
6. `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/03_ARTIFACT_CONTRACT.md`
7. `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/04_IMPLEMENTATION_TASKS.md`
8. `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/05_ACCEPTANCE_AND_VERIFICATION.md`
9. `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/07_RESEARCH_NOTES.md`

Implement with Red -> Green.

Start by adding failing tests in `tests/research/test_ndx_layer25_strategy_lab_export.py`.

Then add:

- `src/sis/research/ndx/strategy_lab_export.py`
- `schemas/ndx_strategy_lab_research_export_manifest.v1.schema.json`
- `research-ndx-strategy-lab-export` command in `src/sis/commands/research.py`
- selected signal `block_reasons` propagation in `build-paper-candidate-pack`
- minimal active docs updates after tests pass

Do not:

- create a new package root;
- add VectorBT or any new dependency;
- fetch external data;
- add a venue, wallet, account, paper, live, or exchange write path;
- claim alpha, backtest readiness, paper readiness, or live readiness;
- change `strategy_signal.v1` unless a failing test proves it is unavoidable.
- use `data/research/ndx/reports` as the Layer 2.4 reports default; current Layer 2.4 reports live under `data/reports`.
- rely on venue suitability alone to preserve research-only signal block reasons.

Required final verification:

```bash
uv run sis research-ndx-strategy-lab-export --help
uv run sis research-ndx-strategy-lab-export --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
uv run pytest tests/research/test_ndx_layer25_strategy_lab_export.py
uv run python scripts/check_current_docs.py
./scripts/check
```
