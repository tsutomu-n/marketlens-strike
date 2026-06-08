<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# C_CODER_HANDOFF_PROMPT

あなたは `marketlens-strike` の実装者です。

このPRでは、Layer 2.2を新規実装しません。現在のRepoには、Layer 2.2 DAG foundation と Exit Gate Review Harness がすでに実装されています。

## 目的

既存実装を受入監査し、`exit_gate.py` の意味論を明確化してください。

特に以下を保証してください。

```text
APPROVE_2_3 の時:
  second_review_required=false
  unresolved_human_decisions=[]
  blocker_count=0
  freeze_manifestあり

REVISE_2_2 / REJECT_SEED の時:
  freeze_manifestなし
```

## 旧ZIPの扱い

過去に作成したv2/v5 ZIPは、新規実装指示ではありません。設計背景・監査チェックリストとしてだけ読んでください。

## 主に触るファイル

```text
src/sis/research/dag/exit_gate.py
tests/research/test_layer22_exit_gate.py
tests/fixtures/research_layer_2_2/reviews/
docs/research/ndx/09_LLM_REVIEW_GATE.md
```

## 触らないファイル

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
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## やらないこと

```text
feature panel
Open Gap Residual計算
residual model
neutralization
Strategy Lab export
backtest
paper/live/order
external API
credentials
dependency追加
```
