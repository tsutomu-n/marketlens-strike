<!--
作成日: 2026-06-22_20:37 JST
更新日: 2026-06-22_21:39 JST
-->

# Local Dogfood Selection Catalog

## 結論

ユーザー回答の反映:

1. 必須 1 の lane は `Local dogfood`。
   - 言い換え: 外部 API、認証情報、注文、実資金を使わず、手元の実ファイルで今回の機能を試す。
2. 必須 2 の対象 strategy / case / venue は `unknown`。
   - 言い換え: どの戦略を選ぶかは、今ある artifact を見てから決める。
3. 必須 3 の根拠 artifact は、まず Codex 推奨で候補を出す。
   - 言い換え: こちらで現物を棚卸しし、選べる材料を並べる。
4. 必須 4 の permission boundary は未決。
   - この文書では未承認として扱う。したがって credential、network、paper order、live order、wallet、signing、exchange write は使わない。
5. 必須 5 の secret / account / statement handling は未決。
   - この文書では secret、account raw data、statement raw data を扱わない。

推奨は `trend_pullback_user_v1` を第一候補にすること。理由は、local/offline のまま `Strategy Case Lite`、`Strategy Case Index`、`Workbench Viewer` をすでに生成できており、backtest / review artifact も多いから。

`ndx_open_gap_residual_v1` は第二候補。`Strategy Input Feedback` の proposal / review まで通っているが、paper observation 寄りで、quote age stale や PnL 不足などの現実的な保留理由も含む。

2026-06-22_21:33 JST 時点の補足: Loop 08-14 で B は追加 dogfood 済み。Viewer、Input Feedback proposal、Case Lite、Case Index は `HOLD` / `NEEDS_SOURCE_CONTRACT_CONTEXT` / `pnl_available=false` / `max_observed_quote_age_ms=1048982067` を一覧で見落としにくい表示に更新した。B は「進める候補」ではなく、いったん completion audit 済みの dogfood slice として読む。

2026-06-22_21:39 JST 時点の補足: `strategy_id=unknown` から選ぶためのファイル単位の詳細棚卸しは [26_LOCAL_DOGFOOD_UNKNOWN_TARGET_FULL_INVENTORY.md](26_LOCAL_DOGFOOD_UNKNOWN_TARGET_FULL_INVENTORY.md) を正として読む。この文書は高レベル catalog として残す。

Crypto Perp truth-cycle は第三候補。Viewer / Daily Brief の読みやすさ確認には使えるが、今回の Strategy Input Feedback / Case Index plan の中心ではない。

追加調査で補正した点:

- active `data/` には対象拡張候補ではないが、見落としやすい `data/evidence`、`data/manifests`、`data/notifications`、`data/ops`、`data/registry`、`data/reports`、`data/state` がある。
- これらは Local dogfood の第一候補ではない。主に operations、venue readiness、Trade[XYZ]、human-readable report mirror、state cache の文脈であり、必須 4 / 5 が未決のまま選ぶと scope が崩れる。
- ただし「存在しない」のではないため、この文書では候補外として明示列挙する。

## この文書の目的

目的:

- `strategy_id=unknown` の状態から、いま選べる Local dogfood 候補を具体的に並べる。
- 「何があるか」「何が足りないか」「どれを選ぶと何ができるか」を分ける。
- 必須 4 と必須 5 が未決でも、安全に選べる範囲を明示する。

対象:

- `data/local_dogfood/2026-06-22-*` にある生成済み local dogfood artifact。
- `data/research/`、`data/strategy_reviews/`、`data/paper/`、`data/crypto_perp/`、`data/bot/` にある、Local dogfood の候補になり得る active artifact。
- CLI help で確認した `strategy-input-feedback-proposal-build`、`strategy-input-feedback-proposal-review`、`strategy-case-lite-update`、`strategy-case-index-build`、`strategy-workbench-viewer-build` の入力境界。

対象外:

- credential、API key、API secret、passphrase、wallet、signing key。
- raw account statement、raw exchange response、注文 id、口座残高全文。
- external network probe、paper order 実行、live order 実行。
- `data/archive/pre_2026_05_31_unusable_real_data/`。
- raw market data 全行、quote 全行、WebSocket capture 全行。必要なら別の data freshness / venue inventory に分ける。

## 確認したコマンド

```bash
git status --short --branch
find data/local_dogfood -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name '*.html' \) | sort
find data/strategy_reviews data/research data/paper data/crypto_perp data/bot -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name '*.html' \) | sort
for d in data/*; do [ -d "$d" ] || continue; printf '%s\t' "$d"; find "$d" -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name '*.html' \) -not -path 'data/archive/*' | wc -l; done
uv run sis strategy-input-feedback-proposal-build --help
uv run sis strategy-input-feedback-proposal-review --help
uv run sis strategy-case-lite-update --help
uv run sis strategy-case-index-build --help
uv run sis strategy-workbench-viewer-build --help
```

## Active data coverage

この section は「候補に入れたもの」だけでなく、「見たが候補外にしたもの」を明示するための coverage 表である。

active `data/` の JSON / JSONL / YAML / Markdown / HTML 対象ファイル数は 516 件。`data/archive/pre_2026_05_31_unusable_real_data/` は候補外として除外した。

| directory | 対象ファイル数 | Local dogfood での扱い | 理由 |
|---|---:|---|---|
| `data/local_dogfood/` | 29 | primary candidate | Loop 01-07 で生成した今回 plan 直結 artifact |
| `data/research/` | 70 | primary / supporting candidate | `trend_pullback_user_v1` と NDX research / backtest の主材料 |
| `data/strategy_reviews/` | 25 | primary / edge candidate | review success / missing / boundary sample |
| `data/paper/` | 39 | paper-adjacent candidate | NDX runtime observation / paper status の素材。ただし paper lane に広がりやすい |
| `data/crypto_perp/` | 67 | viewer-only candidate | Viewer / Daily Brief / permission flag dogfood には使えるが、Strategy Feedback 中心ではない |
| `data/bot/` | 2 | supporting candidate | NDX paper intent / bot decision context |
| `data/evidence/` | 1 | not primary | evidence card は readiness / gate 文脈。Local dogfood の中心にすると permission 誤読リスクがある |
| `data/manifests/` | 23 | not primary | Trade[XYZ] / raw data / venue readiness manifest が中心。必須 4 / 5 未決の間は選ばない |
| `data/notifications/` | 2 | not primary | notification queue / outbox。Strategy Feedback / Case Index の候補ではない |
| `data/ops/` | 47 | not primary | operations / readiness / read-only / remediation summary。Operations gate lane 向け |
| `data/raw/` | 107 | not primary | raw market / quote / fee / funding / ws data。Local dogfood の直接対象ではなく、data freshness / venue inventory 向け |
| `data/registry/` | 1 | not primary | Trade[XYZ] instrument registry。今回の Case Index / Strategy Feedback とは別 |
| `data/reports/` | 102 | supporting mirror, not source | human-readable mirror が多い。source artifact ではなく補助 report として読む |
| `data/state/` | 1 | not primary | local state cache。選定の source of truth にしない |
| `data/archive/` | 0 | excluded | unusable real data archive。候補にしない |
| `data/normalized/` | 0 | none | 対象ファイルなし |

### Candidate 外として確認した小規模 directory

| path | 状態 / 読み方 | 候補外理由 |
|---|---|---|
| `data/evidence/evidence_card_20260617_111729.json` | top-level `status=GO`; schema なし | `GO` を execution permission と誤読しやすい。Local dogfood の主対象ではなく、別 gate 文脈で読む |
| `data/notifications/latest_notification.json` | top-level `status=queued`; schema なし | notification queue。今回の artifact chain ではない |
| `data/notifications/outbox.jsonl` | outbox rows | notification outbox。今回の選定候補ではない |
| `data/registry/trade_xyz_instrument_registry.json` | Trade[XYZ] instrument registry | Trade[XYZ] venue registry。Strategy Feedback / Case Index の中心ではない |
| `data/state/paper_last_run.json` | local paper state | state cache。paper evidence の source of truth にはしない |

### `data/manifests/` の扱い

`data/manifests/` は 23 件ある。Local dogfood の候補としては原則選ばないが、venue / raw data / Trade[XYZ] の別 lane へ進む時の材料になる。

| path | schema / 状態 | 今回の扱い |
|---|---|---|
| `data/manifests/fee_manifest.json` | `fee_manifest.v1` | raw fee context。候補外 |
| `data/manifests/funding_history_join_manifest.json` | `funding_history_join_manifest.v1` | funding context。候補外 |
| `data/manifests/funding_history_manifest.json` | `funding_history_manifest.v1` | funding context。候補外 |
| `data/manifests/funding_manifest.json` | `funding_manifest.v1` | funding context。候補外 |
| `data/manifests/instrument_registry_manifest.json` | `instrument_registry_manifest.v1` | instrument registry context。候補外 |
| `data/manifests/oracle_timestamp_manifest.json` | `oracle_timestamp_manifest.v1` | timestamp context。候補外 |
| `data/manifests/session_calendar_manifest.json` | `session_calendar_manifest.v1` | session calendar context。候補外 |
| `data/manifests/session_state_manifest.json` | `session_state_manifest.v1` | session state context。候補外 |
| `data/manifests/trade_xyz_account_fee_manifest.json` | `trade_xyz_account_fee_manifest.v1`; `status=pass` | Trade[XYZ] account fee context。候補外 |
| `data/manifests/trade_xyz_data_collection_bundle_manifest.json` | `trade_xyz_data_collection_bundle_manifest.v1`; `status=completed` | Trade[XYZ] collection context。候補外 |
| `data/manifests/trade_xyz_data_readiness_manifest.json` | `trade_xyz_data_readiness_manifest.v1`; `status=NOT_READY` | readiness not ready。候補外 |
| `data/manifests/trade_xyz_historical_archive_bulk_execution_manifest.json` | `trade_xyz_historical_archive_bulk_execution_manifest.v1`; `status=planned` | archive plan。候補外 |
| `data/manifests/trade_xyz_historical_archive_bulk_plan_manifest.json` | `trade_xyz_historical_archive_bulk_plan_manifest.v1` | archive plan。候補外 |
| `data/manifests/trade_xyz_historical_archive_preflight_manifest.json` | `trade_xyz_historical_archive_preflight_manifest.v1`; `status=fail` | failed preflight。候補外 |
| `data/manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json` | `trade_xyz_historical_asset_ctxs_archive_manifest.v1`; `status=planned` | archive plan。候補外 |
| `data/manifests/trade_xyz_historical_l2_archive_manifest.json` | `trade_xyz_historical_l2_archive_manifest.v1`; `status=planned` | archive plan。候補外 |
| `data/manifests/trade_xyz_quote_coverage_manifest.json` | `trade_xyz_quote_coverage_manifest.v1` | quote coverage context。候補外 |
| `data/manifests/trade_xyz_real_market_reference_manifest.json` | `trade_xyz_real_market_reference_manifest.v1`; `status=pass` | real market reference context。候補外 |
| `data/manifests/trade_xyz_reference_datasets_manifest.json` | `trade_xyz_reference_datasets_manifest.v1` | reference dataset context。候補外 |
| `data/manifests/trade_xyz_rest_parity_manifest.json` | `trade_xyz_rest_parity_manifest.v1`; `status=pass` | REST parity context。候補外 |
| `data/manifests/trade_xyz_signal_candles_manifest.json` | `trade_xyz_signal_candles_manifest.v1` | signal candle context。候補外 |
| `data/manifests/trade_xyz_ws_capture_manifest.json` | `trade_xyz_ws_capture_manifest.v1` | WebSocket capture context。候補外 |
| `data/manifests/trade_xyz_ws_quality_manifest.json` | `trade_xyz_ws_quality_manifest.v1`; `status=pass` | WebSocket quality context。候補外 |

### `data/ops/` の扱い

`data/ops/` は 47 件ある。operations / readiness / remediation 系であり、今回の Local dogfood の第一候補ではない。特に `READ_ONLY_GO`、`configured`、`fixture_only`、`blocked` は live / order permission ではない。

代表的な読み方:

| group | paths | 今回の扱い |
|---|---|---|
| Alpaca / read-only | `data/ops/alpaca_live_smoke_summary.json`, `data/ops/pr12_fresh_read_only_smoke_summary.json`, `data/ops/venue_read_only_probe_summary.json` | D6 / D7 / D18 系。必須 4 / 5 未決の間は選ばない |
| Phase / readiness | `data/ops/phase_gate_review_summary.json`, `data/ops/readiness_snapshot.json`, `data/ops/monitoring_status.json`, `data/ops/current_state_index.json` | operations gate 系。`READ_ONLY_GO` は live permission ではない |
| Execution summaries | `data/ops/execution_snapshot_summary.json`, `data/ops/execution_drift_overview_summary.json`, `data/ops/execution_gap_history_summary.json`, `data/ops/execution_read_only_surfaces_summary.json`, `data/ops/execution_venue_comparison_summary.json`, `data/ops/execution_venue_diagnostics_summary.json` | execution / venue diagnostics。今回の中心ではない |
| Operations bundle | `data/ops/operations_audit_pack.json`, `data/ops/operations_bundle_manifest.json`, `data/ops/operations_dashboard_summary.json`, `data/ops/operations_timeline_summary.json`, `data/ops/ops_review_summary.json` | operations review。D20 向け |
| Paper operations | `data/ops/paper_cycle_history_summary.json`, `data/ops/paper_operations_cycle_summary.json`, `data/ops/paper_operations_runbook_summary.json` | paper operations。Paper evidence lane 向け |
| Remediation | `data/ops/remediation_*_summary.json` | remediation workflow。今回の Strategy Feedback / Case Index 中心ではない |
| Trade[XYZ] collection | `data/ops/trade_xyz_collection_status.json`, `data/ops/trade_xyz_quote_collection_summary.json`, `data/ops/trade_xyz_until_ready_supervisor_state.json` | Trade[XYZ] data collection。今回の候補外 |
| Notification / daemon | `data/ops/notification_outbox_summary.json`, `data/ops/daemon_loop.json`, `data/ops/daemon_loop_events.jsonl`, `data/ops/daemon_loop_summary.json`, `data/ops/daemon_manifest.json`, `data/ops/daemon_manifest_summary.json` | old daemon / notification context。今回の候補外 |
| Cost / quote | `data/ops/venue_cost_matrix_summary.json`, `data/ops/quote_diagnostics_summary.json` | venue / quote diagnostics。今回の候補外 |

### `data/reports/` の扱い

`data/reports/` は 102 件ある。多くは `data/research/`、`data/ops/`、`data/paper/` の human-readable mirror であり、source of truth ではない。Local dogfood で読む場合は、対応する JSON / YAML artifact を先に確認し、report は人間が読む補助として使う。

Local dogfood に近い report:

- `data/reports/strategy_backtest_pack_report.md`
- `data/reports/strategy_backtest_pack_validation_report.md`
- `data/reports/strategy_backtest_suite_report.md`
- `data/reports/strategy_backtest_comparison_report.md`
- `data/reports/strategy_backtest_portfolio_comparison_report.md`
- `data/reports/strategy_authoring_bundle_report.md`
- `data/reports/strategy_lifecycle_review.md`
- `data/reports/paper_observation_status.md`
- `data/reports/paper_observation_session_report.md`
- `data/reports/paper_intent_preview.md`
- `data/reports/ndx_strategy_lab_research_export_report.md`
- `data/reports/ndx_paper_observation_review_report.md`

候補外または別 lane の report:

- operations: `data/reports/operations_*.md`, `data/reports/audit_*.md`, `data/reports/ops_review_report.md`
- venue/read-only: `data/reports/venue_read_only_probe.md`, `data/reports/alpaca_live_smoke.md`, `data/reports/pr12_fresh_read_only_smoke_report.md`
- Trade[XYZ]: `data/reports/trade_xyz_*.md`, `data/reports/real_market_to_trade_xyz_tracking_report.md`
- remediation: `data/reports/remediation_*.md`
- daemon / notification: `data/reports/daemon_*.md`, `data/reports/notification_outbox.md`

## Coverage verdict

この文書の選定 coverage は次の読み方に固定する。

- Local dogfood 直結: `data/local_dogfood/`、`data/research/`、`data/strategy_reviews/`、`data/paper/`、`data/crypto_perp/`、`data/bot/`。
- 存在確認済みだが候補外: `data/evidence/`、`data/manifests/`、`data/notifications/`、`data/ops/`、`data/raw/`、`data/registry/`、`data/reports/`、`data/state/`。
- 空または除外: `data/normalized/`、`data/archive/`。

したがって、次に選ぶべき primary 候補は依然として A/B/C の3つ。その他 directory は「見落とし」ではなく、scope drift と permission 誤読を避けるために候補外へ分ける。

## 用語の言い換え

| 用語 | 言い換え | この文書での扱い |
|---|---|---|
| Local dogfood | 手元の実ファイルで試す | 外部 API と注文なしで、artifact chain を実際に読む |
| artifact | 証拠ファイル / 実行結果ファイル | JSON、YAML、Markdown、HTML、JSONL |
| strategy_id | 戦略の名前 / ID | `trend_pullback_user_v1`、`ndx_open_gap_residual_v1` など |
| proposal | 更新候補 | 自動反映ではなく、人間が見るための提案 |
| review | 人間レビュー記録 | `APPROVE`、`HOLD`、`REJECT`、`NEEDS_FIX` など |
| Case Lite | 戦略ケースの軽量まとめ | 複数 artifact を1つの戦略ケースとして並べた JSON |
| Case Index | ケース一覧 | 複数 Case Lite を検索・比較しやすくする派生 artifact |
| Viewer | 静的 HTML 表示 | artifact を読むための local HTML。source of truth ではない |
| permission boundary | 許可しない範囲 | live order や exchange write をしないための境界 |
| secret handling | 秘密情報の扱い | API key や明細をどこに置くかの運用 |
| paper-adjacent | paper に近い | 模擬取引 evidence と接続しやすいが、live 許可ではない |

## 選択ランキング

| 推奨順位 | 候補 | 選ぶ理由 | できること | 足りないもの / 注意 |
|---:|---|---|---|---|
| 1 | `trend_pullback_user_v1` | local/offline のまま Case Lite / Case Index / Viewer まで生成済み。backtest / review artifact が多い | Case Index と Viewer の読みやすさ評価、backtest artifact の Case Lite 化、direct apply / registry / UI の要否判断 | Input Feedback proposal は runtime observation / learning event がないため未生成。paper / live readiness ではない |
| 2 | `ndx_open_gap_residual_v1` | Runtime Observation、Input Feedback proposal / review、Case Lite、Case Index、Viewer が生成済み | Input Feedback の境界確認、source contract あり / なしの比較、paper-adjacent dogfood | paper observation 寄り。quote age stale、PnL 不足、manual contract update 未承認が残る |
| 3 | Crypto Perp truth-cycle | Viewer manifest と Daily Brief が複数あり、表示確認に向く | Viewer / Daily Brief の表示・読みやすさ確認 | Strategy Input Feedback / Case Index の中心素材ではない。別主軸に広がりやすい |
| 4 | Paper observation sessions | paper observation status と session が複数ある | normal threshold gap の現実確認、runtime observation の素材 | 新しい trading day は増えない。paper order / live には進まない |
| 5 | Strategy Review negative samples | missing / strict / boundary violation の review manifest がある | 失敗例、保留例、境界違反の表示確認 | 成功 path ではない。自動修正や direct apply には使わない |

## 候補 A: `trend_pullback_user_v1`

### 推奨判断

第一候補。`strategy_id=unknown` から選ぶなら、まずこれを選ぶのが現実的。

理由:

- backtest / suite / validation / review の材料が多い。
- Loop 03 で source contract を local dogfood 用に作成し、validation summary は failure 0。
- Loop 04 で Case Lite、Case Index、Viewer まで生成済み。
- credential、network、paper order、live order、wallet、signing、exchange write なしで続けられる。

注意:

- Runtime Observation と Learning Event はまだない。
- そのため、`Strategy Input Feedback proposal` をそのまま増やす候補ではなく、まず Case Lite / Case Index / Viewer の dogfood に向く。
- `data/research/strategy_signal_manifest.json` は NDX を指す。trend の source contract では `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` を使う。

### 生成済み local dogfood artifact

| 種類 | path | 重要 field / 状態 | 読み方 |
|---|---|---|---|
| Strategy Input Contract | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml` | local dogfood 用 | source contract の文脈。tracked docs ではなく generated data |
| Contract Validation JSON | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json` | `schema_version=strategy_input_contract_validation.v1`; summary failure 0 | source contract を local に検証できた |
| Contract Validation report | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.md` | report | 人間が読む要約 |
| Case Lite JSON | `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json` | `schema_version=strategy_case_lite.v1`; `case_id=trend_pullback_user_v1-backtest-dogfood`; `artifact_count=7`; `latest_status=READY_FOR_HUMAN_REVIEW` | backtest / validation / review artifact を1ケース化 |
| Case Lite report | `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.md` | report | 人間が読む要約 |
| Case Index JSON | `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json` | `schema_version=strategy_case_index.v1`; `case_count=1`; `strategy_count=1`; `latest_status=READY_FOR_HUMAN_REVIEW` | Case Lite 一覧 |
| Case Index report | `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.md` | report | 人間が読む要約 |
| Viewer HTML | `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html` | static HTML | 直接開いて読む候補 |
| Viewer manifest | `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json` | `schema_version=strategy_workbench_viewer.v1`; `viewer_id=trend-pullback-local-dogfood-viewer` | HTML viewer の manifest |

### 元になった active artifact

| 種類 | path | 重要 field / 状態 | 読み方 |
|---|---|---|---|
| Backtest metrics | `data/research/strategy_backtest_metrics.json` | `schema_version=strategy_authoring_backtest_result.v1`; `strategy_id=trend_pullback_user_v1` | backtest result の中心素材 |
| Backtest suite | `data/research/backtest_suite/strategy_backtest_suite_result.json` | `schema_version=strategy_backtest_suite_result.v1`; generated `2026-06-17T10:35:56.707377+00:00` | suite 結果 |
| Backtest pack | `data/research/backtest_pack/strategy_backtest_pack.json` | `schema_version=strategy_backtest_pack.v1`; source artifacts 45 | backtest artifact pack |
| Backtest pack validation | `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `schema_version=strategy_backtest_pack_validation.v1`; `status=PASS` | pack validation |
| Backtest comparison | `data/research/backtest_compare/strategy_backtest_comparison.json` | `schema_version=strategy_backtest_comparison.v1` | 比較素材 |
| Portfolio comparison | `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json` | `schema_version=strategy_backtest_portfolio_comparison.v1` | portfolio comparison |
| Authoring run | `data/research/strategy_authoring_run.json` | `schema_version=strategy_authoring_run.v1`; `strategy_id=trend_pullback_user_v1` | authoring 文脈 |
| Authoring bundle | `data/research/strategy_authoring_bundle_result.json` | `schema_version=strategy_authoring_bundle_result.v1` | bundle 結果 |
| Trend signal manifest | `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` | `schema_version=strategy_signal_manifest.v1`; `strategy_id=trend_pullback_user_v1` | trend 用の正しい signal manifest |
| Trend signals | `data/research/backtest_pack/source_artifacts/research/strategy_signals.jsonl` | signal rows | trend 用 signals |
| Current operator review | `data/strategy_reviews/dogfood-operator-current/review_manifest.json` | `schema_version=strategy_review_manifest.v1`; `review_status=READY_FOR_HUMAN_REVIEW`; source artifacts 18 | 第一候補の review context |
| Current operator review note | `data/strategy_reviews/dogfood-operator-current/review.md` | report | 人間が読む report |
| Current operator decision | `data/strategy_reviews/dogfood-operator-current/operator_review.yaml` | human decision | operator 判断 |

### この候補で次にできること

1. `trend_pullback_user_v1` の Viewer を読み、Case Lite / Case Index が実務上読みやすいか確認する。
2. `strategy-case-lite-update --artifact` に含める artifact を増やすべきか判断する。
3. `Strategy Input Feedback` をやるなら、Runtime Observation または Learning Event を先に用意する。
4. D3 direct apply、D4 registry、D5 UI のどれが本当に必要かを、見た痛みに基づいて選ぶ。

### この候補で今やらないこと

- Strategy Input Contract の自動編集。
- DB registry。
- Svelte / server UI。
- paper order、live order、network、wallet、signing、exchange write。

## 候補 B: `ndx_open_gap_residual_v1`

### 推奨判断

第二候補。`Strategy Input Feedback` の proposal / review まで含めて見るなら有用。ただし paper-adjacent で、Local dogfood から Paper evidence lane に広がりやすい。

理由:

- Runtime Observation が生成済み。
- source contract なし proposal と、source contract あり proposal の両方がある。
- `READY_FOR_HUMAN_REVIEW` まで進む一方で、review は `HOLD` として止めている。
- paper observation status は `normal_thresholds_met=false` で、trading days が 1 / 10 のまま。

注意:

- PnL は runtime observation から取れていない。
- max observed quote age が大きく、stale quote-age evidence が残る。
- manual contract update は未承認。
- paper / live readiness ではない。

### 生成済み local dogfood artifact

| 種類 | path | 重要 field / 状態 | 読み方 |
|---|---|---|---|
| Runtime Observation JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json` | `schema_version=strategy_runtime_observation_manifest.v1`; `paper_fill_count=20`; `pnl_available=false`; `max_observed_quote_age_ms=1048982067` | paper observation 由来の runtime observation |
| Runtime Observation report | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_summary.md` | report | 人間が読む要約 |
| Runtime Observation ledger | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/runtime_observation_ledger.jsonl` | 20 rows | observation の行データ |
| Source Contract | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml` | local dogfood 用 | proposal に source context を足すため作成 |
| Contract Validation JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json` | `schema_version=strategy_input_contract_validation.v1`; summary failure 0 | local source contract validation |
| Proposal without contract | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json` | `status=NEEDS_SOURCE_CONTRACT_CONTEXT` | source contract 不足を確認した proposal |
| Review without contract | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json` | `decision=HOLD` | direct apply せず保留 |
| Proposal with contract | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json` | `status=READY_FOR_HUMAN_REVIEW`; proposed change `runtime-001` | source contract ありで proposal が人間レビュー待ちまで進む |
| Review with contract | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json` | `decision=HOLD`; `manual_contract_update_input_allowed=false` | manual update は未承認のため保留 |
| Case Lite JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json` | `schema_version=strategy_case_lite.v1`; `case_id=ndx_open_gap_residual_v1-local-dogfood` | NDX dogfood case |
| Case Index JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json` | `schema_version=strategy_case_index.v1`; `index_id=ndx-open-gap-local-dogfood-index` | NDX case index |
| Viewer HTML | `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html` | static HTML | NDX viewer |
| Viewer manifest | `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json` | `schema_version=strategy_workbench_viewer.v1`; `viewer_id=ndx-open-gap-local-dogfood-viewer` | Viewer manifest |

Loop 14 後の current read:

- Runtime Observation は `pnl_available=false`、`max_observed_quote_age_ms=1048982067`、`paper_fill_count=20` を Viewer summary に出す。
- Source contract なし proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT`。
- Source contract あり proposal は `READY_FOR_HUMAN_REVIEW` だが、review は `HOLD`。
- Case Lite / Case Index は `latest_status=HOLD`、first open action と first blocked reason を持つ。
- `manual_contract_update_input_allowed=false`、`auto_applied=false`、`direct_contract_edit_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false` は維持。

### 元になった active artifact

| 種類 | path | 重要 field / 状態 | 読み方 |
|---|---|---|---|
| Paper status | `data/research/strategy_lifecycle/paper_observation_status.json` | `normal_thresholds_met=false`; `next_action=continue_normal_paper_observation`; trading days `1/10` | normal paper gap の正本 |
| Paper lifecycle review | `data/research/strategy_lifecycle/strategy_lifecycle_review.json` | `decision=CONTINUE_PAPER_OBSERVATION` | paper continuation 文脈 |
| Backtest acceptance | `data/research/strategy_lifecycle/backtest_acceptance_decision.json` | `decision=PASS_BACKTEST_ACCEPTANCE` | backtest acceptance は paper / live permission ではない |
| NDX export manifest | `data/research/ndx/strategy_lab_research_export_manifest.json` | `schema_version=ndx_strategy_lab_research_export_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | NDX research export |
| NDX residual validation decision | `data/research/ndx/residual_validation_decision.json` | `decision=APPROVE_STRATEGY_LAB_EXPORT` | research export approval |
| NDX paper gate decision | `data/research/ndx/paper_observation_gate_decision.json` | `decision=APPROVE_PAPER_OBSERVATION_REVIEW` | paper review gate |
| NDX paper review decision | `data/research/ndx/paper_observation_review_decision.json` | `decision=NEEDS_MORE_PAPER_OBSERVATION` | more paper observation needed |
| Paper candidate pack | `data/research/paper_candidate_pack.json` | `schema_version=paper_candidate_pack.v1` | NDX paper candidate context |
| Paper intent preview | `data/bot/paper_intent_preview.json` | `schema_version=bot_preview.v1` | paper intent preview |

### Paper observation sessions

| path | review decision | session type / 注意 |
|---|---|---|
| `data/paper/observations/local-smoke-next/` | `PASS_PAPER_OBSERVATION_REVIEW` | smoke。normal pass として数えない |
| `data/paper/observations/local-paper-20260612-2055/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260612-2107/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-190737/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-192827/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-193618/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-194023/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-194550/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-200702/` | `NEEDS_MORE_PAPER_OBSERVATION`; append summary `continue_normal_paper_observation` | latest normal candidate。trading days 不足 |

### この候補で次にできること

1. Loop 08-14 の差分を completion audit し、local dogfood slice として固める。
2. Paper evidence lane へ進むか、Local dogfood だけで止めるか判断する。
3. manual contract update に進む場合は、別途ユーザー承認済みの更新対象と方針を用意する。

### この候補で今やらないこと

- manual contract update。
- paper order。
- normal paper threshold 達成の主張。
- micro live、live order、profit claim。

## 候補 C: Crypto Perp truth-cycle / Daily Brief / Viewer

### 推奨判断

第三候補。Viewer の読みやすさ検証には使えるが、今回の Strategy Input Feedback / Case Index 中心ではない。

理由:

- `strategy_workbench_viewer.v1`、`strategy_daily_brief.v1`、`crypto_perp_truth_cycle_status.v1` が複数セットである。
- permission flag の表示確認に向く。

注意:

- Strategy Input Feedback proposal / review の素材ではない。
- Case Lite / Case Index の中心素材でもない。
- Crypto Perp は別主軸なので、今回の plan と混ぜると scope が広がる。

### 既存 run dir 一覧

| run dir | 主な artifact | 読み方 |
|---|---|---|
| `data/crypto_perp/truth_cycle_dogfood_check/` | truth-cycle status、Daily Brief、Viewer | dogfood 名付きの基本候補 |
| `data/crypto_perp/truth_cycle_next_steps_check/` | truth-cycle status、Daily Brief、Viewer | next steps 表示確認 |
| `data/crypto_perp/truth_cycle_surface_check/` | truth-cycle status、Daily Brief、Viewer | surface 表示確認 |
| `data/crypto_perp/truth_cycle_stage_checklist_check/` | truth-cycle status、Daily Brief、Viewer | stage checklist 確認 |
| `data/crypto_perp/truth_cycle_stage_surface_check/` | truth-cycle status、Daily Brief、Viewer | stage surface 確認 |
| `data/crypto_perp/truth_cycle_schema_contract_check/` | truth-cycle status、Daily Brief、Viewer | schema contract 確認 |
| `data/crypto_perp/truth_cycle_summary_schema_check/` | truth-cycle status、Daily Brief、Viewer | summary schema 確認 |
| `data/crypto_perp/truth_cycle_network_flag_schema_check/` | truth-cycle status、Daily Brief、Viewer | network flag 表示確認 |
| `data/crypto_perp/truth_cycle_viewer_permission_flag_check/` | truth-cycle status、Daily Brief、Viewer | permission flag 表示確認 |
| `data/crypto_perp/truth_cycle_status_next_steps_check/` | truth-cycle status | status-only |
| `data/crypto_perp/truth_cycle_status_stage_checklist_check/` | truth-cycle status | status-only |

各 run dir の代表 path:

- `truth_cycle_status/truth_cycle_status.json`
- `truth_cycle_status/truth_cycle_status.md`
- `reports/strategy_daily_brief/strategy_daily_brief.json`
- `reports/strategy_daily_brief/strategy_daily_brief.md`
- `reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json`
- `reports/strategy_workbench_viewer/strategy_workbench_viewer.html`
- `dogfood_pack.md`

### この候補で次にできること

1. Viewer が permission flag を誤読させないか見る。
2. Daily Brief が `ready` や `needs_human_approval` を live permission のように見せていないか見る。
3. Strategy Workbench Viewer の表示改善が必要か判断する。

### この候補で今やらないこと

- Strategy Input Contract update。
- Strategy Case Index 中心の dogfood。
- crypto-perp order preview、tiny live、real network。

## 候補 D: Strategy Review negative / edge samples

### 推奨判断

補助候補。成功 path だけでなく、欠損、strict missing、boundary violation を見たい時に使う。

| path | review_status | source count | 読み方 |
|---|---|---:|---|
| `data/strategy_reviews/dogfood-operator-current/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | 第一候補の current review |
| `data/strategy_reviews/dogfood-operator-20260617/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | 日付固定版 |
| `data/strategy_reviews/dogfood-plan-check-20260617T115909/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | plan check 用 |
| `data/strategy_reviews/dogfood-complete-001/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | complete sample |
| `data/strategy_reviews/dogfood-complete-20260616/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | older complete sample |
| `data/strategy_reviews/dogfood-missing-lenient-001/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | lenient missing sample |
| `data/strategy_reviews/dogfood-missing-lenient-20260616/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | older lenient missing sample |
| `data/strategy_reviews/dogfood-missing-strict-001/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | strict missing sample |
| `data/strategy_reviews/dogfood-missing-strict-20260616/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | older strict missing sample |
| `data/strategy_reviews/dogfood-boundary-001/review_manifest.json` | `BLOCKED_BOUNDARY_VIOLATION` | 17 | boundary violation sample |
| `data/strategy_reviews/dogfood-boundary-20260616/review_manifest.json` | `BLOCKED_BOUNDARY_VIOLATION` | 17 | older boundary violation sample |

同じ directory にある `review.md` は人間向け report、`operator_review.yaml` は operator の判断記録。

## 候補 E: Backtest / Research artifact pool

### 推奨判断

`trend_pullback_user_v1` の材料として使う。単体で選ぶというより、候補 A の根拠として読む。

| path | schema / 状態 | 読み方 |
|---|---|---|
| `data/research/strategy_backtest_metrics.json` | `strategy_authoring_backtest_result.v1`; `strategy_id=trend_pullback_user_v1` | backtest result |
| `data/research/backtest_suite/strategy_backtest_suite_result.json` | `strategy_backtest_suite_result.v1` | backtest suite |
| `data/research/backtest_pack/strategy_backtest_pack.json` | `strategy_backtest_pack.v1` | backtest pack |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `strategy_backtest_pack_validation.v1`; `status=PASS` | pack validation |
| `data/research/backtest_compare/strategy_backtest_comparison.json` | `strategy_backtest_comparison.v1` | comparison |
| `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json` | `strategy_backtest_portfolio_comparison.v1` | portfolio comparison |
| `data/research/backtest_framework_run/strategy_backtest_framework_run.json` | `strategy_backtest_framework_run.v1` | framework run |
| `data/research/backtest_framework_run/vectorbt_external/strategy_backtest_external_result.json` | `strategy_backtest_external_result.v1` | vectorbt external result |
| `data/research/backtest_framework_run/bt_portfolio/strategy_backtest_portfolio_comparison.json` | `strategy_backtest_portfolio_comparison.v1` | bt portfolio comparison |
| `data/research/backtest_framework_run/empyrical_metrics/strategy_backtest_metric_extension.json` | `strategy_backtest_metric_extension.v1` | metric extension |
| `data/research/backtest_framework_run/quantstats_report/strategy_backtest_report_extension.json` | `strategy_backtest_report_extension.v1` | report extension |
| `data/research/backtest_framework_run/quantstats_report/strategy_backtest_quantstats_report.html` | HTML | quantstats report |
| `data/research/backtest_metric_extension/strategy_backtest_metric_extension.json` | `strategy_backtest_metric_extension.v1` | metric extension |
| `data/research/backtest_report_extension/strategy_backtest_report_extension.json` | `strategy_backtest_report_extension.v1` | report extension |
| `data/research/backtest_report_extension/strategy_backtest_quantstats_report.html` | HTML | quantstats report |
| `data/research/backtest_regime_split/strategy_backtest_regime_split.json` | `strategy_backtest_regime_split.v1` | regime split |
| `data/research/backtest_stress/strategy_backtest_stress.json` | `strategy_backtest_stress.v1` | stress |
| `data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json` | `strategy_backtest_rolling_stability.v1` | rolling stability |
| `data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json` | `strategy_backtest_no_lookahead_diff.v1`; `status=pass` | no-lookahead check |
| `data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json` | `strategy_backtest_execution_simulation.v1`; `status=pass` | execution simulation |
| `data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json` | `strategy_backtest_baseline_comparison.v1`; `status=pass` | baseline comparison |
| `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json` | `strategy_backtest_benchmark_relative.v1` | benchmark relative |
| `data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json` | `strategy_backtest_trial_ledger.v1`; `status=pass` | trial ledger |
| `data/research/backtest_html_report/strategy_backtest_html_report.json` | `strategy_backtest_html_report.v1` | HTML report metadata |
| `data/research/strategy_authoring_run.json` | `strategy_authoring_run.v1`; `strategy_id=trend_pullback_user_v1` | authoring run |
| `data/research/strategy_authoring_bundle_result.json` | `strategy_authoring_bundle_result.v1` | authoring bundle |
| `data/research/strategy_signals.jsonl` | signal rows | root signal rows。manifest との組み合わせに注意 |
| `data/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | root manifest は NDX を指す |
| `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1`; `strategy_id=trend_pullback_user_v1` | trend 用 manifest |
| `data/research/backtest_pack/source_artifacts/research/strategy_signals.jsonl` | signal rows | trend 用 signals |

## 候補 F: NDX research / paper-adjacent artifact pool

### 推奨判断

`ndx_open_gap_residual_v1` の材料として使う。Local dogfood だけで閉じるより、paper evidence 判断に広がりやすい。

| path | schema / 状態 | 読み方 |
|---|---|---|
| `data/research/ndx/core_dag.json` | JSON | NDX core DAG |
| `data/research/ndx/data_requirements.yaml` | YAML | data requirements |
| `data/research/ndx/ndx_feature_manifest.json` | `ndx_feature_manifest.v1` | feature manifest |
| `data/research/ndx/open_gap_residual_manifest.json` | `ndx_open_gap_residual_manifest.v1` | residual manifest |
| `data/research/ndx/residual_validation_summary.json` | `ndx_residual_validation_summary.v1`; `decision=APPROVE_STRATEGY_LAB_EXPORT` | residual validation summary |
| `data/research/ndx/residual_validation_decision.json` | `ndx_residual_validation_decision.v1`; `decision=APPROVE_STRATEGY_LAB_EXPORT` | residual validation decision |
| `data/research/ndx/strategy_lab_research_export_manifest.json` | `ndx_strategy_lab_research_export_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | research export |
| `data/research/ndx/operator_promotion_decision.json` | `ndx_operator_promotion_decision.v1`; `decision=promote_to_paper_observation` | operator promotion |
| `data/research/ndx/paper_observation_gate_decision.json` | `ndx_paper_observation_gate_decision.v1`; `decision=APPROVE_PAPER_OBSERVATION_REVIEW` | paper review gate |
| `data/research/ndx/paper_observation_review_decision.json` | `ndx_paper_observation_review_decision.v1`; `decision=NEEDS_MORE_PAPER_OBSERVATION` | more paper observation needed |
| `data/research/ndx/source_resolution/data_source_resolution.json` | `ndx_source_resolution.v1` | source resolution |
| `data/research/ndx/review/layer_2_2_exit_decision.json` | JSON | Layer 2.2 exit decision |
| `data/research/ndx/review/layer_2_2_freeze_manifest.json` | JSON | freeze manifest |
| `data/research/ndx/review/llm_review_input.json` | JSON | review input |
| `data/research/ndx/review/normalized_review.json` | JSON | normalized review |
| `data/research/ndx/reports/ndx_data_source_resolution.md` | Markdown | report |
| `data/research/ndx/reports/ndx_feature_panel.md` | Markdown | report |
| `data/research/ndx/reports/ndx_open_gap_residual.md` | Markdown | report |
| `data/research/paper_candidate_pack.json` | `paper_candidate_pack.v1` | paper candidate pack |
| `data/research/trial_ledger.jsonl` | trial rows | trial record rows |
| `data/bot/paper_intent_preview.json` | `bot_preview.v1`; `decision=HOLD` | paper intent preview |

## 現時点で不足しているもの

| 不足 | 影響 | 代替 / 次手 |
|---|---|---|
| `strategy_id` の最終指定 | どの Case を伸ばすか決まらない | この文書から候補 A / B / C を選ぶ |
| 必須 4 permission boundary | network / paper / live をどこまで禁止するか未決 | 未決の間は全部禁止扱い |
| 必須 5 secret handling | secret や statement を扱う作業に進めない | 未決の間は secret / account / statement を扱わない |
| `trend_pullback_user_v1` の Runtime Observation | Trend で Input Feedback proposal を生成できない | Case Lite / Case Index / Viewer dogfood を先にやる |
| `trend_pullback_user_v1` の Learning Event | Trend で learning-driven proposal を生成できない | Learning Event が必要かを Viewer dogfood 後に判断 |
| `ndx_open_gap_residual_v1` の manual contract update approval | proposal を contract 更新に使えない | review は `HOLD` のまま読む |
| fresh normal paper days | normal threshold が達成しない | Paper evidence lane を選ぶ場合に別途用意 |
| PnL evidence | profit / alpha / accounting claim ができない | D21 accounting まで触らない |

## 選ぶときの実務判断

### A を選ぶべき場合

- まず Local dogfood だけで進めたい。
- Viewer / Case Index が実務上使えるか見たい。
- direct apply、registry、UI のどれが必要か判断したい。
- credential / network / paper order / live order はまだ決めたくない。

推奨する指定:

```text
lane: Local dogfood
strategy_id: trend_pullback_user_v1
primary artifacts:
- data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json
- data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json
- data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html
permission boundary: undecided, so treat network / paper order / live / wallet / signing / exchange write as no
secret handling: undecided, so do not use secret / account / statement
```

### B を選ぶべき場合

- Strategy Input Feedback proposal / review の現物を見たい。
- source contract あり / なしの差分を見たい。
- paper observation status の gap も見たい。

推奨する指定:

```text
lane: Local dogfood
strategy_id: ndx_open_gap_residual_v1
primary artifacts:
- data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json
- data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json
- data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json
permission boundary: undecided, so treat network / paper order / live / wallet / signing / exchange write as no
secret handling: undecided, so do not use secret / account / statement
```

### C を選ぶべき場合

- Strategy Feedback より Viewer 表示の読みやすさを先に見たい。
- permission flag や Daily Brief が誤読されないか確認したい。

推奨する指定:

```text
lane: Local dogfood
strategy_id: crypto_perp_truth_cycle_viewer_only
primary artifacts:
- data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer.html
- data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_daily_brief/strategy_daily_brief.md
- data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json
permission boundary: undecided, so treat network / paper order / live / wallet / signing / exchange write as no
secret handling: undecided, so do not use secret / account / statement
```

## Codex 推奨

次は A を選ぶ。

理由:

- 必須 4 と 5 が未決でも進められる。
- `trend_pullback_user_v1` は local/offline artifact が多く、現在の plan の中心である Case Lite / Case Index / Viewer の評価に一番近い。
- NDX は Input Feedback の現物確認には強いが、paper evidence と manual contract update の未承認が絡む。
- Crypto Perp は Viewer 確認には強いが、今回の Strategy Feedback / Case Index plan から外れやすい。

次にユーザーが選ぶなら、最小回答はこれで足りる。

```text
選択: A
strategy_id: trend_pullback_user_v1
必須4: まだ未決。未決の間は no network / no paper order / no live / no wallet / no signing / no exchange write として扱う
必須5: まだ未決。未決の間は secret / account / statement を扱わない
```

## 抜け漏れ・誤謬リスク

- この文書の「網羅」は Local dogfood 候補の網羅であり、raw market data や archive の全ファイル棚卸しではない。
- `READY_FOR_HUMAN_REVIEW` は実行許可ではない。人間が読む準備ができたという意味。
- `PASS` は validation の pass であり、paper / live / profit の pass ではない。
- Viewer HTML は source of truth ではない。source of truth は JSON / YAML artifact、schema、CLI、tests。
- 必須 4 が未決なので、許可側に倒さない。未決は `no` として扱う。
- 必須 5 が未決なので、secret や raw account data は扱わない。
- `trend_pullback_user_v1` は root `data/research/strategy_signal_manifest.json` ではなく、backtest pack 内の manifest を使う必要がある。
- `ndx_open_gap_residual_v1` は paper-adjacent なので、Local dogfood だけで閉じる場合は scope を絞る必要がある。
