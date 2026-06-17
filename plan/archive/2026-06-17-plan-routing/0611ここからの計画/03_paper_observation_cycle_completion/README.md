<!--
作成日: 2026-06-11_23:57 JST
更新日: 2026-06-11_23:57 JST
-->

# Paper observation cycle completion plan

## 結論

この計画のゴールは、Strategy Lifecycle が紙運用観測を「手作業で1回だけ試す」状態から、「fresh intent を生成し、隔離された観測 session に記録し、その session を review し、lifecycle 判定へ渡せる」状態へ進めることである。

この計画は live trading を実装しない。API credential、wallet、signing、exchange write、public live operator CLI、production venue enablement も扱わない。完成地点は、紙運用観測ループを実務で繰り返せること、かつ条件未達なら正しく `CONTINUE_PAPER_OBSERVATION` のまま止まることである。

## 背景

現行コードと artifact から確認した実務上の不足は次である。

- `paper-from-intents` は paper order / fill / position / `paper_observation_ledger.jsonl` を生成できる。
- ただし `paper-from-intents` の CLI は現状 `--observation-ledger-path` を持たず、default ledger に追記される。
- `run_paper_from_intents()` は内部で `data_dir / "paper/paper_observation_ledger.jsonl"` を使っており、観測 session を隔離しにくい。
- `paper-operations-cycle` は legacy `paper-step` の cycle であり、Strategy Lifecycle の paper intent / NDX review / lifecycle review をまとめる導線ではない。
- `build-paper-intent-preview` は `valid_until` を短く持つため、古い `data/bot/paper_intent_preview.json` を再利用すると実務上危険である。
- 現在の paper observation review は、実データ不足なら `NEEDS_MORE_PAPER_OBSERVATION` と返すべきであり、閾値を下げて本番相当の合格に見せてはいけない。
- `READ_ONLY_GO` は read-only / paper gate の結果であり、live readiness ではない。

## 目的

実務で使える状態とは、次の問いにローカル artifact だけで答えられる状態である。

1. この paper 観測 run はどの戦略、どの backtest acceptance、どの operator promotion、どの intent preview に基づいたか。
2. 観測 ledger は他の run や古い欠損 ledger と混ざっていないか。
3. intent preview は生成時点から見て fresh で、期限切れを再利用していないか。
4. filled / blocked / skipped の観測行は review に必要な時刻、symbol、notional、数量、境界 flag、source hash を持つか。
5. paper observation review は session 単位で実行でき、fills、trading days、block rate、timestamp completeness、live boundary violation を判定できるか。
6. Strategy Lifecycle は paper review 結果を受け、未達なら `CONTINUE_PAPER_OBSERVATION`、paper pass 後に blocker が残るなら `CONTINUE_EXECUTION_READINESS` と返せるか。

## ゴール地点

この計画の完成後、標準オペレーターは次の流れで paper 観測を繰り返せる。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-run \
  --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml \
  --through backtest
uv run sis strategy-backtest-acceptance \
  --metrics-path data/research/strategy_backtest_metrics.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
uv run sis strategy-paper-observation-cycle \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
uv run sis strategy-lifecycle-review \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

標準出力は、少なくとも次を残す。

- `data/paper/observations/<session_id>/paper_observation_session_manifest.json`
- `data/paper/observations/<session_id>/paper_observation_ledger.jsonl`
- `data/paper/observations/<session_id>/paper_observation_review_decision.json`
- `data/research/ndx/paper_observation_review_decision.json`
- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`
- `data/reports/paper_observation_session_report.md`

完成時点の通常判定は、実運用日数と fill 数が足りなければ `CONTINUE_PAPER_OBSERVATION` でよい。完成条件は「今日 paper pass を作ること」ではなく、「本物の paper pass か、本物の未達かを区別できる loop ができていること」である。

## 制約

必須制約:

- 外部 API、credential、wallet、signing、exchange write、live order を追加しない。
- DB migration、常駐 daemon、新しい scheduler、auth、課金、deploy、CI secret を追加しない。
- 新しい dependency を追加しない。`pyproject.toml` と `uv.lock` は原則変更しない。
- `data/` 配下の生成 artifact を source-controlled truth にしない。
- 閾値を下げて本番相当の pass を作らない。smoke 用の短縮閾値を使う場合は、出力と test 名に `smoke` を明記する。
- 既存の欠損 ledger に timestamp を後入れして trading day を作らない。
- `paper-operations-cycle` を Strategy Lifecycle の完成導線として流用しない。使うなら別途 bridge 設計を作る。
- `READ_ONLY_GO`、paper pass、`ELIGIBLE_FOR_LIVE_CANARY_PLAN` のいずれも live order 許可にしない。

設計制約:

- orchestration の core logic は Typer command 関数内に閉じ込めない。必要なら既存 command の中身を小さな pure helper に先に切り出す。
- CLI から CLI を subprocess 呼び出ししない。同一 process 内の reusable module を呼ぶ。
- session manifest を paper 観測 run の正本にする。単なる path 手渡しにしない。
- default path は後方互換を維持する。新しい session path は明示 option または cycle command から使う。
- review は fail closed にする。artifact 欠損、schema mismatch、期限切れ、source hash mismatch、境界違反は pass にしない。

## 対象ファイル

新規ファイル:

- `src/sis/research/strategy_lifecycle/paper_observation_cycle.py`
- `src/sis/paper/observation_session.py`
- `schemas/paper_observation_session_manifest.v1.schema.json`
- `tests/research/test_strategy_paper_observation_cycle.py`
- `tests/paper/test_observation_session.py`
- `docs/strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md`

既存編集ファイル:

- `src/sis/commands/paper.py`
- `src/sis/commands/research.py`
- `src/sis/paper/runner.py`
- `src/sis/research/ndx/paper_observation_review.py`
- `schemas/ndx_paper_observation_review_decision.v1.schema.json`
- `tests/test_paper_from_intents.py`
- `tests/test_cli_smoke.py`
- `tests/research/test_ndx_layer28_paper_observation_review.py`
- `tests/research/test_strategy_lifecycle_review.py`
- `docs/strategy_lifecycle/README.md`
- `docs/strategy_lifecycle/TARGET_OPERATING_MODEL.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
- `docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`

原則として触らないファイル:

- `pyproject.toml`
- `uv.lock`
- `.github/workflows/ci.yml`
- live execution adapter
- venue signing / wallet / credential 周辺
- `src/sis/commands/operations_reports.py` の `lifecycle-report`

## 実装タスク

### T0: 現状確認と境界固定

目的:

- 実装前に、現行 CLI、artifact、欠損、既存計画との関係を固定する。

対象ファイル:

- なし。read-only inspection のみ。

作業:

1. `git status --short --branch --untracked-files=all` を確認する。
2. `uv run sis paper-from-intents --help` を確認し、`--observation-ledger-path` が未実装なら T1 の対象にする。
3. `uv run sis research-ndx-paper-observation-review --help` を確認する。
4. `uv run sis strategy-lifecycle-review --help` を確認する。未実装なら先に `02_strategy_lifecycle_control_plane` を完了させる。
5. 既存 artifact の判定を `jq` で読む。

確認コマンド:

```bash
git status --short --branch --untracked-files=all
uv run sis paper-from-intents --help
uv run sis research-ndx-paper-observation-review --help
uv run sis strategy-lifecycle-review --help
jq '.decision, .metrics, .reason_codes' data/research/ndx/paper_observation_review_decision.json
jq '.decision, .blocker_counts, .boundary_flags' data/research/strategy_lifecycle/strategy_lifecycle_review.json
```

受け入れ条件:

- 現行コードがこの計画の前提と衝突していない。
- `strategy-lifecycle-review` が未実装なら、この計画の T3 以降へ進む前に `02_strategy_lifecycle_control_plane` を完了する。
- 期限切れ preview や古い ledger を pass 根拠にしないと明記する。

### T1: paper-from-intents に観測 ledger path を追加する

目的:

- session ごとに paper observation ledger を隔離できるようにする。

対象ファイル:

- `src/sis/paper/runner.py`
- `src/sis/commands/paper.py`
- `tests/test_paper_from_intents.py`
- `tests/test_cli_smoke.py`

実装:

1. `run_paper_from_intents()` に `observation_ledger_path: Path | None = None` を追加する。
2. `None` の場合は現行 default の `data_dir / "paper/paper_observation_ledger.jsonl"` を使う。
3. CLI `paper-from-intents` に `--observation-ledger-path` を追加する。
4. 指定 path の parent directory を作成する。
5. 指定 path にだけ ledger row が追記され、default ledger に混ざらないことを保証する。
6. 既存の `orders.parquet`、`fills.parquet`、`positions.parquet` の default 挙動は変えない。

受け入れ条件:

- `uv run sis paper-from-intents --help` に `--observation-ledger-path` が出る。
- custom ledger path 指定時、custom path に ledger が作られる。
- custom ledger path 指定時、default `data/paper/paper_observation_ledger.jsonl` は変更されない。
- option 未指定時の後方互換が維持される。

検証:

```bash
uv run sis paper-from-intents --help
uv run pytest tests/test_paper_from_intents.py tests/test_cli_smoke.py -q
```

### T2: paper observation session manifest を追加する

目的:

- 観測 run の source、path、threshold、境界 flag を1つの JSON manifest に固定し、review と handoff の正本にする。

対象ファイル:

- `src/sis/paper/observation_session.py`
- `schemas/paper_observation_session_manifest.v1.schema.json`
- `tests/paper/test_observation_session.py`

manifest 必須 field:

- `schema_version`
- `session_id`
- `created_at`
- `data_dir`
- `session_dir`
- `observation_ledger_path`
- `paper_orders_path`
- `paper_fills_path`
- `paper_positions_path`
- `source_backtest_acceptance_path`
- `source_backtest_acceptance_sha256`
- `source_operator_promotion_path`
- `source_operator_promotion_sha256`
- `source_intent_preview_path`
- `source_intent_preview_sha256`
- `thresholds.min_fills_for_pass`
- `thresholds.min_trading_days_for_pass`
- `thresholds.max_blocked_rate`
- `permits_live_order`
- `wallet_used`
- `venue_write_used`
- `exchange_write_used`

実装:

1. `create_paper_observation_session()` を追加する。
2. `session_id` 未指定時は UTC timestamp ベースで deterministic に衝突しにくい値を作る。
3. path は `data/paper/observations/<session_id>/` 配下に集約する。
4. source artifact は path と sha256 を記録する。
5. live / wallet / write 系 flag は必ず false にする。
6. manifest を JSON Schema で検証できる形にする。

受け入れ条件:

- manifest が schema validation に通る。
- source artifact が欠損している場合は fail closed する。
- live / wallet / write 系 field が true になる経路がない。
- Windows path 前提ではなく POSIX path 文字列として安定する。

検証:

```bash
uv run pytest tests/paper/test_observation_session.py -q
```

### T3: Strategy paper observation cycle CLI を追加する

目的:

- fresh paper intent の生成、paper 実行、session ledger への記録、paper review、lifecycle review までの手順を1コマンドで安全に回せるようにする。

対象ファイル:

- `src/sis/research/strategy_lifecycle/paper_observation_cycle.py`
- `src/sis/commands/research.py`
- `tests/research/test_strategy_paper_observation_cycle.py`
- `tests/test_cli_smoke.py`

CLI:

```bash
uv run sis strategy-paper-observation-cycle \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
```

主要 option:

- `--session-id`
- `--data-dir`
- `--artifact-dir`
- `--reports-dir`
- `--backtest-acceptance-path`
- `--operator-promotion-path`
- `--min-fills-for-pass`
- `--min-trading-days-for-pass`
- `--max-blocked-rate`
- `--smoke`

実装:

1. backtest acceptance artifact が `PASS_BACKTEST_ACCEPTANCE` であることを要求する。
2. operator promotion artifact が存在し、selected candidates があることを要求する。
3. `build-paper-intent-preview` 相当の helper を呼び、fresh intent preview を生成する。
4. 期限切れの既存 `paper_intent_preview.json` は再利用しない。
5. session manifest を作る。
6. `run_paper_from_intents()` を `observation_ledger_path=session_ledger` で呼ぶ。
7. `research-ndx-paper-observation-review` 相当の helper を session manifest または session ledger に対して実行する。
8. `strategy-lifecycle-review` 相当の helper を実行する。
9. report と manifest に、これは paper-only で live permission ではないと出す。

実装上の注意:

- `src/sis/commands/research.py` 内の既存 Typer command 関数を直接呼ばない。必要なら candidate pack、promotion decision、intent preview、paper review、lifecycle review の pure helper を先に切り出す。
- subprocess で `uv run sis ...` を呼ばない。test が遅くなり、error handling が不安定になる。
- `--smoke` は test 用の短縮閾値だけに使う。通常 output を paper pass と誤認させないため、manifest と report に `smoke: true` を明記する。

受け入れ条件:

- `uv run sis strategy-paper-observation-cycle --help` が通る。
- fresh intent preview が cycle 内で生成される。
- 期限切れ intent preview が存在しても、それを pass 根拠にしない。
- session ledger が `data/paper/observations/<session_id>/paper_observation_ledger.jsonl` に作られる。
- paper review decision が session copy と canonical copy の両方に出る。
- lifecycle review が更新される。
- すべての output で live / wallet / write permission が false のまま。

検証:

```bash
uv run sis strategy-paper-observation-cycle --help
uv run pytest tests/research/test_strategy_paper_observation_cycle.py tests/test_cli_smoke.py -q
```

### T4: paper observation review を session manifest 対応にする

目的:

- 単なる ledger path ではなく、source hash と threshold を持つ session manifest から review できるようにする。

対象ファイル:

- `src/sis/research/ndx/paper_observation_review.py`
- `src/sis/commands/research.py`
- `schemas/ndx_paper_observation_review_decision.v1.schema.json`
- `tests/research/test_ndx_layer28_paper_observation_review.py`
- `docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md`

CLI 追加:

```bash
uv run sis research-ndx-paper-observation-review \
  --session-manifest data/paper/observations/<session_id>/paper_observation_session_manifest.json \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
```

実装:

1. `--session-manifest` を追加する。
2. `--session-manifest` 指定時は manifest の `observation_ledger_path` と thresholds を使う。
3. manifest の source hash、session id、ledger path を decision JSON に記録する。
4. manifest と ledger の不整合は fail closed にする。
5. 既存 `--ledger-path` は manual / backward compatible path として残す。
6. timestamp 欠損 ledger は crash ではなく `NEEDS_MORE_PAPER_OBSERVATION` にする。

受け入れ条件:

- session manifest 指定で review が走る。
- decision JSON に `source_paper_observation_session_manifest_path` と sha256 が出る。
- old ledger の timestamp 欠損は pass しない。
- live / wallet / write boundary violation は `STOP_PAPER_OBSERVATION` 相当の stop decision になる。
- `--ledger-path` の既存利用は壊れない。

検証:

```bash
uv run sis research-ndx-paper-observation-review --help
uv run pytest tests/research/test_ndx_layer28_paper_observation_review.py -q
```

### T5: 紙運用 artifact の累積意味を明文化する

目的:

- `orders.parquet` / `fills.parquet` / `positions.parquet` と ledger の役割を混同しないようにする。

対象ファイル:

- `src/sis/paper/runner.py`
- `docs/strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
- `tests/test_paper_from_intents.py`

方針:

- この計画では session ledger を観測 window の正本にする。
- `orders.parquet`、`fills.parquet`、`positions.parquet` は current paper state snapshot として扱う。
- cumulative fills の正本を Parquet append にする変更は、必要になるまで追加しない。
- review は fills / trading days を session ledger から計算する。

受け入れ条件:

- docs と report が「session ledger が観測 window の正本」と明記している。
- review が Parquet snapshot だけを根拠に paper pass しない。
- ledger row に order id / fill id / intent id が残り、後追い監査できる。

検証:

```bash
uv run pytest tests/test_paper_from_intents.py tests/research/test_ndx_layer28_paper_observation_review.py -q
uv run python scripts/check_current_docs.py
```

### T6: docs と operator runbook を更新する

目的:

- コーダーとオペレーターが同じ手順で paper 観測を回せるようにする。

対象ファイル:

- `docs/strategy_lifecycle/README.md`
- `docs/strategy_lifecycle/TARGET_OPERATING_MODEL.md`
- `docs/strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
- `docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`

記載する内容:

1. paper observation cycle の標準コマンド。
2. `--smoke` の用途と禁止事項。
3. session manifest の読み方。
4. 期限切れ intent preview の扱い。
5. `CONTINUE_PAPER_OBSERVATION` が正常な未達状態であること。
6. paper pass 後も live には進まず、execution readiness blocker を別に潰すこと。

受け入れ条件:

- docs は current implementation と一致する。
- Markdown metadata timestamp が更新されている。
- live permission と誤読できる記述がない。

検証:

```bash
uv run python scripts/check_current_docs.py
```

### T7: verification と差分監査

目的:

- 追加実装が paper 観測 loop だけに閉じ、依存や live path を変えていないことを確認する。

対象ファイル:

- `scripts/check`
- `src/sis/commands/paper.py`
- `src/sis/commands/research.py`
- `src/sis/paper/`
- `src/sis/research/ndx/`
- `src/sis/research/strategy_lifecycle/`
- `schemas/`
- `tests/`
- `docs/`

検証:

```bash
uv run sis paper-from-intents --help
uv run sis research-ndx-paper-observation-review --help
uv run sis strategy-paper-observation-cycle --help
uv run sis strategy-lifecycle-review --help
uv run pytest tests/test_paper_from_intents.py tests/paper/test_observation_session.py tests/research/test_strategy_paper_observation_cycle.py tests/research/test_ndx_layer28_paper_observation_review.py tests/research/test_strategy_lifecycle_review.py tests/test_cli_smoke.py -q
uv run python scripts/check_current_docs.py
./scripts/check
git diff -- pyproject.toml uv.lock .github/workflows/ci.yml
git status --short --branch --untracked-files=all
```

受け入れ条件:

- targeted pytest が pass する。
- docs checker が pass する。
- `./scripts/check` が pass する。
- `pyproject.toml`、`uv.lock`、`.github/workflows/ci.yml` に不要差分がない。
- live execution、credential、wallet、signing、exchange write 周辺に差分がない。
- generated `data/` artifact を git に含めない。

## テスト方針

優先順位:

1. pure module の unit test。
2. CLI help / Typer smoke test。
3. session manifest schema validation。
4. paper ledger / review / lifecycle の integration test。
5. docs checker。
6. full `./scripts/check`。

必須 test case:

- `paper-from-intents --observation-ledger-path` が custom ledger にだけ書く。
- option 未指定時に default ledger 挙動が維持される。
- session manifest が schema validation に通る。
- manifest source artifact 欠損で fail closed する。
- expired preview が存在しても cycle が再利用しない。
- `--smoke` なしでは短縮閾値を使わない。
- old ledger の timestamp 欠損は pass しない。
- session manifest 指定 review が source hash と session id を decision に残す。
- live / wallet / write flag true は paper pass ではなく boundary stop になる。
- lifecycle review は paper 未達なら `CONTINUE_PAPER_OBSERVATION`。
- paper pass 後に live readiness blocker が残るなら `CONTINUE_EXECUTION_READINESS`。
- どの decision でも `permits_live_order=false`。

## 完了条件

この計画は、次をすべて満たした時に完了とする。

- `paper-from-intents` が session ledger path を受け取れる。
- paper observation session manifest が schema 付きで生成される。
- `strategy-paper-observation-cycle` が fresh intent generation から paper review / lifecycle review までを paper-only で実行できる。
- `research-ndx-paper-observation-review` が session manifest を入力として扱える。
- paper observation review は session ledger を観測 window の正本として fills、trading days、block rate、timestamp completeness、boundary violation を判定する。
- 実データが不足している場合、system は pass を捏造せず `CONTINUE_PAPER_OBSERVATION` と返す。
- paper pass 後に blocker が残る場合、system は live に進まず `CONTINUE_EXECUTION_READINESS` と返す。
- docs と runbook が実装済み CLI / artifact / stop condition と一致する。
- `uv run pytest ... -q` の targeted suite、`uv run python scripts/check_current_docs.py`、`./scripts/check` が pass する。
- dependency、lockfile、CI、live execution、credential、wallet、signing、exchange write に不要差分がない。

## 抜け漏れ・誤謬リスクの修正

実装時に特に潰すべきリスク:

- 期限切れ `data/bot/paper_intent_preview.json` を使って paper 実行してしまう。
- 古い欠損 ledger を session に混ぜ、trading day や fill 数を過大評価する。
- `--smoke` の短縮閾値で得た pass を本番 paper pass と誤読する。
- Typer command 関数を別 command から直接呼び、test しにくい orchestration になる。
- `orders.parquet` / `fills.parquet` を累積観測の正本と誤解する。
- `READ_ONLY_GO` や `ELIGIBLE_FOR_LIVE_CANARY_PLAN` を live order 許可と誤解する。
- generated `data/` artifact を commit に含める。

Better な余地として、この計画では「session manifest」を追加する。単なる `--ledger-path` だけでも最小実装は可能だが、実務では source hash、threshold、session id がないと後で何を観測したかが曖昧になるため、manifest を完成条件に含める。

