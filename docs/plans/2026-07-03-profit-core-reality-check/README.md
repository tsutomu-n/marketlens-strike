<!--
作成日: 2026-07-03_10:10 JST
更新日: 2026-07-03_10:10 JST
-->

# Profit Core Reality Check Sprint

## 結論

次にやることは、PR #17 の Smart Edge Candidate Factory / Multiplicity / Virtual Gate を上から全部実装することではない。

まず、既存の候補生成、search ledger、C9 v0 authoring bridge、risk-taker review、actual-cash gate 周辺 artifact を読み、候補がどこで何件止まるかを 1 枚の reality check artifact に集約する。

この sprint の成果物は次です。

```text
profit_core_reality_check.v1
profit_core_reality_check.md
```

この artifact は profit proof ではない。目的は、実データで既存 pipeline を通した時の blocker 分布、candidate lineage の断絶、actual cash 到達条件の不足、次に直すべき single blocker を明示することです。

## 背景

現 repo には、候補生成、search ledger、selection-adjusted metrics、Bitget USDT-FUTURES risk-taker profile、Perp local cost estimate、Perp estimate bridge、C9 v0 Prep Watchdeck authoring bridge、risk-taker review、actual-cash rows / gate の土台が既にある。

一方で、PR #17 の計画は docs-only の大設計です。Smart Prior Generator、Trial Multiplicity Account、Backtest Kill Gate、Virtual Execution Gate、LLM Adversarial Review をすべて実装する前に、既存 pipeline の詰まりを実Repoのartifactで測る必要がある。

## 目的

1. 既存機能だけで、candidate generation から C9 bridge、risk review、actual-cash readiness までの到達状況を集計する。
2. `BRIDGED` を economic pass と誤読しないよう、technical bridge と economic readiness を分離して表示する。
3. 候補生成を強化すべきか、C9 bridge を広げるべきか、actual cash input を作るべきか、virtual lifecycle を作るべきかを、blocker 分布で決める。
4. PR #17 を設計バックログとして維持しつつ、今すぐ必要な最小実装だけを切り出す。

## 非目的

この sprint では次をやらない。

- Smart Prior Generator 新規実装。
- GA / ML / LightGBM / Optuna 導入。
- Hyperliquid / GRVT 対応。
- external LLM API 実装。
- full Virtual Execution Gate 実装。
- Bitget demo / testnet の実 order lifecycle 実行。
- actual cash rows の捏造または preview / estimate / virtual PnL からの変換。
- production live trading、wallet、signing、production exchange write。

## 制約

1. `profit_core_reality_check` は既存 artifact を読むだけにする。
2. network access、credentials、exchange write、live order は使わない。
3. `data/` runtime artifact を tracked source of truth にしない。
4. optional input が欠けている場合は `missing` として扱い、勝手に生成しない。
5. `BRIDGED` は technical bridge status として扱う。
6. `actual_cash_result_usd` は ledger-connected actual cash basis だけを actual cash として扱う。
7. `NO_TRADE` を失敗扱いしない。
8. candidate id、path、hash の lineage が切れたら、停止理由として表示する。

## 実装対象

新規:

```text
src/sis/profit_core_reality_check/__init__.py
src/sis/profit_core_reality_check/models.py
src/sis/profit_core_reality_check/readers.py
src/sis/profit_core_reality_check/summarize.py
src/sis/profit_core_reality_check/rendering.py
src/sis/commands/profit_core_reality_check.py
schemas/profit_core_reality_check.v1.schema.json
tests/profit_core_reality_check/test_models.py
tests/profit_core_reality_check/test_readers.py
tests/profit_core_reality_check/test_summarize.py
tests/profit_core_reality_check/test_cli.py
```

変更:

```text
src/sis/cli.py
scripts/check_cli_catalog.py の期待更新が必要な場合はCLI catalog docs更新で対応
docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md
docs/IMPLEMENTED_SURFACES.md
docs/CURRENT_STATE.md
```

ただし、`docs/IMPLEMENTED_SURFACES.md` と `docs/CURRENT_STATE.md` は、実装PRで current surface として入った後だけ更新する。この docs-only plan PR では更新しない。

## 新CLI

```bash
uv run sis profit-core-reality-check \
  --candidate-set <strategy_idea_candidate_set.json> \
  --search-ledger <search_ledger.jsonl> \
  --export-manifest <strategy_idea_candidate_export_manifest.json> \
  --authoring-bridge <strategy_idea_candidate_authoring_bridge_manifest.json> \
  --risk-review <risk_taker_review.json> \
  --profit-readiness-inventory <profit_readiness_inventory.json> \
  --source-availability <source_availability.json> \
  --actual-cash-rows-summary <actual_cash_rows_summary.json> \
  --actual-cash-report-gate <manifest.json> \
  --out data/profit_core_reality_check/latest
```

すべての入力を必須にしない。必須は candidate-set と search-ledger のみ。その他はあれば読む。無い場合は missing として artifact に残す。

## 出力

```text
profit_core_reality_check.json
profit_core_reality_check.md
```

stdout は最低限次を出す。

```text
network_attempted=false
credentials_used=false
exchange_write_used=false
production_exchange_write_used=false
live_order_submitted=false
permits_live_order=false
status=<complete|blocked>
next_single_blocker_to_fix=<reason>
reality_check_path=<path>
report_path=<path>
known_gap_count=<int>
```

## 文書構成

この folder のファイル:

1. `README.md`: sprint全体の目的、制約、実装対象。
2. `01_CURRENT_REPO_FACTS.md`: 現repo事実とPR #17の位置づけ。
3. `02_EXISTING_PIPELINE_TRACE.md`: 既存pipelineと入力/出力artifact。
4. `03_REALITY_CHECK_ARTIFACT_SPEC.md`: schema / field / status / summary仕様。
5. `04_DOGFOOD_RUNBOOK.md`: BTCUSDT / ETHUSDT で既存pipelineを通す手順。
6. `05_BLOCKER_TAXONOMY.md`: blocker taxonomy と next action mapping。
7. `06_NEXT_DECISION_AFTER_DOGFOOD.md`: dogfood結果ごとの次PR判断。

## 完了条件

この sprint 実装の完了条件:

1. `profit_core_reality_check.v1` schema と Pydantic model がある。
2. candidate-set と search-ledger だけで reality check が生成できる。
3. authoring bridge manifest がある場合、BRIDGED / BLOCKED の分布を集計できる。
4. `BRIDGED` は `technical_only` として表示される。
5. risk review がある場合、status count と known gaps を集計できる。
6. actual cash rows summary / report gate が無い場合、actual_cash_available_count は 0 または unknown になり、補完しない。
7. `next_single_blocker_to_fix` が deterministic に出る。
8. すべてのpermission boundaryが false。
9. focused tests と `./scripts/check` が通る。

## 最終ローカル検証

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run ty check src --python-version 3.13 --output-format concise
uv run pytest tests/profit_core_reality_check -q
uv run pytest tests/strategy_idea_candidates/test_candidate_cli.py -q
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
uv run pytest tests/crypto_perp/test_risk_taker_review.py -q
./scripts/check
```

固定pass countは書かない。作業時点で再実行する。
