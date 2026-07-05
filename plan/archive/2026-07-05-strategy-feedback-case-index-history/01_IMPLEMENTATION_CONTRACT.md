<!--
作成日: 2026-06-22_17:55 JST
更新日: 2026-06-22_18:36 JST
-->

# Implementation Contract

## 目的

Strategy Operations Workbench の post-MVP gap を、実行権限を増やさずに閉じる。

具体的には、既存の `strategy_runtime_observation_manifest.v1` と `strategy_learning_event.v1` から Strategy Input Contract 更新候補を作り、人間レビューで止める。その後、既存の `strategy_case_lite.v1` を複数 case で一覧化し、Static Workbench Viewer でレビューしやすくする。

この実装は alpha 証明、paper readiness、live readiness、account readiness、wallet readiness、exchange-write readiness を一切主張しない。

## 制約

- local/offline artifact workflow に限定する。
- network、credential、secret、account state、paper order、live order、wallet、signing、exchange write は扱わない。
- Strategy Input Contract の直接編集、自動 patch、自動適用を実装しない。
- Case Index は再生成可能な派生 artifact とし、DB registry、merge policy、conflict resolution を実装しない。
- Viewer は existing static HTML generation の改善に限定し、server UI や Svelte UI を実装しない。
- 既存 command / schema / docs の命名と boundary pattern を優先する。
- 新規または大きく編集する Python file は 800 行以下に保つ。

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
- source artifact は schema_version ごとの既存 model で読む。schema_version だけを文字列判定して中身を ad hoc に扱わない。
- `--source-contract` がない proposal は direct update candidate ではなく、source contract context が不足した review-only proposal として扱う。
- `--source-contract` がある場合は `StrategyInputContract` model で読む。contract 内の各 source file の存在、hash、column、timestamp 検査は既存 `strategy-input-contract-validate` の責務であり、この計画では暗黙に再実装しない。
- source contract の検査結果まで proposal に入れたい場合は、既存 `strategy_input_contract_validation.v1` artifact を別入力として明示追加する必要がある。この計画では追加しない。
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
- data-dir scan は `schema_version == "strategy_case_lite.v1"` の JSON だけを採用する。任意 JSON、viewer manifest、既存 index artifact を混ぜない。
- explicit `--case` は `StrategyCaseLite` model validation に通らない場合 fail する。data-dir scan は schema_version が違う JSON を無視してよいが、schema_version が `strategy_case_lite.v1` なのに壊れている JSON は fail する。
- 欠損 artifact は黙って無視せず、エラーまたは明示 status にする。

### P3: Static Workbench Viewer 改善

既存 `strategy-workbench-viewer-build` に `strategy_case_index.v1` summary を追加する。

成果物:

- Case index の `strategy_count`、`case_count`、latest status、open actions、blocked reasons、source hash を viewer で確認できる。
- compact summary の key は case index schema の既存フィールドから作る。permission 系 true flag が来た場合は permission として表示せず boundary violation として扱う。
- viewer manifest schema は現状 `summary: dict[str, Any]` なので、case index summary 追加だけなら `schemas/strategy_workbench_viewer.v1.schema.json` を広げる必要はない。manifest shape を変える場合だけ schema を更新する。

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
4. T2 と T4 は並列に進めてもよいが、`src/sis/cli.py` の登録差分は conflict しやすいので片方ずつ確認する。
5. current docs / CLI catalog 更新は、CLI help と schema が実装された後に行う。
6. 最後に `./scripts/check` を実行する。

## 成功条件

- `uv run sis --help` に新規 CLI が表示される。
- 新規 schema が pytest で検証される。
- Runtime Observation / Learning Event fixture から proposal artifact を生成できる。
- source contract なしの proposal が apply-ready と誤読されない。
- proposal review artifact は decision を持ち、direct apply を許可しない。
- 複数 case-lite artifact から case index を生成できる。
- data-dir scan が case-lite 以外の JSON を混ぜない。
- viewer が case index artifact を表示できる。
- current docs と CLI catalog が新規 surface を説明している。
- `./scripts/check` が通る。
