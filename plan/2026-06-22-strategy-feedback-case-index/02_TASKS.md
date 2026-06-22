<!--
作成日: 2026-06-22_17:55 JST
更新日: 2026-06-22_18:36 JST
-->

# Task Plan

## T0: 実装前確認

目的: 実装者が古い計画や stale handoff に引っ張られず、現行 repo から開始する。

対象ファイル: なし。

実行:

- `git status --short --branch`
- `git log -1 --oneline --decorate`
- `uv run sis --help`
- `uv run python scripts/check_current_docs.py`

完了条件:

- 作業ブランチ状態を把握している。
- `strategy-input-contract-validate`、`strategy-runtime-observation-ingest`、`strategy-learning-ledger-update`、`strategy-case-lite-update`、`strategy-workbench-viewer-build` が現行 CLI にあることを確認する。

## T1: Strategy Input Feedback schema / models

目的: Strategy Input Contract 更新候補とレビュー結果を machine-readable artifact にする。

対象ファイル:

- `src/sis/strategy_input_feedback/__init__.py`
- `src/sis/strategy_input_feedback/models.py`
- `schemas/strategy_input_contract_update_proposal.v1.schema.json`
- `schemas/strategy_input_contract_update_review.v1.schema.json`
- `tests/strategy_input_feedback/test_strategy_input_feedback_schema.py`

実装内容:

- `strategy_input_contract_update_proposal.v1` model を追加する。
- `strategy_input_contract_update_review.v1` model を追加する。
- source artifact は `path`、`sha256`、`schema_version`、`artifact_kind` を持つ。
- proposal は `proposal_id`、`strategy_id`、`created_at`、`status`、`source_artifacts`、`proposed_changes`、`boundary` を持つ。
- proposed change は `change_id`、`target_section`、`recommendation`、`evidence_summary`、`source_reason`、`requires_human_review` を持つ。
- review は `review_id`、`proposal_id`、`strategy_id`、`decision`、`approved_change_ids`、`required_actions`、`source_proposal`、`boundary` を持つ。
- boundary は少なくとも `permits_live_order=false`、`permits_wallet=false`、`permits_signing=false`、`permits_exchange_write=false`、`auto_applied=false`、`direct_contract_edit_allowed=false` を表現する。
- proposal status は少なくとも `READY_FOR_HUMAN_REVIEW`、`NEEDS_SOURCE_CONTRACT_CONTEXT`、`NO_CHANGES_RECOMMENDED`、`BLOCKED_BOUNDARY_VIOLATION` を分ける。
- review decision は少なくとも `APPROVE_FOR_MANUAL_CONTRACT_UPDATE`、`REJECT`、`HOLD`、`NEEDS_FIX` を分ける。

受け入れ条件:

- valid fixture が schema validation を通る。
- boundary を true にした fixture は validation または model construction で失敗する。
- unknown schema version は失敗する。
- `approved_change_ids` が proposal 内の `change_id` 以外を参照した review は失敗する。

## T2: Strategy Input Feedback service / CLI

目的: Runtime Observation と Learning Event から proposal を生成し、人間レビュー artifact を作る。

対象ファイル:

- `src/sis/strategy_input_feedback/service.py`
- `src/sis/strategy_input_feedback/rendering.py`
- `src/sis/commands/strategy_input_feedback.py`
- `src/sis/cli.py`
- `tests/strategy_input_feedback/test_strategy_input_feedback.py`
- `tests/strategy_input_feedback/test_strategy_input_feedback_cli.py`

実装内容:

- `build_input_feedback_proposal(...)` を追加する。
- `build_input_feedback_review(...)` を追加する。
- `strategy-input-feedback-proposal-build` CLI を追加する。
- `strategy-input-feedback-proposal-review` CLI を追加する。
- CLI options は既存コマンドの Typer pattern に合わせる。
- `--runtime-observation` は複数指定できる。
- `--learning-event` は複数指定できる。
- `--source-contract` は optional にする。指定された場合は path / hash を source artifact に含める。
- `--source-contract` がない場合、proposal status は `NEEDS_SOURCE_CONTRACT_CONTEXT` に固定し、`READY_FOR_HUMAN_REVIEW` にしない。
- `--source-contract` がある場合は `StrategyInputContract` model validation を行う。contract 内の declared source hash / columns / timestamp 検査をこの service 内に再実装しない。必要なら利用者は先に `strategy-input-contract-validate` を実行する。
- `--runtime-observation` と `--learning-event` の両方が空なら non-zero exit にする。
- `--out` と `--replace-existing` を既存 artifact builder の流儀に合わせる。
- 生成時は JSON artifact と review 用 Markdown summary を出す。Markdown は補助であり、JSON を正にする。
- source artifact は既存 Pydantic model で schema_version と boundary を検証する。単なる dict 読みだけで進めない。
- review の `approved_change_ids` 整合性は schema 単体では保証できないため、model には source proposal summary を入れ、service / CLI で proposal の `change_id` set と突合する。

受け入れ条件:

- Runtime Observation fixture だけで proposal を生成できる。
- Learning Event fixture だけで proposal を生成できる。
- 両方を指定したとき、source artifact がすべて記録される。
- source artifact が boundary violation を示す場合、proposal status は ready ではなく blocked になる。
- source contract なしの proposal は direct update candidate として扱われない。
- review CLI は proposal を読み、decision と required actions を含む review artifact を生成する。
- review CLI は `approved_change_ids` と proposal の `change_id` 整合を検査する。
- `NEEDS_FIX` decision は `required_actions` 空を拒否する。`REJECT` / `HOLD` で `approved_change_ids` がある場合も拒否する。
- review artifact でも direct apply は許可されない。
- `uv run sis --help` に新規 CLI が表示される。

## T3: Strategy Case Lite Index schema / models

目的: 複数 `strategy_case_lite.v1` を一覧化する read-only index artifact を定義する。

対象ファイル:

- `src/sis/strategy_case_index/__init__.py`
- `src/sis/strategy_case_index/models.py`
- `schemas/strategy_case_index.v1.schema.json`
- `tests/strategy_case_index/test_strategy_case_index_schema.py`

実装内容:

- `strategy_case_index.v1` model を追加する。
- index は `index_id`、`created_at`、`producer`、`case_count`、`strategy_count`、`cases`、`strategies`、`source_artifacts`、`boundary` を持つ。
- case entry は `case_id`、`strategy_id`、`case_path`、`case_sha256`、`latest_status`、`artifact_count`、`timeline_count`、`open_actions`、`blocked_reasons`、`updated_at` を持つ。
- strategy summary は strategy_id ごとに latest case と open actions を集約する。
- latest case は `updated_at`、次に path の deterministic sort で決める。
- boundary は live / wallet / signing / exchange write / DB persistence を許可しない。

受け入れ条件:

- valid index fixture が schema validation を通る。
- case_count / strategy_count の不整合は失敗する。
- boundary true は失敗する。
- 同じ入力順で同じ index が生成される deterministic contract がある。

## T4: Strategy Case Lite Index service / CLI

目的: 既存 case-lite artifacts から index を再生成できるようにする。

対象ファイル:

- `src/sis/strategy_case_index/service.py`
- `src/sis/strategy_case_index/rendering.py`
- `src/sis/commands/strategy_case_index.py`
- `src/sis/cli.py`
- `tests/strategy_case_index/test_strategy_case_index.py`
- `tests/strategy_case_index/test_strategy_case_index_cli.py`

実装内容:

- `build_strategy_case_index(...)` を追加する。
- `strategy-case-index-build` CLI を追加する。
- `--case` は複数指定できる。
- `--data-dir` は optional にする。指定時は `strategy_case_lite.v1` JSON を再帰探索する。
- `--case` と `--data-dir` の両方指定を許可するが、同一 path と同一 hash を deterministic に dedupe する。hash が同じ場合は path sort で先頭を代表にする。
- `--out`、`--index-id`、`--replace-existing` を持たせる。
- data-dir scan は `strategy_case_lite.v1` JSON だけを採用する。任意 JSON、Markdown、viewer manifest、既存 index は採用しない。
- explicit `--case` の欠損 path、schema mismatch、壊れた JSON は明示エラーにする。
- data-dir scan は schema_version が違う JSON を無視する。ただし schema_version が `strategy_case_lite.v1` の壊れた JSON / model validation failure は明示エラーにする。
- case-lite 0件は明示エラーにする。
- JSON index と Markdown summary を出す。

受け入れ条件:

- 明示 `--case` 2件から index を生成できる。
- `--data-dir` から case-lite artifact を発見できる。
- 同一 artifact の重複指定で二重 count しない。
- missing file は non-zero exit になる。
- explicit `--case` に case-lite 以外を渡すと non-zero exit になる。
- data-dir に無関係な JSON だけがある場合は non-zero exit になる。
- `uv run sis --help` に新規 CLI が表示される。

## T5: Static Workbench Viewer case index 表示

目的: 生成した case index を既存 viewer でレビューできるようにする。

対象ファイル:

- `src/sis/strategy_workbench_viewer/models.py`
- `src/sis/strategy_workbench_viewer/service.py`
- `src/sis/strategy_workbench_viewer/rendering.py`
- `schemas/strategy_workbench_viewer.v1.schema.json`（manifest shape を変える場合のみ）
- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`

実装内容:

- viewer artifact summary に `strategy_case_index.v1` を追加する。
- HTML に strategy count、case count、latest status、open actions、blocked reasons、latest case path、source hash を表示する。実装は既存 `ViewerSourceArtifact.summary` の compact summary 経由を第一候補にする。
- 既存 summary type と HTML escaping pattern を壊さない。
- viewer は生成済み artifact を表示するだけで、index の作成や補正をしない。
- case index の permission 系 true flag は permission として表示せず、boundary violation として扱う。
- `StrategyWorkbenchViewerManifest` の shape を変えない場合、`schemas/strategy_workbench_viewer.v1.schema.json` は更新しない。テストで schema validation が既存のまま通ることを確認する。

受け入れ条件:

- explicit `--artifact` で case index を渡すと viewer に case index summary が表示される。
- `--data-dir` scan でも case index artifact が拾われる。
- HTML escaping test が通る。
- schema validation が通る。
- viewer manifest schema を変更しない場合は、既存 schema のまま case index artifact を含む manifest が validation を通る。
- existing viewer output を viewer 自身が source of truth として読まない。

## T6: docs / CLI catalog / current-doc routing 更新

目的: 新規 surface を current docs から辿れるようにし、古い計画と混同しない。

対象ファイル:

- `docs/strategy_input_feedback/README.md`
- `docs/strategy_case_index/README.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `scripts/check_current_docs.py`

実装内容:

- 新規 docs は hidden metadata header を付ける。
- `scripts/check_current_docs.py` の `CURRENT_DOC_DIRS` に新規 docs directory が入っているか確認し、未追加なら追加する。
- CLI catalog に新規 command を追加する。
- `NEXT_DIRECTION_CURRENT.md` から、P1/P2/P3 の該当 gap を実装済みに更新する。ただし paper bridge / network / live / schema widening は未実装のまま残す。

受け入れ条件:

- `uv run python scripts/check_current_docs.py` が通る。
- `uv run python scripts/check_cli_catalog.py` が通る。
- docs に live readiness、paper readiness、venue readiness の誤った主張がない。

## T7: 最終検証

目的: 実装・docs・schema・CLI catalog の破綻をまとめて検出する。

対象ファイル: なし。

実行:

- `uv run sis --help`
- `uv run sis strategy-input-feedback-proposal-build --help`
- `uv run sis strategy-case-index-build --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `uv run pytest tests/strategy_input_feedback tests/strategy_case_index tests/strategy_workbench_viewer`
- `./scripts/check`

完了条件:

- すべて通る。
- 生成 artifact の sample path を final report に残す。
- この計画で明示的に対象外にした live / network / venue / schema widening を実施していない。
