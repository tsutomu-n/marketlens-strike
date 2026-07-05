<!--
作成日: 2026-06-22_22:05 JST
更新日: 2026-06-22_22:22 JST
-->

# Local Dogfood All Current Selection Inventory

## 結論

ユーザー回答は次の前提として固定する。

1. 必須 1: `Local dogfood`
   - 言い換え: 外部 API、認証情報、paper order、live order、wallet、signing、exchange write を使わず、手元にある artifact だけで試す。
2. 必須 2: `unknown`
   - 言い換え: 対象 strategy / case / venue はまだ選ばない。いまあるものを見てから選ぶ。
3. 必須 3: Codex 推奨
   - 言い換え: こちらで現物の有無、status、足りないもの、危険な誤読を見たうえで候補を並べる。
4. 必須 4: 未決
   - この文書では `no network / no paper order / no live order / no wallet / no signing / no exchange write` として扱う。
5. 必須 5: 未決
   - この文書では secret、account raw data、statement raw data、raw exchange response、注文 ID、残高全文は扱わない。

現時点の推奨順位は次の通り。

1. 第一候補: `trend_pullback_user_v1`
   - 理由: local/offline のまま、Case Lite、Case Index、Workbench Viewer、backtest pack、review manifest の読みやすさを追加で確認できる。
   - 注意: Runtime Observation / Learning Event はない。Input Feedback proposal を根拠なしに作る候補ではない。
2. 第二候補: Crypto Perp truth-cycle viewer-only
   - 理由: Daily Brief と Viewer が複数あり、permission flag と `MISSING_PROBE_AUDIT` の誤読を潰せる。
   - 注意: Strategy Input Feedback / Case Index の中心素材ではない。
3. 第三候補: `ndx_open_gap_residual_v1`
   - 理由: Runtime Observation、Input Feedback proposal / review、Case Lite、Case Index、Viewer が揃っている。
   - 注意: 既に Loop 08-15 で dogfood 済み。次に選ぶなら manual contract update や paper evidence へ広げない境界が必要。

この文書の「すべて」は、`Local dogfood` で選択対象または判断材料になり得る現行 active artifact の全体である。raw market data 全行や report mirror 全文は、選択対象ではなく候補外として存在量と理由を明示する。

2026-06-22_22:22 JST 補足: 第二候補 C の Crypto Perp Daily Brief / Viewer dogfood を実施し、Daily Brief の count と first follow-up item が Viewer summary に出るようにした。詳細は [31_LOCAL_DOGFOOD_LOOP_19_CRYPTO_PERP_DAILY_BRIEF_VIEWER_SUMMARY_RESULTS.md](31_LOCAL_DOGFOOD_LOOP_19_CRYPTO_PERP_DAILY_BRIEF_VIEWER_SUMMARY_RESULTS.md) を読む。これは permission 表示の改善であり、probe audit、network、paper/live order、wallet、signing、exchange write の許可ではない。

## 読み方

| 用語 | 言い換え | この文書での扱い |
|---|---|---|
| Local dogfood | 手元の実ファイルで試す | API、注文、実資金を使わずに artifact chain を読む |
| artifact | 証拠ファイル / 実行結果ファイル | JSON、YAML、Markdown、HTML、JSONL |
| source of truth | 正本 | JSON / YAML artifact、schema、code、CLI、tests。HTML や Markdown は補助 |
| viewer | 静的 HTML 表示 | 読むための画面。判断の正本ではない |
| permission flag | 許可境界の印 | `live_allowed=false` など、やってよいことを狭くする flag |
| candidate | 選択候補 | 次に dogfood する対象 |
| supporting pool | 補助材料 | 候補 A/B/C の根拠として読むが、単体で選ぶと範囲が広がるもの |
| candidate 外 | 今回は選ばないもの | 存在は確認したが、必須 4/5 未決では scope drift するもの |

## 確認コマンド

この文書は次の read-only 確認を元に書いた。

```bash
git status --short --branch
git log -1 --oneline --decorate
find data/local_dogfood data/research data/strategy_reviews data/paper data/crypto_perp data/bot data/evidence data/manifests data/notifications data/ops data/raw data/registry data/reports data/state -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name '*.html' \) -not -path 'data/archive/*' | sort
uv run python - <<'PY'
# JSON / JSONL の schema_version、status、decision、row count を抽出する read-only inventory
PY
```

現行 HEAD は確認時点で次だった。

```text
de5d812 (HEAD -> main, origin/main, origin/HEAD) Update strategy workbench viewer and input feedback to add runtime observation summary fields for quote age, spread, PnL availability and execution counts
```

`HANDOFF.md` は `551bb28` を期待しており古い。したがって、この文書では `HANDOFF.md` を restart artifact として読んだうえで、現行ファイル、現行 git、現行 artifact を優先している。

## Active Data Coverage

Local dogfood の選択前に存在確認した active `data/` は次の通り。

| directory | 対象ファイル数 | 今回の扱い | 判断 |
|---|---:|---|---|
| `data/local_dogfood/` | 29 | primary candidate | A/B の direct selection source |
| `data/research/` | 70 | primary / supporting | A の backtest pool、B の NDX research pool |
| `data/strategy_reviews/` | 25 | supporting / edge | A の review source、D の negative sample |
| `data/paper/` | 39 | paper-adjacent | B/F の補助。paper lane に広がりやすい |
| `data/crypto_perp/` | 67 | viewer-only candidate | C の source |
| `data/bot/` | 2 | B supporting | NDX bot / paper intent context |
| `data/evidence/` | 1 | candidate 外 | `GO` 誤読リスクがある gate context |
| `data/manifests/` | 23 | candidate 外 | Trade[XYZ] / raw data / venue readiness |
| `data/notifications/` | 2 | candidate 外 | notification queue |
| `data/ops/` | 47 | candidate 外 | operations / readiness / remediation |
| `data/raw/` | 107 | candidate 外 | raw market / quote / fee / funding / WebSocket data |
| `data/registry/` | 1 | candidate 外 | Trade[XYZ] instrument registry |
| `data/reports/` | 102 | supporting mirror | human-readable report。source JSON/YAML を先に読む |
| `data/state/` | 1 | candidate 外 | local state cache |

## 選択候補一覧

| ID | 候補 | 推奨 | 選ぶとできること | 選ぶ前の注意 |
|---|---|---:|---|---|
| A | `trend_pullback_user_v1` | 1 | Case Lite / Case Index / Viewer / backtest evidence の読みやすさ dogfood | Runtime Observation / Learning Event なし |
| B | `ndx_open_gap_residual_v1` | 3 | HOLD / proposal / review / stale quote / no PnL の境界確認 | 既に dogfood 済み。manual update や paper evidence へ広げない |
| C | Crypto Perp truth-cycle viewer-only | 2 | Daily Brief / Viewer / permission flag の誤読確認 | Strategy Feedback / Case Index 中心ではない |
| D | Strategy Review negative / edge samples | 4 | missing / strict / boundary violation 表示の確認 | 成功 path ではなく失敗表示の改善になる |
| E | Backtest / research artifact pool | 5 | A の根拠確認、backtest evidence の表示確認 | 単体 target にすると範囲が広い |
| F | Paper observation sessions | 6 | normal paper gap の現実確認 | paper evidence lane に広がる |
| G | ops / raw / manifests / reports / registry | 選ばない | 別 lane の棚卸し材料 | 必須 4/5 未決では scope drift する |

## A: `trend_pullback_user_v1`

### 現在の読み

| 項目 | 値 |
|---|---|
| `strategy_id` | `trend_pullback_user_v1` |
| `case_id` | `trend_pullback_user_v1-backtest-dogfood` |
| Case Lite status | `READY_FOR_HUMAN_REVIEW` |
| Case Lite artifact count | 7 |
| Case Lite open actions | 0 |
| Case Lite blocked reasons | 0 |
| Viewer id | `trend-pullback-local-dogfood-viewer` |
| Viewer artifact count | 9 |
| Viewer boundary violation count | 0 |
| `live_allowed` | `false` |
| `paper_execution_allowed` | `false` |
| `exchange_write_used` | `false` |
| `signing_used` | `false` |
| `wallet_used` | `false` |

### A の local dogfood artifact

| path | 種類 | 現在の読み |
|---|---|---|
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml` | input contract | local dogfood 用 source contract |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json` | validation JSON | `strategy_input_contract_validation.v1`; boundary violation 0 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.md` | validation report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json` | Case Lite JSON | `strategy_case_lite.v1`; `READY_FOR_HUMAN_REVIEW`; artifact count 7 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.md` | Case Lite report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json` | Case Index JSON | `strategy_case_index.v1`; `index_id=trend-pullback-local-dogfood-index` |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.md` | Case Index report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json` | Viewer manifest | `strategy_workbench_viewer.v1`; artifact count 9 |
| `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html` | Viewer HTML | 静的 HTML。正本ではない |

### A の source artifact

| path | schema / status | 読み方 |
|---|---|---|
| `data/research/strategy_backtest_metrics.json` | `strategy_authoring_backtest_result.v1`; `strategy_id=trend_pullback_user_v1`; `backtest_passed=true` | backtest result の中心 |
| `data/research/backtest_pack/strategy_backtest_pack.json` | `strategy_backtest_pack.v1`; pack artifact count 45 | backtest pack |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `strategy_backtest_pack_validation.v1`; `decision=PASS` | pack validation |
| `data/research/backtest_suite/strategy_backtest_suite_result.json` | `strategy_backtest_suite_result.v1`; run count 5; passed count 5 | suite result |
| `data/research/backtest_compare/strategy_backtest_comparison.json` | `strategy_backtest_comparison.v1` | comparison |
| `data/strategy_reviews/dogfood-operator-current/review_manifest.json` | `strategy_review_manifest.v1`; `READY_FOR_HUMAN_REVIEW`; boundary violation 0 | current operator review |
| `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1`; `strategy_id=trend_pullback_user_v1` | Trend 用 signal manifest |
| `data/research/backtest_pack/source_artifacts/research/strategy_signals.jsonl` | JSONL; 7 rows | Trend 用 signal rows |

### A でできること

1. Viewer / Case Lite / Case Index が実 artifact で読みやすいか確認する。
2. backtest result、pack、suite、comparison の要約が人間の判断に足りるか確認する。
3. direct apply、registry、UI、paper bridge のどれが本当に必要かを、実際の読みづらさから選ぶ。

### A で今やらないこと

- Runtime Observation を fixture として偽造する。
- Learning Event を根拠なしに作る。
- Input Feedback proposal を無理に作る。
- paper / live readiness を主張する。
- Trade[XYZ] venue readiness へ広げる。

## B: `ndx_open_gap_residual_v1`

### 現在の読み

| 項目 | 値 |
|---|---|
| `strategy_id` | `ndx_open_gap_residual_v1` |
| `case_id` | `ndx_open_gap_residual_v1-local-dogfood` |
| Runtime Observation | `INGESTED` |
| paper orders / fills | 20 / 20 |
| PnL | `pnl_available=false` |
| max observed quote age | `1048982067 ms` |
| source contract なし proposal | `NEEDS_SOURCE_CONTRACT_CONTEXT` |
| source contract あり proposal | `READY_FOR_HUMAN_REVIEW` |
| reviews | `HOLD` |
| Case Lite status | `HOLD` |
| Case Lite artifact count | 6 |
| first blocked reason | `strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT` |
| first open action | human-approved manual contract update target の選択 |
| Viewer id | `ndx-open-gap-local-dogfood-viewer` |
| Viewer artifact count | 8 |
| Viewer boundary violation count | 0 |
| `live_allowed` | `false` |
| `paper_execution_allowed` | `false` |
| `exchange_write_used` | `false` |
| `signing_used` | `false` |
| `wallet_used` | `false` |

### B の local dogfood artifact

| path | 種類 | 現在の読み |
|---|---|---|
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json` | Runtime Observation manifest | `strategy_runtime_observation_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/runtime_observation_ledger.jsonl` | Runtime Observation ledger | 20 rows |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_summary.md` | Runtime Observation report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml` | input contract | local dogfood 用 source contract |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json` | validation JSON | `strategy_input_contract_validation.v1`; boundary violation 0 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.md` | validation report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json` | proposal without contract | `NEEDS_SOURCE_CONTRACT_CONTEXT` |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.md` | proposal report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json` | review without contract | `HOLD` |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.md` | review report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json` | proposal with contract | `READY_FOR_HUMAN_REVIEW` |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.md` | proposal report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json` | review with contract | `HOLD` |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.md` | review report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json` | Case Lite JSON | `strategy_case_lite.v1`; `HOLD`; blocked reasons 2; open actions 3 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.md` | Case Lite report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json` | Case Index JSON | `strategy_case_index.v1`; `index_id=ndx-open-gap-local-dogfood-index` |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.md` | Case Index report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json` | Viewer manifest | `strategy_workbench_viewer.v1`; artifact count 8 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html` | Viewer HTML | 静的 HTML。正本ではない |

### B の backing artifact

| path | schema / decision | 読み方 |
|---|---|---|
| `data/research/strategy_lifecycle/paper_observation_status.json` | `strategy_paper_observation_status.v1`; normal threshold 未達 | trading days 1 / required 10 |
| `data/research/strategy_lifecycle/strategy_lifecycle_review.json` | `strategy_lifecycle_review.v1`; `CONTINUE_PAPER_OBSERVATION` | paper 継続判断 |
| `data/research/strategy_lifecycle/backtest_acceptance_decision.json` | `strategy_backtest_acceptance_decision.v1`; `PASS_BACKTEST_ACCEPTANCE` | backtest acceptance。live permission ではない |
| `data/research/ndx/strategy_lab_research_export_manifest.json` | `ndx_strategy_lab_research_export_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | NDX export |
| `data/research/ndx/residual_validation_decision.json` | `ndx_residual_validation_decision.v1`; `APPROVE_STRATEGY_LAB_EXPORT` | research export approval |
| `data/research/ndx/paper_observation_gate_decision.json` | `ndx_paper_observation_gate_decision.v1`; `APPROVE_PAPER_OBSERVATION_REVIEW` | paper review gate |
| `data/research/ndx/paper_observation_review_decision.json` | `ndx_paper_observation_review_decision.v1`; `NEEDS_MORE_PAPER_OBSERVATION` | more paper observation required |
| `data/research/paper_candidate_pack.json` | `paper_candidate_pack.v1` | paper candidate context |
| `data/bot/paper_intent_preview.json` | list length 1; `paper_only=true`; `live_conversion_allowed=false`; `exchange_write_used=false` | paper intent preview |
| `data/bot/bot_decision.json` | `bot_preview.v1`; `decision=HOLD` | bot decision context |

### B でできること

1. `HOLD`、`NEEDS_SOURCE_CONTRACT_CONTEXT`、PnL 不足、stale quote を誤読しない表示の確認。
2. proposal with contract / without contract の比較。
3. Case Lite / Viewer の blocked reason と open action の読みやすさ確認。

### B で今やらないこと

- manual contract update。
- paper order。
- live order。
- PnL / profit claim。
- stale quote age を無視した readiness 主張。

## C: Crypto Perp Truth-Cycle Viewer-Only

### 現在の読み

C は Strategy Feedback の中心ではなく、Daily Brief / Viewer / permission flag を読む候補である。

| 項目 | 値 |
|---|---|
| 主 status | `MISSING_PROBE_AUDIT` |
| Daily Brief items | 各 viewer run で 1 |
| Viewer artifact count | 各 viewer run で 4 |
| Viewer boundary violation count | 0 |
| `live_allowed` | `false` |
| `paper_execution_allowed` | `false` |
| 推奨 next action | `uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>` |
| この文書での扱い | viewer-only。network / order / wallet / signing / exchange write はしない |

### C の run directory 一覧

| run dir | status artifact | Daily Brief | Viewer | 現在の読み |
|---|---|---|---|---|
| `data/crypto_perp/truth_cycle_dogfood_check/` | あり | あり | あり | `MISSING_PROBE_AUDIT`; viewer artifact count 4 |
| `data/crypto_perp/truth_cycle_network_flag_schema_check/` | あり | あり | あり | network flag schema check |
| `data/crypto_perp/truth_cycle_next_steps_check/` | あり | あり | あり | next steps 表示確認 |
| `data/crypto_perp/truth_cycle_schema_contract_check/` | あり | あり | あり | schema contract 表示確認 |
| `data/crypto_perp/truth_cycle_stage_checklist_check/` | あり | あり | あり | stage checklist 表示確認 |
| `data/crypto_perp/truth_cycle_stage_surface_check/` | あり | あり | あり | stage surface 表示確認 |
| `data/crypto_perp/truth_cycle_summary_schema_check/` | あり | あり | あり | summary schema 表示確認 |
| `data/crypto_perp/truth_cycle_surface_check/` | あり | あり | あり | surface 表示確認 |
| `data/crypto_perp/truth_cycle_viewer_permission_flag_check/` | あり | あり | あり | viewer permission flag 表示確認 |
| `data/crypto_perp/truth_cycle_status_next_steps_check/` | あり | なし | なし | status-only |
| `data/crypto_perp/truth_cycle_status_stage_checklist_check/` | あり | なし | なし | status-only |

### C の各 viewer run にある代表 file

| relative path | 種類 | 読み方 |
|---|---|---|
| `dogfood_pack.md` | pack report | 人間向け pack |
| `truth_cycle_status/truth_cycle_status.json` | truth-cycle status JSON | `crypto_perp_truth_cycle_status.v1`; `MISSING_PROBE_AUDIT` |
| `truth_cycle_status/truth_cycle_status.md` | truth-cycle status report | 人間向け要約 |
| `reports/strategy_daily_brief/strategy_daily_brief.json` | Daily Brief JSON | `strategy_daily_brief.v1`; follow-up item 1 |
| `reports/strategy_daily_brief/strategy_daily_brief.md` | Daily Brief report | 人間向け要約 |
| `reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json` | Viewer manifest | `strategy_workbench_viewer.v1`; artifact count 4 |
| `reports/strategy_workbench_viewer/strategy_workbench_viewer.html` | Viewer HTML | 静的 HTML。正本ではない |

`status-only` run は `truth_cycle_status.json` と `truth_cycle_status.md` のみ。

### C でできること

1. Daily Brief が `MISSING_PROBE_AUDIT` と recommended command を見落とさず表示するか確認する。
2. Viewer が `live_allowed=false`、`paper_execution_allowed=false`、`exchange_write_used=false` を見落とさないか確認する。
3. `READY` や `follow_up` を live / order permission と誤読しない設計になっているか確認する。

### C で今やらないこと

- Bitget / exchange network access。
- probe audit のための credential 提供。
- tiny live measurement。
- order preview / submit / cancel / close。
- wallet、signing、exchange write。

## D: Strategy Review Negative / Edge Samples

### 現在の読み

D は失敗例、欠損例、境界違反例の表示確認用である。成功 path を伸ばす候補ではない。

| directory | review_status | boundary violation | 読み方 |
|---|---|---:|---|
| `data/strategy_reviews/dogfood-operator-current/` | `READY_FOR_HUMAN_REVIEW` | 0 | A の current operator review |
| `data/strategy_reviews/dogfood-operator-20260617/` | `READY_FOR_HUMAN_REVIEW` | 0 | 日付固定 operator review |
| `data/strategy_reviews/dogfood-plan-check-20260617T115909/` | `READY_FOR_HUMAN_REVIEW` | 0 | plan check sample |
| `data/strategy_reviews/dogfood-complete-001/` | `READY_FOR_HUMAN_REVIEW` | 0 | complete sample |
| `data/strategy_reviews/dogfood-complete-20260616/` | `READY_FOR_HUMAN_REVIEW` | 0 | older complete sample |
| `data/strategy_reviews/dogfood-missing-lenient-001/` | `INCOMPLETE_ARTIFACTS` | 0 | missing lenient sample |
| `data/strategy_reviews/dogfood-missing-lenient-20260616/` | `INCOMPLETE_ARTIFACTS` | 0 | older missing lenient sample |
| `data/strategy_reviews/dogfood-missing-strict-001/` | `INCOMPLETE_ARTIFACTS` | 0 | missing strict sample |
| `data/strategy_reviews/dogfood-missing-strict-20260616/` | `INCOMPLETE_ARTIFACTS` | 0 | older missing strict sample |
| `data/strategy_reviews/dogfood-boundary-001/` | `BLOCKED_BOUNDARY_VIOLATION` | 1 | boundary violation sample |
| `data/strategy_reviews/dogfood-boundary-20260616/` | `BLOCKED_BOUNDARY_VIOLATION` | 1 | older boundary violation sample |

各 directory の基本構成:

- `review_manifest.json`
- `review.md`
- `operator_review.yaml` がある directory では operator 判断もある

## E: Backtest / Research Artifact Pool

### 現在の読み

E は単体 target ではなく、主に A の根拠として読む pool である。`PASS`、`backtest_passed=true`、`APPROVE_*` は、それぞれの検証での pass / approve であり、paper / live / profit permission ではない。

### E の artifact 一覧

| path | schema / status | 読み方 |
|---|---|---|
| `data/research/strategy_backtest_metrics.json` | `strategy_authoring_backtest_result.v1`; `strategy_id=trend_pullback_user_v1`; `backtest_passed=true` | A の中心 backtest result |
| `data/research/strategy_authoring_run.json` | `strategy_authoring_run.v1`; `strategy_id=trend_pullback_user_v1` | authoring run |
| `data/research/strategy_authoring_bundle_result.json` | `strategy_authoring_bundle_result.v1` | authoring bundle |
| `data/research/backtest_pack/strategy_backtest_pack.json` | `strategy_backtest_pack.v1` | pack |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `strategy_backtest_pack_validation.v1`; `decision=PASS` | pack validation |
| `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1`; `strategy_id=trend_pullback_user_v1` | A の signal manifest |
| `data/research/backtest_pack/source_artifacts/research/strategy_signals.jsonl` | JSONL; 7 rows | A の signal rows |
| `data/research/backtest_suite/strategy_backtest_suite_result.json` | `strategy_backtest_suite_result.v1` | suite |
| `data/research/backtest_compare/strategy_backtest_comparison.json` | `strategy_backtest_comparison.v1` | comparison |
| `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json` | `strategy_backtest_portfolio_comparison.v1` | portfolio comparison |
| `data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json` | `strategy_backtest_no_lookahead_diff.v1`; `status=pass` | no-lookahead |
| `data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json` | `strategy_backtest_execution_simulation.v1`; `status=pass` | execution simulation |
| `data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json` | `strategy_backtest_baseline_comparison.v1`; `status=pass` | baseline comparison |
| `data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json` | `strategy_backtest_assumption_ledger.v1`; `status=pass` | assumption ledger |
| `data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json` | `strategy_backtest_trial_ledger.v1`; `status=pass` | trial ledger |
| `data/research/backtest_regime_split/strategy_backtest_regime_split.json` | `strategy_backtest_regime_split.v1` | regime split |
| `data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json` | `strategy_backtest_rolling_stability.v1` | rolling stability |
| `data/research/backtest_stress/strategy_backtest_stress.json` | `strategy_backtest_stress.v1` | stress |
| `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json` | `strategy_backtest_benchmark_relative.v1` | benchmark relative |
| `data/research/backtest_data_availability/backtest_data_availability_ledger.json` | `backtest_data_availability_ledger.v1`; `status=pass` | data availability |
| `data/research/backtest_html_report/strategy_backtest_html_report.json` | `strategy_backtest_html_report.v1` | HTML report metadata |
| `data/research/backtest_adapter_selection/strategy_backtest_adapter_selection.json` | `strategy_backtest_adapter_selection.v1`; selected Phase C adapters | external adapter planning |
| `data/research/backtest_adapter_contract/strategy_backtest_adapter_contract.json` | `strategy_backtest_adapter_contract.v1` | adapter contract planning |
| `data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json` | `strategy_backtest_adapter_spike.v1`; dependency adoption deferred | external dependency spike |
| `data/research/backtest_framework_smoke/strategy_backtest_framework_smoke.json` | `strategy_backtest_framework_smoke.v1`; dependency adoption deferred | external framework smoke |
| `data/research/backtest_framework_run/strategy_backtest_framework_run.json` | `strategy_backtest_framework_run.v1` | framework run |
| `data/research/backtest_external/strategy_backtest_external_result.json` | `strategy_backtest_external_result.v1` | external result |
| `data/research/backtest_framework_run/vectorbt_external/strategy_backtest_external_result.json` | `strategy_backtest_external_result.v1` | vectorbt external result |
| `data/research/backtest_metric_extension/strategy_backtest_metric_extension.json` | `strategy_backtest_metric_extension.v1` | metric extension |
| `data/research/backtest_metric_extension/strategy_backtest_returns.jsonl` | JSONL; 7 rows | returns rows |
| `data/research/backtest_report_extension/strategy_backtest_report_extension.json` | `strategy_backtest_report_extension.v1` | report extension |
| `data/research/backtest_report_extension/strategy_backtest_report_returns.jsonl` | JSONL; 7 rows | report returns rows |
| `data/research/backtest_report_extension/strategy_backtest_quantstats_report.html` | HTML | report output |
| `data/research/backtest_framework_run/empyrical_metrics/strategy_backtest_metric_extension.json` | `strategy_backtest_metric_extension.v1` | framework metric extension |
| `data/research/backtest_framework_run/empyrical_metrics/strategy_backtest_returns.jsonl` | JSONL; 7 rows | framework returns |
| `data/research/backtest_framework_run/quantstats_report/strategy_backtest_report_extension.json` | `strategy_backtest_report_extension.v1` | quantstats extension |
| `data/research/backtest_framework_run/quantstats_report/strategy_backtest_report_returns.jsonl` | JSONL; 7 rows | quantstats returns |
| `data/research/backtest_framework_run/quantstats_report/strategy_backtest_quantstats_report.html` | HTML | quantstats report |
| `data/research/backtest_framework_run/bt_portfolio/strategy_backtest_portfolio_comparison.json` | `strategy_backtest_portfolio_comparison.v1` | bt portfolio comparison |
| `data/research/go_no_go_report.md` | Markdown | go/no-go report。permission と誤読しない |

### E の NDX artifact

| path | schema / status | 読み方 |
|---|---|---|
| `data/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | root signal manifest は NDX |
| `data/research/strategy_signals.jsonl` | JSONL; 7 rows | NDX signal rows |
| `data/research/trial_ledger.jsonl` | JSONL; 3 rows | trial ledger |
| `data/research/ndx/core_dag.json` | `core_dag.v1` | NDX Layer 2.2 DAG |
| `data/research/ndx/counter_dags.md` | Markdown | counter DAG report |
| `data/research/ndx/data_requirements.yaml` | YAML | data requirements |
| `data/research/ndx/ndx_feature_manifest.json` | `ndx_feature_manifest.v1` | feature manifest |
| `data/research/ndx/open_gap_residual_manifest.json` | `ndx_open_gap_residual_manifest.v1` | open gap residual manifest |
| `data/research/ndx/source_resolution/data_source_resolution.json` | `ndx_source_resolution.v1` | source resolution |
| `data/research/ndx/residual_validation_decision.json` | `ndx_residual_validation_decision.v1`; `APPROVE_STRATEGY_LAB_EXPORT` | residual validation |
| `data/research/ndx/residual_validation_summary.json` | `ndx_residual_validation_summary.v1`; `APPROVE_STRATEGY_LAB_EXPORT` | residual summary |
| `data/research/ndx/strategy_lab_research_export_manifest.json` | `ndx_strategy_lab_research_export_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | strategy lab export |
| `data/research/ndx/operator_promotion_decision.json` | `ndx_operator_promotion_decision.v1`; `promote_to_paper_observation` | promotion decision |
| `data/research/ndx/paper_observation_gate_decision.json` | `ndx_paper_observation_gate_decision.v1`; `APPROVE_PAPER_OBSERVATION_REVIEW` | paper gate |
| `data/research/ndx/paper_observation_review_decision.json` | `ndx_paper_observation_review_decision.v1`; `NEEDS_MORE_PAPER_OBSERVATION` | paper review |
| `data/research/ndx/review/layer_2_2_exit_decision.json` | `layer_2_2_exit_decision.v1`; `APPROVE_2_3` | Layer 2.2 exit |
| `data/research/ndx/review/layer_2_2_freeze_manifest.json` | `layer_2_2_freeze_manifest.v1` | freeze manifest |
| `data/research/ndx/review/llm_review_input.json` | `llm_dag_review_pack.v1` | review input |
| `data/research/ndx/review/llm_review_result.json` | `llm_dag_review.v1` | review result |
| `data/research/ndx/review/normalized_review.json` | `llm_dag_review.v1` | normalized review |
| `data/research/ndx/review/llm_review_pack.md` | Markdown | review pack |
| `data/research/ndx/review/llm_review_prompt.md` | Markdown | review prompt |
| `data/research/ndx/reports/ndx_data_source_resolution.md` | Markdown | source report |
| `data/research/ndx/reports/ndx_feature_panel.md` | Markdown | feature panel report |
| `data/research/ndx/reports/ndx_open_gap_residual.md` | Markdown | residual report |

## F: Paper Observation Sessions

### 現在の読み

F は paper-adjacent である。Local dogfood の補助として読めるが、選ぶと paper evidence lane に近づく。

`data/research/strategy_lifecycle/paper_observation_status.json` の current gap:

- `normal_thresholds_met=false`
- fills: observed 20 / required 20 / remaining 0
- timestamp quality: complete
- trading days: observed 1 / required 10 / remaining 9
- `next_action=continue_normal_paper_observation`

### F の session 一覧

| directory | review decision | file 構成 | 読み方 |
|---|---|---|---|
| `data/paper/observations/local-smoke-next/` | `PASS_PAPER_OBSERVATION_REVIEW` | manifest / ledger / review / cycle summary | smoke。normal pass ではない |
| `data/paper/observations/local-paper-20260612-2055/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary | normal candidate |
| `data/paper/observations/local-paper-20260612-2107/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary | normal candidate |
| `data/paper/observations/local-paper-20260617-190737/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary | normal candidate |
| `data/paper/observations/local-paper-20260617-192827/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary | normal candidate |
| `data/paper/observations/local-paper-20260617-193618/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary | normal candidate |
| `data/paper/observations/local-paper-20260617-194023/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary | normal candidate |
| `data/paper/observations/local-paper-20260617-194550/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary | normal candidate |
| `data/paper/observations/local-paper-20260617-200702/` | `NEEDS_MORE_PAPER_OBSERVATION` | manifest / ledger / review / cycle summary / append summary / source artifacts | latest normal candidate。B Runtime Observation の source |

代表 files:

- `paper_observation_session_manifest.json`
- `paper_observation_ledger.jsonl`
- `paper_observation_review_decision.json`
- `paper_observation_cycle_summary.json`
- `paper_observation_append_summary.json` は `local-paper-20260617-200702/` にのみある
- `source_artifacts/paper_intent_preview.json` は `local-paper-20260617-200702/` にのみある
- `data/paper/paper_observation_ledger.jsonl` は top-level ledger

## G: Candidate 外だが存在するもの

ここは「見ていない」のではなく、「存在を確認したが、今回の `Local dogfood` では選ばない」もの。

### `data/evidence/`

| path | 現在の読み | 候補外理由 |
|---|---|---|
| `data/evidence/evidence_card_20260617_111729.json` | top-level `status=GO`; schema なし | `GO` を execution permission と誤読しやすい。別 gate context |

### `data/manifests/`

| path | schema / status | 候補外理由 |
|---|---|---|
| `data/manifests/fee_manifest.json` | `fee_manifest.v1` | fee context |
| `data/manifests/funding_history_join_manifest.json` | `funding_history_join_manifest.v1` | funding context |
| `data/manifests/funding_history_manifest.json` | `funding_history_manifest.v1` | funding context |
| `data/manifests/funding_manifest.json` | `funding_manifest.v1` | funding context |
| `data/manifests/instrument_registry_manifest.json` | `instrument_registry_manifest.v1` | instrument context |
| `data/manifests/oracle_timestamp_manifest.json` | `oracle_timestamp_manifest.v1` | timestamp context |
| `data/manifests/session_calendar_manifest.json` | `session_calendar_manifest.v1` | session calendar |
| `data/manifests/session_state_manifest.json` | `session_state_manifest.v1` | session state |
| `data/manifests/trade_xyz_account_fee_manifest.json` | `trade_xyz_account_fee_manifest.v1`; `status=pass` | Trade[XYZ] account fee |
| `data/manifests/trade_xyz_data_collection_bundle_manifest.json` | `trade_xyz_data_collection_bundle_manifest.v1`; `status=completed` | Trade[XYZ] collection |
| `data/manifests/trade_xyz_data_readiness_manifest.json` | `trade_xyz_data_readiness_manifest.v1`; `status=NOT_READY` | readiness not ready |
| `data/manifests/trade_xyz_historical_archive_bulk_execution_manifest.json` | `trade_xyz_historical_archive_bulk_execution_manifest.v1`; `status=planned` | archive plan |
| `data/manifests/trade_xyz_historical_archive_bulk_plan_manifest.json` | `trade_xyz_historical_archive_bulk_plan_manifest.v1` | archive plan |
| `data/manifests/trade_xyz_historical_archive_preflight_manifest.json` | `trade_xyz_historical_archive_preflight_manifest.v1`; `status=fail` | failed preflight |
| `data/manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json` | `trade_xyz_historical_asset_ctxs_archive_manifest.v1`; `status=planned` | archive plan |
| `data/manifests/trade_xyz_historical_l2_archive_manifest.json` | `trade_xyz_historical_l2_archive_manifest.v1`; `status=planned` | archive plan |
| `data/manifests/trade_xyz_quote_coverage_manifest.json` | `trade_xyz_quote_coverage_manifest.v1` | quote coverage |
| `data/manifests/trade_xyz_real_market_reference_manifest.json` | `trade_xyz_real_market_reference_manifest.v1`; `status=pass` | real market reference |
| `data/manifests/trade_xyz_reference_datasets_manifest.json` | `trade_xyz_reference_datasets_manifest.v1` | reference dataset |
| `data/manifests/trade_xyz_rest_parity_manifest.json` | `trade_xyz_rest_parity_manifest.v1`; `status=pass` | REST parity |
| `data/manifests/trade_xyz_signal_candles_manifest.json` | `trade_xyz_signal_candles_manifest.v1` | signal candles |
| `data/manifests/trade_xyz_ws_capture_manifest.json` | `trade_xyz_ws_capture_manifest.v1` | WebSocket capture |
| `data/manifests/trade_xyz_ws_quality_manifest.json` | `trade_xyz_ws_quality_manifest.v1`; `status=pass` | WebSocket quality |

### `data/notifications/`

| path | 現在の読み | 候補外理由 |
|---|---|---|
| `data/notifications/latest_notification.json` | `status=queued` | notification queue |
| `data/notifications/outbox.jsonl` | 3 rows | notification outbox |

### `data/ops/`

`data/ops/` は 47 files。operations / readiness / remediation / read-only smoke の文脈であり、必須 4/5 未決のまま主対象にしない。

| path | schema / status | 候補外理由 |
|---|---|---|
| `data/ops/alpaca_live_smoke_summary.json` | `status=blocked` | read-only/live-smoke context |
| `data/ops/audit_bundle_history_summary.json` | summary | operations audit |
| `data/ops/audit_bundle_manifest.json` | manifest | operations audit |
| `data/ops/audit_dashboard_summary.json` | summary | operations audit |
| `data/ops/audit_timeline_summary.json` | summary | operations audit |
| `data/ops/current_state_index.json` | summary | current state index |
| `data/ops/daemon_loop.json` | `status=completed` | daemon context |
| `data/ops/daemon_loop_events.jsonl` | 3 rows | daemon context |
| `data/ops/daemon_loop_summary.json` | `status=completed` | daemon context |
| `data/ops/daemon_manifest.json` | manifest | daemon context |
| `data/ops/daemon_manifest_summary.json` | summary | daemon context |
| `data/ops/execution_drift_overview_summary.json` | summary | execution diagnostics |
| `data/ops/execution_gap_history_summary.json` | summary | execution diagnostics |
| `data/ops/execution_read_only_surfaces_summary.json` | summary | read-only surfaces |
| `data/ops/execution_snapshot_drift_history_summary.json` | summary | execution diagnostics |
| `data/ops/execution_snapshot_summary.json` | summary | execution diagnostics |
| `data/ops/execution_state_comparison_history_summary.json` | summary | execution diagnostics |
| `data/ops/execution_venue_comparison_summary.json` | summary | venue diagnostics |
| `data/ops/execution_venue_diagnostics_summary.json` | summary | venue diagnostics |
| `data/ops/monitoring_status.json` | `status=degraded` | monitoring context |
| `data/ops/notification_outbox_summary.json` | `status=queued` | notification context |
| `data/ops/operation_manifests.jsonl` | 203 rows | operations history |
| `data/ops/operations_audit_pack.json` | pack | operations audit |
| `data/ops/operations_bundle_manifest.json` | manifest | operations audit |
| `data/ops/operations_dashboard_summary.json` | summary | operations audit |
| `data/ops/operations_timeline_summary.json` | summary | operations audit |
| `data/ops/ops_review_summary.json` | summary | operations review |
| `data/ops/paper_cycle_history_summary.json` | summary | paper operations |
| `data/ops/paper_operations_cycle_summary.json` | summary | paper operations |
| `data/ops/paper_operations_runbook_summary.json` | summary | paper operations |
| `data/ops/phase_gate_review_summary.json` | `decision=READ_ONLY_GO` | read-only gate。live permission ではない |
| `data/ops/pr12_fresh_read_only_smoke_summary.json` | summary | read-only smoke |
| `data/ops/quote_diagnostics_summary.json` | summary | quote diagnostics |
| `data/ops/readiness_snapshot.json` | summary | readiness snapshot |
| `data/ops/remediation_command_results_summary.json` | summary | remediation |
| `data/ops/remediation_evaluator_summary.json` | summary | remediation |
| `data/ops/remediation_evidence_summary.json` | summary | remediation |
| `data/ops/remediation_execution_plan_summary.json` | summary | remediation |
| `data/ops/remediation_planner_summary.json` | summary | remediation |
| `data/ops/remediation_scoreboard_summary.json` | summary | remediation |
| `data/ops/remediation_session_checkpoint_summary.json` | summary | remediation |
| `data/ops/remediation_session_summary.json` | summary | remediation |
| `data/ops/trade_xyz_collection_status.json` | `trade_xyz_collection_status.v1`; `COLLECT_MORE_QUOTES` | Trade[XYZ] collection |
| `data/ops/trade_xyz_quote_collection_summary.json` | summary | Trade[XYZ] collection |
| `data/ops/trade_xyz_until_ready_supervisor_state.json` | `trade_xyz_until_ready_supervisor_state.v1`; `COLLECT_MORE_QUOTES` | Trade[XYZ] collection |
| `data/ops/venue_cost_matrix_summary.json` | summary | venue cost |
| `data/ops/venue_read_only_probe_summary.json` | `venue_read_only_probe_summary.v1`; `status=fixture_only` | read-only probe fixture |

### `data/raw/`

`data/raw/` は 107 files。raw market / quote / fee / funding / WebSocket data であり、Local dogfood の選択 target ではない。選ぶなら data freshness / venue inventory の別計画にする。

| group | file_count | 内容 |
|---|---:|---|
| `candles/trade_xyz` | 44 | intervals `1d`, `30m`, `3d`, `4h` x 11 symbols |
| `fees/trade_xyz` | 4 | fee JSONL |
| `fees/trade_xyz_account` | 1 | account fee raw JSON |
| `funding/trade_xyz` | 4 | funding JSONL |
| `funding/trade_xyz_from_history` | 2 | funding history-derived JSONL |
| `funding_history/trade_xyz` | 2 | funding history JSONL |
| `quotes/trade_xyz` | 3 | quote JSONL |
| `sessions/trade_xyz` | 4 | session JSONL |
| `sessions/trade_xyz_state` | 3 | session state JSONL |
| `ws/trade_xyz` | 20 | WebSocket captures |
| `ws/trade_xyz_24h_20260602_1902` | 20 | 24h WebSocket captures |

### `data/registry/`

| path | 現在の読み | 候補外理由 |
|---|---|---|
| `data/registry/trade_xyz_instrument_registry.json` | JSON list length 11 | Trade[XYZ] registry |

### `data/reports/`

`data/reports/` は 102 files。ほとんどは `data/research/`、`data/ops/`、`data/paper/` の人間向け mirror である。正本としては読まず、対応する JSON / YAML を先に読む。

今回の選択で見る価値がある代表 report:

- `data/reports/strategy_backtest_report.md`
- `data/reports/strategy_backtest_pack_report.md`
- `data/reports/strategy_backtest_pack_validation_report.md`
- `data/reports/strategy_backtest_suite_report.md`
- `data/reports/strategy_backtest_comparison_report.md`
- `data/reports/strategy_lifecycle_review.md`
- `data/reports/paper_observation_status.md`
- `data/reports/paper_observation_session_report.md`
- `data/reports/paper_intent_preview.md`
- `data/reports/ndx_strategy_lab_research_export_report.md`
- `data/reports/ndx_paper_observation_review_report.md`

候補外として読む report group:

- operations: `operations_*`, `audit_*`, `ops_review_report.md`
- venue/read-only: `venue_read_only_probe.md`, `alpaca_live_smoke.md`, `pr12_fresh_read_only_smoke_report.md`
- Trade[XYZ]: `trade_xyz_*`, `real_market_to_trade_xyz_tracking_report.md`
- remediation: `remediation_*`
- daemon / notification: `daemon_*`, `notification_outbox.md`

### `data/state/`

| path | 現在の読み | 候補外理由 |
|---|---|---|
| `data/state/paper_last_run.json` | local paper state cache | source of truth にしない |

## Codex 推奨の選択

推奨をそのまま採用するなら、次は A を選ぶ。

```text
選択: A
strategy_id: trend_pullback_user_v1
primary artifacts:
- data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json
- data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json
- data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json
- data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html
必須4: 未決のまま。no network / no paper order / no live / no wallet / no signing / no exchange write
必須5: 未決のまま。secret / account / statement / raw exchange response は扱わない
```

ただし A は、まず Case / Viewer / backtest evidence の読みやすさを dogfood する候補である。Runtime Observation や Learning Event がない状態で Input Feedback proposal を作ると fake completion になる。

permission flag の誤読潰しを優先したいなら C を選ぶ。

```text
選択: C
strategy_id: none
primary artifacts:
- data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json
- data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_daily_brief/strategy_daily_brief.json
- data/crypto_perp/truth_cycle_dogfood_check/reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json
必須4: 未決のまま。no network / no paper order / no live / no wallet / no signing / no exchange write
必須5: 未決のまま。secret / account / statement / raw exchange response は扱わない
```

## 選択テンプレート

このまま次に選ぶ場合は、次の形で返せば足りる。

```text
選択: A / B / C / D / E / F / G
strategy_id: <選んだもの or none>
primary artifacts:
- <path>
- <path>
必須4: 未決のまま。no network / no paper order / no live / no wallet / no signing / no exchange write
必須5: 未決のまま。secret / account / statement / raw exchange response は扱わない
```

## 抜け漏れ・誤謬リスク

- `unknown` は「全 directory を無制限に広げる」ではない。Local dogfood の選択対象をまだ固定していない、という意味。
- `READY_FOR_HUMAN_REVIEW` は実行許可ではない。人間が読む準備ができたという意味。
- `PASS` はその validation / backtest / check の pass であり、paper / live / profit の pass ではない。
- `READ_ONLY_GO` は read-only gate の判断であり、wallet、signing、exchange write、live order の許可ではない。
- Viewer HTML は正本ではない。正本は JSON / YAML artifact、schema、CLI、tests。
- `data/reports/` は便利だが mirror が多い。判断時は対応する JSON / YAML を先に読む。
- `data/raw/` は量が多いが、今回の Strategy Feedback / Case Index dogfood の直接 target ではない。
- B は現物が揃っているが、既に Loop 08-15 で dogfood 済み。次に選ぶなら「何を見るか」を狭く決める。
- C は追加実装しやすいが、Strategy Feedback / Case Index の中心から外れやすい。
- D は失敗例として有用だが、選ぶと目的は「失敗表示の改善」になる。
- E/F は材料 pool であり、単体 target にすると scope が広がる。
