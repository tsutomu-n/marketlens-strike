<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-07_19:37 JST
-->

# Causal Roles

Causal Role Assignment は変数を treatment candidate、outcome、confounder、moderator などに分類する層である。

HYP-NDX-001 の中心ロール:
- `open_gap_residual`: treatment_candidate
- `qqq_open_to_close_return`: outcome
- `spy_gap`, `smh_gap`, `dgs10_delta`, `mega_cap_basket_gap`: confounder
- `vix_level`, `vix_change`: moderator

正本 config は `configs/research_layer_2_2/ndx/causal_roles.yaml`。
