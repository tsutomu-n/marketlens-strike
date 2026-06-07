<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-07_19:37 JST
-->

# Layer 2.2 Implementation Boundary

今回の完成扱いは、HYP-NDX-001 を YAML から validation、lint、counter DAG、data requirements、Mermaid、Markdown report まで再現できる状態である。

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
- `uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml`
- `uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx`
