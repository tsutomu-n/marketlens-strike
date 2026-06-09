<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 14_IMPLEMENTER_CHECKLIST

## 実装前

- [ ] `uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx` が通る
- [ ] `uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx` が通る
- [ ] `layer_2_2_exit_decision.json` が `APPROVE_2_3`
- [ ] freeze manifestがある
- [ ] second_review_required=false
- [ ] unresolved_human_decisions=[]
- [ ] v2/v5旧ZIPを新規実装指示として読まない

## 実装

- [ ] T0 Start Condition Guard
- [ ] T1 Data Source Resolution
- [ ] T2 Fixture Data Contract
- [ ] T3 Feature Panel Builder
- [ ] T4 Leakage Checks
- [ ] T5 Rolling OLS Residual Builder
- [ ] T6 Diagnostics / Neutralization Pre-report
- [ ] T7 Counter-DAG Refutation Skeleton
- [ ] T8 CLI Wrappers

## Safety

- [ ] external APIを呼んでいない
- [ ] credentialsを読んでいない
- [ ] pyproject.tomlを変えていない
- [ ] uv.lockを変えていない
- [ ] Strategy Lab exportをしていない
- [ ] strategy_signals.parquetを生成していない
- [ ] PaperIntentPreviewを生成していない
- [ ] paper/live/order pathに触っていない
- [ ] Trade[XYZ] executionに触っていない

## Verification

- [ ] `uv run pytest -q tests/research`
- [ ] `uv run python scripts/check_current_docs.py`
- [ ] `./scripts/check`

## PR説明に書くこと

```text
Purpose:
  Add Layer 2.3 NDX Data Source Resolution, Feature Panel, and Open Gap Residual research artifacts.

Changed:
  src/sis/research/ndx/
  configs/research_layer_2_3/ndx/
  schemas/ndx_*.schema.json
  tests/research/test_ndx_*.py
  docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md

Not included:
  external API, credentials, Strategy Lab export, backtest, paper/live, NQ/VXN/SOX direct, options/gamma.

Verification:
  commands run and outputs generated.
```
