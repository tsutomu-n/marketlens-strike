<!--
作成日: 2026-06-19_02:16 JST
更新日: 2026-06-22_22:22 JST
-->

# Strategy Workbench Viewer

## 結論

Strategy Workbench Viewer は、Strategy Operations Workbench の JSON / Markdown artifact を読むための static HTML viewer です。

これは正本ではありません。正本は各 artifact、schema、CLI、test です。viewer は artifact を探しやすくするだけで、paper 実行、live 実行、scale-up、wallet、signing、exchange write を許可しません。

Crypto Perp の `crypto_perp_tournament_report.v1`、`crypto_perp_tournament_gate.v1`、`crypto_perp_truth_cycle_status.v1` も通常の JSON artifact として読めます。viewer は `tournament_status`、`gate_status`、`cycle_status`、`human_summary`、`approval_boundary`、`leader_action`、`primary_metric`、`event_count`、`proxy_gap_count`、`failed_condition_count`、`stop_reason_count`、`first_stop_reason`、`missing_artifact_path_count`、`first_next_step`、`first_next_step_network_allowed=false`、`first_stage_blocker`、`first_stage_blocker_expected_cli_option`、`leader_actual_cash_result_usd` などのcompact summaryを表示対象にします。

`strategy_case_lite.v1` と `strategy_case_index.v1` は、root の `status` field がない場合でも `latest_status` を status badge として表示します。Case Lite は artifact count、timeline count、first source artifact type / path / schema / hash、first open action、first blocked reason を compact summary として表示できます。Case Index は、case count、strategy count、latest status、latest case path、first open action、first blocked reason、source hash を compact summary として表示できます。

`strategy_input_contract_update_review.v1` など、top-level `decision` を持つ artifact は、その `decision` を status badge として表示します。Input Feedback proposal / review では `proposal_id`、`decision`、`source_proposal_status`、`manual_contract_update_input_allowed`、`requires_human_contract_update`、`direct_contract_edit_allowed`、`auto_applied`、`paper_execution_allowed`、`live_allowed`、change / action count、first proposed change の target / source reason / evidence summary を compact summary として表示します。

`strategy_runtime_observation_manifest.v1` など、runtime observation の summary を持つ artifact では、ledger / paper order / fill / no-fill / blocked count、unique intent / symbol count、filled notional、最大 quote age、最大 spread、PnL 利用可否、PnL がない理由、first / last observed timestamp を compact summary として表示します。これは paper / live 実行許可ではなく、実行観測が stale quote や PnL 不足を含むかを人間が見落としにくくするための表示です。

`strategy_authoring_backtest_result.v1` では、`backtest_passed`、`trade_count`、`total_return`、`max_drawdown`、`net_pnl_usd`、`ending_equity_usd`、`max_drawdown_loss_usd`、`executed_count`、`blocked_count`、`paper_only`、`live_order_submitted` を compact summary として表示します。`strategy_backtest_pack_validation.v1` では、`decision`、`check_count`、`passed_count`、`failed_count`、`locked_dependency_added`、`external_framework_policy_decision`、`paper_only`、`live_order_submitted` を表示します。これらは backtest evidence を探しやすくするための表示であり、paper / live 実行許可や alpha 証明ではありません。

`strategy_backtest_pack.v1` では、pack artifact count、suite method / run / passed count、external result count、external framework policy、standard engine、locked dependency の有無、capital summary を表示します。`strategy_backtest_suite_result.v1` では、suite id、method count、run / pass / fail count、trade count、total return、cost drag、best run summary を表示します。`strategy_backtest_comparison.v1` では、comparison id、method / external / framework adapter count、native result、suite best run、weakest era、optional framework の skipped status を表示します。これらも読みやすさのための要約であり、外部 framework 採用、paper / live 実行、profit claim を許可しません。

`strategy_daily_brief.v1` では、scanned JSON count、total item count、broken artifact count、Crypto Perp gate / truth-cycle follow-up count、normal paper gap count、drift / learning request count、first brief item の category / severity / status / schema / action / reason / path を compact summary として表示します。これは「次に確認すべき follow-up」を見つけやすくするための表示であり、follow-up action の実行許可ではありません。

## CLI

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/strategy_cases/<strategy-id>/strategy_case_lite.json \
  --artifact data/reports/strategy_daily_brief/strategy_daily_brief.json \
  --out data/reports/strategy_workbench_viewer
```

`--artifact` を省略すると `--data-dir` 配下の `.json`、`.md`、`.txt` を scan します。

```bash
uv run sis strategy-workbench-viewer-build \
  --data-dir data \
  --out data/reports/strategy_workbench_viewer \
  --replace-existing
```

出力:

```text
data/reports/strategy_workbench_viewer/
  strategy_workbench_viewer.html
  strategy_workbench_viewer_manifest.json
```

## Manifest

`strategy_workbench_viewer_manifest.json` は `strategy_workbench_viewer.v1` です。

主な内容:

- source artifact path
- source artifact sha256
- schema_version
- status / decision / decision_status / plan_status / ingest_status / tournament_status / gate_status / cycle_status などの抜粋
- Crypto Perp tournament / gate / truth-cycle status の leader_action / primary_metric / event_count / proxy_gap_count / stop_reason_count / first_stop_reason / first_next_step / first_stage_blocker / human_summary などのcompact summary
- Strategy Input Feedback proposal / review の proposal_id / decision / source_proposal_status / manual_contract_update_input_allowed / direct_contract_edit_allowed / auto_applied / paper_execution_allowed / live_allowed / first_proposed_change_evidence_summary などのcompact summary
- Strategy Runtime Observation の ledger_entry_count / paper_order_count / paper_fill_count / no_fill_count / blocked_count / filled_notional_usd_total / max_observed_quote_age_ms / max_observed_spread_bps / pnl_available / pnl_unavailable_reason などのcompact summary
- Strategy Backtest result / pack validation の backtest_passed / trade_count / total_return / net_pnl_usd / failed_count / locked_dependency_added などのcompact summary
- Strategy Backtest pack / suite / comparison の pack_artifact_count / suite_method_count / method_count / best_run_method_id / weakest_era / optional framework skipped status などのcompact summary
- Strategy Daily Brief の scanned_json_count / total_item_count / crypto_perp_truth_cycle_follow_up_count / first_brief_item_action / first_brief_item_reason などのcompact summary
- Strategy Case Lite / Strategy Case Index の latest_status status badge と first open action / first blocked reason
- Strategy Case Lite の artifact_count / timeline_count / first_source_artifact_type / first_source_artifact_path / first_source_artifact_schema_version / first_source_artifact_hash などのcompact summary
- Strategy Case Index の case_count / strategy_count / latest_status / latest_case_path / first_open_action / first_blocked_reason / case_index_source_hash などのcompact summary
- boundary violation count
- HTML report path / hash
- fixed false permission flags

## 境界

- static HTML を生成するだけ。
- artifact を編集しない。
- paper / live execution permission ではない。
- `first_next_step_network_allowed`、`first_next_step_exchange_write_allowed`、`first_next_step_live_order_allowed` は false の時だけ summary に出す。true は許可ではなく malformed source artifact として扱う。
- `READY_FOR_HUMAN_TINY_LIVE_REVIEW` は warning badge と `approval_boundary` で表示する。これは承認待ちであり、live execution permission ではない。
- `first_stage_blocker` は先に読むべき欠損 stage の索引であり、次 stage や tiny live へ進む許可ではない。
- `strategy_case_index.v1` は read-only case index として表示するだけで、source case artifact、DB registry、paper/live permission を作らない。
- hidden mutable state を持たない。
- `data/` runtime artifact の内容を docs に固定しない。

## 検証

```bash
uv run pytest tests/strategy_workbench_viewer -q
uv run sis strategy-workbench-viewer-build --help
uv run python scripts/check_current_docs.py
```
