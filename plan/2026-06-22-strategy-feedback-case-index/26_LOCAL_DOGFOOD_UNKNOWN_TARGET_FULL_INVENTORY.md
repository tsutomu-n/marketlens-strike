<!--
作成日: 2026-06-22_21:39 JST
更新日: 2026-06-22_22:05 JST
-->

# Local Dogfood Unknown Target Full Inventory

## 結論

ユーザー回答の反映:

1. 必須 1: `Local dogfood`
   - 言い換え: 外部 API、認証情報、paper order、live order、wallet、signing、exchange write を使わず、手元にある artifact で試す。
2. 必須 2: `unknown`
   - 言い換え: どの strategy / case / venue を選ぶかは、この棚卸しを見てから決める。
3. 必須 3: Codex 推奨
   - 言い換え: 現物の artifact と status を見たうえで、現実的に次へ進めやすい順を提示する。
4. 必須 4: 未決
   - この文書では未承認として扱う。したがって network、paper order、live order、wallet、signing、exchange write は使わない。
5. 必須 5: 未決
   - この文書では secret、account raw data、statement raw data、raw exchange response は扱わない。

現時点の推奨は次の通り。

1. `trend_pullback_user_v1` を次の選択候補にする。
   - Local / offline のまま、Case Lite、Case Index、Workbench Viewer の読みやすさと不足を確認できる。
   - ただし Runtime Observation / Learning Event はないので、Input Feedback proposal を無理に作らない。
2. `ndx_open_gap_residual_v1` は参照用にする。
   - Input Feedback proposal / review、Runtime Observation、Case Lite / Index / Viewer まで揃っているが、Loop 08-15 で dogfood 済み。
   - 現在の正しい読みは `HOLD`、`pnl_available=false`、`max_observed_quote_age_ms=1048982067`、manual contract update 未承認。
3. Crypto Perp truth-cycle は、Viewer / Daily Brief の permission 表示確認をしたい時だけ選ぶ。
   - Strategy Input Feedback / Case Index 中心の次手からは外れやすい。

この文書の「網羅」は、`Local dogfood` の選択候補として意味がある現行 artifact の網羅である。raw market data 全行、archive、secret、account raw data、外部 network evidence は対象外。

2026-06-22_21:49 JST 補足: A の次ループとして、Trend Viewer に backtest result / pack validation の compact summary を追加した。詳細は [27_LOCAL_DOGFOOD_LOOP_16_TREND_BACKTEST_VIEWER_SUMMARY_RESULTS.md](27_LOCAL_DOGFOOD_LOOP_16_TREND_BACKTEST_VIEWER_SUMMARY_RESULTS.md) を読む。A の不足は引き続き Runtime Observation / Learning Event であり、これを根拠なしに作らない。

2026-06-22_21:58 JST 補足: A の次ループとして、Trend Viewer に backtest pack / suite / comparison の compact summary を追加した。詳細は [28_LOCAL_DOGFOOD_LOOP_17_TREND_PACK_SUITE_COMPARISON_VIEWER_SUMMARY_RESULTS.md](28_LOCAL_DOGFOOD_LOOP_17_TREND_PACK_SUITE_COMPARISON_VIEWER_SUMMARY_RESULTS.md) を読む。A は readable backtest evidence の dogfood が進んだが、Runtime Observation / Learning Event がない状態は変わらない。

2026-06-22_22:05 JST 補足: ユーザー回答 `1=Local dogfood`、`2=unknown`、`3=Codex推奨`、`4/5=未決` に合わせた、より選択用の網羅 inventory を [29_LOCAL_DOGFOOD_ALL_CURRENT_SELECTION_INVENTORY.md](29_LOCAL_DOGFOOD_ALL_CURRENT_SELECTION_INVENTORY.md) として追加した。この `26` は詳細調査の前段として残す。

## 読み方

| 用語 | 平易な言い換え | この文書での意味 |
|---|---|---|
| Local dogfood | 手元の実ファイルで試す | 外部接続なしで、既存 artifact を読んで粗を出す |
| artifact | 証拠ファイル / 実行結果ファイル | JSON、YAML、Markdown、HTML、JSONL |
| strategy_id | 戦略 ID | `trend_pullback_user_v1`、`ndx_open_gap_residual_v1` など |
| Case Lite | 戦略ケースの軽量まとめ | 複数 artifact を1つの case として束ねる JSON |
| Case Index | case の一覧 | 複数 Case Lite を比較・検索しやすくした JSON |
| Viewer | 静的 HTML 表示 | artifact を読むための HTML。正本ではない |
| proposal | 更新候補 | 自動反映ではなく、人間レビュー用の提案 |
| review | レビュー記録 | `HOLD`、`READY_FOR_HUMAN_REVIEW` などの判断 artifact |
| permission flag | 許可境界の印 | `live_allowed=false` など、やってよいことを絞る flag |
| source of truth | 正本 | code、schema、CLI、JSON/YAML artifact。Viewer / Markdown report ではない |

## 今回確認した範囲

確認対象:

- `data/local_dogfood/`
- `data/research/`
- `data/strategy_reviews/`
- `data/paper/`
- `data/crypto_perp/`
- `data/bot/`
- Local dogfood 候補外の `data/*` directory counts

確認コマンド:

```bash
find data/local_dogfood -type f | sort
find data/research data/strategy_reviews data/paper data/crypto_perp data/bot -maxdepth 5 -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name '*.html' \) | sort
jq '{schema_version,index_id,summary,cases}' data/local_dogfood/2026-06-22-*/strategy_case_index/*.json
jq '{schema_version,generated_at,latest_normal_requirement_gaps,next_action,normal_thresholds_met}' data/research/strategy_lifecycle/paper_observation_status.json
```

active `data/` の対象ファイル数:

| directory | 対象ファイル数 | 今回の扱い |
|---|---:|---|
| `data/local_dogfood/` | 29 | primary |
| `data/research/` | 70 | primary / supporting |
| `data/strategy_reviews/` | 25 | supporting / negative samples |
| `data/paper/` | 39 | paper-adjacent |
| `data/crypto_perp/` | 67 | viewer-only candidate |
| `data/bot/` | 2 | NDX supporting |
| `data/evidence/` | 1 | candidate 外 |
| `data/manifests/` | 23 | venue / Trade[XYZ] context、candidate 外 |
| `data/notifications/` | 2 | notification context、candidate 外 |
| `data/ops/` | 47 | operations lane、candidate 外 |
| `data/raw/` | 107 | raw data、candidate 外 |
| `data/registry/` | 1 | Trade[XYZ] registry、candidate 外 |
| `data/reports/` | 102 | report mirror、source artifact ではない |
| `data/state/` | 1 | local state cache、candidate 外 |
| `data/archive/` | 0 | excluded |
| `data/normalized/` | 0 | none |

## 候補ランキング

| 順位 | 候補 | 現在の状態 | 選ぶとできること | 選ばない方がよい場合 |
|---:|---|---|---|---|
| 1 | `trend_pullback_user_v1` | `READY_FOR_HUMAN_REVIEW`; Case Lite / Index / Viewer あり | Local dogfood として、Case / Viewer の実用性、見づらさ、不足 artifact を確認する | Input Feedback proposal を今すぐ作りたい場合。runtime / learning artifact がない |
| 2 | Crypto Perp truth-cycle viewer-only | 複数 run dir に Viewer / Daily Brief / status あり | permission flag や Daily Brief の誤読を潰す | Strategy Feedback / Case Index を中心に進めたい場合 |
| 3 | `ndx_open_gap_residual_v1` | `HOLD`; Input Feedback / Runtime Observation / Case / Viewer あり | NDX の proposal / review / HOLD 境界を参照する | 既に Loop 08-15 で dogfood 済み。次の主対象にすると paper / manual update へ広がりやすい |
| 4 | Strategy Review negative samples | `INCOMPLETE_ARTIFACTS` / `BLOCKED_BOUNDARY_VIOLATION` あり | 失敗例、欠損例、境界違反の表示テスト | 成功 path を伸ばしたい場合 |
| 5 | Paper observation sessions | normal gap は trading days 1 / 10 | paper-adjacent evidence の現実確認 | Local dogfood だけで閉じたい場合 |
| 6 | Backtest / research pool | Trend / NDX の backing artifact が多い | A/B の根拠として読む | 単体 target として選ぶと scope が広い |

## 候補 A: `trend_pullback_user_v1`

### 現在の読み

- `strategy_id`: `trend_pullback_user_v1`
- local case: `trend_pullback_user_v1-backtest-dogfood`
- Case Lite status: `READY_FOR_HUMAN_REVIEW`
- Case Lite artifact count: 7
- open actions: empty
- blocked reasons: empty
- Case Index: 1 case / 1 strategy
- Viewer: artifact count 9、boundary violation 0
- permission flags: `live_allowed=false`、`paper_execution_allowed=false`、`exchange_write_used=false`、`signing_used=false`、`wallet_used=false`

### Local dogfood artifact 一覧

| path | 種類 | 現在の読み |
|---|---|---|
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml` | Strategy Input Contract | local dogfood 用 input contract |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json` | validation JSON | `strategy_input_contract_validation.v1`; `validation_status=PASS`; boundary violation 0; missing required 0; warning 0 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.md` | validation report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json` | Case Lite JSON | `strategy_case_lite.v1`; `latest_status=READY_FOR_HUMAN_REVIEW`; artifact count 7 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.md` | Case Lite report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json` | Case Index JSON | `strategy_case_index.v1`; case count 1; strategy count 1 |
| `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.md` | Case Index report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json` | Viewer manifest | `strategy_workbench_viewer.v1`; artifact count 9; boundary violation 0 |
| `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html` | Viewer HTML | 静的 HTML。読むための表示であり正本ではない |

### Case Lite に含まれる source artifact

| artifact_type | path | status / 読み |
|---|---|---|
| `strategy_input_contract_validation` | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json` | `PASS` |
| `strategy_authoring_backtest_result` | `data/research/strategy_backtest_metrics.json` | `strategy_id=trend_pullback_user_v1`; `backtest_passed=true` |
| `strategy_backtest_suite_result` | `data/research/backtest_suite/strategy_backtest_suite_result.json` | generated `2026-06-17T10:35:56.707377+00:00` |
| `strategy_backtest_comparison` | `data/research/backtest_compare/strategy_backtest_comparison.json` | comparison artifact |
| `strategy_backtest_pack` | `data/research/backtest_pack/strategy_backtest_pack.json` | backtest pack |
| `strategy_backtest_pack_validation` | `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `decision=PASS` |
| `strategy_review_manifest` | `data/strategy_reviews/dogfood-operator-current/review_manifest.json` | `READY_FOR_HUMAN_REVIEW`; source count 18 |

### この候補で次にできること

1. Viewer HTML と manifest を読み、status / artifact / hashes / boundary flags が探しやすいか確認する。
2. Case Lite に追加すべき artifact があるかを、backtest / review pool から選ぶ。
3. direct apply、registry、UI のどれが本当に必要かを、実際の読みづらさから判断する。

### この候補で今やらないこと

- Input Feedback proposal を無理に生成する。
- Runtime Observation を fixture として偽造する。
- Learning Event を根拠なしに作る。
- paper / live readiness を主張する。
- Trade[XYZ] の venue readiness や raw data collection に広げる。

### 不足

| 不足 | 実務上の意味 | 次手 |
|---|---|---|
| Runtime Observation | 実運用観察から proposal を作れない | まず Case / Viewer dogfood に止める |
| Learning Event | 学習イベント起点の更新候補を作れない | 必要性が出た時だけ別計画化 |
| fresh paper evidence | paper threshold は進まない | Paper lane を選ぶまで扱わない |

## 候補 B: `ndx_open_gap_residual_v1`

### 現在の読み

- `strategy_id`: `ndx_open_gap_residual_v1`
- local case: `ndx_open_gap_residual_v1-local-dogfood`
- Runtime Observation: `INGESTED`
- paper orders / fills: 20 / 20
- PnL: `pnl_available=false`
- PnL 不足理由: ledger rows に `realized_pnl_usd`、`paper_pnl_usd`、`pnl_usd` がない
- max observed quote age: `1048982067 ms`
- source contract なし proposal: `NEEDS_SOURCE_CONTRACT_CONTEXT`
- source contract あり proposal: `READY_FOR_HUMAN_REVIEW`
- review: どちらも `HOLD`
- Case Lite / Case Index: `HOLD`
- first blocked reason: `strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT`
- first open action: human-approved manual contract update target の選択
- Viewer: artifact count 8、boundary violation 0
- permission flags: `live_allowed=false`、`paper_execution_allowed=false`、`exchange_write_used=false`、`signing_used=false`、`wallet_used=false`

### Local dogfood artifact 一覧

| path | 種類 | 現在の読み |
|---|---|---|
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json` | Runtime Observation manifest | `INGESTED`; paper order 20; fill 20; PnLなし; quote age大 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/runtime_observation_ledger.jsonl` | Runtime Observation ledger | 20 rows の行データ |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_summary.md` | Runtime Observation report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml` | Strategy Input Contract | local dogfood 用 input contract |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json` | validation JSON | `PASS`; boundary violation 0; missing required 0; warning 0 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.md` | validation report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json` | proposal without contract | `NEEDS_SOURCE_CONTRACT_CONTEXT`; proposed changes 1 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.md` | proposal report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json` | review without contract | `HOLD`; required actions 2 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.md` | review report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json` | proposal with contract | `READY_FOR_HUMAN_REVIEW`; proposed changes 1 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.md` | proposal report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json` | review with contract | `HOLD`; required actions 3 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.md` | review report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json` | Case Lite JSON | `HOLD`; artifact count 6; open actions 3; blocked reasons 2 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.md` | Case Lite report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json` | Case Index JSON | `HOLD`; case count 1; strategy count 1 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.md` | Case Index report | 人間向け要約 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json` | Viewer manifest | artifact count 8; boundary violation 0 |
| `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html` | Viewer HTML | 静的 HTML。読むための表示であり正本ではない |

### Proposal / review の具体値

| artifact | status / decision | target | evidence / required action |
|---|---|---|---|
| no-contract proposal | `NEEDS_SOURCE_CONTRACT_CONTEXT` | `execution_reality` | `max_observed_quote_age_ms=1048982067`; `max_observed_spread_bps=0.332474441027346`; `pnl_available=False` |
| no-contract review | `HOLD` | direct apply なし | source contract を提供または生成する。contract を patch しない |
| with-contract proposal | `READY_FOR_HUMAN_REVIEW` | `execution_reality` | 同じ runtime evidence。source contract context あり |
| with-contract review | `HOLD` | direct apply なし | human-approved manual contract update target を先に選ぶ。manual update 後は validate 再実行 |

### Backing artifact

| path | schema / decision | 読み方 |
|---|---|---|
| `data/research/strategy_lifecycle/paper_observation_status.json` | `strategy_paper_observation_status.v1`; `normal_thresholds_met=false` | normal paper threshold 未達。trading days 1 / 10 |
| `data/research/strategy_lifecycle/strategy_lifecycle_review.json` | `CONTINUE_PAPER_OBSERVATION` | paper 継続判断 |
| `data/research/strategy_lifecycle/backtest_acceptance_decision.json` | `PASS_BACKTEST_ACCEPTANCE` | backtest acceptance。paper/live permission ではない |
| `data/research/ndx/strategy_lab_research_export_manifest.json` | `ndx_strategy_lab_research_export_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | NDX export |
| `data/research/ndx/residual_validation_decision.json` | `APPROVE_STRATEGY_LAB_EXPORT` | research export approval |
| `data/research/ndx/paper_observation_gate_decision.json` | `APPROVE_PAPER_OBSERVATION_REVIEW` | paper review gate |
| `data/research/ndx/paper_observation_review_decision.json` | `NEEDS_MORE_PAPER_OBSERVATION` | more paper observation required |
| `data/research/paper_candidate_pack.json` | `paper_candidate_pack.v1` | paper candidate context |
| `data/bot/paper_intent_preview.json` | array length 1; `paper_only=true`; `live_conversion_allowed=false`; `exchange_write_used=false` | paper intent preview |
| `data/bot/bot_decision.json` | `bot_preview.v1`; `decision=HOLD` | bot decision context |

### この候補で次にできること

1. B を「完了済み dogfood slice」として参照し、HOLD / blocker 表示の期待値にする。
2. manual contract update に進みたい場合、必須 4 / 5 とは別に「どの target contract を、どの範囲で、人間が承認したか」を決める。
3. Paper evidence lane に進みたい場合、fresh normal paper day を別途用意する。

### この候補で今やらないこと

- manual contract update。
- paper order。
- live order。
- PnL / profit claim。
- stale quote age を無視した readiness 主張。

## 候補 C: Crypto Perp truth-cycle / Daily Brief / Viewer

### 現在の読み

- 主用途は Viewer / Daily Brief / permission flag の表示確認。
- Strategy Input Feedback proposal の素材ではない。
- Case Lite / Case Index の中心素材ではない。
- tracked plan の中心から外れやすいので、選ぶなら `viewer-only` と明示する。
- Viewer がある run は artifact count 4、boundary violation 0、`live_allowed=false`、`paper_execution_allowed=false`。

### run dir 一覧

| run dir | status artifact | Daily Brief | Viewer | 現在の読み |
|---|---|---|---|---|
| `data/crypto_perp/truth_cycle_dogfood_check/` | あり | あり | あり | summary `cycle_status=MISSING_PROBE_AUDIT`; viewer artifact count 4 |
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

代表 path:

- `truth_cycle_status/truth_cycle_status.json`
- `truth_cycle_status/truth_cycle_status.md`
- `reports/strategy_daily_brief/strategy_daily_brief.json`
- `reports/strategy_daily_brief/strategy_daily_brief.md`
- `reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json`
- `reports/strategy_workbench_viewer/strategy_workbench_viewer.html`
- `dogfood_pack.md`

### この候補で次にできること

1. Daily Brief の `ready` / `needs_human_approval` が live permission に見えないか確認する。
2. Viewer の permission flag が見落とされないか確認する。
3. `MISSING_PROBE_AUDIT` のような stop reason が、人間に分かる形で表示されるか確認する。

### この候補で今やらないこと

- Crypto Perp order preview。
- tiny live measurement。
- real network。
- wallet、signing、exchange write。

## 候補 D: Strategy Review negative / edge samples

### 現在の読み

成功例だけでなく、欠損、strict missing、boundary violation を読むための補助候補。

| path | review_status | source count | 読み方 |
|---|---|---:|---|
| `data/strategy_reviews/dogfood-operator-current/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | Trend の current operator review |
| `data/strategy_reviews/dogfood-operator-20260617/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | 日付固定 operator review |
| `data/strategy_reviews/dogfood-plan-check-20260617T115909/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | plan check sample |
| `data/strategy_reviews/dogfood-complete-001/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | complete sample |
| `data/strategy_reviews/dogfood-complete-20260616/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | 18 | older complete sample |
| `data/strategy_reviews/dogfood-missing-lenient-001/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | missing lenient sample |
| `data/strategy_reviews/dogfood-missing-lenient-20260616/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | older missing lenient sample |
| `data/strategy_reviews/dogfood-missing-strict-001/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | missing strict sample |
| `data/strategy_reviews/dogfood-missing-strict-20260616/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | 17 | older missing strict sample |
| `data/strategy_reviews/dogfood-boundary-001/review_manifest.json` | `BLOCKED_BOUNDARY_VIOLATION` | 17 | boundary violation sample |
| `data/strategy_reviews/dogfood-boundary-20260616/review_manifest.json` | `BLOCKED_BOUNDARY_VIOLATION` | 17 | older boundary violation sample |

各 directory の `review.md` は人間向け report、`operator_review.yaml` がある directory は operator 判断記録もある。

### この候補で次にできること

1. Viewer / Case の表示が失敗例で崩れないか確認する。
2. `READY_FOR_HUMAN_REVIEW` 以外の status が人間に伝わるか確認する。
3. boundary violation を permission と誤読しないか確認する。

## 候補 E: Backtest / research artifact pool

### 現在の読み

単体 target ではなく、主に `trend_pullback_user_v1` の根拠 pool として使う。

| path | schema / status | 読み方 |
|---|---|---|
| `data/research/strategy_backtest_metrics.json` | `strategy_authoring_backtest_result.v1`; `strategy_id=trend_pullback_user_v1`; `backtest_passed=true` | Trend backtest 中心 |
| `data/research/backtest_suite/strategy_backtest_suite_result.json` | `strategy_backtest_suite_result.v1` | suite |
| `data/research/backtest_pack/strategy_backtest_pack.json` | `strategy_backtest_pack.v1` | pack |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `strategy_backtest_pack_validation.v1`; `decision=PASS` | pack validation |
| `data/research/backtest_compare/strategy_backtest_comparison.json` | `strategy_backtest_comparison.v1` | comparison |
| `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json` | `strategy_backtest_portfolio_comparison.v1` | portfolio comparison |
| `data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json` | `strategy_backtest_no_lookahead_diff.v1`; `status=pass` | no-lookahead check |
| `data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json` | `strategy_backtest_execution_simulation.v1`; `status=pass` | execution simulation |
| `data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json` | `strategy_backtest_baseline_comparison.v1`; `status=pass` | baseline comparison |
| `data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json` | `strategy_backtest_trial_ledger.v1`; `status=pass` | trial ledger |
| `data/research/strategy_authoring_run.json` | `strategy_authoring_run.v1`; `strategy_id=trend_pullback_user_v1` | authoring run |
| `data/research/strategy_authoring_bundle_result.json` | `strategy_authoring_bundle_result.v1` | authoring bundle |
| `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1`; `strategy_id=trend_pullback_user_v1` | Trend 用 signal manifest |
| `data/research/backtest_pack/source_artifacts/research/strategy_signals.jsonl` | JSONL | Trend 用 signal rows |
| `data/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1`; `strategy_id=ndx_open_gap_residual_v1` | root manifest は NDX。Trend と混同しない |
| `data/research/strategy_signals.jsonl` | JSONL | root signal rows。manifest と strategy_id の対応に注意 |

### 注意

- `PASS` や `backtest_passed=true` は paper / live / profit permission ではない。
- root `data/research/strategy_signal_manifest.json` は NDX を指す。Trend では backtest pack 内の manifest を使う。

## 候補 F: Paper observation sessions

### 現在の読み

Paper-adjacent の材料。Local dogfood の target にはできるが、paper lane に広がりやすい。

`data/research/strategy_lifecycle/paper_observation_status.json` の current gap:

- `normal_thresholds_met=false`
- fills: observed 20 / required 20 / remaining 0
- timestamp quality: complete
- trading days: observed 1 / required 10 / remaining 9
- `next_action=continue_normal_paper_observation`

Session 一覧:

| directory | decision | 読み方 |
|---|---|---|
| `data/paper/observations/local-smoke-next/` | `PASS_PAPER_OBSERVATION_REVIEW` | smoke。normal pass ではない |
| `data/paper/observations/local-paper-20260612-2055/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260612-2107/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-190737/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-192827/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-193618/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-194023/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-194550/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal candidate |
| `data/paper/observations/local-paper-20260617-200702/` | `NEEDS_MORE_PAPER_OBSERVATION` | latest normal candidate。NDX Runtime Observation の source |

代表 files:

- `paper_observation_session_manifest.json`
- `paper_observation_ledger.jsonl`
- `paper_observation_review_decision.json`
- `paper_observation_cycle_summary.json`
- `paper_observation_append_summary.json` は `local-paper-20260617-200702/` にのみある

## 候補外だが存在確認済みのもの

| group | 理由 |
|---|---|
| `data/evidence/` | gate / evidence card 文脈。`GO` を execution permission と誤読しやすい |
| `data/manifests/` | Trade[XYZ] / raw data / venue readiness が中心。Local dogfood の target にすると scope が崩れる |
| `data/notifications/` | notification outbox。今回の artifact chain ではない |
| `data/ops/` | operations / readiness / remediation。D19/D20 方面 |
| `data/raw/` | raw market / quote / fee / funding / WebSocket data。選ぶなら data freshness / venue inventory の別文書にする |
| `data/registry/` | Trade[XYZ] instrument registry。今回の Strategy Feedback / Case Index 中心ではない |
| `data/reports/` | Markdown report mirror が多い。対応する JSON / YAML を先に読む |
| `data/state/` | local state cache。source of truth にしない |
| `data/archive/` | unusable real data archive として候補外 |

## 選択テンプレート

次に選ぶ時は、この形で返せば足りる。

```text
選択: A / B / C / D / E / F
strategy_id: <選んだもの or none>
primary artifacts:
- <path>
- <path>
必須4: 未決のまま。no network / no paper order / no live / no wallet / no signing / no exchange write
必須5: 未決のまま。secret / account / statement / raw exchange response は扱わない
```

## Codex 推奨の具体回答

私の推奨をそのまま採用するなら、次はこれ。

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

ただし、次に「追加実装」をしたいなら、A は最初に dogfood / gap 記録を行う候補であり、いきなり Input Feedback proposal 実装へ進める候補ではない。無理に runtime evidence を作ると fake completion になる。

## 抜け漏れ・誤謬リスク

- `unknown` は、target が未決という意味であり、全 directory を無制限に広げる意味ではない。
- `READY_FOR_HUMAN_REVIEW` は、実行許可ではない。人間が読む準備ができたという意味。
- `PASS` は、その validation の pass であり、paper / live / profit の pass ではない。
- Viewer HTML は読みやすさ確認用。正本は JSON / YAML artifact、schema、CLI、tests。
- 必須 4 が未決なので、permission は全部 `no` として扱う。
- 必須 5 が未決なので、secret / account / statement は扱わない。
- B は現物が一番揃っているが、Loop 08-15 で既に dogfood 済み。次対象に選ぶなら、manual contract update / paper evidence へ広がらないように明示する。
- C は追加実装しやすいが、Strategy Feedback / Case Index の中心から外れやすい。
- D は失敗例として有用だが、主 target にすると「失敗表示の改善」が目的になる。
- E/F は材料 pool であり、単体 target にすると scope が大きくなりすぎる。
