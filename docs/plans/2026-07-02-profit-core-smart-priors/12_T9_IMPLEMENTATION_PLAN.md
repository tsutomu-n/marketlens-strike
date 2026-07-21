<!--
作成日: 2026-07-02_21:02 JST
更新日: 2026-07-02_21:02 JST
-->

# T9 Implementation Plan

## 結論

T9ではRisk-Taker Review / Actual Cash Report Gateへ渡す前のhandoff artifactを生成する。virtual/backtest evidenceはsource refsとして保持するが、actual cash rowsの代替にはしない。actual cash rows refが無い場合は正式に `BLOCKED_NEEDS_ACTUAL_CASH_ROWS` とする。

## チェックポイントID

CP8 / PR #17 T9

## 目的

既存 `crypto-perp-risk-taker-review` と `crypto-perp-actual-cash-report-gate` へ進める前に、candidate refs、backtest gate refs、virtual gate refs、actual cash rows availabilityを明示し、誤送信を防ぐ。

## 現状

- CP1で `RiskActualCashHandoff` model/schemaは追加済み。
- model validatorは `READY_WITH_ACTUAL_CASH_ROWS` に `actual_cash_rows_ref` を要求する。
- builder moduleと public commandは未実装。

## 制約

- actual cash rowsを生成しない。
- `crypto-perp-risk-taker-review` や `crypto-perp-actual-cash-report-gate` を呼ばない。
- virtual/backtest artifactをactual cash rowsとして扱わない。
- paper/live/wallet/signing/exchange writeは使わない。

## 対象ファイル

新規:

- `docs/plans/2026-07-02-profit-core-smart-priors/12_T9_IMPLEMENTATION_PLAN.md`
- `src/sis/edge_candidate_factory/risk_actual_cash_handoff.py`
- `tests/edge_candidate_factory/test_risk_actual_cash_handoff.py`

変更:

- `src/sis/commands/edge_candidate_factory.py`
- `src/sis/edge_candidate_factory/__init__.py`
- `tests/edge_candidate_factory/test_cli.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `build_risk_actual_cash_handoff()` は必須refsと任意 `actual_cash_rows_ref` から `RiskActualCashHandoff` を返す。
2. rows refなしなら両statusを `BLOCKED_NEEDS_ACTUAL_CASH_ROWS` にする。
3. rows refありなら両statusを `READY_WITH_ACTUAL_CASH_ROWS` にする。
4. `actual_cash_rows_required=true`、`virtual_or_backtest_used_as_actual_cash=false` は固定する。
5. known gapsにrows欠落時の blocker と、virtual/backtest not actual cash evidence を残す。
6. CLIは入力artifact pathをhash化してrefsを作る。actual cash rows pathは明示指定時だけrefにする。
7. rows refなしの stdout は actual-cash-report-gate 呼び出し案を出さない。

## 実装手順

1. RED: handoff builder testsとCLI help/write testsを追加する。
2. GREEN: `risk_actual_cash_handoff.py` を追加する。
3. GREEN: CLI commandとcatalogを追加する。
4. VERIFY: focused tests、schema validation、CLI catalog、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_risk_actual_cash_handoff.py tests/edge_candidate_factory/test_cli.py -q
uv run pytest tests/edge_candidate_factory -q
uv run sis edge-candidate-risk-actual-cash-handoff --help
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

- virtual/backtest artifactだけでは actual cash gate ready にならない。
- actual cash rows refが無い場合、既存 `crypto-perp-actual-cash-report-gate` 呼び出し案を出さない。
- handoff artifactが candidate id と gate refs を保持する。
- `virtual_or_backtest_used_as_actual_cash=true` はvalidationで落ちる。

## 失敗条件

- rows refなしで READY にする。
- virtual/backtest gate refsをactual cash rows refに流用する。
- 既存 risk/actual-cash commandを自動実行する。
- safety stdoutを出さない。

## 影響範囲

edge_candidate_factoryのhandoff module、既存command moduleへのcommand追加、CLI catalog、testsのみ。

## ロールバック方針

T9追加module/tests、command registration、CLI catalog行、plan docを戻す。

## 代替案

- 代替案A: existing risk/actual-cash commandsを自動呼び出しする。T9の目的はhandoff契約なので不採用。
- 代替案B: rows refなしでもrisk review readyにする。actual cash混同を招くため不採用。
- 採用案: rows ref availabilityだけで BLOCKED/READY を決める thin handoff。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- risk reviewが「実務レビュー」でも actual cash rowsなしにREADYへ進めると後段で誤読する。T9は両statusをrows ref有無で揃える。
- virtual/backtest refsは有用なsource refsだがcash evidenceではない。known gapsと boolean fieldで二重に固定する。
- CLI stdoutに次コマンド提案を出すとrows欠落時に危険な誘導になる。statusとartifact pathだけ出す。

## 批判レビュー2

- schema/model validatorに既にREADY rows ref制約があるため、同じ制約をbuilder testで固定する。
- actual cash rowsのschema深読みやrow validationは既存 builder/gate の責任。T9ではref/hashの保存までに留める。
- handoffは外部副作用なしのlocal artifactであり、risk/actual cash command実行は次段の明示作業に残す。
