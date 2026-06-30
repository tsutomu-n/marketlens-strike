<!--
作成日: 2026-06-30_20:36 JST
更新日: 2026-06-30_20:36 JST
-->

# Profit Core CP1-CP3 Implementation Plan

## チェックポイントID

CP1 `candidate_protocol_manifest.v1`
CP2 `trial_multiplicity_account.v1`
CP3 thin `backtest_kill_gate.v1`

## 目的

`docs/profit_core_hybrid_modes/IMPLEMENTATION_CHECKPOINTS.md` の最初の実装 slice だけを実装する。候補生成そのものを増やす前に、探索空間固定、試行会計、薄い backtest kill gate を schema / Python model / focused tests で固定する。

## 現状

- Profit Core hybrid modes docs は docs-only decision package として存在する。
- `candidate_protocol_manifest.v1`、`trial_multiplicity_account.v1`、`backtest_kill_gate.v1` はまだ実装されていない。
- 既存 repo には `strategy_idea_candidates` の candidate set、search ledger、selection-adjusted metrics、C9 bridge 補助 surface がある。
- 既存 selection-adjusted metrics は raw p-value がある時だけ BH/FDR を `AVAILABLE` にし、DSR / PBO / White Reality Check は入力不足時 `NOT_ESTIMABLE` に止める。
- 開始時 worktree には pre-existing modified `docs/profit_core_hybrid_modes/APPENDIX_RESEARCH_EVIDENCE.md` と untracked `資料/意見0630.md` がある。今回の実装では触らない。

## 制約

- scope は CP1-CP3 のみ。
- `actual_cash` と virtual / proxy / estimate を混ぜない。
- `NO_TRADE` を first-class outcome として扱う。
- success-only reporting を禁止する。
- sealed holdout を selection に使わない。
- `risk_taker_sprint` は隔離 mode とし、本命集計や actual cash 直行に混ぜない。
- 統計入力が足りない場合は `NOT_ESTIMABLE` を正式結果にする。
- GA / ML、external venue adapters、Bitget / Hyperliquid / GRVT execution、LLM API integration、tiny-live / live execution、依存関係変更、broad UI / workbench work は実装しない。
- 外部送信、課金、秘密情報変更、不可逆削除、`git push` はしない。

## 対象ファイル

- `schemas/candidate_protocol_manifest.v1.schema.json`
- `schemas/trial_multiplicity_account.v1.schema.json`
- `schemas/backtest_kill_gate.v1.schema.json`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/edge_candidates/protocol.py`
- `src/sis/edge_candidates/multiplicity.py`
- `src/sis/edge_candidates/backtest_kill_gate.py`
- `src/sis/commands/edge_candidates.py`
- `src/sis/cli.py`
- `tests/edge_candidates/__init__.py`
- `tests/edge_candidates/test_protocol_manifest.py`
- `tests/edge_candidates/test_multiplicity_account.py`
- `tests/edge_candidates/test_backtest_kill_gate.py`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## 実装方針

- 既存の Pydantic v2 model style を踏襲する。
- schema は draft 2020-12、`additionalProperties: false` を基本にする。
- CLI は validation / artifact write 用の薄い command に留め、候補生成、外部 venue、実行、LLM 呼び出しはしない。
- CP1 は protocol manifest の固定と boundary false を優先する。
- CP2 は trial accounting の整合性と method status を優先する。高度な統計計算は入れず、入力不足を明示する。
- CP3 は candidate-level gate state を決めるだけにする。`SHORTLIST_FOR_VIRTUAL` は permission ではないことを model と output に固定する。

## 実装手順

1. 既存 schema / Pydantic / CLI / test pattern を確認する。
2. CP1 の失敗テストを追加する。
3. CP1 の schema、model、CLI registration を実装する。
4. CP1 focused tests と CLI catalog check を実行する。
5. CP2 の失敗テストを追加する。
6. CP2 の schema と model を実装する。
7. CP2 focused tests と関連 strategy idea candidate tests を実行する。
8. CP3 の失敗テストを追加する。
9. CP3 の schema と model を実装する。
10. CP3 focused tests と関連 crypto perp gate / bias guard tests を実行する。
11. docs を編集した場合は current-doc check を実行する。
12. `git diff --check` と最終 status / diff review を実行する。

## テスト方針

CP1:

```bash
uv run pytest tests/edge_candidates/test_protocol_manifest.py -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
git diff --check
```

CP2:

```bash
uv run pytest tests/edge_candidates/test_multiplicity_account.py -q
uv run pytest tests/strategy_idea_candidates/test_candidate_set_validation.py tests/strategy_idea_candidates/test_candidate_generator.py -q
git diff --check
```

CP3:

```bash
uv run pytest tests/edge_candidates/test_backtest_kill_gate.py -q
uv run pytest tests/crypto_perp/test_tournament_gate.py tests/crypto_perp/test_bias_guards.py -q
git diff --check
```

最終確認:

```bash
uv run pytest tests/edge_candidates/test_protocol_manifest.py tests/edge_candidates/test_multiplicity_account.py tests/edge_candidates/test_backtest_kill_gate.py -q
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```

## 完了条件

- CP1-CP3 の schema が存在し、focused schema validation tests が通る。
- CP1 model は `verification_throughput` / `risk_taker_sprint`、boundary false、sealed holdout 必須、sprint isolation 必須を enforce する。
- CP2 model は success-only reporting 禁止、sealed test selection 禁止、BH/FDR availability 条件、PBO / DSR / White Reality Check の `NOT_ESTIMABLE` を enforce する。
- CP3 model は missing NO_TRADE comparison、event count policy、after-cost edge、source gap、permission false を enforce する。
- 追加 CLI surface がある場合は help と catalog check で検証する。
- current-doc checker、focused tests、whitespace check が通る。

## 失敗条件

- `SHORTLIST_FOR_VIRTUAL`、`AVAILABLE`、`BRIDGED` などを paper / live / actual cash permission と誤読できる。
- `risk_taker_sprint` が actual cash へ直行できる。
- `PBO` / `DSR` / `White Reality Check` の入力不足を pass として扱う。
- event count を全 family 一律閾値で無条件 KILL する。
- external venue / LLM / live execution に scope が広がる。

## 影響範囲

新規 schema、Python model、薄い CLI command、focused tests。既存 generated runtime artifacts は変更しない。

## ロールバック方針

この plan の対象新規ファイルを削除し、`src/sis/cli.py` の `edge_candidates` 登録だけを戻す。pre-existing modified docs と untracked `資料/意見0630.md` は rollback 対象外。

## 代替案

- 既存 `strategy_idea_candidates` に直接統合する案: CP1-CP3 の責務が candidate generation 実装に混ざるため採用しない。
- CP1-CP3 を一つの巨大 schema にする案: checkpoint ごとの検証が弱くなるため採用しない。
- PBO / DSR / SPA / White の実計算まで入れる案: 必要入力がまだ不足しており、初手として過剰なので採用しない。

## 未解決事項

なし。外部 venue、LLM、tiny-live / live、依存関係変更が必要になった場合はこの goal の範囲外として止める。

## 破壊的変更の有無

破壊的操作はしない。schema / CLI の新規追加はあるが、既存 API の削除や既存データの不可逆変更はしない。

## ブランチ名

`ai/profit-core-cp1-cp3-20260630-2036`

## 移行手順

なし。新規 artifact contract を追加するだけで、既存 artifact の migration はしない。

## 実装前 Critique

- CP1-CP3 を一度に実装すると広く見えるが、3 つは false positive を止める最小単位として依存している。実行は checkpoint ごとに分ける。
- CP2 で高度統計を実装したくなるが、今回は `NOT_ESTIMABLE` と会計の欠損理由を first-class にする方が重要。
- CP3 は permission gate ではない。名前や output に permission false を入れて誤読を防ぐ。
- CLI を追加しすぎると public surface が太る。まず validation / artifact write の薄い command に限る。

Readiness: ready with assumptions.
