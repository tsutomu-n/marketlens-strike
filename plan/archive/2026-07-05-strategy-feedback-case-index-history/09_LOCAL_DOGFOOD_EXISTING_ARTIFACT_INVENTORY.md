<!--
作成日: 2026-06-22_19:50 JST
更新日: 2026-06-22_20:37 JST
-->

# Local Dogfood Existing Artifact Inventory

## 現在の読み方

この文書は、Loop 01 以前の初期棚卸しを含む。Loop 01-07 の実行後に生成された `data/local_dogfood/2026-06-22-*` を含めて対象選定する場合は、[17_LOCAL_DOGFOOD_SELECTION_CATALOG.md](17_LOCAL_DOGFOOD_SELECTION_CATALOG.md) を優先して読む。

## 結論

ユーザー指定は `Local dogfood`。`strategy_id` は `unknown`。そのため、先に「今あるもの」を棚卸しし、そこから対象を選ぶ。

この棚卸しで確認した現実は次の通り。

- `data/` には Local dogfood に使える候補 artifact が多い。
- ただし、今回追加した `Strategy Input Feedback` と `Strategy Case Index` をそのまま試すための完成済み artifact は、現時点の active `data/` には見当たらない。
- 具体的には、active `data/` 内に `strategy_input_contract_update_proposal.v1`、`strategy_input_contract_update_review.v1`、`strategy_case_lite.v1`、`strategy_case_index.v1` は見つからなかった。
- 一方で、backtest、paper observation、Strategy Review、paper observation status、Crypto Perp truth-cycle、Workbench Viewer の既存 artifact はある。
- したがって推奨は、既存 artifact から「どの strategy / case を Local dogfood の対象にするか」を選び、足りない artifact を local/offline CLI で生成していくこと。

credential、network、paper order、live order、wallet、signing、exchange write は未決なので、この inventory では扱わない。

## 棚卸し範囲

対象:

- `data/` 配下の active runtime artifact。
- `configs/` 配下の設定候補。
- Local dogfood に関係する schema version、path、status、decision、boundary flag。

非対象:

- credential の値。
- API response 全文。
- raw statement 全文。
- live / network 実行。
- `data/archive/pre_2026_05_31_unusable_real_data/` の中身を候補に採用すること。

この文書での「網羅」は、Local dogfood の選択に関係する active artifact の網羅である。raw quote、fee、funding、WebSocket capture の全行列挙はしない。必要になった場合は `Venue / data freshness lane` の別 inventory を作る。

## 調査コマンド

```bash
git status --short --branch
find data -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name '*.html' \) | wc -l
find data -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name '*.html' \) | head -400
rg -n "strategy_input_contract\.v1|strategy_runtime_observation_manifest\.v1|strategy_learning_event\.v1|strategy_case_lite\.v1|strategy_input_contract_update_proposal\.v1|strategy_input_contract_update_review\.v1|strategy_case_index\.v1" data configs docs tests src -g '!docs/archive/**' -g '!data/archive/**' -g '!plan/archive/**'
find data -type f \( -name '*strategy_input*' -o -name '*runtime_observation*' -o -name '*learning*' -o -name '*case_lite*' -o -name '*case_index*' -o -name '*workbench_viewer*' -o -name '*input_feedback*' \) | sort
```

補助的に JSON parser で `schema_version`、主要 id、status、permission boundary を抽出した。本文中には secret や raw payload は写していない。

## 全体件数

`data/` 内の JSON / JSONL / YAML / Markdown / HTML 対象ファイル数:

- 543 件。

JSON として parse できたファイル:

- 281 件。
- parse error: 0 件。

active `data/` の主要 schema count:

| 件数 | schema_version | 読み方 |
|---:|---|---|
| 46 | `<none>` | schema なし JSON。個別確認が必要 |
| 44 | `trade_xyz_signal_candle_raw.v1` | raw market / signal candle 系。Local dogfood では直接候補にしない |
| 11 | `crypto_perp_truth_cycle_status.v1` | Crypto Perp truth-cycle 状態 |
| 11 | `strategy_review_manifest.v1` | Strategy Review dogfood manifest |
| 10 | `ndx_paper_observation_review_decision.v1` | NDX paper observation review |
| 9 | `strategy_daily_brief.v1` | daily brief |
| 9 | `strategy_workbench_viewer.v1` | static viewer manifest |
| 9 | `paper_observation_cycle_summary.v1` | paper observation cycle summary |
| 9 | `paper_observation_session_manifest.v1` | paper observation session |
| 1 | `strategy_paper_observation_status.v1` | normal paper status |
| 1 | `strategy_lifecycle_review.v1` | lifecycle review |
| 1 | `strategy_backtest_pack.v1` | backtest pack |
| 1 | `strategy_backtest_pack_validation.v1` | backtest pack validation |
| 1 | `strategy_backtest_suite_result.v1` | backtest suite result |

重要な欠落:

| 探したもの | active `data/` での結果 | 意味 |
|---|---|---|
| `strategy_input_contract.v1` | 見つからない | source contract ありの Input Feedback dogfood は、このままではできない |
| `strategy_runtime_observation_manifest.v1` | 見つからない | Runtime Observation を先に生成する必要がある |
| `strategy_learning_event.v1` | 見つからない | Learning Event からの proposal dogfood は、このままではできない |
| `strategy_input_contract_update_proposal.v1` | 見つからない | 今回追加した proposal build はまだ active data で dogfood されていない |
| `strategy_input_contract_update_review.v1` | 見つからない | proposal review もまだ active data で dogfood されていない |
| `strategy_case_lite.v1` | 見つからない | Case Index の入力がまだ active data にない |
| `strategy_case_index.v1` | 見つからない | Case Index build はまだ active data で dogfood されていない |

## strategy_id 候補

active `data/` から抽出できた `strategy_id` は次の2つ。

| 推奨順位 | strategy_id | 見つかった path 数 | 主な根拠 | 評価 |
|---:|---|---:|---|---|
| 1 | `trend_pullback_user_v1` | 23 | backtest / strategy signals / suite / report / portfolio comparison | Local dogfood の入口として扱いやすい。backtest と review の材料が多い |
| 2 | `ndx_open_gap_residual_v1` | 6 | paper candidate / NDX export / paper intent preview | Paper evidence 寄り。normal paper gap とつながるが、Local dogfood だけなら少し重い |

`trend_pullback_user_v1` の主な path:

- `data/research/strategy_signals.jsonl`
- `data/research/strategy_signal_manifest.json`
- `data/research/strategy_backtest_metrics.json`
- `data/research/backtest_suite/strategy_backtest_suite_result.json`
- `data/research/backtest_pack/strategy_backtest_pack.json`
- `data/research/backtest_pack/strategy_backtest_pack_validation.json`
- `data/research/strategy_authoring_run.json`
- `data/research/strategy_authoring_bundle_result.json`
- `data/research/backtest_compare/strategy_backtest_comparison.json`
- `data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json`

Loop 03 補足:

- `data/research/strategy_signals.jsonl` の行は `trend_pullback_user_v1` だが、現在の active `data/research/strategy_signal_manifest.json` は `ndx_open_gap_residual_v1` を指している。
- `trend_pullback_user_v1` の source contract には、active root の signal manifest ではなく、backtest pack 内に固定された `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` を使う。
- この補正後の current result は [12_LOCAL_DOGFOOD_LOOP_03_TREND_PULLBACK_RESULTS.md](12_LOCAL_DOGFOOD_LOOP_03_TREND_PULLBACK_RESULTS.md) を読む。

`ndx_open_gap_residual_v1` の主な path:

- `data/research/trial_ledger.jsonl`
- `data/research/paper_candidate_pack.json`
- `data/research/ndx/strategy_lab_research_export_manifest.json`
- `data/bot/paper_intent_preview.json`
- `data/paper/observations/local-paper-20260617-200702/source_artifacts/paper_intent_preview.json`

## 推奨候補

### 推奨 1: `trend_pullback_user_v1` を Local dogfood の第一候補にする

理由:

- active artifact が最も多い。
- backtest pack、backtest suite、strategy signals、review dogfood が揃っている。
- credential / network / order / live なしで進められる。
- `strategy_id=unknown` の状態から選ぶなら、最も材料が多く、検証対象を作りやすい。

現実的な進め方:

1. `trend_pullback_user_v1` を対象 strategy として仮固定する。
2. 既存 backtest / review artifact から、source contract がない状態でどこまで dogfood できるか確認する。
3. `strategy-runtime-observation-ingest` で paper session から runtime observation を生成できるか確認する。
4. 生成できたら `strategy-input-feedback-proposal-build` を試す。
5. `strategy-case-lite-update`、`strategy-case-index-build`、`strategy-workbench-viewer-build` へ進む。

注意:

- source contract が active data にないので、初回 proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT` になる可能性が高い。
- それは失敗ではなく、現実的な dogfood 結果として扱う。

### 推奨 2: `ndx_open_gap_residual_v1` を Paper evidence 寄りの第二候補にする

理由:

- paper observation とつながりやすい。
- `data/research/strategy_lifecycle/paper_observation_status.json` が `normal_thresholds_met=false` を明示している。
- normal paper gap を見ながら、paper bridge / runtime observation の読み口を確認できる。

注意:

- Local dogfood だけで閉じるには、paper evidence lane に寄りやすい。
- 新しい trading day の evidence がない場合、normal threshold は進まない。

### 推奨 3: Crypto Perp truth-cycle を Viewer dogfood 専用候補にする

理由:

- `strategy_workbench_viewer.v1` が複数ある。
- `strategy_daily_brief.v1` と `crypto_perp_truth_cycle_status.v1` もセットである。
- viewer / daily brief の読みやすさ検証には使える。

注意:

- Strategy Input Feedback や Strategy Case Index の dogfood には直結しにくい。
- Crypto Perp は別主軸なので、今回の Strategy Feedback / Case Index plan の中心に置くと scope がずれる。

## Strategy Review artifact 一覧

Strategy Review は、既存の dogfood 済み review manifest が多く、Local dogfood の読み物として使いやすい。

| path | status | created_at | source count | 読み方 |
|---|---|---|---:|---|
| `data/strategy_reviews/dogfood-operator-current/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | `2026-06-17T11:54:00Z` | 18 | 第一候補。current と名前が付いている |
| `data/strategy_reviews/dogfood-operator-current/operator_review.yaml` | human decision | n/a | n/a | operator の判断記録 |
| `data/strategy_reviews/dogfood-operator-current/review.md` | report | n/a | n/a | 人間が読む report |
| `data/strategy_reviews/dogfood-operator-20260617/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | `2026-06-17T00:03:08Z` | 18 | 日付固定版 |
| `data/strategy_reviews/dogfood-plan-check-20260617T115909/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | `2026-06-17T02:59:10Z` | 18 | plan check 用 |
| `data/strategy_reviews/dogfood-complete-001/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | `2026-06-16T12:19:41Z` | 18 | complete sample |
| `data/strategy_reviews/dogfood-complete-20260616/review_manifest.json` | `READY_FOR_HUMAN_REVIEW` | `2026-06-16T11:27:17Z` | 18 | older complete sample |
| `data/strategy_reviews/dogfood-missing-lenient-001/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | `2026-06-16T12:19:41Z` | 17 | 欠損 sample |
| `data/strategy_reviews/dogfood-missing-lenient-20260616/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | `2026-06-16T11:27:17Z` | 17 | older 欠損 sample |
| `data/strategy_reviews/dogfood-missing-strict-001/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | `2026-06-16T12:19:53Z` | 17 | strict 欠損 sample |
| `data/strategy_reviews/dogfood-missing-strict-20260616/review_manifest.json` | `INCOMPLETE_ARTIFACTS` | `2026-06-16T11:27:17Z` | 17 | older strict 欠損 sample |
| `data/strategy_reviews/dogfood-boundary-001/review_manifest.json` | `BLOCKED_BOUNDARY_VIOLATION` | `2026-06-16T12:19:41Z` | 17 | boundary violation sample |
| `data/strategy_reviews/dogfood-boundary-20260616/review_manifest.json` | `BLOCKED_BOUNDARY_VIOLATION` | `2026-06-16T11:27:17Z` | 17 | older boundary sample |

## Paper / Lifecycle artifact 一覧

Paper 系は Local dogfood の素材にはなるが、Paper evidence lane と混ざりやすい。今回は read-only で使う。

| path | schema | status / decision | created / generated | boundary |
|---|---|---|---|---|
| `data/research/strategy_lifecycle/paper_observation_status.json` | `strategy_paper_observation_status.v1` | `continue_normal_paper_observation`, `normal_thresholds_met=false` | `2026-06-19T23:59:34.644437+00:00` | `permits_live_order=false`, `live_conversion_allowed=false` |
| `data/research/strategy_lifecycle/strategy_lifecycle_review.json` | `strategy_lifecycle_review.v1` | `CONTINUE_PAPER_OBSERVATION` | `2026-06-17T14:20:55.560752+00:00` | no live |
| `data/research/strategy_lifecycle/backtest_acceptance_decision.json` | `strategy_backtest_acceptance_decision.v1` | `PASS_BACKTEST_ACCEPTANCE` | `2026-06-11T12:37:26.377648+00:00` | no live |
| `data/research/ndx/paper_observation_gate_decision.json` | `ndx_paper_observation_gate_decision.v1` | `APPROVE_PAPER_OBSERVATION_REVIEW` | `2026-06-17T10:35:45.000746+00:00` | no live |
| `data/research/ndx/paper_observation_review_decision.json` | `ndx_paper_observation_review_decision.v1` | `NEEDS_MORE_PAPER_OBSERVATION` | `2026-06-17T11:13:45.239099+00:00` | no live |

Paper observation sessions:

| session path | review decision | note |
|---|---|---|
| `data/paper/observations/local-smoke-next/` | `PASS_PAPER_OBSERVATION_REVIEW` | smoke。normal pass として扱わない |
| `data/paper/observations/local-paper-20260612-2055/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal observation candidate |
| `data/paper/observations/local-paper-20260612-2107/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal observation candidate |
| `data/paper/observations/local-paper-20260617-190737/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal observation candidate |
| `data/paper/observations/local-paper-20260617-192827/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal observation candidate |
| `data/paper/observations/local-paper-20260617-193618/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal observation candidate |
| `data/paper/observations/local-paper-20260617-194023/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal observation candidate |
| `data/paper/observations/local-paper-20260617-194550/` | `NEEDS_MORE_PAPER_OBSERVATION` | normal observation candidate |
| `data/paper/observations/local-paper-20260617-200702/` | `NEEDS_MORE_PAPER_OBSERVATION` + append summary | 最新寄り。`continue_normal_paper_observation` |

## Backtest / Research artifact 一覧

Local dogfood の基礎材料として有用。

| path | schema | status / decision | note |
|---|---|---|---|
| `data/research/backtest_pack/strategy_backtest_pack.json` | `strategy_backtest_pack.v1` | n/a | source artifacts 45 |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `strategy_backtest_pack_validation.v1` | `PASS` | backtest pack validation |
| `data/research/backtest_suite/strategy_backtest_suite_result.json` | `strategy_backtest_suite_result.v1` | n/a | `trend_pullback_user_v1` 系 |
| `data/research/strategy_signals.jsonl` | `strategy_signal.v1` rows | n/a | `trend_pullback_user_v1` |
| `data/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1` | n/a | signal manifest |
| `data/research/strategy_authoring_run.json` | `strategy_authoring_run.v1` | n/a | authoring run |
| `data/research/strategy_authoring_bundle_result.json` | `strategy_authoring_bundle_result.v1` | n/a | authoring bundle |
| `data/research/trial_ledger.jsonl` | `trial_record.v1` rows | n/a | includes `ndx_open_gap_residual_v1` |
| `data/research/paper_candidate_pack.json` | `paper_candidate_pack.v1` | n/a | `ndx_open_gap_residual_v1` |
| `data/bot/paper_intent_preview.json` | `bot_preview.v1` | n/a | `ndx_open_gap_residual_v1` |

## Crypto Perp / Viewer artifact 一覧

Viewer dogfood の材料としては有用。ただし Strategy Input Feedback / Case Index の主対象にはしない。

| run dir | status artifact | daily brief | viewer manifest | note |
|---|---|---|---|---|
| `data/crypto_perp/truth_cycle_dogfood_check/` | `truth_cycle_status/truth_cycle_status.json` | `reports/strategy_daily_brief/strategy_daily_brief.json` | `reports/strategy_workbench_viewer/strategy_workbench_viewer_manifest.json` | dogfood 名付き |
| `data/crypto_perp/truth_cycle_network_flag_schema_check/` | same | same | same | network flag schema check |
| `data/crypto_perp/truth_cycle_next_steps_check/` | same | same | same | next steps check |
| `data/crypto_perp/truth_cycle_schema_contract_check/` | same | same | same | schema contract check |
| `data/crypto_perp/truth_cycle_stage_checklist_check/` | same | same | same | stage checklist check |
| `data/crypto_perp/truth_cycle_stage_surface_check/` | same | same | same | stage surface check |
| `data/crypto_perp/truth_cycle_summary_schema_check/` | same | same | same | summary schema check |
| `data/crypto_perp/truth_cycle_surface_check/` | same | same | same | surface check |
| `data/crypto_perp/truth_cycle_viewer_permission_flag_check/` | same | same | same | permission flag check |

Additional standalone status files:

- `data/crypto_perp/truth_cycle_status_next_steps_check/truth_cycle_status.json`
- `data/crypto_perp/truth_cycle_status_stage_checklist_check/truth_cycle_status.json`

All listed Crypto Perp candidate JSONs inspected here carry no live permission in their boundary fields.

## Config 候補

Local dogfood では原則 config は read-only context として扱う。

| path | use |
|---|---|
| `configs/research_layer_2_2/ndx/*.yaml` | NDX research context |
| `configs/research_layer_2_3/ndx/*.yaml` | NDX feature / residual context |
| `configs/research_layer_2_4/ndx/residual_validation.yaml` | NDX validation context |
| `configs/crypto_perp/bitget_personal_edge_lab.yaml` | Crypto Perp context。今回の主対象にはしない |
| `configs/crypto_perp/tiny_live_measurement.yaml` | tiny live context。今回使わない |
| `configs/micro_live_policy.yaml` | micro live policy。今回使わない |
| `configs/fee_model.bitget_demo.yaml` | venue / fee context。今回使わない |
| `configs/fee_model.trade_xyz.yaml` | trade_xyz fee context。今回使う場合は read-only |

## 非推奨または保留

| 対象 | 理由 |
|---|---|
| `data/archive/pre_2026_05_31_unusable_real_data/` | 名前通り unusable real data archive。候補にしない |
| `data/raw/` | raw market / fee / funding / ws data。Local dogfood では直接候補にしない |
| `data/ops/` | operations / readiness / audit 系。Operations gate lane 向け |
| `data/registry/` | venue registry。今回の Local dogfood では補助 context |
| tests fixtures | 実 artifact ではなく test fixture。必要なら fallback として使う |
| docs examples | current proof ではない。説明用 |

## 選択肢

### Choice A: `trend_pullback_user_v1` で Local dogfood

選ぶ理由:

- 現存 artifact が最多。
- backtest / review / report の材料がある。
- credential / network / live なしで進められる。

想定する次の実行計画:

1. `data/strategy_reviews/dogfood-operator-current/review_manifest.json` を読み、source artifacts を確認する。
2. `data/research/backtest_pack/strategy_backtest_pack_validation.json` と `data/research/backtest_suite/strategy_backtest_suite_result.json` を確認する。
3. source contract がない前提で `Strategy Input Feedback` の dogfood 可能性を判断する。
4. paper session から `strategy_runtime_observation_manifest.v1` を生成できるか確認する。
5. `strategy_case_lite.v1` と `strategy_case_index.v1` を生成する計画に進む。

### Choice B: `ndx_open_gap_residual_v1` で Paper-adjacent dogfood

選ぶ理由:

- paper candidate / paper intent preview / paper observation status とつながる。
- normal paper gap の現実を見ながら dogfood できる。

注意:

- Local dogfood から Paper evidence に広がりやすい。
- 必須4/5が未決の間は、paper order、network、live は対象外にする。

### Choice C: Crypto Perp truth-cycle で Viewer dogfood

選ぶ理由:

- Workbench Viewer manifest が複数ある。
- Viewer / Daily Brief の読みやすさ確認には最適。

注意:

- Strategy Input Feedback / Case Index の中心素材ではない。
- Crypto Perp 側の別主軸に寄るため、今回 plan の主目的から少し離れる。

## 私の推奨

最初は Choice A を選ぶ。

理由:

- `strategy_id` が不明な状態から始めるなら、`trend_pullback_user_v1` が最も証拠ファイル数が多い。
- Local dogfood の範囲で閉じやすい。
- source contract や runtime observation が足りないことも、今回の新 surface の現実的な dogfood 結果として有益。

推奨する仮指定:

```text
lane: Local dogfood
strategy_id: trend_pullback_user_v1
primary review: data/strategy_reviews/dogfood-operator-current/review_manifest.json
primary backtest validation: data/research/backtest_pack/strategy_backtest_pack_validation.json
primary paper status: data/research/strategy_lifecycle/paper_observation_status.json
do not use:
- credentialed network
- paper order
- live order
- wallet / signing / exchange write
```

## 次に選ぶための質問

1. Choice A の `trend_pullback_user_v1` でよいか。
2. それとも Choice B の `ndx_open_gap_residual_v1` を優先したいか。
3. Viewer の見やすさを先に見たいなら Choice C にするか。
4. 必須4の permission boundary は、当面 `no credential / no network / no paper order / no live / no wallet / no signing / no exchange write` で仮固定してよいか。
5. 必須5の secret / account / statement handling は、当面「secret は使わない、`.env` も読まない、raw statement も扱わない」で仮固定してよいか。
