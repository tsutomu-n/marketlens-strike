<!--
作成日: 2026-07-01_21:05 JST
更新日: 2026-07-01_21:05 JST
-->

# Profit Core Completion Implementation Package

## 結論

この folder は、`docs/plans/profit-core-long-horizon-goal-checkpoints-2026-06-30.md` の P0-P13 を、コーダーが chat transcript なしで完了・再現・監査できる粒度に落とした実装 package です。

2026-07-01_21:05 JST 時点の code truth では、P1-P13 の主要 schema、source module、tests、public CLI は実装済みです。したがって、この package の目的は「未実装を煽ること」ではなく、次のどちらにも使える completion contract を残すことです。

- 現在 branch の P0-P13 実装を検証して完了判定する。
- 古い branch / fresh branch から P0-P13 を再実装する時に、この順序と acceptance で復元する。

## 読む順番

1. `README.md`: この package の目的、正本、境界。
2. `IMPLEMENTATION_PLAN.md`: P0-P13 の実装順、対象ファイル、完了条件。
3. `TASK_CHAIN.yaml`: solo coder がそのまま消化できる task chain。
4. `VERIFICATION_MATRIX.md`: focused / adjacent / full verification command。
5. `APPENDIX_ARTIFACT_SOURCE_MAP.md`: schema、module、CLI、test の対応表。
6. `APPENDIX_BOUNDARIES_RISKS_AND_OMISSIONS.md`: Must-not-break、止める条件、抜け漏れリスク。

## 実装の正本

優先順位:

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`
2. CLI help: `uv run sis --help`
3. `pyproject.toml`, `.python-version`, `uv.lock`, `.github/workflows/ci.yml`
4. current docs under `docs/`
5. historical plan docs under `docs/plans/`, `plan/`, `docs/archive/`

この package は current truth を説明する docs です。実装の正本ではありません。

## 完成の定義

P0-P13 completion は次を満たすことです。

- Candidate lineage が protocol、multiplicity、bridge、backtest kill gate、virtual gate、evidence packet、actual cash readiness、tiny actual-cash measurement、actual cash report gate、feedback calibration まで切れない。
- `actual_cash` と `backtest` / `virtual_exchange` / `paper` / `demo` / `testnet` / `estimate` が同じ metric として混ざらない。
- `NO_TRADE` comparison が first-class outcome であり、actual-cash promotion では `actual_cash_edge_over_NO_TRADE` が必須。
- `BRIDGED_TECHNICAL_ONLY`、`SHORTLIST_FOR_VIRTUAL`、`READY_FOR_HUMAN_REVIEW`、`AVAILABLE` は permission ではない。
- LLM は adversarial reviewer であり、official metric、PnL、actual_cash 判定、gate override、paper/live/tiny-live 許可をしない。
- Tiny actual-cash は artifact recording path だけであり、この package から credential use、external write、live order、wallet、signing は実行しない。
- P13 は feedback calibration proposal であり、既存 protocol / multiplicity account / threshold を自動変更しない。

## Out Of Scope

- 本番 deploy。
- 課金が発生する操作。
- 外部サービスへの送信。
- credential 作成、変更、使用、削除。
- exchange write、wallet、signing、live order、tiny-live execution。
- demo/testnet/legal/account-condition を current verification なしに固定すること。
- P13 calibration output から次 protocol を自動生成・自動適用すること。

## Grill Result

確認した正本:

- `AGENTS.md`
- `./.ai_memory/HANDOFF.md`
- `docs/plans/profit-core-long-horizon-goal-checkpoints-2026-06-30.md`
- `docs/final-summary.md`
- `docs/CURRENT_STATE.md`
- `schemas/*profit_core*`, `schemas/candidate_protocol_manifest.v1.schema.json`, `schemas/trial_multiplicity_account.v1.schema.json`, `schemas/backtest_kill_gate.v1.schema.json`, `schemas/virtual_execution_gate.v1.schema.json`
- `src/sis/edge_candidates/`
- `src/sis/strategy_idea_candidates/`
- `tests/edge_candidates/`
- `tests/strategy_idea_candidates/`
- `uv run sis --help`

用語衝突:

- `actual_cash`: 実 fill / fee / funding / cash ledger に基づく証拠だけ。paper、demo、testnet、virtual、estimate とは別 basis。
- `BRIDGED_TECHNICAL_ONLY`: 技術接続であり、alpha/profit/paper/live proof ではない。
- `AVAILABLE`: 補正計算や source が利用可能という意味であり、performance pass ではない。
- `READY_FOR_HUMAN_REVIEW`: human review input であり、permission ではない。
- `risk_taker_sprint`: attack mode であり、本命成績には混ぜない。

責任境界:

- `strategy_idea_candidates` は candidate set、ledger、bridge を扱う。
- `edge_candidates` は Profit Core gates と evidence artifacts を扱う。
- `research/strategy_lab`、`backtest`、`paper`、`execution` は既存 subsystem として残し、Profit Core artifact を permission に読み替えない。

仕様化 readiness: ready.

Assumption:

- この docs package は current code を前提にした completion/replay plan であり、実 actual-cash execution を開始する runbook ではない。
