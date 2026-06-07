<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-07_19:37 JST
-->

# Variable Inventory

Variable Inventory は DAG node 候補の棚卸しである。各変数は source symbol、formula、proxy のいずれかを持つ必要がある。

初期変数:
- `qqq_open_gap`
- `qqq_open_to_close_return`
- `spy_gap`
- `smh_gap`
- `dgs10_delta`
- `vix_level`
- `vix_change`
- `mega_cap_basket_gap`
- `expected_ndx_move`
- `open_gap_residual`

正本 config は `configs/research_layer_2_2/ndx/variable_inventory.yaml`。
