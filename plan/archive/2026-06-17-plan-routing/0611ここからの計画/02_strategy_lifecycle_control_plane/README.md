<!--
作成日: 2026-06-11_21:15 JST
更新日: 2026-06-11_21:15 JST
-->

# Strategy lifecycle control plane implementation plan

## 結論

この計画のゴールは、戦略を「研究」「バックテスト合格」「紙運用継続」「実行準備継続」「ライブ canary 計画候補」へ進めるための、ローカル artifact ベースの判定面を作ることである。

この計画は live trading を実装しない。API credential、wallet、signing、exchange write、public live operator CLI、production venue enablement も扱わない。最終到達点は `ELIGIBLE_FOR_LIVE_CANARY_PLAN` までであり、これは「別計画で live canary の仕様を書いてよい」という意味に限定する。live order を出してよい、という意味ではない。

既存の `lifecycle-report` は operations / recovery 用の別コマンドである。新しい戦略判定面は名前を衝突させず、`strategy-backtest-acceptance` と `strategy-lifecycle-review` として追加する。

## 目的

実務で使える状態とは、次の問いにローカル artifact だけで答えられる状態である。

1. この戦略はバックテスト合格条件を満たしたか。
2. バックテストを通らずに紙運用へ進んでいないか。
3. 紙運用の観測数、block 率、境界違反、紙 artifact は十分か。
4. read-only / paper gate と execution drift の状態は次段階を許すか。
5. live、wallet、signing、exchange write の境界違反が混入していないか。
6. 次の判断は reject / revise、研究継続、paper observation 継続、実行準備継続、live canary 計画候補のどれか。

## ゴール地点

実装後、標準オペレーターは次の順で進められる。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-run \
  --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml \
  --through backtest
uv run sis strategy-backtest-acceptance \
  --metrics-path data/research/strategy_backtest_metrics.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
uv run sis phase-gate-review
uv run sis strategy-lifecycle-review \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

最終出力は次の 2 つを基本にする。

- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`

最終判定値は次に固定する。

- `REJECT_OR_REVISE`: バックテスト不合格、紙運用停止、または明示的な棄却。
- `CONTINUE_RESEARCH`: 必須 artifact が不足し、研究またはバックテストからやり直す。
- `BACKTEST_ACCEPTED`: バックテストは通過したが、紙運用 review がまだない。
- `CONTINUE_PAPER_OBSERVATION`: 紙運用の観測量または期間が不足している。
- `CONTINUE_EXECUTION_READINESS`: 紙運用は通過したが、phase gate、read-only/paper gate、execution drift、live readiness blocker が残っている。
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN`: バックテスト、紙運用、phase gate、execution readiness の blocker がすべて計画上の条件を満たし、別計画として live canary 仕様を書く候補になった。
- `BLOCKED_BOUNDARY_VIOLATION`: live order、wallet、signing、exchange write、または禁止された外部副作用が artifact に混入した。

## 現在確認した実装事実

この計画は、次を code / tests / CLI / docs から確認した前提で作る。

- `strategy-author-run --through backtest` は `data/research/strategy_backtest_metrics.json` を生成し、`summary.backtest_passed`、`summary.pass_min_trade_count`、`summary.pass_all_thresholds`、`summary.walk_forward_eras` を持てる。
- `schemas/strategy_authoring_backtest_result.v1.schema.json` は既存。
- NDX Layer 2.6 / 2.7 / 2.8 は実装済みで、Layer 2.8 は `research-ndx-paper-observation-review` と `schemas/ndx_paper_observation_review_decision.v1.schema.json` を持つ。
- Layer 2.8 の現行 default は `--min-fills-for-pass 20`、`--max-blocked-rate 0.5`、`--max-consecutive-blocked 3`、`--paper-notional-usd 1000.0`。
- `paper-from-intents` は paper order / fill / position / `paper_observation_ledger.jsonl` を生成するが、現状の ledger は実務 review に必要な quote freshness、market status、spread、source confidence、venue quality、notional、created timestamp が薄い。
- `phase-gate-review` は read-only / paper gate の review であり、`READ_ONLY_GO` は live readiness ではない。
- `lifecycle-report` は `src/sis/commands/operations_reports.py` の operations / recovery report であり、新しい戦略 lifecycle 判定名として再利用しない。

## 制約

必須制約:

- 外部 API、credential、wallet、signing、exchange write、live order を追加しない。
- DB migration、常駐 daemon、新しい scheduler、auth、課金、deploy、CI secret を追加しない。
- 新しい dependency を追加しない。`pyproject.toml` と `uv.lock` は原則変更しない。
- 既存の NDX Layer 2.6 / 2.7 / 2.8 を壊さず、追加判定として扱う。
- `Trade[XYZ]` を新しい主軸に戻さない。NDX は research / paper observation の一線として扱う。
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` は live 実行許可ではない。出力にも `permits_live_order=true` を置かない。
- fresh checkout で `data/` artifact がない場合は fail closed または `CONTINUE_RESEARCH` にする。暗黙に成功扱いしない。

設計制約:

- core 判定ロジックは CLI wrapper に置かない。`src/sis/research/strategy_lifecycle/` に pure module を置く。
- artifact は JSON schema で固定する。
- 既存 reader を壊さない。paper ledger の追加 field は後方互換にする。
- public CLI 名は明示的にする。`lifecycle-report` とは別名にする。
- 計画外の live blocker を「消す」作業はしない。分類と evidence 化だけを行う。

## 対象ファイル

新規ファイル:

- `src/sis/research/strategy_lifecycle/__init__.py`
- `src/sis/research/strategy_lifecycle/backtest_acceptance.py`
- `src/sis/research/strategy_lifecycle/review.py`
- `schemas/strategy_backtest_acceptance_decision.v1.schema.json`
- `schemas/strategy_lifecycle_review.v1.schema.json`
- `tests/research/test_strategy_lifecycle_backtest_acceptance.py`
- `tests/research/test_strategy_lifecycle_review.py`
- `docs/strategy_lifecycle/README.md`
- `docs/strategy_lifecycle/TARGET_OPERATING_MODEL.md`
- `docs/strategy_lifecycle/LIVE_CANARY_PLAN_GATE.md`

既存編集ファイル:

- `src/sis/commands/research.py`
- `src/sis/paper/runner.py`
- `src/sis/research/ndx/paper_observation_review.py`
- `schemas/ndx_paper_observation_review_decision.v1.schema.json`
- `tests/research/test_ndx_layer28_paper_observation_review.py`
- `tests/test_paper_from_intents.py`
- `tests/test_cli_smoke.py`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/research/ndx/README.md`
- `docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md`
- `docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md`
- `docs/strategy_research_lab/04_PAPER_PROMOTION_AND_INTENT_SPEC.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
- `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md`
- `docs/backtest/README.md`

原則として触らないファイル:

- `pyproject.toml`
- `uv.lock`
- `.github/workflows/ci.yml`
- live execution adapter
- venue signing / wallet / credential 周辺
- `src/sis/commands/operations_reports.py` の `lifecycle-report` 実装

## 実装タスク

### T0: current truth と用語を固定する

目的:

- lifecycle のゴールを docs に先に固定し、実装者が live 化と誤解しないようにする。

対象ファイル:

- `docs/strategy_lifecycle/README.md`
- `docs/strategy_lifecycle/TARGET_OPERATING_MODEL.md`
- `docs/strategy_lifecycle/LIVE_CANARY_PLAN_GATE.md`

実装:

1. `docs/strategy_lifecycle/README.md` を作る。
2. `TARGET_OPERATING_MODEL.md` に decision ladder と artifact flow を書く。
3. `LIVE_CANARY_PLAN_GATE.md` に `ELIGIBLE_FOR_LIVE_CANARY_PLAN` の意味を限定する。
4. すべての Markdown に Tokyo timestamp header を入れる。

受け入れ条件:

- docs は live order を許可していない。
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` が live 実行許可ではないと明記されている。
- 既存 `lifecycle-report` と新しい `strategy-lifecycle-review` の違いが明記されている。

検証:

```bash
uv run python scripts/check_current_docs.py
```

### T1: backtest acceptance gate を追加する

目的:

- 紙運用の前に、Strategy Authoring backtest の合格判定を独立 artifact として固定する。

対象ファイル:

- `src/sis/research/strategy_lifecycle/__init__.py`
- `src/sis/research/strategy_lifecycle/backtest_acceptance.py`
- `src/sis/commands/research.py`
- `schemas/strategy_backtest_acceptance_decision.v1.schema.json`
- `tests/research/test_strategy_lifecycle_backtest_acceptance.py`

CLI:

```bash
uv run sis strategy-backtest-acceptance \
  --metrics-path data/research/strategy_backtest_metrics.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

出力:

- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/reports/strategy_backtest_acceptance_report.md`

判定値:

- `PASS_BACKTEST_ACCEPTANCE`
- `FAIL_BACKTEST_ACCEPTANCE`
- `NEEDS_BACKTEST`
- `BLOCK_BACKTEST_BOUNDARY`

判定条件:

- metrics が存在しない場合は `NEEDS_BACKTEST`。
- `schema_version` がある場合、`strategy_authoring_backtest_result.v1` 以外は fail closed。
- `summary.backtest_passed=true`、`summary.pass_min_trade_count=true`、`summary.pass_all_thresholds=true` をすべて要求する。
- `summary.walk_forward_eras` が存在する場合は era 数、era signal count、era metrics の有無を記録する。最初の実装では era 全勝を必須にしないが、`era_pass_count` と `era_fail_count` を artifact に出す。
- `live_order_submitted`、`wallet_used`、`exchange_write_used`、`venue_write_used` のどれかが true と読める場合は `BLOCK_BACKTEST_BOUNDARY`。
- `profitability_claimed=true`、`live_ready_claimed=true`、`paper_ready_claimed=true` が混入した場合は `BLOCK_BACKTEST_BOUNDARY`。

テスト:

- backtest pass artifact で `PASS_BACKTEST_ACCEPTANCE`。
- `summary.backtest_passed=false` で `FAIL_BACKTEST_ACCEPTANCE`。
- metrics missing で `NEEDS_BACKTEST`。
- schema mismatch で CLI exit code 2。
- live / wallet / write flag が true の場合 `BLOCK_BACKTEST_BOUNDARY`。
- decision JSON が schema validation に通る。
- report が作られる。
- `uv run sis strategy-backtest-acceptance --help` に option が出る。

### T2: paper observation ledger を実務 review 可能な粒度へ増やす

目的:

- `paper-from-intents` の ledger に、あとから紙運用を監査できる最低限の execution context を残す。

対象ファイル:

- `src/sis/paper/runner.py`
- `tests/test_paper_from_intents.py`
- `docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md`
- `docs/strategy_research_lab/04_PAPER_PROMOTION_AND_INTENT_SPEC.md`

追加する ledger field:

- `created_at`
- `intent_id`
- `candidate_id`
- `venue`
- `execution_symbol`
- `real_market_symbol`
- `status`
- `block_reasons`
- `quote_ts`
- `quote_age_ms`
- `market_status`
- `is_tradable`
- `spread_bps`
- `source_confidence`
- `venue_quality_score`
- `notional_usd`
- `quantity`
- `order_id`
- `fill_id`
- `source_operator_promotion_path`
- `source_operator_promotion_hash`
- `live_order_submitted`
- `wallet_used`
- `exchange_write_used`
- `venue_write_used`

互換性:

- 既存 ledger entry を読む処理は壊さない。
- field が欠けている古い ledger は Layer 2.8 review で `unknown` または reason code に落とす。例外で全停止させるのは boundary violation のみ。

テスト:

- filled entry に quote freshness と paper-only flags が入る。
- blocked entry に block reason と paper-only flags が入る。
- raw JSON bypass でも ledger field が同じ構造になる。
- 既存の `paper-from-intents` テストが通る。

### T3: NDX Layer 2.8 paper observation review を強化する

目的:

- fills count だけで pass しないようにし、実務運用に必要な観測日数、artifact completeness、boundary violation、紙 artifact metrics を見る。

対象ファイル:

- `src/sis/research/ndx/paper_observation_review.py`
- `src/sis/commands/research.py`
- `schemas/ndx_paper_observation_review_decision.v1.schema.json`
- `tests/research/test_ndx_layer28_paper_observation_review.py`
- `docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md`

CLI 追加 option:

```bash
--min-trading-days-for-pass 10
--max-open-position-age-hours 0
```

仕様:

- `--min-trading-days-for-pass` は default 10。
- `--max-open-position-age-hours 0` は無効を意味する。0 より大きい場合だけ open position age を検査する。
- distinct trading day は ledger の `created_at` から計算する。欠けている場合は fill timestamp、order timestamp、または status count fallback を使い、fallback を `metrics.timestamp_quality` に記録する。
- `orders.parquet`、`fills.parquet`、`positions.parquet` の存在と hash は今まで通り記録する。
- artifact がない場合は pass しない。
- live / wallet / write flag が一つでも true なら `STOP_PAPER_OBSERVATION`。

判定:

- boundary violation または unknown status は `STOP_PAPER_OBSERVATION`。
- blocked rate 超過、連続 blocked 超過、artifact 不足は `STOP_PAPER_OBSERVATION`。
- fills 数または観測日数が不足する場合は `NEEDS_MORE_PAPER_OBSERVATION`。
- thresholds を満たす場合だけ `PASS_PAPER_OBSERVATION_REVIEW`。

テスト:

- min fills と min trading days を満たした場合 pass。
- fills は足りるが trading days が足りない場合 `NEEDS_MORE_PAPER_OBSERVATION`。
- created timestamp が欠ける古い ledger は `timestamp_quality=fallback_or_missing` になり pass しない。
- artifact missing は stop または needs_more ではなく明示 block reason を出す。
- live boundary violation は stop。
- schema validation が通る。

### T4: strategy lifecycle review を追加する

目的:

- backtest acceptance、paper observation review、phase gate、execution drift を統合し、次の実務判断を 1 artifact にする。

対象ファイル:

- `src/sis/research/strategy_lifecycle/review.py`
- `src/sis/commands/research.py`
- `schemas/strategy_lifecycle_review.v1.schema.json`
- `tests/research/test_strategy_lifecycle_review.py`

CLI:

```bash
uv run sis strategy-lifecycle-review \
  --data-dir data \
  --backtest-decision-path data/research/strategy_lifecycle/backtest_acceptance_decision.json \
  --paper-review-path data/research/ndx/paper_observation_review_decision.json \
  --phase-gate-path data/ops/phase_gate_review_summary.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

出力:

- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`
- `data/reports/strategy_lifecycle_review.md`

統合判定規則:

- 入力 artifact のどれかに live / wallet / venue write / exchange write が true と読める field があれば `BLOCKED_BOUNDARY_VIOLATION`。
- backtest decision がない場合は `CONTINUE_RESEARCH`。
- backtest decision が `NEEDS_BACKTEST` の場合は `CONTINUE_RESEARCH`。
- backtest decision が `FAIL_BACKTEST_ACCEPTANCE` の場合は `REJECT_OR_REVISE`。
- backtest decision が `BLOCK_BACKTEST_BOUNDARY` の場合は `BLOCKED_BOUNDARY_VIOLATION`。
- backtest decision が pass し、paper review がない場合は `BACKTEST_ACCEPTED`。
- paper review が `STOP_PAPER_OBSERVATION` の場合は `REJECT_OR_REVISE`。ただし live boundary reason がある場合は `BLOCKED_BOUNDARY_VIOLATION`。
- paper review が `NEEDS_MORE_PAPER_OBSERVATION` の場合は `CONTINUE_PAPER_OBSERVATION`。
- paper review が pass しても phase gate が missing の場合は `CONTINUE_EXECUTION_READINESS`。
- phase gate に `P2_BLOCKER > 0` がある場合は `CONTINUE_EXECUTION_READINESS`。
- phase gate に `LIVE_READINESS_BLOCKER > 0` がある場合は `CONTINUE_EXECUTION_READINESS`。
- paper review pass、phase gate `READ_ONLY_GO` または `PAPER_GO`、P2 blocker 0、live readiness blocker 0 の場合だけ `ELIGIBLE_FOR_LIVE_CANARY_PLAN`。

出力 field:

- `schema_version`
- `decision`
- `decision_reasons`
- `next_actions`
- `source_backtest_acceptance_path`
- `source_backtest_acceptance_hash`
- `source_paper_review_path`
- `source_paper_review_hash`
- `source_phase_gate_path`
- `source_phase_gate_hash`
- `input_status`
- `blocker_counts`
- `boundary_flags`
- `permits_live_order=false`
- `live_conversion_allowed=false`
- `wallet_used=false`
- `venue_write_used=false`
- `exchange_write_used=false`

テスト:

- missing backtest -> `CONTINUE_RESEARCH`。
- failed backtest -> `REJECT_OR_REVISE`。
- passed backtest, missing paper review -> `BACKTEST_ACCEPTED`。
- paper needs more -> `CONTINUE_PAPER_OBSERVATION`。
- paper pass with live blockers -> `CONTINUE_EXECUTION_READINESS`。
- paper pass with no P2/live blocker -> `ELIGIBLE_FOR_LIVE_CANARY_PLAN` だが `permits_live_order=false`。
- any boundary true -> `BLOCKED_BOUNDARY_VIOLATION`。
- schema validation が通る。
- `uv run sis strategy-lifecycle-review --help` が通る。

### T5: docs と runbook を更新する

目的:

- 現行の実務導線を docs から辿れるようにし、historical plan と混ざらないようにする。

対象ファイル:

- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/backtest/README.md`
- `docs/research/ndx/README.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
- `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md`

更新内容:

- `strategy-backtest-acceptance` を backtest 後の必須 review artifact として記載する。
- `research-ndx-paper-observation-review` は paper observation review であり、alpha 証明ではないと再明記する。
- `strategy-lifecycle-review` を最終のローカル統合判定として追加する。
- `READ_ONLY_GO` と live readiness を分離して書く。
- `lifecycle-report` は operations / recovery であり、新しい strategy lifecycle 判定とは別物と書く。

検証:

```bash
uv run python scripts/check_current_docs.py
```

### T6: CLI smoke と schema inventory を更新する

目的:

- 新 CLI と schema が CI / smoke で落ちないようにする。

対象ファイル:

- `tests/test_cli_smoke.py`
- schema inventory tests が存在する場合は該当テスト
- `schemas/strategy_backtest_acceptance_decision.v1.schema.json`
- `schemas/strategy_lifecycle_review.v1.schema.json`

テスト:

- root help に `strategy-backtest-acceptance` が出る。
- root help に `strategy-lifecycle-review` が出る。
- 既存 `lifecycle-report` help も残る。
- 新 schema は `Draft202012Validator.check_schema` に通る。

### T7: live canary は計画 gate だけ残す

目的:

- 実務的な次段階を塞がず、かつ live 実装を混入させない。

対象ファイル:

- `docs/strategy_lifecycle/LIVE_CANARY_PLAN_GATE.md`
- `tests/research/test_strategy_lifecycle_review.py`

仕様:

- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` は live canary 計画書作成候補であり、注文実行権限ではない。
- `strategy-lifecycle-review` はどの decision でも `permits_live_order=false` を出す。
- live canary 実装に必要な credentials、wallet/signing、operator controls、risk limits、kill switch、venue write test、account boundary はこの計画外にする。

テスト:

- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` ケースでも live permission fields は全部 false。
- report に "does not permit live orders" 相当の文言が入る。

### T8: 最終検証

実装完了前に必ず次を実行する。

```bash
uv run sis strategy-backtest-acceptance --help
uv run sis strategy-lifecycle-review --help
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-run \
  --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml \
  --through backtest
uv run sis strategy-backtest-acceptance \
  --metrics-path data/research/strategy_backtest_metrics.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
uv run sis phase-gate-review
uv run sis strategy-lifecycle-review \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
uv run pytest \
  tests/research/test_strategy_lifecycle_backtest_acceptance.py \
  tests/research/test_strategy_lifecycle_review.py \
  tests/research/test_ndx_layer28_paper_observation_review.py \
  tests/test_paper_from_intents.py \
  tests/test_cli_smoke.py \
  -q
uv run python scripts/check_current_docs.py
./scripts/check
```

追加 diff 確認:

```bash
git diff -- pyproject.toml uv.lock .github/workflows/ci.yml
git diff -- src/sis/research/strategy_lifecycle src/sis/commands/research.py src/sis/paper/runner.py src/sis/research/ndx/paper_observation_review.py schemas tests docs
git status --short --branch --untracked-files=all
```

期待:

- `pyproject.toml`、`uv.lock`、`.github/workflows/ci.yml` に不要な差分がない。
- `data/` の生成 artifact は git 管理対象に混ぜない。
- `./scripts/check` が pass する。

## テスト方針

原則は Red -> Green。

優先順:

1. pure module の単体テスト。
2. CLI smoke。
3. schema validation。
4. 既存 paper / NDX Layer 2.8 regression。
5. docs current checker。
6. full `./scripts/check`。

重点テスト:

- fail closed: missing artifact、schema mismatch、hash mismatch、boundary flag true。
- false positive prevention: fixture-derived signal、paper observation、`READ_ONLY_GO` を live readiness と誤認しない。
- backward compatibility: 古い paper ledger を読める。ただし pass にはしない。
- naming guard: `lifecycle-report` は残り、新しい `strategy-lifecycle-review` と混ざらない。
- no side effects: external API、credential、wallet、venue write、live order を使わない。

## 完了条件

この計画は、次のすべてを満たした時だけ完了とする。

- `strategy-backtest-acceptance` CLI が実装され、help と tests が通る。
- `strategy_lifecycle/backtest_acceptance.py` が CLI から分離された pure logic として存在する。
- `strategy_backtest_acceptance_decision.v1` schema が追加され、生成 artifact が validation に通る。
- `paper-from-intents` ledger が実務 review に必要な context を持つ。
- Layer 2.8 paper observation review が観測日数、fills、block rate、artifact completeness、boundary violation を見る。
- `strategy-lifecycle-review` CLI が実装され、decision ladder を正しく出す。
- `strategy_lifecycle_review.v1` schema が追加され、生成 artifact が validation に通る。
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` でも live permission fields はすべて false。
- `docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`docs/OPERATIONS_RUNBOOK.md`、`docs/strategy_lifecycle/` が実装後の状態を説明する。
- `uv run python scripts/check_current_docs.py` が pass する。
- `./scripts/check` が pass する。
- 不要な dependency / lockfile / CI 差分がない。

## stop conditions

次のどれかに当たったら、実装を止めて計画を分ける。

- live order、wallet、signing、exchange write、credential、external API を触る必要が出た。
- DB migration、daemon、scheduler、deploy、CI secret が必要になった。
- NDX 以外の venue を同時に一般化しないと実装できない。
- `paper-from-intents` の ledger 追加が既存 artifact reader を破壊する。
- `strategy_lifecycle_review` が既存 `lifecycle-report` と意味上衝突する。
- `READ_ONLY_GO` を live readiness と扱わないと pass しない。

## 抜け漏れと誤謬リスクの修正

修正したリスク:

- 紙運用から逆算して live に進める narrative を採らない。先に backtest acceptance を独立 artifact 化する。
- NDX Layer 2.8 の fills count だけを pass 条件にしない。観測日数と ledger quality を追加する。
- `READ_ONLY_GO` を live readiness と誤読しない。execution drift / live readiness blocker を lifecycle review に残す。
- 既存 `lifecycle-report` と名前を衝突させない。
- fresh checkout で `data/` がない場合を成功扱いしない。
- live readiness blocker を消すことを目的にしない。分類し、残っていれば `CONTINUE_EXECUTION_READINESS` にする。

より良くした点:

- 「NDX 専用の続き」ではなく、Strategy Authoring backtest と paper observation をつなぐ汎用 lifecycle 面にした。
- ただし過剰な一般化は避け、入力は既存 local JSON artifact だけに限定した。
- live canary は実装ではなく計画 gate に留め、現実の安全境界を崩さない。
- コーダーがそのまま T0 から T8 まで Red -> Green で進められるよう、対象ファイル、CLI、artifact、tests、完了条件を固定した。

