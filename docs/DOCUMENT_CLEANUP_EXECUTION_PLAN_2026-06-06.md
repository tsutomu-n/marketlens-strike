<!--
作成日: 2026-06-06_07:27 JST
更新日: 2026-06-06_10:28 JST
-->

# Document Cleanup Execution Plan 2026-06-06

この文書は、[DOCUMENT_AUDIT_2026-06-06_CODE_TRUTH_REFRESH.md](DOCUMENT_AUDIT_2026-06-06_CODE_TRUTH_REFRESH.md) を実行計画へ作り直したもの。目的は、コード・CLI・schema・tests を正として、current docs の誤読を先に止め、その後で長い historical docs を整理すること。

## 結論

ここからの docs cleanup は、次の順で進める。

```text
P0:
  正本と禁止事項を固定する。

P1:
  current docs の明確な古さを最小編集で直す。

P2:
  current docs の構造を短く作り直す。

P3:
  historical plan / Trade[XYZ] collection docs を archive または historical label に分ける。

P4:
  checker / links / verification を固定して完了する。
```

最初にやるべきことは archive 移動ではない。まず `README.md`、`docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`docs/backtest/README.md`、`docs/ARCHITECTURE_AND_PHASES.md` を更新し、次の誤読を消す。

```text
消すべき誤読:
  current docs が checked 83 / 830 passed を最新値のように見せる。
  current docs が trade_xyz only venue contract のように見える。
  current docs が Bitget status=configured を network/account/order ready と読ませる。
  current docs が Trade[XYZ] quote coverage を今の主経路 next action と読ませる。
```

## 2026-06-06_10:28 実装結果

実装済み:

```text
P1:
  README.md / CURRENT_STATE / CODE_STATUS / backtest README / ARCHITECTURE / OPERATIONS_RUNBOOK / Strategy docs を更新。
  stale pass count を current truth として読ませない形に変更。
  backtest-first / venue-neutral / bitget_demo local smoke 境界を current docs へ反映。

P2:
  pivot plan 冒頭に current summary を追加。
  実装前の Literal["trade_xyz"] 調査を historical と明示。
  Strategy Authoring baseline seed の実行入口を backtest docs と Strategy docs に追加。

P3:
  plan/README.md と migration pack README に historical / superseded 表示を追加。
  Trade[XYZ] quote coverage NEXT_STEPS / USER_DECISION_RECORD を current main next action ではない historical / operational record と明示。
```

意図的に未実施:

```text
archive 移動:
  今回は実施しない。まず label で誤読を止めた。

新規 current backtest status doc:
  今回は作らない。`docs/backtest/README.md` と pivot plan current summary で足りる。

full `./scripts/check`:
  docs-only cleanup なので最終確認は current-doc checker と whitespace check を優先する。
  code/schema/CLI の挙動は変更していない。
```

検証注意:

```text
README.md docs plan 全体への broad `rg` を合否判定にしない。
audit / execution plan / historical docs が古い語を説明目的で引用するため、false positive になる。
critical current docs だけを scoped scan し、historical label 付きの引用は許容する。
```

## 現行正本

コード正本:

```text
src/sis/venues/ids.py
src/sis/execution/bitget_demo_adapter.py
src/sis/commands/execution.py
src/sis/commands/execution_artifacts.py
src/sis/research/strategy_lab/specs.py
src/sis/paper/runner.py
src/sis/paper/broker.py
schemas/strategy_signal.v1.schema.json
schemas/trade_candidate.v1.schema.json
schemas/paper_intent_preview.v1.schema.json
```

docs 正本:

```text
docs/DOCUMENT_AUDIT_2026-06-06_CODE_TRUTH_REFRESH.md
docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md
docs/OPERATIONS_RUNBOOK.md
.ai_memory/HANDOFF.md
```

検証正本:

```text
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

現行事実:

```text
VenueId:
  trade_xyz
  bitget_demo

Bitget demo:
  bitget-demo-smoke は root CLI に存在する。
  local/mock-first smoke であり、外部 network probe は未実行。
  status=configured は credential env が揃ったことだけを意味する。
  external_write_enabled=false。
  exchange_write_used=false。

Backtest-first:
  scripts/seed_strategy_authoring_baseline_data.py で baseline fixture を作れる。
  strategy-author-run --through backtest は local baseline で通っている。
  Trade[XYZ] backtest_data_ready=true ではない。
```

## 制約

必ず守ること:

```text
1. docs cleanup でコード挙動を変えない。
2. archive 移動は current docs の誤読を先に止めてから行う。
3. historical docs は削除より archive / label を優先する。
4. `backtest_data_ready=true` を書かない。
5. Bitget credentialed network smoke や demo order を確認済み扱いしない。
6. `status=configured` を ready / connected と書かない。
7. generated artifact の古い test count を current truth として残さない。
8. current-doc checker に入っている doc は metadata header / links / EOF を通す。
```

## Phase P0: 正本固定

goal:

```text
作業前に、今の docs cleanup が何を正本にするかを固定する。
```

target_files:

```text
docs/DOCUMENT_AUDIT_2026-06-06_CODE_TRUTH_REFRESH.md
docs/DOCUMENT_CLEANUP_EXECUTION_PLAN_2026-06-06.md
scripts/check_current_docs.py
```

tasks:

```text
P0-1:
  `uv run sis --help` で bitget-demo-smoke / strategy-author-run / paper-from-intents の存在を確認する。

P0-2:
  `src/sis/venues/ids.py` と schema enum で VenueId が trade_xyz, bitget_demo であることを確認する。

P0-3:
  `src/sis/execution/bitget_demo_adapter.py` で read_only_network_probe=not_executed / external_write_disabled を確認する。

P0-4:
  この計画 doc を current-doc checker に入れる。
```

acceptance:

```text
1. この計画 doc が current-doc checker 対象になる。
2. P1 以降で参照する正本が文書内に明記される。
3. archive / move / rewrite の前に確認するコマンドが明記される。
```

verification:

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

## Phase P1: Current Docs の古さを最小編集で止める

goal:

```text
current docs を読んだ人が、古い verification 数値、Trade[XYZ] 主軸、trade_xyz only contract、Bitget configured ready を誤読しない状態にする。
```

target_files:

```text
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/backtest/README.md
docs/ARCHITECTURE_AND_PHASES.md
docs/OPERATIONS_RUNBOOK.md
docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md
```

tasks:

```text
P1-1 README:
  Current Boundaries に bitget-demo-smoke local/configured smoke を追加する。
  Trade[XYZ] は実装済み主要 venue だが、現在の注文口主軸ではないと書く。
  verification を latest full check に合わせるか、数値を固定せず command 参照にする。

P1-2 CURRENT_STATE:
  結論を backtest-first / venue-neutral pivot に合わせる。
  Implemented Surfaces に VenueId / bitget_demo local smoke / baseline seed backtest を追加する。
  Strategy Authoring の長い capability 列挙は短くし、詳細 doc へ逃がす。
  verification の checked 83 / 830 passed を消す。

P1-3 CODE_STATUS:
  Post-pivot rows を追加する。
    - Backtest-first baseline seed
    - Venue-neutral execution_venue contract
    - Bitget demo local smoke
    - Paper runner venue-specific fee lookup
  Known Gaps に credentialed Bitget read-only network smoke / demo order lifecycle を追加する。

P1-4 backtest README:
  最初に使う backtest-first baseline command を明記する。
  Trade[XYZ] pure backtest は専用 Python API surface として残す。
  verification を更新する。

P1-5 ARCHITECTURE:
  Migration Boundary の「新規コードの主軸は trade_xyz」を修正する。
  Execution Boundary に bitget_demo local smoke を追加する。

P1-6 OPERATIONS_RUNBOOK:
  既存の Bitget demo local smoke section を確認し、status=configured の意味を維持する。
  古い verification 数値があれば更新する。

P1-7 Pivot plan:
  実装前調査 section に `pre-implementation finding` ラベルを付ける。
  現在読むべき summary を冒頭に追加する。
```

acceptance:

```text
1. current docs に `checked 83 current docs` が current verification として残らない。
2. current docs に `830 passed` が latest verification として残らない。
3. current docs が `execution_venue: Literal["trade_xyz"]` を current contract として提示しない。
4. current docs が Bitget `status=configured` を network/account/order ready と読ませない。
5. current docs が Trade[XYZ] quote coverage を今の主経路 next action と読ませない。
```

verification:

```bash
rg -n 'checked 83|830 passed|repo の主軸|main venue path|execution_venue: Literal\["trade_xyz"\]' README.md docs/CURRENT_STATE.md docs/CODE_STATUS.md docs/backtest/README.md docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md docs/strategy_research_lab/11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md docs/ARCHITECTURE_AND_PHASES.md
uv run python scripts/check_current_docs.py
git diff --check
```

## Phase P2: Current Docs の構造を作り直す

goal:

```text
current docs の役割を分け、短い入口 doc と詳細 capability / historical log を分離する。
```

target_files:

```text
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/backtest/CURRENT_BACKTEST_FIRST_STATUS.md
docs/backtest/BACKTEST_FIRST_PIVOT_EXECUTION_LOG_2026-06-05.md
docs/backtest/README.md
docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md
docs/strategy_research_lab/11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md
```

tasks:

```text
P2-1 CURRENT_STATE rewrite:
  入口 doc として 100-150 lines 程度に短縮する。
  capability の長文列挙は `08_CURRENT_CAPABILITIES.md` にリンクする。
  runtime readiness と code surface を分けて書く。

P2-2 CODE_STATUS rewrite:
  実装済み surface と known gaps に絞る。
  generated artifact snapshot は current truth として持たせない。

P2-3 Backtest current status:
  `docs/backtest/CURRENT_BACKTEST_FIRST_STATUS.md` を新規作成する。
  baseline seed、Strategy Authoring backtest、Trade[XYZ] pure backtest、Bitget demo local smoke の関係を短く書く。

P2-4 Pivot execution log:
  長い pivot plan から実行記録を `BACKTEST_FIRST_PIVOT_EXECUTION_LOG_2026-06-05.md` に分離するか、少なくとも current summary を冒頭に置く。

P2-5 Strategy Authoring docs:
  `11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md` に baseline seed path と current verification を追加する。
  `08_CURRENT_CAPABILITIES.md` は capabilities の本体として維持する。
```

acceptance:

```text
1. `docs/CURRENT_STATE.md` は current truth の入口として短く読める。
2. `docs/CODE_STATUS.md` は実装状況に集中し、runtime readiness を混ぜすぎない。
3. backtest-first の現状を1文書で読める。
4. pivot plan の事前調査と実行済み状態を混同しない。
```

verification:

```bash
uv run python scripts/check_current_docs.py
uv run pytest -q tests/test_docs_current_truth.py
git diff --check
```

## Phase P3: Historical Docs の archive / label 化

goal:

```text
current truth と historical plan / log を分ける。移動は一括でやらず、リンク切れを確認しながら小さく行う。
```

target_files:

```text
plan/README.md
docs/archive/README.md
scripts/check_current_docs.py
docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md
docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
docs/TRADE_XYZ_REAL_DATA_COLLECTION_STATUS_APPENDIX_2026-06-01.md
docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md
plan/TRADE_XYZ_*.md
plan/marketlens_strategy_research_lab_migration_pack/
```

tasks:

```text
P3-1 no-move label:
  まず current 誤読が強い docs に historical label を入れる。
  特に filename が CURRENT_RECORD / NEXT_STEPS のものは冒頭で「現在の next action ではない」と書く。

P3-2 top-level plan archive:
  `plan/TRADE_XYZ_*` を `plan/archive/` へ移すか、plan/README.md で historical-only とさらに強調する。
  移動するなら link update と archive index update を同時に行う。

P3-3 migration pack:
  `plan/marketlens_strategy_research_lab_migration_pack/` は current VenueId とズレる。
  まず README に superseded banner を入れる。
  必要なら次の小タスクで `plan/archive/` へ移す。

P3-4 Trade[XYZ] collection docs:
  WS / quote coverage / collection runbook は historical collection docs として扱う。
  backtest-first path の current next action として読ませない。
```

acceptance:

```text
1. top-level plan docs が current implementation plan として読めない。
2. migration pack の `Literal["trade_xyz"]` が current contract として読めない。
3. Trade[XYZ] quote coverage docs が現在の主経路 next action として読めない。
4. archive 移動後に markdown/html link が壊れていない。
```

verification:

```bash
uv run python scripts/check_current_docs.py
rg -n 'checked 83|830 passed|repo の主軸|main venue path|execution_venue: Literal\["trade_xyz"\]' README.md docs/CURRENT_STATE.md docs/CODE_STATUS.md docs/backtest/README.md docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md docs/strategy_research_lab/11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md docs/ARCHITECTURE_AND_PHASES.md
rg -n 'execution_venue: Literal\["trade_xyz"\]' plan/README.md plan/marketlens_strategy_research_lab_migration_pack/README.md
git diff --check
```

2本目の `rg` は no-hit ではなく、historical / superseded label の説明行だけに限定されることを確認する。

## Phase P4: Final Verification

goal:

```text
docs cleanup が current truth を壊していないことを確認する。
```

verification commands:

```bash
uv run python scripts/check_current_docs.py
uv run pytest -q tests/test_docs_current_truth.py
git diff --check
./scripts/check
```

acceptance:

```text
1. current-docs checker が pass。
2. docs policy tests が pass。
3. `git diff --check` が pass。
4. full check を実行した場合は pass count と日時を docs に書きすぎず、必要なら final report にだけ記録する。
5. `git status --short --branch --untracked-files=all` で意図した docs / checker 変更だけが残る。
```

## 優先順位

最短で価値がある順:

```text
1. P1 current docs minimum update
2. P2 current docs structure rewrite
3. P3 historical docs label/archive
4. P4 final verification
```

避ける順:

```text
1. いきなり大量 archive 移動する。
2. `docs/CURRENT_STATE.md` にさらに長い capability 列挙を足す。
3. 古い pass count を別の古い pass count へ置き換えるだけで終わる。
4. Bitget configured を ready と書く。
5. Trade[XYZ] data readiness と Strategy Authoring baseline backtest を同じ ready として扱う。
```

## 完了条件

docs cleanup 全体の完了条件:

```text
1. current docs は backtest-first / venue-neutral pivot を明示している。
2. current docs は Trade[XYZ] を実装済み主要 venue / 将来候補として扱い、当面の注文口主軸としない。
3. current docs は VenueId trade_xyz / bitget_demo を反映している。
4. current docs は Bitget demo local smoke の限界を明示している。
5. current docs は baseline Strategy Authoring backtest の実行方法を示している。
6. historical plan / migration pack / collection logs は historical として読める。
7. checker と docs policy tests が pass する。
```
