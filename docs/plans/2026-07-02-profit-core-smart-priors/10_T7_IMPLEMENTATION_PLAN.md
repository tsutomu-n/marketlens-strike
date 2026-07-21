<!--
作成日: 2026-07-02_20:49 JST
更新日: 2026-07-02_20:49 JST
-->

# T7 Implementation Plan

## 結論

T7ではC9 authoring bridgeの `BRIDGED` を廃止せず、technical bridge statusであることをmanifestに明示する。economic gate、actual cash、paper/live readinessは未評価として固定し、default backtest packをcandidate proofと誤読させない。

## チェックポイントID

CP6 / PR #17 T7

## 目的

C9 bridgeをtechnical bridgeとeconomic gateに分け、candidate-scoped artifact生成の成功をprofit proofやactual cash readinessと誤読しないようにする。

## 現状

- `strategy-idea-candidates-authoring-bridge` は対応candidateに `BRIDGED` を出す。
- manifest summaryは `bridged_count` と `actual_cash_result_available=false` を持つが、technical/economicの境界が薄い。
- schemaはsummaryの追加keyを許容する一方、candidate objectは追加fieldを許容しない。
- `_authoring_spec()` は `min_trade_count: 0` と `pass_thresholds: {}` を使うため、economic gateは評価済みと扱えない。

## 制約

- 既存 `BRIDGED` statusをすぐ廃止しない。
- candidate object schemaを広げない。
- backtest executionやeconomic gate実装はしない。
- paper/live/wallet/signing/exchange writeは有効化しない。
- default example backtestやglobal outputをcandidate proofとして流用しない。

## 対象ファイル

新規:

- `docs/plans/2026-07-02-profit-core-smart-priors/10_T7_IMPLEMENTATION_PLAN.md`

変更:

- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- 必要なら `schemas/strategy_idea_candidate_authoring_bridge.v1.schema.json`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. manifest summaryに後方互換の追加keyを入れる。
2. `technical_bridged_count` は現行 `BRIDGED` countと同じにする。
3. `economic_gate_ready_count=0`、`economic_gate_not_evaluated_count=technical_bridged_count`、`actual_cash_ready_count=0`、`actual_cash_missing_count=candidate_count` を保存する。
4. `bridge_success_semantics="technical_only"`、`bridged_status_semantics="technical_bridge_only_not_profit_proof"` を保存する。
5. `min_trade_count: 0` または `pass_thresholds: {}` が出るC9 v0は `economic_gate_status="NOT_EVALUATED"` と明示する。
6. candidate-scoped path/hashを壊さない。既存 artifacts mapは維持する。
7. source manifestにも `bridge_success_semantics` と economic/actual-cash boundaryを入れる。
8. docs glossaryにC9 `BRIDGED` のtechnical-only境界を追記する。

## 実装手順

1. RED: `tests/strategy_idea_candidates/test_authoring_bridge.py` にmanifest summary/source manifest assertionsを足す。
2. GREEN: `authoring_bridge.py` のsummaryとsource manifest生成を拡張する。
3. GREEN: glossary docsを更新する。
4. VERIFY: focused test、schema validation、docs check、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
uv run pytest tests/strategy_idea_candidates/test_bitget_public_source.py -q
uv run ruff check src/sis/strategy_idea_candidates/authoring_bridge.py tests/strategy_idea_candidates/test_authoring_bridge.py
uv run ruff format --check src/sis/strategy_idea_candidates/authoring_bridge.py tests/strategy_idea_candidates/test_authoring_bridge.py
uv run ty check src/sis/strategy_idea_candidates/authoring_bridge.py --python-version 3.13 --output-format concise
uv run pyrefly check src/sis/strategy_idea_candidates/authoring_bridge.py
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## 完了条件

- `BRIDGED` がprofit proofではなくtechnical bridge statusだとmanifestに保存される。
- `technical_bridged_count`、`economic_gate_ready_count`、`economic_gate_not_evaluated_count`、`actual_cash_ready_count`、`actual_cash_missing_count`、`bridge_success_semantics` がsummaryに保存される。
- `min_trade_count: 0` と `pass_thresholds: {}` の場合、economic gateは `NOT_EVALUATED` と明記される。
- candidate-scoped artifacts path/hash入力参照が失われない。
- default example backtestをcandidate proofとして流用しない。

## 失敗条件

- `BRIDGED` をeconomic pass、profit proof、paper/live readinessとして扱う。
- candidate status enumを不用意に変えて既存互換を壊す。
- schemaを広げすぎて後段の互換性を落とす。
- backtest結果を読んでprofit判定を始める。

## 影響範囲

C9 authoring bridge manifest summary、candidate source manifest、glossary docs、focused testsのみ。

## ロールバック方針

T7追加summary/source manifest fields、test assertions、glossary追記、plan docを戻す。

## 代替案

- 代替案A: `BRIDGED_TECHNICAL_ONLY` をcandidate statusへ追加する。schema更新と既存期待値の変更が大きく、T7では過剰。
- 代替案B: economic gateをこのtaskで実装する。PR #17の後続gateと責任が混ざるため不採用。
- 採用案: status互換維持 + summary/source manifestでtechnical-only境界を明示する。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。既存 `BRIDGED` consumerはそのまま動く。

## 批判レビュー1

- `BRIDGED_TECHNICAL_ONLY` を今入れるとschema、tests、downstream consumerの変更が広がる。T7の目的は誤読防止なので、summaryのsemantic明示で足りる。
- `economic_gate_ready_count` を `bridged_count` と同じにすると、`min_trade_count: 0` / `pass_thresholds: {}` の現実と矛盾する。
- actual cashはこのbridgeでは存在しない。`actual_cash_missing_count` は全candidate countで固定する。

## 批判レビュー2

- source manifestだけに境界を書くと、manifest summaryだけ読む後段が誤読する。summaryとsource manifestの両方に書く。
- docsだけの修正では runtime artifactが変わらないため不十分。manifest JSONへの保存をテストする。
- path/hashの保持は既存仕様の要なので、candidate_set/export_manifest/ledger path/hashには触らない。
