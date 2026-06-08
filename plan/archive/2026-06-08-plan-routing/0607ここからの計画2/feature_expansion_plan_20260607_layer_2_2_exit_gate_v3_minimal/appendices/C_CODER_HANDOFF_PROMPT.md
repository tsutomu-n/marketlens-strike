<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# C_CODER_HANDOFF_PROMPT

あなたは `marketlens-strike` の実装者です。

このPRでは、Layer 2.2 DAG Compilerの次段として **Layer 2.2 Exit Gate Review Harness v3 Minimal** を実装してください。

## 実装するもの

```text
- LLM review result schema
- review pack generator
- manual LLM review result importer
- exit gate decision
- freeze manifest
- Markdown reports
- minimal CLI
- fixture-based tests
```

## 実装しないもの

```text
- external LLM API integration
- provider SDK
- API key / credentials
- feature panel
- open gap residual calculation
- neutralization
- Strategy Lab export
- backtest
- paper candidate
- PaperIntentPreview
- live order
- Trade[XYZ] integration
```

## 触るファイル

Create:

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

docs/research/ndx/09_LLM_REVIEW_GATE.md
```

Edit:

```text
src/sis/research/dag/__init__.py
src/sis/commands/research.py
```

No-touch:

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
```

## 必ず通す

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 停止条件

以下が必要になったら実装を止めて確認してください。

```text
- external API
- credentials
- dependency追加
- pyproject.toml / uv.lock変更
- Strategy Lab model変更
- paper/live/order path変更
- feature panel生成
- residual calculation
```
