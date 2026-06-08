<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 06_TARGET_FILE_MAP

## Create

```text
schemas/llm_dag_review.v1.schema.json
schemas/layer_2_2_human_resolutions.v1.schema.json
schemas/layer_2_2_exit_decision.v1.schema.json
schemas/layer_2_2_freeze_manifest.v1.schema.json

src/sis/research/dag/review_contracts.py
src/sis/research/dag/review_pack.py
src/sis/research/dag/review_import.py
src/sis/research/dag/exit_gate.py
src/sis/research/dag/freeze_manifest.py

tests/research/test_llm_review_schema.py
tests/research/test_llm_review_pack.py
tests/research/test_llm_review_import.py
tests/research/test_layer22_exit_gate.py
tests/research/test_research_layer22_review_commands.py

tests/fixtures/research_layer_2_2/reviews/valid_approve.json
tests/fixtures/research_layer_2_2/reviews/valid_warn_requires_resolution.json
tests/fixtures/research_layer_2_2/reviews/invalid_pack_hash_mismatch.json
tests/fixtures/research_layer_2_2/reviews/invalid_unknown_evidence_ref.json
tests/fixtures/research_layer_2_2/reviews/blocker_temporal_leakage.json
tests/fixtures/research_layer_2_2/reviews/reject_seed.json

docs/research/ndx/09_LLM_REVIEW_GATE.md
```

## Edit

```text
src/sis/research/dag/__init__.py
src/sis/commands/research.py
```

必要な場合のみ。

```text
src/sis/cli.py
scripts/check_current_docs.py
```

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
data/research/ndx/review/
data/reports/
```

注意: `data/` はruntime artifactで、通常git管理しない想定。

## Module size rule

新規Pythonファイルは小さく保つ。

```text
目安:
  800 lines 以下
```

既存Repo運用では新規または大幅編集Pythonファイルを小さく保つ方針があるため、review pack生成、import、exit gateを1ファイルに詰め込まない。
