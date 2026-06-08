<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Appendix C: Coder Handoff Prompt

以下をコーダーに渡す。

```text
目的:
  marketlens-strike に Layer 2.2 Research DAG Compiler foundation を追加する。
  対象は HYP-NDX-001 Open Gap Residual。

完成扱い:
  Seed / mechanism parts / data source contract / variable inventory / causal roles / temporal availability / core DAG / counter-DAG をYAMLで定義し、validate / lint / export / report生成できること。

やらないこと:
  feature panel、residual calculation、neutralization、strategy_signals.parquet export、evaluate-strategy-lab、backtest、paper/live order、external API、credentials、dependency追加。

実装順:
  1. Phase A: hypothesis 前段contract
  2. Phase B: core DAG compiler
  3. CLIはPhase B最後に validate/export の2コマンドだけ

主要追加path:
  configs/research_layer_2_2/ndx/
  schemas/research_*.schema.json
  schemas/core_dag.v1.schema.json
  src/sis/research/hypothesis/
  src/sis/research/dag/
  tests/research/
  docs/research/ndx/

触らないpath:
  src/sis/backtest/
  src/sis/paper/
  src/sis/execution/
  src/sis/venues/trade_xyz/
  src/sis/bot/
  pyproject.toml
  uv.lock

検証:
  uv run pytest -q tests/research
  uv run python scripts/check_current_docs.py
  ./scripts/check

停止条件:
  external API、credentials、dependency、paper/live/order、Strategy Lab model変更、DB/deploy/CI変更が必要になったら止めて確認する。
```
