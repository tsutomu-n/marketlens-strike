<!--
作成日: 2026-07-02_21:15 JST
更新日: 2026-07-02_21:15 JST
-->

# T11 Implementation Plan

## 結論

T11では日常確認用の `edge-candidate-artifact-summary` を追加する。欠損artifactは失敗にせず `exists=false` として集約し、Core statusはCore artifactだけから決める。Addon的なadversarial review結果は known gaps / blockers には反映しても、Core statusを勝手に昇格しない。

## チェックポイントID

CP10 / PR #17 T11

## 目的

Smart Priors実装で増えたartifact群を1画面で読み、次の作業が「source収集」「backtest」「virtual」「actual cash rows」「review」なのかを判定しやすくする。

## 現状

- T4-T10でcandidate report、multiplicity、backtest kill gate、virtual gate、risk/actual cash handoff、adversarial reviewのCLIが追加済み。
- 日常確認用の統合summaryは未実装。

## 制約

- 新規schemaは追加しない。
- 欠損artifactでcommandを失敗させない。
- production exchange write / live order permissionは常にfalseとして出す。
- Addon結果をCore statusに混ぜない。

## 対象ファイル

新規:

- `docs/plans/2026-07-02-profit-core-smart-priors/14_T11_IMPLEMENTATION_PLAN.md`
- `src/sis/edge_candidate_factory/summary.py`
- `tests/edge_candidate_factory/test_summary.py`

変更:

- `src/sis/commands/edge_candidate_factory.py`
- `src/sis/edge_candidate_factory/__init__.py`
- `tests/edge_candidate_factory/test_cli.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `build_edge_candidate_artifact_summary()` は任意path群を読み、存在しないものは `exists=false` として記録する。
2. candidate countsは `smart_candidate_prior_report.v1` から読む。
3. virtual pass countは `virtual_execution_gate.v1` の `gate_status=VIRTUAL_PASSED_EXECUTION_LIFECYCLE` から読む。
4. actual cash ready countは `edge_candidate_risk_actual_cash_handoff.v1` の `actual_cash_report_gate_input_status=READY_WITH_ACTUAL_CASH_ROWS` から読む。
5. shortlist for virtual countはT6/T8の責任境界上 v0では0にする。
6. known gapsはCore artifactの `known_gaps`、missing artifact、blocked gate statusから集約する。
7. CLIはsummary JSONを書き、stdoutにも主要fieldを出す。

## 実装手順

1. RED: summary builder testsとCLI help/write testsを追加する。
2. GREEN: `summary.py` を追加する。
3. GREEN: CLI commandとcatalogを追加する。
4. VERIFY: focused tests、CLI catalog、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_summary.py tests/edge_candidate_factory/test_cli.py -q
uv run pytest tests/edge_candidate_factory -q
uv run sis edge-candidate-artifact-summary --help
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

- 欠損artifactを `exists=false` として表示し、失敗しない。
- 日常判断に必要なstatusを1画面で読める。
- Addon結果をCore statusに混ぜない。
- stdoutに `production_exchange_write_used=false`, `live_order_allowed=false`, `known_gap_count=<int>` が出る。

## 失敗条件

- missing artifactでcommand全体を失敗させる。
- LLM/adversarial reviewでCore statusをreadyにする。
- virtual passをactual cash readyにする。
- safety stdoutを出さない。

## 影響範囲

edge_candidate_factory summary module、既存command moduleへのcommand追加、CLI catalog、testsのみ。

## ロールバック方針

T11追加module/tests、command registration、CLI catalog行、plan docを戻す。

## 代替案

- 代替案A: 全artifactへ厳密schema validationをかける。summary commandが重くなり、欠損に弱くなるため不採用。
- 代替案B: stdoutだけにする。後段の自動確認で再利用しにくいためJSON artifactも書く。
- 採用案: tolerant JSON summary + concise stdout。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- summary は判断補助であり、新しいgateではない。Core statusを昇格する権限を持たせない。
- missing artifactをerrorにすると日常確認で使いにくい。missingを明示しつつ次actionを返す。
- `shortlist_for_virtual_count` は現T6が `SHORTLIST_FOR_VIRTUAL` を出さないため0固定が正しい。

## 批判レビュー2

- known gap countを全artifactの単純合計にするとノイズが増える。v0はmissingとCore blockersを中心に数える。
- Addonのadversarial reviewはoverclaim検出として有用だが、Core statusのready判定には混ぜない。
- actual cash readinessはhandoffの rows ref statusだけを読む。virtual gate passはactual cash readyではない。
