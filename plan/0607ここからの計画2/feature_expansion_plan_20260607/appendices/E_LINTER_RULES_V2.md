<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Appendix E: Linter Rules v2

## Error rules

### no_unknown_node_edge

edge.source / edge.target が nodes に存在しなければ error。

### no_self_loop

source == target は error。

### no_duplicate_edge

同じ source / target の重複は error。

### no_outcome_to_treatment

outcome role の node から treatment_candidate / observed_proxy / modeled_latent へのedgeは error。

### no_future_to_signal

`t_after_close` から `t_open_plus_buffer` 以前へのedgeは error。

### no_post_treatment_to_pre_treatment

post-treatment / outcome / after-close variable を signal側へ戻すedgeは error。

### no_forbidden_edge_in_edges

forbidden_edges にある edge が edges に存在すれば error。

### role_consistency_rule

core_dag.yaml の role と causal_roles.yaml の role が矛盾すれば error。

### unknown_variable_rule

DAG node の variable_ref が variable_inventory に存在しなければ error。

### temporal_layer_required_rule

observed node / treatment_candidate / outcome は temporal_layer 必須。欠損は error。

### no_model_output_to_input_rule

modeled_latent の入力に outcome variable が含まれている場合は error。

### counter_dag_minimum_rule

HYP-NDX-001 は counter-DAG 8本未満なら error。

## Warning rules

### optional_provider_as_required_proxy

source_tier が optional_provider_dependent / deferred の proxy が required node に使われている場合は warning。

### proxy_missing_rule

confounder / moderator / observed_proxy に proxy がない場合は warning。ただし modeled_latent は除外。

### too_many_nodes_rule

初期Core DAGのnode数が15を超えたら warning。

### too_many_edges_rule

初期Core DAGのedge数が20を超えたら warning。

### index_methodology_missing_rule

NDX scopeなのに index methodology mechanism part が無ければ warning。

### qqq_nq_mixed_proxy_rule

QQQとNQが同一nodeの同一proxyとして扱われている場合は warning または error。

## Rule output

```json
{
  "severity": "error",
  "rule_id": "no_outcome_to_treatment",
  "message": "open_to_close_return must not point to open_gap_residual",
  "edge": ["open_to_close_return", "open_gap_residual"]
}
```
