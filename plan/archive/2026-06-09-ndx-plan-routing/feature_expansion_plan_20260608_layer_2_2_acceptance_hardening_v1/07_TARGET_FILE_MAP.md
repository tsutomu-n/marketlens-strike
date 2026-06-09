<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 07_TARGET_FILE_MAP

## 主に確認・必要なら編集するファイル

```text
src/sis/research/dag/exit_gate.py
tests/research/test_layer22_exit_gate.py
tests/fixtures/research_layer_2_2/reviews/
docs/research/ndx/09_LLM_REVIEW_GATE.md
docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md
```

## 原則編集しないファイル

```text
src/sis/research/dag/review_pack.py
src/sis/research/dag/review_import.py
src/sis/research/dag/review_contracts.py
src/sis/research/dag/validator.py
src/sis/research/dag/linter.py
configs/research_layer_2_2/ndx/*.yaml
schemas/*.schema.json
```

ただし、T1/T2のテスト結果から明確な不足が見つかる場合のみ最小編集する。

## No-touch

```text
src/sis/backtest/
src/sis/paper/
src/sis/execution/
src/sis/venues/trade_xyz/
src/sis/bot/
src/sis/real_market/providers/
src/sis/research/strategy_lab/
src/sis/research_protocol/
pyproject.toml
uv.lock
.github/workflows/ci.yml
.env
.env.example
configs/env.example
```

## Runtime outputs

```text
data/research/ndx/
data/research/ndx/review/
data/reports/
```

`data/`はgit-ignored runtime artifactである。通常commitしない。
