<!--
作成日: 2026-06-22_17:55 JST
更新日: 2026-06-22_18:36 JST
-->

# Test And Acceptance

## テスト方針

fixture-first、offline-only、artifact boundary-first でテストする。network、credential、paper order、live order、exchange write は使わない。

新規 domain logic は unit test を先に置く。CLI は Typer runner か既存 CLI test pattern に合わせる。schema は valid fixture と invalid fixture の両方を置く。

## 最小テストセット

### Strategy Input Feedback

対象:

- `tests/strategy_input_feedback/test_strategy_input_feedback_schema.py`
- `tests/strategy_input_feedback/test_strategy_input_feedback.py`
- `tests/strategy_input_feedback/test_strategy_input_feedback_cli.py`

確認:

- Runtime Observation から proposal が生成される。
- Learning Event から proposal が生成される。
- Runtime Observation / Learning Event が両方ない場合は non-zero exit になる。
- source artifact path / hash / schema version が残る。
- source artifact は既存 model validation を通る。
- boundary flags が false に固定される。
- boundary violation source を指定すると ready proposal にならない。
- source contract なしの proposal は apply-ready にならない。
- source contract ありの場合は `StrategyInputContract` model validation を通す。
- source contract 内の declared source hash / columns / timestamp 検査はこの計画の proposal service では再実装しない。必要なら既存 `strategy-input-contract-validate` の出力を別計画で接続する。
- review artifact は decision / approved_change_ids / required_actions を持つ。
- unknown approved_change_id は non-zero exit または validation failure になる。
- `NEEDS_FIX` で `required_actions` 空は失敗する。
- `REJECT` / `HOLD` で `approved_change_ids` がある場合は失敗する。
- review artifact は direct apply を許可しない。
- missing source は non-zero exit になる。

### Strategy Case Index

対象:

- `tests/strategy_case_index/test_strategy_case_index_schema.py`
- `tests/strategy_case_index/test_strategy_case_index.py`
- `tests/strategy_case_index/test_strategy_case_index_cli.py`

確認:

- 2件以上の case-lite artifact から index が作れる。
- strategy_id ごとの summary が作られる。
- duplicate case path / hash は重複 count しない。
- latest case selection は deterministic である。
- missing file は non-zero exit になる。
- malformed JSON は non-zero exit になる。
- explicit `--case` の schema mismatch は non-zero exit になる。
- data-dir scan は schema_version が違う JSON を無視し、schema_version が `strategy_case_lite.v1` の壊れた JSON は失敗する。
- unrelated JSON only の data-dir は non-zero exit になる。
- boundary flags が false に固定される。

### Workbench Viewer

対象:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`

確認:

- case index artifact が viewer summary に入る。
- HTML に case count、strategy count、latest status、open actions、blocked reasons、source hash が出る。
- permission 系 true flag は boundary violation として出る。
- HTML escaping が効く。
- viewer manifest schema を変更しない場合は、既存 schema のまま case index artifact を含む manifest が validation を通る。
- 既存 artifact type の rendering が壊れない。

## 検証コマンド

狭い検証:

```bash
uv run pytest tests/strategy_input_feedback tests/strategy_case_index tests/strategy_workbench_viewer
```

docs / catalog:

```bash
uv run sis strategy-input-feedback-proposal-build --help
uv run sis strategy-case-index-build --help
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
```

全体:

```bash
./scripts/check
```

## 完了条件

- 新規 CLI が `uv run sis --help` に出る。
- 新規 schema が fixture と pytest で確認される。
- docs checker と CLI catalog checker が通る。
- `./scripts/check` が通る。
- final report に、生成した sample artifact path と検証コマンド結果を書く。
- final report で、live / wallet / signing / exchange write / production venue readiness を実施していないことを明記する。
