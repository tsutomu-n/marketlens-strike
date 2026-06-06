<!--
作成日: 2026-06-06_07:27 JST
更新日: 2026-06-06_10:28 JST
-->

# Code-Truth Documentation Audit 2026-06-06

この文書は、2026-06-06_07:27 JST 時点のコード、CLI、schema、tests、docs checker を正として、更新できるドキュメント、古い内容があるドキュメント、作り直したほうがよいドキュメント、削除・archive 候補を分類する。

## 確認した正本

確認コマンド:

```bash
git status --short --branch --untracked-files=all
NO_COLOR=1 COLUMNS=160 uv run sis --help
uv run python scripts/check_current_docs.py
```

確認したコード / schema:

```text
src/sis/venues/ids.py
src/sis/execution/bitget_demo_adapter.py
src/sis/commands/execution.py
src/sis/commands/execution_artifacts.py
src/sis/research/strategy_lab/specs.py
schemas/strategy_signal.v1.schema.json
schemas/trade_candidate.v1.schema.json
schemas/paper_intent_preview.v1.schema.json
```

確認済みの現行事実:

```text
worktree:
  調査開始時点では clean。

current docs checker:
  2026-06-06_10:28 JST の再確認では checked 86 current docs: metadata, links, EOF, and legacy roots ok

root CLI:
  bitget-demo-smoke が存在する。
  strategy-author-run が存在する。
  paper-from-intents が存在する。
  Trade[XYZ] collection / readiness CLI 群は引き続き存在する。

venue contract:
  VenueId = Literal["trade_xyz", "bitget_demo"]
  strategy_signal / trade_candidate / paper_intent_preview schema は execution_venue enum を trade_xyz, bitget_demo にしている。
  Trade[XYZ] proxy requirement は execution_venue == "trade_xyz" の時だけ適用する。

Bitget demo:
  adapter は local/mock-first。
  required env は BITGET_DEMO_API_KEY, BITGET_DEMO_API_SECRET, BITGET_DEMO_PASSPHRASE。
  REST header 境界は paptrading=1。
  healthcheck / local smoke は read_only_network_probe=not_executed。
  cancel / close は external_write_disabled。
  credential が揃っても status=configured であり、network/account/order readiness ではない。
```

## 2026-06-06_10:28 実装追記

この audit から作った cleanup 計画は、まず archive 移動ではなく current docs の誤読停止として実装した。

実装済み:

```text
README.md:
  backtest-first / venue-neutral / bitget_demo local smoke boundary を反映。

docs/CURRENT_STATE.md:
  Trade[XYZ] 注文口主軸表現をやめ、VenueId / baseline seed / Bitget demo local smoke を追加。

docs/CODE_STATUS.md:
  post-pivot rows と known gaps を追加。

docs/backtest/README.md:
  Strategy Authoring baseline seed を最短 backtest 入口として追加。

docs/ARCHITECTURE_AND_PHASES.md:
  Migration Boundary と Execution Boundary を更新。

docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md:
  current summary を追加し、実装前調査を historical と明示。

plan/README.md / migration pack README:
  historical / superseded 表示を追加。

Trade[XYZ] quote coverage decision docs:
  current main next action ではない historical / operational record と明示。
```

検証上の補正:

```text
`checked 83` / `830 passed` / `Literal["trade_xyz"]` を README.md docs plan 全体へ broad rg すると、audit / plan / historical docs の説明引用まで拾う。
したがって acceptance は critical current docs の scoped scan と docs checker を使う。
```

## 更新できるドキュメント

優先度高:

| Path | 理由 | 更新内容 |
|---|---|---|
| `README.md` | verification が `checked 83` / `830 passed` のまま。Bitget demo local smoke と backtest-first pivot が Current Boundaries にない。末尾の "active repo tree now uses Trade[XYZ] as the main venue path" は現在の開発判断とズレやすい。 | verification は固定数値ではなく command 参照へ寄せる。`bitget-demo-smoke` は local/configured smoke で外部接続なし、と追記。Trade[XYZ] は実装済み主要 venue だが当面の注文口主軸ではない、と修正。 |
| `docs/CURRENT_STATE.md` | `repo の主軸は Trade[XYZ] / real market / tracking / venue-gated paper / micro live canary` が、backtest-first pivot と bitget_demo local smoke 後の状態を反映していない。verification も古い。 | 結論を「backtest-first / venue-neutral pivot が現在の開発主軸、Trade[XYZ] は実装済み主要 venue かつ将来候補」と更新。Implemented Surfaces に `bitget_demo` local smoke と `VenueId` を追加。 |
| `docs/CODE_STATUS.md` | PR-00 to PR-08 と post-PR12 の表に、venue-neutral contract / Bitget demo local smoke / baseline seed backtest が入っていない。verification が古い。 | Post-PR08 / post-pivot rows を追加。Known Gaps に credentialed Bitget read-only network smoke / demo order lifecycle を追加。 |
| `docs/backtest/README.md` | pivot doc へのリンクはあるが、最初に読むべき詳細が Trade[XYZ] pure backtest に寄りすぎている。verification が古い。 | backtest-first の最初の実行経路として `scripts/seed_strategy_authoring_baseline_data.py` と `strategy-author-run --through backtest` を追記。Trade[XYZ] pure backtest は専用 surface として残す。 |
| `docs/ARCHITECTURE_AND_PHASES.md` | Migration Boundary の「新規コードの主軸は trade_xyz」は、`bitget_demo` と backtest-first pivot 後に誤読されやすい。Execution Boundary に Bitget demo local smoke がない。 | 「Trade[XYZ] は実装済み主要 venue、現在の開発主軸は backtest-first / venue-neutral」と修正。execution に Bitget demo local smoke を追加。 |
| `docs/OPERATIONS_RUNBOOK.md` | backtest-first と Bitget demo local smoke は追記済みだが、verification section との整合確認が必要。 | `bitget-demo-smoke` の status=configured 境界を維持しつつ、current verification 値が古ければ更新。 |

優先度中:

| Path | 理由 | 更新内容 |
|---|---|---|
| `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md` | content は概ね正しいが verification が古い。 | verification の数値だけ更新。Trade[XYZ] 専用 surface であり backtest-first baseline とは別、と短く再強調。 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | capabilities は厚いが verification が古い。`execution_venue` が bitget_demo も受ける現状が明示されていない可能性がある。 | `VenueId` と bitget_demo paper fixture の境界を追記。verification 更新。 |
| `docs/strategy_research_lab/11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md` | verification が古い。baseline seed artifact と backtest-first example が未反映。 | baseline seed / example spec の現行実行手順を追記。古い pass count を更新または削除。 |
| `docs/TRADE_XYZ_DOCS_CODE_TRUTH_AUDIT_2026-06-01.md` | Trade[XYZ] 実データ収集に限定した audit で、backtest-first pivot と Bitget demo local smoke を反映していない。 | この文書を historical Trade[XYZ] data audit として明記し、現行の総合 docs audit は本書へ寄せる。 |

## 古い内容があるドキュメント

| Path | 古い内容 | 扱い |
|---|---|---|
| `docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md` | 前半の「現在の確認済み事実」に、T2 実装前の `Literal["trade_xyz"]` や schema const、example validate failure が残る。後段に実行記録はあるが、長い文書内で読み違えやすい。 | 「pre-implementation finding」と明示するか、実装済み部分を上に圧縮した current summary を追加する。 |
| `README.md` | `checked 83 current docs`、`830 passed`、Trade[XYZ] main venue path の古い表現。 | 更新対象。 |
| `docs/CURRENT_STATE.md` | backtest-first pivot / bitget_demo local smoke / 845-test full check が未反映。 | 更新対象。 |
| `docs/CODE_STATUS.md` | post-pivot rows がない。 | 更新対象。 |
| `docs/backtest/README.md` | verification が古く、backtest-first baseline が薄い。 | 更新対象。 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | verification が古い。 | 更新対象。 |
| `docs/strategy_research_lab/11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md` | verification が古く、baseline seed が未反映。 | 更新対象。 |
| `plan/marketlens_strategy_research_lab_migration_pack/05_SYMBOL_BINDING_CONTRACT.md` | `execution_venue: Literal["trade_xyz"]` と書く。 | migration pack としては historical。current contract として読ませない。 |
| `plan/marketlens_strategy_research_lab_migration_pack/06_SCHEMA_CONTRACTS.md` | StrategySignalRecord / EvaluationPlan / TradeCandidate 等が `Literal["trade_xyz"]` のまま。 | migration pack としては historical。archive または README で superseded を強調する。 |

## 作り直したほうがいいドキュメント

| Path | 理由 | 作り直し案 |
|---|---|---|
| `docs/CURRENT_STATE.md` | 現行能力一覧が肥大化し、Strategy Authoring capabilities の列挙と runtime state が混在している。 | 「短い current state」に作り直し、能力一覧は `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` へリンクするだけにする。 |
| `docs/CODE_STATUS.md` | PR migration status、post-PR status、runtime readiness、verification が混在している。 | 実装済み surface 表に絞る。runtime/data readiness は `docs/CURRENT_STATE.md` または dedicated readiness doc へ分離する。 |
| `docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md` | 計画、事前調査、実行記録、完了条件、future tasks が1文書に混在し長い。 | `CURRENT_BACKTEST_FIRST_STATUS.md` と `BACKTEST_FIRST_PIVOT_EXECUTION_LOG_2026-06-05.md` に分ける。 |
| `docs/OPERATIONS_RUNBOOK.md` | Trade[XYZ] data collection、Strategy Lab、Alpaca、Bitget demo、operations daemon が1本に入っている。 | root runbook は入口だけにし、Trade[XYZ] collection / backtest-first / Bitget demo / paper ops を専用 runbook に分割する。 |
| `docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md` | 長大な時系列ログで、現在の backtest-first 判断と同列に置くと誤読される。 | historical record として残し、current summary は短い別 doc にする。 |
| `docs/集めるべき実データ0531-2108/README.md` | 実データ定義、運用、計画、ログが混在し、current checker 対象でもない。 | historical archive に移すか、`TRADE_XYZ_DATA_REQUIREMENTS_HISTORY.md` と current short summary に分ける。 |

## 削除・archive してもよいドキュメント

削除より archive を推奨する。理由は、これらは過去の判断経緯としては有用だが、current truth としては誤読リスクがあるため。

| Path | 推奨 | 理由 |
|---|---|---|
| `plan/TRADE_XYZ_AFTER_WS_SMOKE_DATA_READY_PLAN_2026-06-01.md` | `plan/archive/` へ移動候補 | WS smoke 後の data-ready plan で、現在の backtest-first pivot では主経路ではない。 |
| `plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md` | `plan/archive/` へ移動候補 | real-data ingestion handoff としては有用だが、現在の restart 正本ではない。 |
| `plan/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md` | `plan/archive/` へ移動候補 | 実装履歴として読むべきで、現在の運用計画ではない。 |
| `plan/TRADE_XYZ_DATA_COLLECTION_EXPANSION_IMPLEMENTATION_PLAN_2026-06-01.md` | `plan/archive/` へ移動候補 | Trade[XYZ] collection expansion は現在の主目的から外れている。 |
| `plan/TRADE_XYZ_WS_TO_BACKTEST_INGESTION_FINAL_PLAN_2026-06-04.md` | `plan/archive/` へ移動候補 | WS-to-backtest ingestion は完了済み記録。current plan ではなく historical evidence。 |
| `plan/marketlens_strategy_research_lab_migration_pack/` | `plan/archive/` へ移動候補、または README に superseded banner | contract docs が current `VenueId` とズレている。migration pack としてだけ読むべき。 |
| `docs/TRADE_XYZ_DATA_COLLECTION_EXPANSION_OPTIONS_2026-06-01.md` | `docs/archive/` へ移動候補 | Trade[XYZ] collection expansion options は current backtest-first path ではない。 |
| `docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md` | `docs/archive/` へ移動候補、または Trade[XYZ] historical runbook と明記 | WS collection runbook は現在の主経路ではない。 |
| `docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md` | archive 候補ではなく historical-current label を追加 | PID / quote coverage 判断の記録として重要。だが current next step と誤読される名前。 |
| `docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md` | archive 候補ではなく historical-current label を追加 | ユーザー判断記録として残す価値がある。現在の next action ではないと明記する。 |
| `docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md` | archive 候補、または filename を history 化 | 現在の「current record」として読むと誤読される。 |
| `docs/TRADE_XYZ_REAL_DATA_COLLECTION_STATUS_APPENDIX_2026-06-01.md` | archive 候補、または status snapshot と明記 | 2026-06-01 時点の appendices。current status ではない。 |
| `docs/TRADE_XYZ_READINESS_GAP_INVESTIGATION_GUIDE_2026-06-01.md` | archive 候補ではなく historical guide label | gap 調査の手順としては有用。current blocker は backtest-first path ではない。 |

## 残したほうがよい historical docs

| Path | 理由 |
|---|---|
| `docs/archive/README.md` | archive の索引として必要。今回の archive 候補を移動するならここを更新する。 |
| `docs/DOCUMENT_AUDIT_2026-05-31.md` | 2026-05-31 時点の current-doc audit として価値がある。新 audit に superseded するなら archive へ移す。 |
| `docs/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` | backtest update の履歴として価値がある。current summary ではない。 |
| `docs/LONG_RUNNING_SCRIPT_OPERATION_RUNBOOK_2026-06-05.md` | 汎用 long-running script runbook として再利用価値がある。 |
| `docs/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md` | 過去PID依存部分は historical だが、自然終了条件の考え方は reusable。 |

## 推奨実行順

破壊的な移動を避けるため、まず更新から始める。

```text
1. README.md / docs/CURRENT_STATE.md / docs/CODE_STATUS.md / docs/backtest/README.md を current code truth に更新。
2. docs/ARCHITECTURE_AND_PHASES.md に backtest-first / bitget_demo local smoke 境界を追記。
3. docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md の pre-implementation 部分を明示ラベル化。
4. Strategy Authoring capability docs の verification count と baseline seed path を更新。
5. plan/TRADE_XYZ_* top-level docs を archive へ移すか、plan/README.md でさらに強く historical と表示。
6. Trade[XYZ] data collection 系 docs を historical label / archive のどちらにするか決める。
```

## 完了条件

この audit に基づく docs cleanup の完了条件:

```text
1. current docs の verification 数値が `checked 83` / `830 passed` のまま残っていない。
2. current docs が `trade_xyz` only venue contract と読めない。
3. current docs が Bitget `status=configured` を network/account/order ready と読めない。
4. current docs が Trade[XYZ] quote coverage を現在の主経路 next action と読めない。
5. top-level plan docs は historical と明記されるか archive へ移動される。
6. uv run python scripts/check_current_docs.py が pass する。
```
