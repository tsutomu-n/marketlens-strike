<!--
作成日: 2026-06-22_17:55 JST
更新日: 2026-06-22_20:24 JST
-->

# File Map

## 新規 Python package

`src/sis/strategy_input_feedback/`

- `__init__.py`: package marker。
- `models.py`: proposal / review model、enum、boundary model。
- `service.py`: source artifact 読み込み、既存 model validation、hashing、proposal / review generation。
- `rendering.py`: Markdown summary rendering。JSON を正にし、Markdown は補助にする。

`src/sis/strategy_case_index/`

- `__init__.py`: package marker。
- `models.py`: case index model、case entry、strategy summary、boundary model。
- `service.py`: case-lite artifact discovery、validation、dedupe、index generation。
- `rendering.py`: Markdown summary rendering。

## 新規 CLI command modules

`src/sis/commands/strategy_input_feedback.py`

- `register_strategy_input_feedback_commands(app: typer.Typer) -> None`
- `strategy-input-feedback-proposal-build`
- `strategy-input-feedback-proposal-review`
- `--runtime-observation` / `--learning-event` の少なくとも一方を必須にする。
- `--source-contract` なしの status を apply-ready にしない。

`src/sis/commands/strategy_case_index.py`

- `register_strategy_case_index_commands(app: typer.Typer) -> None`
- `strategy-case-index-build`
- `--data-dir` scan は `strategy_case_lite.v1` JSON だけに限定する。

## 更新する CLI root

`src/sis/cli.py`

- 新規 command module を import する。
- 既存 `register(...)` 呼び出しの並びに追加する。
- 既存 CLI 名を変更しない。

## 新規 schema

`schemas/strategy_input_contract_update_proposal.v1.schema.json`

- proposal artifact の schema。

`schemas/strategy_input_contract_update_review.v1.schema.json`

- human review artifact の schema。

`schemas/strategy_case_index.v1.schema.json`

- case index artifact の schema。

## 更新する既存 schema

`schemas/strategy_workbench_viewer.v1.schema.json`

- viewer manifest shape を変更する場合のみ更新する。
- 既存 schema は `summary` を object として受けるため、case index 用 compact summary key を追加するだけなら更新しない。
- 既存 artifact summary の後方互換性を壊さない。

## 新規 tests

`tests/strategy_input_feedback/`

- `test_strategy_input_feedback_schema.py`
- `test_strategy_input_feedback.py`
- `test_strategy_input_feedback_cli.py`

`tests/strategy_case_index/`

- `test_strategy_case_index_schema.py`
- `test_strategy_case_index.py`
- `test_strategy_case_index_cli.py`

## 更新する既存 tests

`tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`

- case index artifact の summary / HTML 表示 / escaping を追加する。

## 新規 docs

`docs/strategy_input_feedback/README.md`

- CLI usage
- artifact boundary
- source artifact rules
- review handoff
- non-goals

`docs/strategy_case_index/README.md`

- CLI usage
- case-lite index semantics
- data-dir scan rules
- non-goals

## 更新する existing docs

`docs/strategy_case_lite/README.md`

- `--artifact` option を追加する。
- known schema は typed artifact、unknown schema は `generic` になることを明記する。
- backtest-only Case Lite が paper / live readiness ではないことを維持する。

`docs/strategy_workbench_viewer/README.md`

- case index 表示に対応した説明を追加する。

`docs/IMPLEMENTED_SURFACES.md`

- 新規 CLI / artifact / boundary を追加する。

`docs/NEXT_DIRECTION_CURRENT.md`

- Runtime Observation / Learning Event から Strategy Input Contract 更新候補を作る gap を実装済みに更新する。
- Strategy Case Lite Index を実装済みに更新する。
- paper bridge、credentialed network probe、demo order lifecycle、production schema widening は未実装のまま残す。

`docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

- 新規 CLI を追加する。

`scripts/check_current_docs.py`

- `docs/strategy_input_feedback` と `docs/strategy_case_index` を current doc dirs に追加する。

## 更新する既存 Case Lite surface

`src/sis/strategy_case_lite/models.py`

- `StrategyCaseArtifactType` に backtest / review / input validation 系の typed artifact を追加する。

`src/sis/strategy_case_lite/service.py`

- schema_version から known artifact type を判定する mapping を追加する。
- top-level `status` を timeline status 候補に追加する。

`src/sis/commands/strategy_case_lite.py`

- `strategy-case-lite-update --artifact` を追加する。

`schemas/strategy_case_lite.v1.schema.json`

- typed artifact enum を追加する。

`tests/strategy_case_lite/`

- `--artifact` help と CLI success を追加する。
- backtest result / strategy review manifest が schema-valid Case Lite になることを確認する。

## 触らないファイル

- `.env`
- secrets / credential files
- venue client secrets
- live order modules
- wallet / signing modules
- production venue schema widening 関連の code
- DB migration files
- archived historical plan files
