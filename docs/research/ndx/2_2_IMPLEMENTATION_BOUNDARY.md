<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-08_18:01 JST
-->

# Layer 2.2 Implementation Boundary

今回の完成扱いは、HYP-NDX-001 を YAML から validation、lint、counter DAG、data requirements、Mermaid、Markdown report、manual review pack/import、exit gate decision まで local-only で再現できる状態である。

今回やらない:
- external API
- Strategy Lab export
- backtest
- feature panel
- residual builder
- strategy signals
- paper/live order
- Trade[XYZ] readiness
- Bitget credentialed network smoke

追加CLI:
- `uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx`
- `uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx`
- `uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review`
- `uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json`
- `uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review`

`research-layer22-validate` は core DAG 単体ではなく、同じ directory の `variable_inventory.yaml`、`causal_roles.yaml`、`temporal_availability.yaml`、`counter_dags.yaml` も必須 companion config として検証する。

`research-layer22-review-*` は手動 review JSON の local harness であり、外部 LLM API は呼ばない。
