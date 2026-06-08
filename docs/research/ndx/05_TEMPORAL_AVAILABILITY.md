<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-08_18:01 JST
-->

# Temporal Availability

Temporal Availability は未来情報と post-treatment leakage を止める層である。

Temporal layers:
- `t_prev_close`
- `t_pre_open`
- `t_open_observed`
- `t_open_plus_buffer`
- `t_after_close`
- `provider_dependent`

`t_after_close` から `t_open_plus_buffer` または `t_open_observed` への edge は future-to-signal leakage として拒否する。

正本 config は `configs/research_layer_2_2/ndx/temporal_availability.yaml`。
