<!--
作成日: 2026-06-22_20:20 JST
更新日: 2026-06-22_20:24 JST
-->

# Local Dogfood Loop 04 Case Lite Backtest Artifact Results

## 結論

Loop 04 では、Loop 03 で出た分岐「`trend_pullback_user_v1` を Case Lite / Case Index に接続するには、runtime observation を用意すべきか、Case Lite に backtest-only support を足すべきか」を現実的に見直した。

結果:

- Case Lite の service は、既に未知 schema を `generic` artifact として扱える設計だった。
- ただし CLI に任意 JSON artifact を渡す option がなかった。
- `strategy_case_lite.v1` schema には `generic` が既に存在した。
- そのため、最小実装として `strategy-case-lite-update --artifact` を追加した。
- さらに、今回使う known schema を typed artifact として記録できるように artifact type を追加した。
- `trend_pullback_user_v1` の backtest-only artifacts を Case Lite に入れ、Case Index まで生成した。
- Viewer も Case Lite / Case Index を含む `artifact_count=9` 版に更新した。
- boundary violation は `0`、paper execution / live / wallet / signing / exchange write はすべて `false`。

この実装は、Case Lite を「なんでも registry」にするものではない。既存の軽量 timeline 仕様に、任意JSONの読み取り入口を足しただけで、実行や承認は発生しない。

## 用語の言い換え

- `--artifact`: 追加のJSONファイルをCase Liteに入れるためのCLI option。
- `typed artifact`: schema version から種類を判定できる artifact。
- `generic`: schema version が未知、または型付け未対応の artifact。
- `Case Index`: Case Lite を集めて戦略別に探しやすくする読み取り index。DBではない。

## 1. 計画

目的:

1. Case Lite に backtest-only artifact を入れる実装が責務を広げすぎないか確認する。
2. 最小変更で `trend_pullback_user_v1` を Case Lite / Case Index へ通す。
3. runtime observation を偽造しない。
4. paper / live permission を発生させない。

採用した方針:

- 新しい backtest 専用 workflow は作らない。
- Case Lite service の既存 `generic` 経路を活かす。
- CLI に `--artifact` を足す。
- よく使う known schema だけ artifact type として追加する。
- Case Lite / Case Index の boundary は既存通り `false` 固定にする。

採用しなかった方針:

- `trend_pullback_user_v1` 用の runtime observation を paper session から作る。
- `ndx_open_gap_residual_v1` の paper evidence を流用する。
- Case Lite を DB registry にする。
- backtest PASS を paper / live readiness と見なす。

## 2. 現実チェック

### 2.1 コードの現実

確認したファイル:

- `src/sis/strategy_case_lite/models.py`
- `src/sis/strategy_case_lite/service.py`
- `src/sis/commands/strategy_case_lite.py`
- `schemas/strategy_case_lite.v1.schema.json`
- `tests/strategy_case_lite/`
- `docs/strategy_case_lite/README.md`

分かったこと:

- `StrategyCaseArtifactType` には既に `GENERIC = "generic"` がある。
- `_artifact_type_for()` は unknown schema を `GENERIC` に落とす。
- `build_strategy_case_lite()` は artifact path の list を受け取り、source path / sha256 / schema / status / action / blocked reason を timeline 化する。
- CLI は named option の artifact だけを raw paths に入れており、任意 artifact を受け取る口がなかった。

実装判断:

- schema と service に既に一般化の足場があるため、CLI `--artifact` は自然な最小拡張。
- typed artifact を追加しないと複数 unknown artifact が `generic` に潰れて `latest_source_hashes` が読みにくい。
- そのため、今回使う known schema は enum / schema mapping に追加した。

### 2.2 追加した artifact type

追加した artifact type:

| schema_version | artifact_type |
|---|---|
| `strategy_input_contract_validation.v1` | `strategy_input_contract_validation` |
| `strategy_authoring_backtest_result.v1` | `strategy_authoring_backtest_result` |
| `strategy_backtest_pack.v1` | `strategy_backtest_pack` |
| `strategy_backtest_pack_validation.v1` | `strategy_backtest_pack_validation` |
| `strategy_backtest_suite_result.v1` | `strategy_backtest_suite_result` |
| `strategy_backtest_comparison.v1` | `strategy_backtest_comparison` |
| `strategy_review_manifest.v1` | `strategy_review_manifest` |

### 2.3 status extraction の補正

`strategy_review_manifest.v1` は `review_status` を持つ。既存の Case Lite status 抽出は `review_status` を見ていた。

今回、追加で `status` も見るようにした。理由は、Viewer や他の artifact では top-level `status` を持つものがあるためである。

この変更は read-only status extraction であり、permission や action を変えない。

## 3. 実装

### 3.1 変更ファイル

コード:

- `src/sis/strategy_case_lite/models.py`
- `src/sis/strategy_case_lite/service.py`
- `src/sis/commands/strategy_case_lite.py`

schema:

- `schemas/strategy_case_lite.v1.schema.json`

tests:

- `tests/strategy_case_lite/test_strategy_case_lite.py`
- `tests/strategy_case_lite/test_strategy_case_lite_cli.py`

docs:

- `docs/strategy_case_lite/README.md`

### 3.2 CLI surface

追加:

```bash
uv run sis strategy-case-lite-update --artifact <json-path>
```

help 表示で `--artifact` が出ることを確認した。

### 3.3 実データで Case Lite 生成

実行:

```bash
uv run sis strategy-case-lite-update \
  --strategy-id trend_pullback_user_v1 \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json \
  --artifact data/research/strategy_backtest_metrics.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --artifact data/research/backtest_suite/strategy_backtest_suite_result.json \
  --artifact data/research/backtest_compare/strategy_backtest_comparison.json \
  --artifact data/strategy_reviews/dogfood-operator-current/review_manifest.json \
  --out data/local_dogfood/2026-06-22-trend-pullback/strategy_cases \
  --case-id trend_pullback_user_v1-backtest-dogfood \
  --replace-existing
```

結果:

- status: `pass`
- case_id: `trend_pullback_user_v1-backtest-dogfood`
- strategy_id: `trend_pullback_user_v1`
- latest_status: `READY_FOR_HUMAN_REVIEW`
- artifact_count: `7`
- paper_execution_allowed: `false`
- live_allowed: `false`

生成物:

```text
data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json
data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.md
```

timeline:

| artifact_type | status | path |
|---|---|---|
| `strategy_input_contract_validation` | `PASS` | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json` |
| `strategy_authoring_backtest_result` | n/a | `data/research/strategy_backtest_metrics.json` |
| `strategy_backtest_suite_result` | n/a | `data/research/backtest_suite/strategy_backtest_suite_result.json` |
| `strategy_backtest_comparison` | n/a | `data/research/backtest_compare/strategy_backtest_comparison.json` |
| `strategy_backtest_pack` | n/a | `data/research/backtest_pack/strategy_backtest_pack.json` |
| `strategy_backtest_pack_validation` | `PASS` | `data/research/backtest_pack/strategy_backtest_pack_validation.json` |
| `strategy_review_manifest` | `READY_FOR_HUMAN_REVIEW` | `data/strategy_reviews/dogfood-operator-current/review_manifest.json` |

### 3.4 実データで Case Index 生成

実行:

```bash
uv run sis strategy-case-index-build \
  --case data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json \
  --out data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index \
  --index-id trend-pullback-local-dogfood-index \
  --replace-existing
```

結果:

- status: `pass`
- index_id: `trend-pullback-local-dogfood-index`
- case_count: `1`
- strategy_count: `1`
- latest_status: `READY_FOR_HUMAN_REVIEW`
- paper_execution_allowed: `false`
- live_allowed: `false`
- db_persistence_allowed: `false`

生成物:

```text
data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json
data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.md
```

### 3.5 Viewer 更新

実行:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json \
  --artifact data/research/strategy_backtest_metrics.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --artifact data/research/backtest_suite/strategy_backtest_suite_result.json \
  --artifact data/research/backtest_compare/strategy_backtest_comparison.json \
  --artifact data/strategy_reviews/dogfood-operator-current/review_manifest.json \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json \
  --out data/local_dogfood/2026-06-22-trend-pullback/viewer \
  --viewer-id trend-pullback-local-dogfood-viewer \
  --replace-existing
```

結果:

- status: `pass`
- artifact_count: `9`
- boundary_violation_count: `0`
- paper_execution_allowed: `false`
- live_allowed: `false`
- wallet_used: `false`
- signing_used: `false`
- exchange_write_used: `false`

生成物:

```text
data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html
data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json
```

## 4. 完了条件

Loop 04 は次を満たした。

- Case Lite の backtest-only artifact support を最小実装した。
- CLI `--artifact` を追加した。
- known backtest / review / input validation schema を typed artifact として扱えるようにした。
- schema と docs を更新した。
- tests を追加した。
- `trend_pullback_user_v1` を Case Lite / Case Index / Viewer まで通した。
- paper execution、live execution、wallet、signing、exchange write、DB persistence は許可していない。

## 5. 残った現実的な課題

1. `trend_pullback_user_v1` の runtime observation はまだない。
   - 影響: drift review、learning event、Input Feedback proposal はまだ作れない。
   - 進める絶対条件: trend と明確に紐づく paper observation session か runtime observation を用意すること。

2. backtest-only Case Lite は operational progress ではない。
   - 影響: latest_status が `READY_FOR_HUMAN_REVIEW` でも、paper / live readiness ではない。
   - 進める絶対条件: paper/runtime evidence を別途用意し、drift / learning route に入ること。

3. `--artifact` は便利だが、入れすぎると Case Lite が読みづらくなる。
   - 影響: artifact dump になると、timeline の意味が薄くなる。
   - 運用条件: strategy の判断に関係する主要 artifact に絞ること。

4. Viewer は YAML contract を直接表示しない。
   - 影響: contract 本体は validation JSON か source path から辿る必要がある。
   - 進める条件: Viewer の YAML support を別途実装するか、現運用を許容すること。

## 6. 次ループ案

### 推奨: Loop 05 は Strategy Input Feedback の「backtest-onlyでは提案を作らない」境界を補強する

状態:

- 実行済み。結果は [14_LOCAL_DOGFOOD_LOOP_05_INPUT_FEEDBACK_BOUNDARY_RESULTS.md](14_LOCAL_DOGFOOD_LOOP_05_INPUT_FEEDBACK_BOUNDARY_RESULTS.md) を読む。

理由:

- 今回、backtest-only artifact は Case Lite / Case Index に通せるようになった。
- 一方で Input Feedback proposal は runtime observation または learning event を要求する。
- この境界は正しいが、利用者が backtest-only Case Lite を見て「Input Feedback も作れる」と誤読する可能性がある。

実行候補:

1. `docs/strategy_input_feedback/README.md` と plan docs に、backtest-only Case Lite は Input Feedback proposal の入力ではないと明記する。
2. 必要なら CLI error text / help を確認し、すでに十分なら docs のみ更新する。
3. その後、`trend_pullback_user_v1` で Input Feedback proposal に進めない理由を current plan に明示する。

この loop はコード変更なしで済む可能性が高い。コード変更が必要かは、現行 CLI help / error の確認後に判断する。
