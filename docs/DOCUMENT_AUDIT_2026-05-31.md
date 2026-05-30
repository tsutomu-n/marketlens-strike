# Documentation Audit 2026-05-31

コード、tests、CLI help、schemas、current docs lint を正として、現行ドキュメントを再分類した結果です。

## 結論

現行 docs は、Strategy Authoring 完了後のコードに対して大筋では追従しています。ただし、2026-05-30 audit 以降に Strategy Authoring coverage が完了したため、検証値と audit 正本に古さが残っていました。

今回の current truth:

- additional audit baseline HEAD: `847e0fc`
- root CLI: `uv run sis --help` で `strategy-author-init`, `strategy-author-validate`, `strategy-author-explain`, `strategy-author-run`, `strategy-author-bundle-run`, `strategy-author-train-model` を確認。
- docs lint: `uv run python scripts/check_current_docs.py` が current docs `78` 件を検査。
- full gate: `./scripts/check` は `586 passed` を最新の全体検証値として扱う。
- Strategy Authoring completion evidence: `docs/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md`。

## Code Truth

現行コードで確認した主要 surface:

```text
src/sis/cli.py
src/sis/commands/strategy_authoring.py
src/sis/research/strategy_lab/authoring.py
src/sis/backtest/bridge.py
src/sis/backtest/signals.py
schemas/strategy_authoring_spec.v1.schema.json
schemas/strategy_authoring_bundle.v1.schema.json
schemas/strategy_authoring_backtest_result.v1.schema.json
schemas/strategy_authoring_bundle_result.v1.schema.json
tests/test_strategy_authoring.py
tests/test_strategy_lab_schemas.py
```

現行 Strategy Authoring boundary:

- YAML authoring は paper-only の strategy generation / signal generation / fixed-horizon backtest / paper-preview / multi-strategy bundle comparison を扱う。
- live order、wallet、exchange write、live atomic multi-leg execution、live bracket/OCO、full order book event replay、profitability / live-ready claim は対象外。
- tracked JSON Schema は interoperability 用の thin guard。詳細 validation は Pydantic model と tests が正本。
- `data/` と `data/reports/` は runtime artifact。古い artifact report があっても、コード未実装の根拠にしない。

## 更新できるドキュメント

| Path | 理由 | 推奨更新 |
|---|---|---|
| `README.md` | read-first と verification 値の入口 | audit 正本を本ファイルへ差し替え、`586 passed` / current docs `78` 件へ更新 |
| `docs/CURRENT_STATE.md` | current truth の入口 | Strategy authoring command list に `strategy-author-train-model` を追加し、検証値を更新 |
| `docs/CODE_STATUS.md` | 実装状態一覧 | verification を 2026-05-31 / `586 passed` / current docs `78` 件へ更新 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | capabilities の current entry | check 結果を `586 passed` / current docs `78` 件へ更新 |
| `docs/strategy_research_lab/11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md` | authoring の現状説明 | check 結果を `586 passed` / current docs `78` 件へ更新 |
| `docs/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md` | 進捗まとめ | 最終検証値だけ 2026-05-31 完了 gate へ追記更新 |
| `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md` | Strategy Lab audit/spec の入口 | 全体 docs audit の参照先を `docs/DOCUMENT_AUDIT_2026-05-31.md` へ差し替え |
| `docs/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md` | completion evidence ledger | 05-31 audit 追加前の current-docs count `77` を、現行 count `78` へ注記更新 |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | current docs allowlist の説明 | current audit を `docs/DOCUMENT_AUDIT_2026-05-31.md` へ差し替え |
| `docs/archive/README.md` | archive と current docs の境界説明 | current audit を本ファイルへ差し替え |
| `scripts/check_current_docs.py` | current docs strict check の正本 | `docs/DOCUMENT_AUDIT_2026-05-31.md` を current audit として検査対象化 |

## 古い内容があるドキュメント

| Path | 古い内容 | 現在の扱い |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-05-30.md` | Strategy Authoring completion 前の audit。`446 passed` / 2026-05-30 前提の表現が残る | superseded audit。現行入口は本ファイル |
| `README.md` | `565 passed`, current docs `76` 件 | この変更で `586 passed` / `78` 件へ修正済み |
| `docs/CURRENT_STATE.md` | `565 passed`, current docs `76` 件、authoring command list に `strategy-author-train-model` が無い | この変更で修正済み |
| `docs/CODE_STATUS.md` | `565 passed`, current docs `76` 件 | この変更で修正済み |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | `565 passed`, current docs `76` 件 | この変更で修正済み |
| `docs/strategy_research_lab/11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md` | `565 passed`, current docs `76` 件 | この変更で修正済み |
| `docs/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md` | `181 passed` / schema tests `2 passed` / full gate `565 passed` の中間 snapshot | historical progress doc として有効。この変更で最終 focused gate `204 passed` と full gate `586 passed` へ更新済み |
| `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md` | 全体 docs audit の参照先が `docs/DOCUMENT_AUDIT_2026-05-30.md` のまま | この変更で current audit `docs/DOCUMENT_AUDIT_2026-05-31.md` へ修正済み |
| `docs/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md` | `checked 77 current docs` は 05-31 audit 追加前の値 | この変更で現行 `checked 78 current docs` も併記 |
| `README.md`, `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md` | `LIVE_READINESS_BLOCKER=6` が最新 `phase-gate-review` の `5` とズレていた | この変更で `LIVE_READINESS_BLOCKER=5` へ修正済み |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | `294 passed` と 2026-05-28 runtime snapshot | focused historical audit。Trade[XYZ] read-only 証跡として読む。current full gate として引用しない |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | What To Read が `docs/DOCUMENT_AUDIT_2026-05-30.md` を指していた | この変更で `docs/DOCUMENT_AUDIT_2026-05-31.md` へ修正済み |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` | `294 passed` を含む 2026-05-28 failure-mode snapshot。read-first が `docs/DOCUMENT_AUDIT_2026-05-30.md` を指していた | design reference。current verification 値として引用しない。read-first 参照はこの変更で `docs/DOCUMENT_AUDIT_2026-05-31.md` へ修正済み |
| `docs/algo/obsidian_note_rewrites_2026-05-28/` | 2026-05-29 rewrite bundle より古い初版 rewrite | historical snapshot。current入口にしない |
| `plan/archive/**` | 実装前/実装中の計画 | historical migration contract。現行状態は `docs/CURRENT_STATE.md` と code を優先 |
| `data/reports/*.md`, `data/research/*.md` | runtime 生成時点の snapshot | 必要なら CLI で再生成。tracked docs の current truth とは分ける |

## 作り直したほうがいいドキュメント

| Path | 推奨 | 理由 |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-05-30.md` | 作り直し済み: `docs/DOCUMENT_AUDIT_2026-05-31.md` | Strategy Authoring completion evidence と最新 gate を含まない |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | 必要なら `current Trade[XYZ] status audit` と `historical PR12 audit` に分離 | 2026-05-28 runtime evidence と current full gate を混同しやすい |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` | 必要なら current blocker map だけの短い新版を作る | failure-mode catalog と古い検証 snapshot が同居している |
| `docs/trade_xyz_bot_beginner_guide.html` | 部分再作成候補 | Strategy Authoring / PaperIntentPreview の初心者向け導線をさらに厚くできる |
| `docs/algo/obsidian_note_rewrites_2026-05-28/` | 作り直すより archive 扱いを継続 | 2026-05-29 bundle に superseded |

## 削除・アーカイブしてもよいドキュメント

物理削除より archive / historical 扱いを推奨します。

| Path | 推奨 | 理由 |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-05-30.md` | 次回整理時に `docs/archive/2026-05-31-doc-audit/` へ移動可 | 本ファイルに superseded。今回はリンク差し替えで十分 |
| `docs/algo/obsidian_note_rewrites_2026-05-28/` | archive 扱い継続、current docs lint 対象外 | 2026-05-29 rewrite bundle が現行参照 |
| `plan/archive/**` | 削除せず archive 維持 | 実装済み計画の証跡として有用 |
| `docs/archive/**` | 削除せず archive 維持 | 過去判断の証跡。current docs ではない |
| `.tmp/**/*.md` | repo commit 対象にしない。必要なければ作業者ローカルで削除可 | 作業中 snapshot / handoff material であり current docs ではない |
| `.pytest_cache/README.md` | 削除可だが git 管理対象ではない | pytest cache 由来。docs audit 対象外 |

削除しない:

- `docs/strategy_research_lab/**`: current Strategy Authoring / Strategy Lab docs。
- `docs/algo/strategy_factory/**`: strategy candidate intake と factory workflow の current docs。
- `docs/algo/obsidian_note_rewrites_2026-05-29/**`: strategy design reference として current docs lint 対象。
- `plan/marketlens_strategy_research_lab_migration_pack/**`: historical implementation contract として有用。

## Current Read Rules

- 実装済み判定は code / tests / schemas / CLI help を優先する。
- docs の検証値は `2026-05-31 code/docs verification` を優先する。
- `READ_ONLY_GO` を production live ready と読まない。
- `PaperIntentPreview` を live order と読まない。
- Strategy Authoring の paper-only completion を live execution readiness と混同しない。
- `data/research/signals.csv` を Strategy Lab 正本にしない。
- historical plan / archive から current command を拾わない。
- `data/` artifact が無いだけで未実装と判断しない。必要なら CLI で再生成する。

## Verification Used For This Audit

```bash
git status --short --branch --untracked-files=all
git rev-parse --short HEAD
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
rg -n "565 passed|586 passed|446 passed|294 passed|checked 76|checked 78|strategy-author-|strategy_authoring_backtest_result|strategy_authoring_bundle_result|13_STRATEGY_ARCHETYPE|14_COMPLETION_EVIDENCE" README.md docs/CURRENT_STATE.md docs/CODE_STATUS.md docs/DOCUMENT_AUDIT_2026-05-30.md docs/strategy_research_lab docs/algo/README.md docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md -g '*.md' -g '*.html'
rg -n "DOCUMENT_AUDIT_2026-05-30|DOCUMENT_AUDIT_2026-05-31|checked 77|checked 78|6609575|847e0fc" README.md docs plan -g '*.md' -g '*.html'
rg -n "@app\.command|def register_|strategy_author|strategy-experiment-run|build-paper|promotion|paper-from-intents|bot-preview" src/sis/commands src/sis/cli.py src/sis/research/strategy_lab src/sis/backtest -g '*.py'
```

確認結果:

- additional audit started clean at `847e0fc`.
- docs lint passed before edits: `checked 78 current docs: links, EOF, and legacy roots ok`.
- full gate passed: `586 passed`.
- CLI help includes the Strategy Authoring commands and paper-only Strategy Lab commands.
- stale verification values are now limited to superseded/historical docs or explicitly historical snapshots.
- additional stale current-doc pointers to `docs/DOCUMENT_AUDIT_2026-05-30.md` were found and corrected in this pass.
