<!--
作成日: 2026-07-02_20:21 JST
更新日: 2026-07-02_20:21 JST
-->

# T4 Implementation Plan

## 結論

T4では、T3の静的catalogから未検証候補artifactを決定的に生成し、JSON/Markdown/JSONLをローカル出力するCLIを追加する。source ingestion、actual source validation、backtest、virtual execution、paper/live/actual cash連携は実装しない。

## チェックポイントID

CP3 / PR #17 T4

## 目的

`edge_candidate_factory` の初期Coreとして、operatorがローカルCLIで候補report、search ledger、trial multiplicity account、rejection ledgerを生成できるようにする。

## 現状

- CP1でartifact model/schemaは追加済み。
- CP2でSmart Prior taxonomyとdefault candidate card builderは追加済み。
- CLI登録はまだ無い。
- 既存 `strategy-idea-candidates-build` はTyper command、writer result、fail-closed output、CLI catalog更新の参考になる。

## 制約

- `--source-root` はT4では存在確認・中身検査をしない。artifact上のsource refとして記録するだけ。
- network、credentials、wallet、signing、live order、exchange write、production exchange writeは使わない。
- `data/` はruntime出力でありtracked sourceにはしない。
- `--replace-existing`なしで既存出力がある場合はfail closed。
- selected-only outputを禁止し、cap rejectionやduplicate/source blockerをledgerに残す。
- public CLI追加に伴い `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` を更新する。

## 対象ファイル

新規:

- `src/sis/edge_candidate_factory/generator.py`
- `src/sis/edge_candidate_factory/ledger.py`
- `src/sis/commands/edge_candidate_factory.py`
- `tests/edge_candidate_factory/test_generator.py`
- `tests/edge_candidate_factory/test_cli.py`

変更:

- `src/sis/cli.py`
- `src/sis/edge_candidate_factory/__init__.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `EdgeCandidateFactoryConfig` をPydantic modelとして作る。
2. `build_edge_candidate_factory_run()` はT3 family catalogから候補cards、search ledger rows、multiplicity accountを決定的に作る。
3. `write_edge_candidate_factory_run()` は次を出す。
   - `smart_candidate_prior_report.json`
   - `smart_candidate_prior_report.md`
   - `edge_candidate_search_ledger.jsonl`
   - `trial_multiplicity_account.json`
   - `candidate_rejections.jsonl`
4. `candidate_cap` 超過分は `cap_rejection` ledger rowとして保存する。
5. family重複指定は `duplicate` ledger rowとして保存し、候補cardへは重複投入しない。
6. unknown familyはfail closedにする。
7. CLI command名は `edge-candidate-factory-build` にする。

## 実装手順

1. RED: generatorとCLIのacceptance testを追加する。
2. GREEN: `generator.py` にconfig、run result、report/multiplicity builderを追加する。
3. GREEN: `ledger.py` にJSONL writerとmarkdown rendererを追加する。
4. GREEN: `commands/edge_candidate_factory.py` と `cli.py` 登録を追加する。
5. GREEN: CLI catalogへ新commandを追加する。
6. REFACTOR: 出力path、safe stdout、replace-existing判定を最小helperへ寄せる。
7. VERIFY: focused tests、CLI help、CLI catalog、docs、ruff/type、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_generator.py tests/edge_candidate_factory/test_cli.py -q
uv run pytest tests/edge_candidate_factory/test_models.py tests/edge_candidate_factory/test_schema_validation.py tests/edge_candidate_factory/test_smart_priors.py -q
uv run sis edge-candidate-factory-build --help
uv run python scripts/check_cli_catalog.py
uv run ruff check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py tests/edge_candidate_factory
uv run ruff format --check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py tests/edge_candidate_factory
uv run pyrefly check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py
uv run ty check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py --python-version 3.13 --output-format concise
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## 完了条件

- CLIが正常系で5 artifactを出す。
- stdoutに安全fieldとartifact path、known_gap_countが出る。
- `--replace-existing`なしの再実行がexit 2で止まる。
- cap超過とduplicateがledgerに保存される。
- 出力JSONがCP1 schemaを通る。
- public CLI catalog checkerが通る。

## 失敗条件

- source-rootの現物検査を始めてT5以降の責務を混ぜる。
- selected-only outputになる。
- cap rejectionやduplicateをsilent dropする。
- paper/live/actual cashに進めるようなstatusやboundaryを出す。
- CLI catalog更新漏れでcheckerが落ちる。

## 影響範囲

新CLI command、edge_candidate_factory package内writer/generator、CLI catalog、testsのみ。既存Strategy Idea Candidate commandの挙動は変更しない。

## ロールバック方針

T4追加ファイル、`cli.py`登録、CLI catalog行、計画docを戻す。runtime出力は`data/`配下なのでgitには入れない。

## 代替案

- 代替案A: `strategy-idea-candidates-build`へ統合する。既存候補生成とSmart Prior Coreの責務が混ざる。
- 代替案B: source-root実検査まで実装する。T5以降のsource availabilityに踏み込み、T4が大きくなる。
- 採用案: T4はdeterministic local writerに限定する。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- `source-root`を受ける名前は誤読されやすい。T4では検査せず、artifactのsource refとknown gapに「source availability not checked」を残す。
- reportとledgerを両方出すため、row countとcandidate countの整合をテストする。
- CLI stdoutは既存commandの`status=pass`だけでは不足。PR #17のstdout conventionsに合わせて安全fieldを必ず出す。

## 批判レビュー2

- candidate capで候補card自体を全削除すると探索量が消える。accepted/generated cardsはcap内に制限し、cap外はsearch ledgerの`cap_rejection`として保存する。
- duplicate family指定はfailではなくledgerに残す方が探索会計として正しい。ただしcandidate cardは重複生成しない。
- multiplicity accountは統計補正を推定しない。`NOT_ESTIMABLE` とknown gapを正式結果として残す。
