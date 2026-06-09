<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 15_CODER_HANDOFF_PROMPT

あなたは `marketlens-strike` の実装者です。

## 目的

現Repoでは Layer 2.2 DAG foundation と Exit Gate Review Harness は既に存在します。今回の作業は、2.2を再実装することではありません。

今回のPRでは、`HYP-NDX-001` を 2.3 へ進めるため、以下を実装してください。

```text
Layer 2.3 NDX Data Source Resolution
Layer 2.3 NDX Feature Panel Skeleton
Layer 2.3 Open Gap Residual Builder
Layer 2.3 Diagnostics / Counter-DAG Refutation Skeleton
```

## まず確認

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
```

`data/research/ndx/review/layer_2_2_exit_decision.json` が存在し、以下を満たさなければ2.3実装へ進まないでください。

```text
decision=APPROVE_2_3
second_review_required=false
unresolved_human_decisions=[]
freeze_manifest exists
```

## 実装するもの

```text
- source resolution artifact
- fixture-first data loader
- NDX feature panel builder
- leakage checks
- rolling OLS residual builder
- residual artifact manifest
- diagnostics / neutralization pre-report
- counter-DAG refutation skeleton
- minimal CLI wrappers
- tests
```

## 実装しないもの

```text
- external API
- credentials
- provider SDK
- dependency追加
- Strategy Lab export
- strategy_signals.parquet
- evaluate-strategy-lab
- backtest
- paper candidate
- PaperIntentPreview
- live order
- Trade[XYZ] integration
- NQ futures本格対応
- VXN直接取得
- SOX直接取得
- options / gamma / 0DTE
```

## 触ってよいファイル

```text
src/sis/research/ndx/
configs/research_layer_2_3/ndx/
schemas/ndx_*.schema.json
tests/research/test_ndx_*.py
tests/fixtures/ndx/
docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md
src/sis/commands/research.py
```

## 原則触らないファイル

```text
src/sis/research/strategy_lab/
src/sis/research_protocol/
src/sis/backtest/
src/sis/paper/
src/sis/execution/
src/sis/venues/trade_xyz/
src/sis/bot/
src/sis/real_market/providers/
pyproject.toml
uv.lock
.github/workflows/ci.yml
```

## 必ず通す

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 完了条件

```text
- data_source_resolution.json 生成
- ndx_feature_panel.parquet 生成
- ndx_feature_manifest.json 生成
- open_gap_residuals.parquet 生成
- open_gap_residual_manifest.json 生成
- ndx_neutralization_report.md 生成
- ndx_counter_dag_refutation_report.md 生成
- 外部APIなし
- Strategy Lab exportなし
- paper/liveなし
```
