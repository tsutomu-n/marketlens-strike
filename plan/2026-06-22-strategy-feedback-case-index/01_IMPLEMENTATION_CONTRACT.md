<!--
作成日: 2026-06-22_17:55 JST
更新日: 2026-06-22_17:55 JST
-->

# Implementation Contract

## 目的

Strategy Operations Workbench の post-MVP gap を、実行権限を増やさずに閉じる。

具体的には、既存の `strategy_runtime_observation_manifest.v1` と `strategy_learning_event.v1` から Strategy Input Contract 更新候補を作り、人間レビューで止める。その後、既存の `strategy_case_lite.v1` を複数 case で一覧化し、Static Workbench Viewer でレビューしやすくする。

この実装は alpha 証明、paper readiness、live readiness、account readiness、wallet readiness、exchange-write readiness を一切主張しない。

## 実装スコープ

### P1: Strategy Input Feedback

Runtime Observation と Learning Event を Strategy Input Contract 更新候補へ変換する local artifact surface を追加する。

成果物:

- `strategy_input_contract_update_proposal.v1`
- `strategy_input_contract_update_review.v1`
- `strategy-input-feedback-proposal-build`
- `strategy-input-feedback-proposal-review`

必須境界:

- 既存 Strategy Input Contract を直接編集しない。
- 自動反映をしない。
- source artifact の hash / path / schema version を残す。
- boundary flags は常に false に固定する。
- live / wallet / signing / exchange write を許可しない。

### P2: Strategy Case Lite Index

複数の `strategy_case_lite.v1` を index artifact にまとめる。これは DB registry ではなく、既存 artifact を読む read-only index である。

成果物:

- `strategy_case_index.v1`
- `strategy-case-index-build`

必須境界:

- case artifact を上書きしない。
- case merge / conflict resolution / DB persistence を実装しない。
- index は再生成可能な派生成果物として扱う。
- 欠損 artifact は黙って無視せず、エラーまたは明示 status にする。

### P3: Static Workbench Viewer 改善

既存 `strategy-workbench-viewer-build` に `strategy_case_index.v1` summary を追加する。

成果物:

- Case index の `strategy_count`、`case_count`、latest status、open actions、blocked reasons、source hash を viewer で確認できる。

必須境界:

- static HTML viewer のままにする。
- サーバー、DB、Svelte UI、JS-heavy app へ広げない。
- viewer は source of truth ではなく表示 artifact のままにする。

## 実装しない範囲

- paper observation bridge の validation
- venue-specific network probe
- credential / secret handling
- order lifecycle
- production venue schema widening
- strategy optimizer / ML / LLM 自動改善
- Strategy Input Contract の自動 patch 生成または direct write
- Strategy Case full registry、検索 DB、UI timeline editor

## 依存関係

1. P1 schema / models が先。CLI と docs はその後。
2. P2 schema / models が先。CLI と viewer はその後。
3. P3 viewer 改善は P2 の artifact shape が確定してから行う。
4. current docs / CLI catalog 更新は、CLI help と schema が実装された後に行う。
5. 最後に `./scripts/check` を実行する。

## 成功条件

- `uv run sis --help` に新規 CLI が表示される。
- 新規 schema が pytest で検証される。
- Runtime Observation / Learning Event fixture から proposal artifact を生成できる。
- proposal review artifact は decision を持ち、direct apply を許可しない。
- 複数 case-lite artifact から case index を生成できる。
- viewer が case index artifact を表示できる。
- current docs と CLI catalog が新規 surface を説明している。
- `./scripts/check` が通る。
