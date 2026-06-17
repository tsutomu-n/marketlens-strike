<!--
作成日: 2026-06-15_07:23 JST
更新日: 2026-06-17_22:30 JST
-->

# Code-Truth Documentation Checklist 2026-06-15

このチェックリストは 2026-06-15_07:23 JST 時点で、コード、CLI、schema、tests、current-doc checker を正として、現行 docs / plan / 資料 を分類する。

## 確認した正本

確認コマンド:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run python scripts/check_current_docs.py
rg --files schemas tests src/sis/backtest src/sis/research/ndx src/sis/research/strategy_lifecycle src/sis/venues
```

確認したコード側の事実:

- `uv run sis --help` で NDX Layer 2.2 から 2.8、Strategy Lifecycle、Strategy Backtest pack、Trade[XYZ] collector / readiness / phase gate 系 command が登録済み。
- `src/sis/venues/ids.py` の `VenueId` は `trade_xyz`, `bitget_demo`。
- `schemas/strategy_signal.v1.schema.json`, `schemas/trade_candidate.v1.schema.json`, `schemas/paper_intent_preview.v1.schema.json` の `execution_venue` も `trade_xyz`, `bitget_demo`。
- `schemas/evaluation_plan.mls.v1.schema.json` の `target_venue` は `trade_xyz` 固定。
- `src/sis/venues/capabilities.py` は `bitget_futures`, `hyperliquid_perp` を catalog known だが schema / paper / network / live disabled として扱う。
- `src/sis/research/ndx/` と `tests/research/` は Layer 2.3 から Layer 2.8 までの local research / paper-observation gate を持つ。
- `src/sis/backtest/`、`schemas/strategy_backtest_*.schema.json`、`tests/strategy_authoring/test_backtest_*.py` は backtest pack、validation、optional framework surface を持つ。
- `pyproject.toml` は Python `>=3.13,<3.14`、optional extras `vectorbt==1.0.0`, `bt==1.2.0`, `empyrical-reloaded==0.5.12`, `quantstats==0.0.81` を持つ。
- 調査開始時点の `scripts/check_current_docs.py` の current-doc 対象は 117 docs。本書と 2026-06-09 NDX/QQQ venue suitability audit を allowlist に追加した後の検証対象は 119 docs。2026-06-17_22:02 JST には古い audit を `docs/archive/2026-06-17-doc-routing/` へ移し、current-doc checker から外した。

## 追加調査で見つけた抜けと修正

- [x] 2026-06-09 NDX/QQQ venue suitability audit は `README.md` の read-first に出るが、`scripts/check_current_docs.py` の単体 allowlist には入っていなかった。
  - 修正: `scripts/check_current_docs.py` の allowlist と `docs/DOCS_LINT_POLICY_2026-05-30.md` の strict check 一覧へ追加した。
  - 後続処置: 2026-06-17_22:02 JST に `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md` へ移し、current-doc checker から外した。
  - 残る注意: 文書内の `946 passed` は 2026-06-09 時点の historical snapshot。current pass count として再利用しない。
- [x] `docs/DOCS_LINT_POLICY_2026-05-30.md` の strict check 一覧が、今回追加した current audit と NDX/QQQ venue suitability audit を含んでいなかった。
  - 修正: strict check 一覧を更新した。
- [x] `plan/archive/2026-06-17-plan-routing/0609ここからの計画/01_ndx_qqq_venue_suitability_gate/` は README 上で implemented at HEAD と書いているが、`plan/README.md` ではまだ current plan 扱いだった。
  - 修正済み: `plan/README.md` では implemented / historical に移し、2026-06-17_22:13 JST に archive へ移動した。
- [x] `plan/archive/2026-06-17-plan-routing/0609ここからの計画/02_bitget_hyperliquid_venue_design_gate/` と `plan/0609ここからの計画/03_venue_read_only_capability_probe/` の扱いが曖昧だった。
  - 追加確認: `02` は `src/sis/venues/capabilities.py`, `docs/venues/bitget_hyperliquid_capability_gate.md`, `tests/test_venue_capabilities.py` と focused tests で実装済み相当。
  - 追加確認: `03` が要求する `src/sis/venues/read_only_probe.py`, `schemas/venue_read_only_probe_summary.v1.schema.json`, `venue-read-only-probe` CLI, `tests/test_venue_read_only_probe*.py`, `docs/venues/read_only_capability_probe.md` は存在しない。
  - 修正済み: `plan/README.md` では `02` を implemented / historical、`03` を current unimplemented implementation handoff として分けた。2026-06-17_22:13 JST に `02` は archive へ移動し、`03` は root `plan/` 側に残した。
- [x] `plan/archive/2026-06-17-plan-routing/0610ここからの計画/01_grok_architecture_adoption_review/` は docs-only review plan としては有用だが、内部に Layer 2.4 が `REVISE_2_3` で止まる前提が残る。
  - 修正済み: current architecture guidance ではなく historical external-review decision として archive へ移動した。

## 更新できるドキュメント

現行コードと大きく矛盾しない。更新するなら最新の確認結果、読み順、短文化、リンク追記を足す。

- [x] `docs/CURRENT_STATE.md`
  - 理由: Layer 2.2-2.8、backtest pack、venue boundary、paper-only boundary は現行コードと概ね一致する。
  - 更新済み: 2026-06-17_22:22 JST に Runtime snapshot の固定値を増やさず、長い capability 列挙を専用 docs に寄せた。
- [ ] `docs/CODE_STATUS.md`
  - 理由: CLI / schema / tests の implemented surface は現行コードと概ね一致する。
  - 更新案: migration PR 表、post-PR status、runtime snapshot を分けて読みやすくする。
- [ ] `docs/research/ndx/README.md`
  - 理由: Layer 2.2-2.8 の command flow と `APPROVE_STRATEGY_LAB_EXPORT` 境界が現行に合う。
  - 更新案: paper observation 系の operator runbook 導線を `docs/strategy_lifecycle/` と相互リンクする。
- [ ] `docs/research/ndx/09_LLM_REVIEW_GATE.md` から `docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md`
  - 理由: current-doc checker 対象で、CLI / schema / tests の実装面と対応している。
  - 更新案: 各 layer の「許可しないこと」を短い共通表に寄せる。
- [ ] `docs/backtest/README.md`
  - 理由: Trade[XYZ] pure backtest、Strategy Authoring fixed-horizon、legacy bridge、pack surface の読み分けとして現行導線になる。
  - 更新案: `BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md` の R0-R10 実装開始条件を冒頭から見える位置に置く。
- [ ] `docs/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md`
  - 理由: HANDOFF 上も実装未開始の coder-ready plan。コード変更前の実装契約として有効。
  - 更新案: R0 baseline 実行後に結果だけ追記する。R1 以降の仕様を先に広げない。
- [x] `docs/archive/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
  - 理由: optional extras、qstrader の isolated runner 候補、standard pack boundary は historical record としては有用だが、current root からは archive 済み。
  - 実施済み: current 技術正本は `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` と `docs/backtest/README.md` へ寄せ、旧 detail doc は archive 配下に固定した。
- [x] `docs/strategy_research_lab/README.md` と `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md`
  - 理由: Strategy Authoring / Strategy Lab の主要 capability 入口として現行コード面と対応する。
  - 実施済み: 2026-06-17_22:30 JST に `08_CURRENT_CAPABILITIES.md` を短い入口にし、詳細列挙を `08_CURRENT_CAPABILITIES_DETAILS.md`、strategy type matrix を `13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md` へ分けた。
- [ ] `docs/strategy_lifecycle/README.md`, `docs/strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md`, `docs/strategy_lifecycle/TARGET_OPERATING_MODEL.md`
  - 理由: `strategy-backtest-acceptance`, `strategy-paper-observation-cycle`, `strategy-lifecycle-review` の実装と対応する。
  - 更新案: NDX Layer 2.6-2.8 docs との読み順を明示する。
- [ ] `docs/venues/bitget_hyperliquid_capability_gate.md`
  - 理由: `bitget_futures` / `hyperliquid_perp` が catalog-only disabled である現行コードと合う。
  - 更新案: `src/sis/venues/capabilities.py` と schema enum の確認コマンドを追加する。
- [x] `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md`
  - 理由: NDX/QQQ paper-path fail-closed 境界、`VenueId`、catalog-only venues の内容は現行コードと概ね合う。
  - 後続処置: 2026-06-17_22:02 JST に historical audit として archive へ移した。
- [ ] `docs/OPERATIONS_RUNBOOK.md`
  - 理由: operator command の入口として使える。
  - 更新案: domain 別 runbook へ分割し、root は command index にする。
- [ ] `docs/ARCHITECTURE_AND_PHASES.md`
  - 理由: current architecture / boundary summary として現行コードに概ね合う。
  - 更新案: NDX Layer 2.5-2.8 と Strategy Lifecycle の境界を図ではなく表で短くする。

## 古い内容があるドキュメント

現行コード・current state と食い違う記述がある。内容を直すか、historical と明記する。

- [ ] `README.md`
  - 古い内容: `README.md` は Layer 2.3/2.4 の default fixture が `REVISE_2_3` で止まると書いていた。
  - コード正本: `docs/CODE_STATUS.md` と `docs/CURRENT_STATE.md` は現行 default を `APPROVE_STRATEGY_LAB_EXPORT` とし、`src/sis/research/ndx/` / `tests/research/test_ndx_layer24_residual_validation.py` が Layer 2.4 gate を実装済み。
  - 修正済み: 2026-06-15_12:02 JST に Layer 2.5-2.8 flow、current local documentation snapshot、本チェックリストへの read-first link を追加した。
- [ ] `plan/README.md`
  - 古い内容: 移動前の 0610/02 と 0611/* を current implementation plan として扱っていた。
  - コード正本: `research-ndx-strategy-lab-export`, `research-ndx-paper-observation-gate`, `research-ndx-operator-promotion`, `research-ndx-paper-observation-review`, `strategy-backtest-acceptance`, `strategy-paper-observation-cycle`, `strategy-lifecycle-review` は CLI 登録済みで、対応 code/schema/tests/docs がある。
  - 修正済み: 2026-06-15_12:02 JST に implemented / historical と current unimplemented plan を分け、2026-06-17_22:13 JST に実装済み plan を `plan/archive/2026-06-17-plan-routing/` へ移動した。
- [x] `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md`
  - 古い内容: 2026-06-09 時点の監査として Layer 2.4 default を `REVISE_2_3`、current-doc count を 101、pytest pass count を 936 と記録している。
  - コード正本: 2026-06-15 時点の current-doc checker は 117 docs。現行 docs/code は Layer 2.4 default を `APPROVE_STRATEGY_LAB_EXPORT` と扱う。
  - 修正済み: `docs/archive/2026-06-17-doc-routing/` へ移動。新しい current audit は `docs/DOCUMENT_AUDIT_2026-06-17_CODE_TRUTH_CHECKLIST.md` を使う。
- [x] `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md`
  - 古い内容: verification に `946 passed` など 2026-06-09 時点の固定 pass count がある。
  - コード正本: pass count は固定せず、`./scripts/check` と `uv run python scripts/check_current_docs.py` を再実行する。
  - 修正済み: `docs/archive/2026-06-17-doc-routing/` へ移動。
- [x] `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md`
  - 古い内容: current-doc count 81 など、当時の snapshot が残る。
  - コード正本: current-doc checker は 117 docs。backtest surface は 2026-06-14 以降さらに pack / optional extras / responsibility plan まで進んでいる。
  - 修正済み: historical backtest update audit として `docs/archive/2026-06-17-doc-routing/` へ移動。
- [x] `docs/archive/2026-06-17-doc-routing/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md`
  - 古い内容: 2026-05-29 時点の blocker decomposition。
  - コード正本: 現行は phase gate / execution drift / Strategy Lifecycle / NDX paper observation の境界が増えている。
  - 修正済み: current blocker plan として更新せず、historical live-readiness plan として `docs/archive/2026-06-17-doc-routing/` へ移動。
- [ ] `docs/DOCS_LINT_POLICY_2026-05-30.md`
  - 古い内容: strict check 対象一覧が今回追加した audit docs を含んでいなかった。
  - 修正済み: 本追加調査で `docs/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md` と 2026-06-09 NDX/QQQ venue suitability audit を追加した。
  - 後続処置: 2026-06-17_22:02 JST に古い audit を archive へ移し、strict check 対象から外した。
  - 残る注意: 今後 current docs を追加する時は checker と policy を同時更新する。
- [ ] `docs/algo/**` と `docs/algo/obsidian_note_rewrites_2026-05-29/**`
  - 古い内容: strategy idea / source-note 系は外部ライブラリや市場文脈の古い記述を含む可能性がある。
  - コード正本: repo 実装面は Strategy Lab / Strategy Authoring / backtest artifacts。外部調査メモは current implementation proof ではない。
  - 修正案: code-linked guide と source/research note を分け、`docs/algo/README.md` から「実装済み」と「研究素材」を明示する。

## 作り直したほうがいいドキュメント

単純更新より、役割を分割した方が保守しやすい。

- [x] `docs/CURRENT_STATE.md`
  - 理由: current state、capability catalog、runtime snapshots、known gaps が一文書に積み上がっている。
  - 実施済み: 2026-06-17_22:22 JST に `CURRENT_STATE.md` を 1 ページ寄りの index にし、詳細は backtest / NDX / Strategy Lab / operations docs へ分割した。
- [ ] `docs/CODE_STATUS.md`
  - 理由: PR migration history、implemented surface、operational interpretation、known gaps、verification snapshot が混在している。
  - 作り直し案: `IMPLEMENTED_SURFACES.md` と `KNOWN_BOUNDARIES.md` に分ける。
- [ ] `docs/OPERATIONS_RUNBOOK.md`
  - 理由: Trade[XYZ] collection、NDX research gates、Strategy Lifecycle、paper operations、long-running script 運用が同居している。
  - 作り直し案: root operator index + domain runbooks に分割する。
- [x] `docs/archive/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
  - 理由: framework evaluation、operator recipe、optional extras、historical smoke、future candidates が長大に混ざっていた。
  - 実施済み: archive 配下に固定済み。current 技術正本は `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` と `docs/backtest/README.md`。
- [x] `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md`
  - 理由: capability の列挙が大きく、更新漏れリスクが高い。
  - 実施済み: 2026-06-17_22:30 JST に operator-facing short guide と `08_CURRENT_CAPABILITIES_DETAILS.md` に分離。schema-driven matrix は `13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md` を使用する。
- [ ] `docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md`
  - 理由: Layer 2.2 実装記録に後続 layer の条件や履歴が追記されやすい。
  - 作り直し案: Layer 2.2 の historical record に固定し、Layer 2.3 以降は個別 records に分ける。
- [ ] `docs/trade_xyz_bot_beginner_guide.html`
  - 理由: README の read-first に入る初心者向け HTML だが、current venue suitability、NDX/QQQ fail-closed、Strategy Lifecycle、backtest-first 境界まで体系的に読むには古い。
  - 作り直し案: Markdown 正本を作ってから HTML を再生成する。旧 HTML は archive へ回す。
- [ ] `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html`
  - 理由: Markdown companion HTML で、Markdown 側を更新した時に同期漏れしやすい。
  - 作り直し案: `08_CURRENT_CAPABILITIES.md` を正本にし、HTML は生成物または明示 companion として更新手順を持たせる。

## 削除・アーカイブしてもよいドキュメント

削除より archive 推奨。過去判断の証跡として残し、current truth から外す。

- [x] `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md`
  - 推奨: `docs/archive/` へ移動。
  - 理由: Layer 2.4 `REVISE_2_3` snapshot と current-doc count が現行とズレる。
- [x] `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md`
  - 推奨: `docs/archive/` へ移動。
  - 理由: backtest docs の歴史資料として有用だが、現行 backtest pack / responsibility plan の正本ではない。
- [x] `docs/archive/2026-06-17-doc-routing/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md`
  - 推奨: `docs/archive/` へ移動。
  - 理由: current live-readiness boundary は `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, `docs/OPERATIONS_RUNBOOK.md`, runtime phase-gate artifacts を正とする。
- [x] `plan/archive/2026-06-17-plan-routing/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/`
  - 推奨: `plan/archive/` へ移動。
  - 理由: Layer 2.5 は実装済み。current proof は code/schema/tests/CLI/docs。
- [x] `plan/archive/2026-06-17-plan-routing/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/`
  - 推奨: `plan/archive/` へ移動。
  - 理由: Layer 2.6 / 2.7 は実装済み。current proof は code/schema/tests/CLI/docs。
- [x] `plan/archive/2026-06-17-plan-routing/0611ここからの計画/02_strategy_lifecycle_control_plane/`
  - 推奨: `plan/archive/` へ移動。
  - 理由: Strategy Lifecycle control plane は CLI / schema / tests / docs が実装済み。
- [x] `plan/archive/2026-06-17-plan-routing/0611ここからの計画/03_paper_observation_cycle_completion/`
  - 推奨: `plan/archive/` へ移動。
  - 理由: Paper observation cycle / review 系は実装済み。
- [x] `plan/archive/2026-06-17-plan-routing/0609ここからの計画/01_ndx_qqq_venue_suitability_gate/`
  - 推奨: `plan/archive/` へ移動。
  - 理由: README 自体が implemented at HEAD と記録しており、current proof は code/schema/tests/CLI/docs。
- [x] `plan/archive/2026-06-17-plan-routing/0609ここからの計画/02_bitget_hyperliquid_venue_design_gate/`
  - 推奨: `plan/archive/` へ移動。
  - 理由: capability contract は `src/sis/venues/capabilities.py`, `docs/venues/bitget_hyperliquid_capability_gate.md`, `tests/test_venue_capabilities.py` で実装済み。focused tests も通る。
- [x] `plan/archive/2026-06-17-plan-routing/0610ここからの計画/01_grok_architecture_adoption_review/`
  - 推奨: historical docs-only review として archive または `plan/README.md` 上で historical に分類。
  - 理由: external suggestion review として有用だが、Layer 2.4 `REVISE_2_3` 前提が古い。
- [ ] `plan/0609ここからの計画/03_venue_read_only_capability_probe/`
  - 推奨: 削除・archive しない。current unimplemented plan として残す。
  - 理由: 計画が要求する module/schema/CLI/tests/docs が現行コードに存在しない。
- [ ] `資料/`
  - 推奨: active docs からは外し、必要なものだけ `docs/archive/` または `docs/algo/` に取り込む。
  - 理由: current-doc checker 対象外で、コード正本との同期保証がない。調査素材としては有用だが current requirements ではない。
- [ ] `docs/archive/**` と `plan/archive/**`
  - 推奨: そのまま archive 維持。
  - 理由: current proof ではないが、過去判断の証跡として有用。

## 先に直す順番

1. [x] `README.md` の Layer 2.4 / 2.5-2.8 current flow を修正する。
2. [x] `plan/README.md` の current implementation plan 分類を現行コードに合わせる。特に 0609/0610/0611 の実装済み plan を historical/superseded に分け、2026-06-17_22:13 JST に archive へ移動する。
3. [ ] `docs/DOCS_LINT_POLICY_2026-05-30.md` と `scripts/check_current_docs.py` の allowlist を今後も同期する。
4. [x] `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md`, `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md`, `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` を historical と明記するか archive する。
5. [x] `docs/CURRENT_STATE.md` / `docs/CODE_STATUS.md` の肥大化を分割計画に落とす。`CODE_STATUS.md` は thin index 済み、`CURRENT_STATE.md` は 2026-06-17_22:22 JST に index 化済み。
6. [x] `docs/archive/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md` は archive 済み、Strategy Lab capability docs は 2026-06-17_22:30 JST に短文化する。

## 残リスク

- この調査では `./scripts/check` は実行していない。重い full gate は docs 分類保存には必須ではないが、archive / README 修正後は実行する。
- `data/` 配下の runtime artifact は git-ignored であり、今回の分類では現 checkout の artifact freshness を正本にしていない。
- `資料/` は素材量が多いため、個別ファイルの正誤までは未分類。current-doc checker 対象外として一括で archive / source material 扱いにした。
- `plan/archive/2026-06-17-plan-routing/0609ここからの計画/02_bitget_hyperliquid_venue_design_gate/` は実装済み相当として archive 済み、`plan/0609ここからの計画/03_venue_read_only_capability_probe/` は未実装 current plan として分類済み。未実装の `03` は削除・archive しない。
