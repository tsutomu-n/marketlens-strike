<!--
作成日: 2026-06-22_20:24 JST
更新日: 2026-06-22_20:28 JST
-->

# Local Dogfood Loop 06 Plan Alignment Results

## 結論

Loop 06 では、Loop 04 で追加した `strategy-case-lite-update --artifact` と backtest-only Case Lite / Case Index dogfood が、active implementation plan に反映されているか確認した。

結果:

- 当初の `02_TASKS.md`、`03_FILE_MAP.md`、`04_TEST_AND_ACCEPTANCE.md`、`TASK_CHAIN.yaml` には、Case Lite `--artifact` 追加が反映されていなかった。
- これは実装済み差分と計画文書のズレなので修正した。
- `T4A: Strategy Case Lite additional artifact input` を追加した。
- `docs/strategy_case_lite/README.md`、schema、tests、CLI、service、models の対象ファイルを plan に追加した。
- `TASK_CHAIN.yaml` の T6 / T7 verification に `tests/strategy_case_lite` を追加した。

## 1. 計画

目的:

1. 実装済みの Case Lite `--artifact` support が active plan に反映されているか確認する。
2. 反映されていなければ、計画文書を current code に合わせて更新する。
3. plan が「古い成功ナラティブ」にならないように、追加実装の対象ファイル、テスト、受け入れ条件を明記する。

対象:

- `plan/2026-06-22-strategy-feedback-case-index/02_TASKS.md`
- `plan/2026-06-22-strategy-feedback-case-index/03_FILE_MAP.md`
- `plan/2026-06-22-strategy-feedback-case-index/04_TEST_AND_ACCEPTANCE.md`
- `plan/2026-06-22-strategy-feedback-case-index/TASK_CHAIN.yaml`

## 2. 現実チェック

分かったこと:

- `02_TASKS.md` は Strategy Input Feedback、Case Index、Workbench Viewer が中心で、Case Lite `--artifact` support を独立タスクとして扱っていなかった。
- `03_FILE_MAP.md` は `strategy_case_lite` の変更対象を含んでいなかった。
- `04_TEST_AND_ACCEPTANCE.md` は `tests/strategy_case_lite` の追加検証を含んでいなかった。
- `TASK_CHAIN.yaml` は T4A 相当の作業を持っていなかった。

誤謬リスク:

- このままだと、後から読むコーダーが Case Lite `--artifact` を計画外の accidental change と誤読する。
- full verification に `tests/strategy_case_lite` が入らず、追加実装の回帰確認が弱くなる。
- backtest-only Case Lite support が Case Index / Viewer dogfood の前提になった事実が plan から抜ける。

## 3. 実装

更新した内容:

### `02_TASKS.md`

追加:

- `T4A: Strategy Case Lite additional artifact input`

主な受け入れ条件:

- `strategy-case-lite-update --help` に `--artifact` が表示される。
- backtest result と strategy review manifest を `--artifact` で渡して Case Lite を生成できる。
- generated Case Lite は `strategy_case_lite.v1` schema validation を通る。
- typed artifact が `latest_source_hashes` で `generic` に潰れない。
- `trend_pullback_user_v1` の backtest-only artifact を Case Lite / Case Index に通せる。
- backtest-only Case Lite は paper / live readiness として扱わない。

### `03_FILE_MAP.md`

追加:

- `src/sis/strategy_case_lite/models.py`
- `src/sis/strategy_case_lite/service.py`
- `src/sis/commands/strategy_case_lite.py`
- `schemas/strategy_case_lite.v1.schema.json`
- `tests/strategy_case_lite/`
- `docs/strategy_case_lite/README.md`

### `04_TEST_AND_ACCEPTANCE.md`

追加:

- `Strategy Case Lite additional artifact input` のテスト方針。
- `uv run pytest tests/strategy_case_lite tests/strategy_input_feedback tests/strategy_case_index tests/strategy_workbench_viewer`

### `TASK_CHAIN.yaml`

追加:

- `T4A: Strategy Case Lite additional artifact input`

修正:

- T6 depends_on に `T4A` を追加。
- T7 verification に `tests/strategy_case_lite` を追加。

## 4. 完了条件

Loop 06 は次を満たした。

- 実装済み差分と active plan のズレを確認した。
- Case Lite `--artifact` support を T4A として明文化した。
- 対象ファイル、受け入れ条件、検証コマンドを plan に追加した。
- backtest-only support を paper/live readiness として扱わない制約を plan に入れた。

## 5. 残った現実的な課題

1. TASK_CHAIN の task order は T4A が T5 の後に表示される。
   - 影響: depends_on では T6/T7 に含めたため検証上の抜けはないが、読み順としてはやや不自然。
   - 理由: 既存 YAML block を最小変更で保った。
   - 改善余地: 後続で task chain を整形するなら、T4A を T4 と T5 の間へ移動する。

2. `strategy_case_lite` の typed artifact は今回使う schema に限定した。
   - 影響: 他の backtest artifact schema はまだ `generic` になる。
   - 理由: 使っていない schema まで一括追加すると責務が広がる。
   - 改善余地: dogfood で必要になった schema だけ追加する。

3. Full verification はまだこの Loop 06 後に未実行。
   - 進める絶対条件: `./scripts/check` を通すこと。

## 6. 次ループ案

### 推奨: Loop 07 は verification-only

状態:

- 実行済み。結果は [16_LOCAL_DOGFOOD_LOOP_07_VERIFICATION_RESULTS.md](16_LOCAL_DOGFOOD_LOOP_07_VERIFICATION_RESULTS.md) を読む。

理由:

- Loop 03-06 で code、schema、docs、plan、runtime artifacts が動いた。
- これ以上コードを増やす前に、focused tests と full `./scripts/check` で破綻を確認するべき。

実行候補:

1. `uv run pytest tests/strategy_case_lite tests/strategy_input_feedback tests/strategy_case_index tests/strategy_workbench_viewer`
2. `uv run python scripts/check_current_docs.py`
3. `uv run python scripts/check_cli_catalog.py`
4. `./scripts/check`
