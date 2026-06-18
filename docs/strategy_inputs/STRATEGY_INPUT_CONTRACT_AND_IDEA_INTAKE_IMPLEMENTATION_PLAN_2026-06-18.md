<!--
作成日: 2026-06-18_21:45 JST
更新日: 2026-06-18_23:11 JST
-->

# Strategy Input Contract And Idea Intake Implementation Plan

## 結論

この文書の実装 slice は、`Strategy Input Contract` と `Idea Intake` の first gate である。

この計画を読んだ coder は、次を実装完了できる粒度で進める。

```text
1. strategy_input_contract.v1
2. strategy_input_contract_validation.v1
3. strategy_idea.v1
4. strategy_intake_decision.v1
5. strategy-input-contract-validate CLI
6. strategy-intake-validate CLI
7. strategy-review-build への optional source artifact 接続
8. docs / tests / schemas / CLI help の整合
```

これは完成形全体の実装ではない。`Human-in-the-loop Strategy Operations Workbench` の最初の入口を固める実装である。

現在の実装状況:

- T1-T5 は実装済み。
- `strategy-review-build --input-contract --strategy-idea` は read-only optional source connection として実装済み。
- この実装は paper / live permission を出さない。

## 現実チェック

この計画だけでは、完成形全体の達成目標は完了しない。

この計画で完了できるもの:

- 入力データ契約を artifact として検証する入口。
- 戦略の種を hypothesis として検証する入口。
- paper / live permission と切り離した validation artifact。

この計画で完了しないもの:

- Strategy Authoring YAML の自動生成。
- Stage Policy / Stage Decision。
- Paper Smoke。
- Runtime Observation Ingest。
- Drift Review。
- Persistent Learning Loop。
- AI / ML / GA loop。
- Daily Brief。
- Micro Live Plan Gate。

したがって、この計画の達成目標は「完成形の全工程」ではなく、「弱い入力と弱い戦略アイデアを後段に流さない最初の gate」を完成させることに限定する。

この前提なら、計画は実装可能である。ただし、下の acceptance matrix と stop condition を満たすことを完了条件に含める。

## 目的

目的は、戦略候補を作る前に、入力データと戦略の種を監査可能な artifact にすること。

この slice が答える問い:

- その戦略は、どの入力データを使う前提なのか。
- その入力は、いつ利用可能だったデータなのか。
- source path / hash / schema version / revision policy は何か。
- execution reality、survivorship、lookahead、secret / live boundary は問題ないか。
- 戦略の種は、hypothesis、baseline、invalidation、risk、required inputs を持つか。
- Strategy Review packet へ後続で接続できる source artifact になっているか。

## 非目的

この slice では次を実装しない。

- strategy factory による自動生成。
- AI / LLM / ML / DL / GA の候補生成。
- Stage Policy / Stage Decision。
- Paper smoke plan / report。
- Normal paper observation の追加実行。
- Drift Review。
- Strategy Case registry。
- Svelte UI。
- wallet / signing / exchange write。
- live order / micro live execution。

## 現行正本

実装前に読む正本:

1. `./.ai_memory/HANDOFF.md`
2. `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md`
3. `docs/IMPLEMENTED_SURFACES.md`
4. `docs/NEXT_DIRECTION_CURRENT.md`
5. `docs/strategy_review/README.md`
6. `docs/strategy_lifecycle/README.md`
7. `src/sis/commands/strategy_review.py`
8. `src/sis/strategy_review/manifest.py`
9. `src/sis/strategy_review/provenance.py`
10. `src/sis/strategy_review/service.py`
11. `schemas/operator_strategy_review.v1.schema.json`
12. `tests/strategy_review/`
13. `uv run sis --help`

code、tests、schemas、config、CLI help が正本。docs は補助であり、runtime artifact の固定値を current truth として扱わない。

## 調査結果

### Repo 内調査

現行 repo は、Pydantic model を runtime validation の正本にし、tracked JSON Schema を外部互換と artifact 検査用に置く流儀である。

既存の `strategy_review` は参考実装として使える。

- Pydantic model: `src/sis/strategy_review/manifest.py`
- service: `src/sis/strategy_review/service.py`
- CLI: `src/sis/commands/strategy_review.py`
- JSON Schema: `schemas/strategy_review_manifest.v1.schema.json`
- tests: `tests/strategy_review/`

path / hash / secret path / boundary flag は、既存の `src/sis/strategy_review/provenance.py` を再利用する。新しい path guard を作らない。

### OSS / 依存調査

結論: この slice では runtime 依存を増やさない。

理由:

- 既に `pydantic>=2`、`jsonschema>=4`、`pyyaml>=6` が入っており、この slice の artifact validation には足りる。
- Pydantic v2 は JSON Schema Draft 2020-12 を生成できるが、この repo は tracked JSON Schema を明示管理する流儀である。
- `jsonschema` は Draft 2020-12 validation に対応しており、既存 tests でも使われている。
- `pandera` は DataFrame / Polars validation には有効だが、この slice は file-level artifact contract であり、まだ DataFrame quality gate ではない。
- Great Expectations / GX は data quality platform として強いが、個人 CLI の first slice には重い。
- Frictionless Data Package は portable tabular data schema として有効だが、既存 repo の Pydantic / JSON Schema contract と二重管理になる。
- `hypothesis-jsonschema` は schema からテストデータを生成できるが、今回の Draft 2020-12 schema と Pydantic parity を保証する primary tool としては採用を急がない。

参照:

- Pydantic JSON Schema docs: https://pydantic.dev/docs/validation/latest/concepts/json_schema/
- jsonschema docs: https://python-jsonschema.readthedocs.io/en/latest/validate/
- Pandera docs: https://pandera.readthedocs.io/
- Great Expectations / GX Core: https://greatexpectations.io/
- Frictionless Table Schema: https://frictionlessdata.io/specs/table-schema/
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- Federal Reserve model risk guidance: https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework

追加調査後の判断:

- Pydantic / JSON Schema は artifact shape と field validation に向く。今回の first slice には十分。
- W3C PROV-O は provenance の考え方として参考になるが、PROV-O ontology を導入すると実装が重くなる。今回は `producer`, `source`, `sha256`, `generated_at`, `available_at`, `validated_at` に考え方だけ反映する。
- Federal Reserve model risk guidance や NIST AI RMF は、validation、monitoring、limitations、governance の重要性を示すが、今回の first slice で model governance framework を実装しない。将来の AI / ML / optimizer loop で参照する。
- DataFrame column-level validation は後続の Runtime Observation / feature panel gate で扱う。今回の input contract は file-level / artifact-level validation に留める。

将来の依存追加候補:

| 候補 | 追加する条件 | 今回の判断 |
|---|---|---|
| `pandera[polars]` | Runtime Observation / feature panel の DataFrame column quality を強く検査する段階 | 今は追加しない |
| Great Expectations / GX | 複数 data source / 多人数 / 自動 data docs が必要になった段階 | 今は追加しない |
| Frictionless | 外部共有用の tabular data package contract を採用する段階 | 今は追加しない |
| Hypothesis / hypothesis-jsonschema | schema fuzzing の価値が deterministic tests を上回った段階 | 今は追加しない |

## 責任境界

### Strategy Input Contract

責務:

- 入力データ、生成物、外部メモ、paper feedback、runtime observation などの source を記録する。
- path、hash、schema version、available_at、generated_at、revision policy、survivorship policy、execution reality を検査する。
- live / wallet / signing / exchange write / secret path を拒否する。

責務ではない:

- 戦略を採用すること。
- backtest を実行すること。
- paper / live に進めること。
- AI / ML で候補を作ること。

### Idea Intake

責務:

- 戦略の種を hypothesis として記録する。
- baseline、invalidation、risk、required inputs、execution assumptions の欠落を出す。
- authoring draft に進めるだけの最低条件を判定する。

責務ではない:

- Strategy Authoring YAML を自動生成すること。
- 勝てる戦略かを判定すること。
- paper / live に進めること。

### Strategy Review Optional Source Connection

現在の扱い: T5 として実装済み。Strategy Review packet に input contract / strategy idea を optional source artifact として追加する。

責務:

- `strategy-review-build` に任意の input contract / idea artifact を読み込ませる。
- `review.md` と `review_manifest.json` の source artifact table に出す。

責務ではない:

- input contract / idea を必須化して既存 flow を壊すこと。
- operator review decision vocabulary を変えること。
- `PAPER_OBSERVATION_CANDIDATE` を permission に変えること。

追加制限:

- Strategy Review optional connection は read-only source summary に限定する。
- input contract / strategy idea は必須化しない。
- 既存 `strategy-review-build` の default output を golden test で固定し、optional 指定なしの互換性を必ず守る。

## Artifact Contract

### `strategy_input_contract.v1`

最小フィールド:

```yaml
schema_version: strategy_input_contract.v1
contract_id: ndx-breakout-inputs-001
created_at: "2026-06-18T12:45:00Z"
producer:
  tool: sis
  command: manual
strategy_scope:
  strategy_family: breakout
  instruments: ["NDX"]
  timeframe: "1d"
  intended_use: research_backtest_only
sources:
  - source_id: ndx_ohlcv_daily
    source_type: raw_market_data
    path: data/research/ndx/source/ohlcv.parquet
    required: true
    declared_sha256: sha256:<64 lowercase hex>
    schema_version: market_ohlcv.v1
    generated_at: "2026-06-18T00:00:00Z"
    available_at: "2026-06-18T00:05:00Z"
    revision_policy: append_only
    survivorship_policy: current_constituents_not_allowed
    execution_reality:
      includes_fills: false
      includes_slippage: false
      includes_latency: false
      assumed_order_type: paper_only_intent
known_gaps:
  - no intraday spread data
boundary:
  permits_live_order: false
  live_conversion_allowed: false
  wallet_used: false
  signing_used: false
  exchange_write_used: false
```

必須検査:

- `schema_version == strategy_input_contract.v1`
- `contract_id` は repo 既存 id pattern に合わせる。
- local path は repo-relative、POSIX separator、hidden path 禁止、secret path 禁止。
- required source が欠損していれば validation status は `NEEDS_FIX`。
- path が存在する場合は actual sha256 を計算し、`declared_sha256` と一致させる。
- `available_at` は source の利用可能時刻として必須。
- `revision_policy` と `survivorship_policy` は空にしない。
- boundary flag が true なら `BLOCKED_BOUNDARY_VIOLATION`。
- secret / credential / wallet / live execution を示す path や flag は拒否する。

### `strategy_input_contract_validation.v1`

validator output。

最小フィールド:

```yaml
schema_version: strategy_input_contract_validation.v1
contract_id: ndx-breakout-inputs-001
validated_at: "2026-06-18T12:45:00Z"
producer:
  tool: sis
  command: strategy-input-contract-validate
validation_status: PASS
strict: false
source_results:
  - source_id: ndx_ohlcv_daily
    status: present
    path: data/research/ndx/source/ohlcv.parquet
    actual_sha256: sha256:<64 lowercase hex>
    declared_sha256: sha256:<64 lowercase hex>
    hash_matches: true
summary:
  missing_required_count: 0
  invalid_required_count: 0
  boundary_violation_count: 0
  warning_count: 0
boundary:
  permits_live_order: false
  live_conversion_allowed: false
  wallet_used: false
  signing_used: false
  exchange_write_used: false
```

`validation_status`:

- `PASS`
- `NEEDS_FIX`
- `INVALID_INPUT`
- `BLOCKED_BOUNDARY_VIOLATION`

CLI exit:

- invalid YAML / JSON、schema mismatch、boundary violation は常に exit 2。
- `NEEDS_FIX` は `--strict` なら exit 2、`--no-strict` なら exit 0。
- `PASS` は exit 0。

### `strategy_idea.v1`

最小フィールド:

```yaml
schema_version: strategy_idea.v1
idea_id: ndx-breakout-001
created_at: "2026-06-18T12:45:00Z"
title: NDX close breakout after volatility compression
hypothesis: >
  NDX が低ボラ後に前日高値を終値で上抜ける場合、短期 follow-through が出やすい。
mechanism: trend_following
timeframe: "1d"
instruments: ["NDX"]
required_input_contract_ids:
  - ndx-breakout-inputs-001
baseline:
  name: cash_or_no_trade
  expected_to_beat: true
invalidation:
  - no improvement over cash baseline
  - performance only exists in one regime
risk:
  max_position_notional_usd: 1000
  max_daily_loss_usd: 50
  kill_conditions:
    - no fill in paper smoke
    - spread degradation exceeds assumption
execution_assumptions:
  order_type: market_on_close_paper_intent
  slippage_model: fixed_bps
authoring_intent:
  target: strategy_authoring_draft
  auto_generate_spec: false
boundary:
  permits_live_order: false
  live_conversion_allowed: false
  wallet_used: false
  signing_used: false
  exchange_write_used: false
```

必須検査:

- hypothesis、baseline、invalidation、risk、execution_assumptions が空でない。
- `required_input_contract_ids` が空でない。
- `authoring_intent.auto_generate_spec` は false。
- paper / live permission を示す field は持たせない。
- boundary flag が true なら blocked。

### `strategy_intake_decision.v1`

validator output。

最小フィールド:

```yaml
schema_version: strategy_intake_decision.v1
idea_id: ndx-breakout-001
decided_at: "2026-06-18T12:45:00Z"
producer:
  tool: sis
  command: strategy-intake-validate
decision: READY_FOR_AUTHORING_DRAFT
required_actions: []
input_contract_refs:
  - contract_id: ndx-breakout-inputs-001
    validation_status: PASS
summary:
  missing_hypothesis: false
  missing_baseline: false
  missing_invalidation: false
  missing_risk: false
  missing_required_inputs: false
  boundary_violation_count: 0
boundary:
  permits_live_order: false
  live_conversion_allowed: false
  wallet_used: false
  signing_used: false
  exchange_write_used: false
```

`decision`:

- `REJECT`
- `NEEDS_SPEC`
- `NEEDS_DATA_CHECK`
- `NEEDS_RISK_SPEC`
- `READY_FOR_AUTHORING_DRAFT`

`READY_FOR_AUTHORING_DRAFT` は Strategy Authoring YAML の draft 作成候補であり、paper / live permission ではない。

## CLI Contract

### `strategy-input-contract-validate`

```bash
uv run sis strategy-input-contract-validate \
  --contract configs/strategy_inputs/ndx-breakout-inputs-001.yaml \
  --out data/strategy_inputs/ndx-breakout-inputs-001 \
  --strict
```

出力:

- `data/strategy_inputs/<contract_id>/strategy_input_contract_validation.json`
- `data/strategy_inputs/<contract_id>/strategy_input_contract_validation.md`

stdout:

```text
status=pass
validation_status=PASS
contract_id=ndx-breakout-inputs-001
validation_path=data/strategy_inputs/ndx-breakout-inputs-001/strategy_input_contract_validation.json
report_path=data/strategy_inputs/ndx-breakout-inputs-001/strategy_input_contract_validation.md
missing_required_count=0
boundary_violation_count=0
```

### `strategy-intake-validate`

```bash
uv run sis strategy-intake-validate \
  --idea configs/strategy_ideas/ndx-breakout-001.yaml \
  --input-contract-validation data/strategy_inputs/ndx-breakout-inputs-001/strategy_input_contract_validation.json \
  --out data/strategy_ideas/ndx-breakout-001 \
  --strict
```

出力:

- `data/strategy_ideas/<idea_id>/strategy_intake_decision.json`
- `data/strategy_ideas/<idea_id>/strategy_intake_decision.md`

stdout:

```text
status=pass
decision=READY_FOR_AUTHORING_DRAFT
idea_id=ndx-breakout-001
decision_path=data/strategy_ideas/ndx-breakout-001/strategy_intake_decision.json
report_path=data/strategy_ideas/ndx-breakout-001/strategy_intake_decision.md
required_action_count=0
boundary_violation_count=0
```

### `strategy-review-build` optional connection

既存 command に optional flag を追加する。

```bash
uv run sis strategy-review-build \
  --review-id ndx-breakout-001 \
  --input-contract configs/strategy_inputs/ndx-breakout-inputs-001.yaml \
  --strategy-idea configs/strategy_ideas/ndx-breakout-001.yaml
```

条件:

- `--input-contract` と `--strategy-idea` は optional。
- 既存 command の default behavior を壊さない。
- `review_manifest.json` の `source_artifacts` に `input_contract` と `strategy_idea` を追加する。
- `review.md` に `Input Contract Summary` と `Idea Intake Summary` を追加する。
- 欠損 optional は review_status を変えない。
- invalid / boundary violation は既存 source safety logic に乗せる。

## Acceptance Matrix

この matrix を満たさない場合、計画達成とは扱わない。

| ID | Requirement | Verification |
|---|---|---|
| A1 | `strategy_input_contract.v1` が valid payload を Pydantic と JSON Schema の両方で受け入れる | `uv run pytest tests/strategy_inputs/test_strategy_input_contract_schema.py` |
| A2 | `strategy_input_contract.v1` が extra field、secret path、absolute path、bare hash、permission true を拒否する | `uv run pytest tests/strategy_inputs/test_strategy_input_contract_schema.py` |
| A3 | `strategy-input-contract-validate` が source path の存在、sha256、missing required、boundary violation を判定する | `uv run pytest tests/strategy_inputs/test_strategy_input_contract_validation.py` |
| A4 | `strategy-input-contract-validate` が strict / non-strict exit code を固定する | `uv run pytest tests/strategy_inputs/test_strategy_input_contract_cli.py` |
| A5 | `strategy_idea.v1` が hypothesis、baseline、invalidation、risk、required inputs を必須にする | `uv run pytest tests/strategy_inputs/test_strategy_idea_schema.py` |
| A6 | `strategy-intake-validate` が `READY_FOR_AUTHORING_DRAFT` と `NEEDS_*` を permission なしで判定する | `uv run pytest tests/strategy_inputs/test_strategy_intake_validation.py` |
| A7 | `strategy-intake-validate` が missing input contract、failed input validation、risk 欠落を `NEEDS_*` に落とす | `uv run pytest tests/strategy_inputs/test_strategy_intake_validation.py` |
| A8 | `uv run sis --help` に新 CLI が出る | CLI test または manual verification log |
| A9 | optional `strategy-review-build --input-contract --strategy-idea` が source artifact と markdown summary を出す | `uv run pytest tests/strategy_review` |
| A10 | optional 指定なしの既存 Strategy Review output が壊れない | `uv run pytest tests/strategy_review` |
| A11 | docs metadata / links / EOF / routing が壊れない | `uv run python scripts/check_current_docs.py` |
| A12 | repo full gate が通る | `./scripts/check` |

## 対象ファイル

新規:

- `src/sis/strategy_inputs/__init__.py`
- `src/sis/strategy_inputs/models.py`
- `src/sis/strategy_inputs/io.py`
- `src/sis/strategy_inputs/validation.py`
- `src/sis/strategy_inputs/rendering.py`
- `src/sis/commands/strategy_inputs.py`
- `schemas/strategy_input_contract.v1.schema.json`
- `schemas/strategy_input_contract_validation.v1.schema.json`
- `schemas/strategy_idea.v1.schema.json`
- `schemas/strategy_intake_decision.v1.schema.json`
- `tests/strategy_inputs/__init__.py`
- `tests/strategy_inputs/test_strategy_input_contract_schema.py`
- `tests/strategy_inputs/test_strategy_input_contract_validation.py`
- `tests/strategy_inputs/test_strategy_input_contract_cli.py`
- `tests/strategy_inputs/test_strategy_idea_schema.py`
- `tests/strategy_inputs/test_strategy_intake_validation.py`
- `tests/strategy_inputs/test_strategy_intake_cli.py`
- `docs/strategy_inputs/README.md`

変更:

- `src/sis/cli.py`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
- `plan/README.md`

T5 で変更する対象:

- `src/sis/commands/strategy_review.py`
- `src/sis/strategy_review/service.py`
- `src/sis/strategy_review/renderer.py`
- `src/sis/strategy_review/manifest.py`
- `schemas/strategy_review_manifest.v1.schema.json`
- `tests/strategy_review/test_strategy_review_build.py`
- `tests/strategy_review/test_strategy_review_rendering.py`
- `tests/strategy_review/test_strategy_review_manifest_schema.py`

変更しない:

- live / execution / wallet / signing modules
- Trade[XYZ] collectors
- paper execution commands
- Strategy Authoring compiler
- NDX Layer gates
- runtime artifacts under `data/`

## Stop Conditions

次のどれかに該当したら、実装を止めて計画を見直す。

- `strategy_input_contract.v1` 実装に Stage Policy / Paper Smoke / Drift Review の schema が必要になる。
- Strategy Review optional connection が既存 manifest schema の破壊的変更を要求する。
- `strategy-author-run` や Strategy Authoring compiler の挙動変更が必要になる。
- live / execution / wallet / signing / exchange write module に触る必要が出る。
- runtime dependency 追加なしでは実装できないことが判明する。
- `./scripts/check` の失敗原因がこの slice と無関係で、修正範囲が広がる。
- generated runtime artifact を tracked file にする必要が出る。

止めた場合の処理:

- どの acceptance が満たせないかを書く。
- 影響ファイルを列挙する。
- 依存追加、scope 縮小、または別 slice 化のどれで解決するかを選ぶ。

## 実装タスク

### T0: Baseline確認

目的: 現在の状態を確認し、既存差分を壊さない。

手順:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run python scripts/check_current_docs.py
```

完了条件:

- 既存の未コミット差分を把握している。
- `sis --help` に現行 command が出ることを確認済み。
- current docs check が通る、または既存失敗を記録済み。

### T1: Pydantic model を作る

目的: runtime contract の正本を実装する。

対象:

- `src/sis/strategy_inputs/models.py`

実装内容:

- `StrategyInputContract`
- `StrategyInputSource`
- `StrategyInputContractValidation`
- `StrategyIdea`
- `StrategyIntakeDecision`
- producer / boundary / summary submodel
- enum:
  - `InputSourceType`
  - `InputRevisionPolicy`
  - `InputSurvivorshipPolicy`
  - `InputValidationStatus`
  - `IdeaIntakeDecision`

必須:

- `model_config = ConfigDict(extra="forbid")`
- id pattern は既存 `REVIEW_ID_PATTERN` と同等にする。
- sha256 は `^sha256:[a-f0-9]{64}$`。
- boundary flags は output artifact では fixed false。
- input payload 内に true boundary があれば blocked 判定へつなげる。

完了条件:

- Pydantic の valid / invalid unit tests が通る。
- extra fields が拒否される。
- empty text が拒否される。
- permission flag true が拒否または blocked になる。

### T2: JSON Schema を作る

目的: artifact compatibility と external validation を可能にする。

対象:

- `schemas/strategy_input_contract.v1.schema.json`
- `schemas/strategy_input_contract_validation.v1.schema.json`
- `schemas/strategy_idea.v1.schema.json`
- `schemas/strategy_intake_decision.v1.schema.json`

実装内容:

- Draft 2020-12 schema。
- `additionalProperties: false`。
- Pydantic model と enum を一致させる。
- conditional rule:
  - `READY_FOR_AUTHORING_DRAFT` は missing flags が false、boundary count 0。
  - validation `PASS` は missing / invalid / boundary count 0。
  - fixed false boundary flags。

完了条件:

- `Draft202012Validator.check_schema(...)` が通る。
- schema が valid payload を受け入れる。
- schema が permission true、bare hash、extra field、missing required を拒否する。
- enum mismatch test が通る。

### T3: IO / validation service を作る

目的: CLI から呼べる reusable service にする。

対象:

- `src/sis/strategy_inputs/io.py`
- `src/sis/strategy_inputs/validation.py`
- `src/sis/strategy_inputs/rendering.py`

実装内容:

- YAML / JSON loader。
- repo-relative path validation は `sis.strategy_review.provenance` を再利用。
- source file exists / missing / invalid / sha256 mismatch / schema version summary。
- boundary true path 検出は `boundary_true_paths` を再利用。
- markdown report renderer。
- atomic write。既存 pattern に合わせ、tmp file + replace。
- `replace_existing` guard。

完了条件:

- required source missing は `NEEDS_FIX`。
- optional source missing は warning。
- declared hash mismatch は `NEEDS_FIX`。
- secret path は `INVALID_INPUT` または `BLOCKED_BOUNDARY_VIOLATION`。
- boundary flag true は `BLOCKED_BOUNDARY_VIOLATION`。
- output JSON と markdown が書かれる。
- `--replace-existing` なしで既存 output を上書きしない。

### T4: CLI を追加する

目的: public `sis` command として使えるようにする。

対象:

- `src/sis/commands/strategy_inputs.py`
- `src/sis/cli.py`

実装内容:

- `register_strategy_input_commands(app)` を作る。
- `strategy-input-contract-validate` を追加。
- `strategy-intake-validate` を追加。
- `_resolve_workspace_path` は既存 `strategy_authoring` helper を使う。
- stdout は machine-readable な `key=value` 形式にする。

完了条件:

- `uv run sis --help` に2 command が出る。
- `uv run sis strategy-input-contract-validate --help` が出る。
- `uv run sis strategy-intake-validate --help` が出る。
- invalid input で exit 2。
- strict mode の exit behavior が tests で固定される。

### T5: Strategy Review optional connection

目的: review packet から input / idea を読めるようにする。

対象:

- `src/sis/commands/strategy_review.py`
- `src/sis/strategy_review/service.py`
- `src/sis/strategy_review/renderer.py`
- `src/sis/strategy_review/manifest.py`
- `schemas/strategy_review_manifest.v1.schema.json`
- `tests/strategy_review/`

実装内容:

- `strategy-review-build` に `--input-contract` と `--strategy-idea` を追加。
- どちらも optional。
- `source_artifacts` に `input_contract` と `strategy_idea` を追加。
- markdown に `Input Contract Summary` と `Idea Intake Summary` を追加。
- invalid / boundary violation は既存 source safety logic に従う。

完了条件:

- 既存 strategy review tests が壊れない。
- optional 指定なしの output は従来互換。
- optional 指定ありの manifest に source artifact が出る。
- optional 指定ありの markdown に summary が出る。
- boundary true を含む optional artifact は review_status を blocked にする。

### T6: Docs を更新する

目的: current docs と CLI help の導線を揃える。

対象:

- `docs/strategy_inputs/README.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
- `plan/README.md`

実装内容:

- 新 command の使い方。
- artifact の意味。
- non-permission boundary。
- Strategy Review optional connection。
- OSS 依存追加なしの理由。

完了条件:

- docs に timestamp header がある。
- current docs check が通る。
- runtime snapshot 値や pass count を固定しない。

### T7: Full verification

目的: slice が壊れていないことを確認する。

必須 command:

```bash
uv run pytest tests/strategy_inputs
uv run pytest tests/strategy_review
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

完了条件:

- すべて pass。
- `uv run sis --help` に新 command が出る。
- generated runtime artifacts は tracked しない。
- `git status --short --branch --untracked-files=all` で意図した tracked diff だけ残る。

## テスト方針

### Unit tests

対象:

- Pydantic model validation。
- enum parity。
- path validation。
- sha256 validation。
- boundary flag validation。
- required field validation。
- strict / non-strict behavior。

### Schema tests

対象:

- tracked JSON Schema の validity。
- valid payload を JSON Schema と Pydantic の両方が受け入れる。
- invalid payload を JSON Schema と Pydantic の両方が拒否する。
- enum が Pydantic と JSON Schema で一致する。

### Service tests

対象:

- valid input contract。
- required source missing。
- optional source missing。
- hash mismatch。
- secret path。
- boundary violation。
- output exists refusal。
- replace existing。
- markdown report content。

### CLI tests

対象:

- help text。
- success stdout。
- invalid exit code。
- strict mode exit code。
- output file paths。

### Integration tests

対象:

- `strategy-input-contract-validate` output を `strategy-intake-validate` が読む。
- `strategy-review-build --input-contract --strategy-idea` が review packet に source artifact を入れる。
- 既存 review build / record flow が壊れない。

## 完了条件

この implementation slice は、次を満たした時に完了。

- `strategy_input_contract.v1` schema と Pydantic model がある。
- `strategy_input_contract_validation.v1` schema と Pydantic model がある。
- `strategy_idea.v1` schema と Pydantic model がある。
- `strategy_intake_decision.v1` schema と Pydantic model がある。
- `strategy-input-contract-validate` が public CLI に出る。
- `strategy-intake-validate` が public CLI に出る。
- Strategy Review が optional input contract / idea を読める。
- permission boundary は固定で、paper / live 許可を出さない。
- focused tests と full gate が通る。
- docs が current truth に更新される。

明示的に未完了として残してよいもの:

- DataFrame / Polars column-level validation は後続 slice。
- AI / ML / optimizer provenance は後続 slice。
- Stage Policy / Paper Smoke / Drift Review は後続 slice。

## 抜け・漏れ・誤謬リスク

| リスク | 対策 |
|---|---|
| Input Contract が path / hash 一覧だけになる | `available_at`, `revision_policy`, `survivorship_policy`, `execution_reality` を必須化する |
| Idea Intake がアイデア投稿箱になる | hypothesis, baseline, invalidation, risk, required inputs を必須にする |
| `READY_FOR_AUTHORING_DRAFT` が paper permission と誤読される | docs / schema / report に non-permission notice を固定する |
| `PAPER_OBSERVATION_CANDIDATE` と接続して permission に見える | Strategy Review optional source connection は読むだけにする |
| CLI が runtime artifact を current truth にする | docs には snapshot 値を書かず、再実行 command だけを書く |
| 依存追加で保守負荷が増える | 今回は runtime dependency を増やさない |
| Pydantic と JSON Schema がズレる | enum parity / valid payload / invalid payload tests を両方に書く |
| source path から secret を読める | 既存 provenance path guard を再利用し、secret path tests を追加する |
| DataFrame quality まで抱え込む | Pandera 等は将来の DataFrame gate まで延期する |
| 計画が完成形全体の完了計画と誤読される | この plan は first gate だけと冒頭に固定する |
| Strategy Review 接続が scope を広げる | read-only optional source summary に限定し、operator decision vocabulary を変えない |
| `available_at` が飾りになる | source ごとの validation report に `available_at_present` と `generated_before_available` を出す |
| source hash が optional 扱いになる | required source は hash 必須、optional source も存在する場合は actual hash を記録する |
| yaml examples だけ実装して schema が追いつかない | Pydantic / JSON Schema parity tests を acceptance に入れる |

## 実装順序

推奨 commit 分割:

1. `strategy_inputs` models + schemas + unit/schema tests。
2. validation service + rendering + service tests。
3. CLI registration + CLI tests。
4. Strategy Review optional connection + integration tests。
5. docs update + full gate。

## Coder Handoff Prompt

```text
Read:
- ./.ai_memory/HANDOFF.md
- AGENTS.md
- docs/strategy_inputs/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md
- docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md
- src/sis/strategy_review/provenance.py
- src/sis/commands/strategy_review.py

Implement only the Strategy Input Contract and Idea Intake slice.
Do not implement Stage Policy, Paper Smoke, Drift Review, AI/ML/GA, UI, wallet, signing, exchange write, or live execution.
Follow existing Pydantic + tracked JSON Schema + Typer CLI patterns.
Add focused tests first where practical.
Run:
  uv run pytest tests/strategy_inputs
  uv run pytest tests/strategy_review
  uv run python scripts/check_current_docs.py
  git diff --check
  ./scripts/check
Stop if implementation requires schema widening outside the planned files or touches live / wallet / signing / exchange write code.
```
