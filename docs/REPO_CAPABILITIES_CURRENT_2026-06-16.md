<!--
作成日: 2026-06-16_06:46 JST
更新日: 2026-06-19_02:22 JST
-->

# Repo Capabilities Current

## 結論

`marketlens-strike` は、Python 3.13 / `uv` 前提の CLI workspace である。現在できることは、Strategy Input Contract / Idea Intake、Strategy Stage Policy / Decision、Strategy Paper Smoke Plan、Strategy Runtime Observation Ingest、Paper vs Backtest Drift Review、Strategy Learning / Revision Request / Authoring Update Handoff、Strategy Case Lite、Strategy Daily Brief、Strategy AI Review、Strategy Model / Optimizer Loop、Strategy Micro Live Plan Gate、Strategy Next Scale Plan、Strategy Live Observation、Strategy Scale Decision、Strategy Workbench Viewer、戦略研究、Strategy Authoring、backtest、paper-only preview、NDX research gate、Trade[XYZ] read-only data collection、read-only / paper operation、ops audit、remediation、artifact validation を local artifact と schema でつなぐこと。

現在できないことは、production live trading、wallet / signing / exchange write、backtest だけによる alpha / paper pass / live readiness の主張、Bitget / Hyperliquid production venue の正式 schema 対応、credentialed external API を暗黙に使う workflow である。

この文書は、コード、CLI help、schema、current docs を正として、repo でできることを漏れなく読む入口にする。

AI / Codex / LLM が戦略作成、編集、backtest、結果解釈を進める場合は [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md) を読む。人間が戦略と backtest 結果を専門用語少なめで理解したい場合は [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) を読む。

## 第三者向けの全体像

この repo は、取引所へ注文を出す本番 trading bot ではない。中心にあるのは、戦略アイデアを local artifact と schema で検査し、backtest、比較、レビュー、paper observation の入口までを安全に進める研究・検証用 CLI である。

大きな流れ:

1. 戦略を考える: `docs/algo/` と Strategy Factory docs で、戦略仮説、候補、reject 理由、validation checklist を整理する。
2. 入力と戦略の種を検査する: `strategy-input-contract-validate` と `strategy-intake-validate` で、入力データ契約、source hash、available_at、survivorship、hypothesis、baseline、invalidation、risk、required inputs を local artifact にする。
3. 戦略を機械で扱える形にする: Strategy Lab または Strategy Authoring YAML で、対象銘柄、entry / exit rule、cost、slippage、risk、pass threshold を定義する。
4. signal と backtest artifact を作る: `strategy-author-run --through backtest` や `strategy-backtest-pack` で、metrics、suite、benchmark、stress、no-lookahead、data availability、comparison、pack validation を出す。
5. 結果を読む: `strategy-backtest-artifact-summary`、`strategy-backtest-html-report`、Strategy Review packet で、数値、グラフ、source hash、欠損、境界違反を確認する。
6. 次の検証に進めるか判断する: `strategy-review-record`、`strategy-stage-policy-validate`、`strategy-stage-decision`、`strategy-paper-smoke-plan`、`strategy-runtime-observation-ingest`、`strategy-drift-review`、`strategy-case-lite-update`、`strategy-daily-brief`、`strategy-ai-review-packet-build`、`strategy-ai-review-note-record`、`strategy-model-run-record`、`strategy-next-scale-plan`、`strategy-workbench-viewer-build`、`strategy-backtest-acceptance`、`strategy-paper-observation-status`、`strategy-lifecycle-review` で、人間判断、stage policy、paper smoke plan、runtime observation、drift review、case timeline、daily brief、AI review note、model / optimizer trial ledger、next scale plan、static viewer、paper observation 状態、lifecycle decision を local artifact として残す。
7. venue / operation 側の境界を確認する: Trade[XYZ] read-only data、venue read-only probe、operations audit、phase gate で、外部 API、credential、wallet、signing、exchange write、live order を使わない範囲の状態を確認する。

第三者が誤読しやすい点:

- `backtest_passed=true` は、その YAML / artifact の閾値を満たしただけで、将来収益、paper 実行、live 実行を意味しない。
- `READY_FOR_AUTHORING_DRAFT` は Strategy Authoring draft に進める最低条件であり、paper 実行、live 実行、alpha 証明を意味しない。
- `READY_FOR_PAPER_SMOKE_PLAN` / `READY_FOR_MICRO_LIVE_PLAN` は計画 artifact へ進む候補であり、paper order、micro live execution、live order の許可ではない。
- `READY_FOR_HUMAN_MICRO_LIVE_REVIEW` は micro live plan artifact の人間確認準備であり、micro live execution、wallet、signing、exchange write、live order の許可ではない。
- `LIVE_OBSERVATION_INGESTED` は既存 micro live canary evidence を読めたという意味であり、scale-up、normal live readiness、production readiness ではない。
- `READY_FOR_HUMAN_SCALE_REVIEW` / `PREPARE_NEXT_SCALE_PLAN` は次の scale plan を検討する人間レビュー候補であり、scale-up execution permission ではない。
- `READY_FOR_HUMAN_NEXT_SCALE_REVIEW` は次の拡大計画の人間レビュー候補であり、next-scale execution permission ではない。
- `strategy_workbench_viewer.v1` は既存 artifact を静的 HTML に並べる viewer manifest であり、paper / live permission、artifact edit、hidden state ではない。
- `READY_TO_RUN_SMOKE_CYCLE` は smoke cycle 実行計画であり、自動 paper 実行、normal paper pass、live readiness ではない。
- `strategy_runtime_observation_manifest.v1` の `INGESTED` は paper runtime ledger を読めたという意味であり、paper pass、drift pass、live readiness ではない。
- `paper_vs_backtest_drift_review.v1` の `READY_FOR_HUMAN_DRIFT_REVIEW` は backtest と runtime observation を読めたという意味であり、micro live plan、paper pass、live readiness ではない。
- `strategy_learning_event.v1`、`strategy_revision_request.v1`、`strategy_revision_request_review.v1` は学習、改訂要求、人間判断の記録であり、自動採用、Strategy Authoring YAML の自動編集、paper / live 許可ではない。
- `strategy-backtest-pack-validate` の `PASS` は、artifact chain と no-live boundary の検査通過であり、alpha 証明ではない。
- `strategy-review-build` と `strategy-review-record` は、人間が読んだ review packet と判断記録を残す仕組みであり、注文許可ではない。`--input-contract` と `--strategy-idea` は read-only optional source summary である。
- `paper観察候補` / `PAPER_OBSERVATION_CANDIDATE` は、次の検証候補であり、paper order を出してよいという意味ではない。
- `venue-read-only-probe` は、将来候補 venue の境界を local fixture で説明するだけで、Bitget / Hyperliquid の本番接続や credential readiness を証明しない。
- Trade[XYZ] は実装済み venue surface だが、標準の開発主軸は backtest-first / venue-neutral である。

この文書で「できる」と書いていることの多くは、local file を読み書きする artifact workflow である。外部 API、wallet、signing、exchange write、live order に接続する機能として読んではいけない。

## 主要 artifact の読み方

この repo は「画面で操作するアプリ」ではなく、「CLI が JSON / Markdown / HTML artifact を作り、それを次の command や人間レビューが読む」構造になっている。

| Artifact | 何を表すか | 第三者が見るべきこと |
|---|---|---|
| `strategy_authoring_spec.v1` | YAML 戦略定義 | 何を見て、どの条件で入退出し、どの閾値で失敗扱いにするか |
| `strategy_authoring_backtest_result.v1` | 単体 native backtest 結果 | `trade_count`, `total_return`, `max_drawdown`, `backtest_passed`, capital block |
| `strategy_backtest_pack.v1` | backtest artifact chain の manifest | どの artifact を pack に含め、どの engine / framework policy で完了扱いにしたか |
| `strategy_backtest_pack_validation.v1` | pack の検証結果 | artifact path / hash、5手法、paper-only / no-live 境界、欠損や失敗 |
| `strategy_input_contract.v1` | 戦略候補が前提にする入力データ契約 | source path / hash、available_at、revision policy、survivorship policy、execution reality |
| `strategy_input_contract_validation.v1` | 入力データ契約の検証結果 | missing required、hash mismatch、boundary violation、strict status |
| `strategy_idea.v1` | Strategy Authoring に進める前の戦略の種 | hypothesis、baseline、invalidation、risk、required input contract |
| `strategy_intake_decision.v1` | 戦略の種の入口判定 | `READY_FOR_AUTHORING_DRAFT` / `NEEDS_*` / `REJECT` と required actions |
| `strategy_stage_policy.v1` | stage ごとの進行条件 | paper smoke、normal paper、drift review、micro live plan の閾値と fixed safety |
| `strategy_stage_policy_validation.v1` | stage policy の検証結果 | policy hash、stage completeness、boundary violation、strict status |
| `strategy_stage_decision.v1` | policy に基づく次段階判定 | selected stage / profile、source hash、passed / failed condition、permission false flags |
| `strategy_paper_smoke_plan.v1` | paper smoke 実行前の計画 | required source artifact、threshold、execution preview、permission false flags |
| `strategy_runtime_observation_manifest.v1` | paper runtime の観測 ingest | normalized ledger path/hash、fills、blocked、no-fill、spread、quote age、block reason |
| `paper_vs_backtest_drift_review.v1` | backtest と paper runtime の差分 review | trade count、fills、blocked、no-fill、spread、quote age、recommended action、permission false flags |
| `strategy_learning_event.v1` | Drift Review から得た学習イベント | finding、impact、recommended action、source hash、auto_applied=false |
| `strategy_next_scale_plan.v1` | scale decision 後の次の拡大計画 | next risk limits、monitoring、kill switch、multiplier guard、permission false flags |
| `strategy_workbench_viewer.v1` | static viewer の根拠 manifest | source artifact path/hash、schema_version、status、boundary violation、HTML path/hash、permission false flags |
| `strategy_revision_request.v1` | Learning ledger から作る改訂要求 | requested changes、reason、source learning events、direct_spec_edit_allowed=false |
| `strategy_revision_request_review.v1` | 改訂要求に対する人間判断 | decision、rationale、source request hash、authoring_update_input_allowed |
| `strategy_backtest_comparison.v1` | native / suite / optional framework / robustness の比較 | method results、suite best run、threshold failure、weakest era |
| `strategy_backtest_html_report.v1` | HTML report の根拠 manifest | source artifact path / hash、result label、visual data、no-live flags |
| `strategy_review_manifest.v1` | 人間 review packet の機械検証 manifest | review が読んだ source artifact、hash、missing / invalid / blocked 状態 |
| `operator_strategy_review.v1` | 人間判断の記録 | reviewer、decision、rationale、reviewed artifact hash、paper/live permission が false か |
| `strategy_paper_observation_status.v1` | paper observation の状態要約 | normal / smoke の分離、requirement gaps、live conversion 禁止 |
| `venue_read_only_probe_summary.v1` | venue capability 境界 | current venue / future venue の disabled 状態、no-network / no-write flags |

## 実務でまず試す最短ルート

外部 API や取引所接続なしで、第三者が repo の主要機能を確認する最短ルート:

```bash
uv sync --dev --locked
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
uv run sis strategy-backtest-html-report
```

このルートで確認できること:

- YAML 戦略が validation を通るか。
- signal / backtest metrics が生成されるか。
- backtest pack と validation artifact が作れるか。
- benchmark、stress、no-lookahead、data availability、comparison の artifact chain が揃うか。
- HTML report で損益グラフ、benchmark 比較、期間別 trade table、stress summary、diagnostics、結果ラベルを読めるか。

このルートで確認できないこと:

- 実市場で利益が出るか。
- paper order を実行してよいか。
- live order、wallet、signing、exchange write が動くか。
- Bitget / Hyperliquid production venue として使えるか。

## 追加調査での補正

この更新では、`uv run sis --help` の public command 一覧、`src/sis/cli.py` の command registration、`schemas/*.json`、`tests/`、既存 current docs を再確認した。

補正した点:

- Public CLI Command Catalog は [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) へ分離した。固定の command count を current truth にせず、確認時は `uv run sis --help` と `uv run python scripts/check_cli_catalog.py` を再実行する。
- Strategy Review には `strategy-review-build` と `strategy-review-record` がある。
- AI / Codex 向けには [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md)、人間向けには [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) が追加され、戦略作成、編集、backtest、結果解釈の入口が分かれた。
- `strategy-backtest-html-report` は dependency 追加なしの repo 標準 HTML report であり、optional `quantstats` report とは別物である。
- 本文側で薄かった `research-dag-*`、`strategy-backtest-framework-run`、legacy `build-backtest`、Trade[XYZ] data cycle、historical archive quote normalization、market-session utility、Strategy Lifecycle docs、Algo / Strategy Factory docs、schema family の説明を補った。
- `docs/strategy_lifecycle/` は current-docs 検査対象に追加した。
- `operator_strategy_review.v1` と `operator_review.yaml` の境界を追記した。これは paper / live 許可ではなく、Strategy Review packet に対する人間判断と source hash 再検証の artifact である。

## 正本と検証方法

優先順位:

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`, `pyproject.toml`, `uv.lock`
2. `uv run sis --help`
3. current docs
4. generated artifacts under `data/`
5. `docs/archive/` と `plan/archive/`

検証 command:

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

`data/` は runtime / generated state であり、fresh checkout では再生成が必要になる。

## 1. Runtime / Repo Operation

できること:

- Python 3.13 固定の CLI workspace として動かせる。
- `uv sync --dev --locked` で lockfile 通りに環境を作れる。
- `sis` CLI を `pyproject.toml` の script entrypoint から実行できる。
- `./scripts/check` で lock sync、Python version、Ruff lint、Ruff format check、current docs check、Pyrefly、ty、Pytest をまとめて検証できる。
- current docs の metadata、links、EOF、legacy root reference を `scripts/check_current_docs.py` で検査できる。
- `implementation-status`, `current-state-index`, `readiness-snapshot` などで repo 状態や readiness を artifact / report 化できる。

主要ファイル:

- `pyproject.toml`
- `uv.lock`
- `.python-version`
- `scripts/check`
- `scripts/check_current_docs.py`
- `src/sis/cli.py`
- `src/sis/commands/`

## 2. Strategy Research Lab

できること:

- Strategy Lab の experiment spec から signal、trial、evaluation、candidate、promotion、paper intent preview を作れる。
- `strategy-preview` で組み込み preview を生成できる。
- `strategy-experiment-run --spec` で spec から strategy signal artifact を生成できる。
- `evaluate-strategy-lab` で signal / evaluation を評価できる。
- `build-paper-candidate-pack` で paper candidate pack を作れる。
- `promotion-decision` で hold / promote などの promotion decision を artifact 化できる。
- `build-paper-intent-preview` で paper-only の intent preview を作れる。
- `paper-from-intents` で paper intent を paper flow へ渡せる。
- venue suitability gate により、NDX/QQQ family などは valid promotion evidence がない限り fail closed できる。

主な schema:

- `strategy_experiment_spec.v1.schema.json`
- `strategy_signal.v1.schema.json`
- `evaluation_plan.mls.v1.schema.json`
- `trial_record.v1.schema.json`
- `trade_candidate.v1.schema.json`
- `paper_candidate_pack.v1.schema.json`
- `promotion_decision.v1.schema.json`
- `paper_intent_preview.v1.schema.json`

境界:

- `PaperIntentPreview` は paper-only。live order ではない。
- Strategy Lab の tracked JSON Schema は interoperability guard で、詳細 validation は Pydantic model が正本。

## 3. Algo Strategy Docs / Strategy Factory

できること:

- `docs/algo/` で、戦略仮説、戦略部品、blueprint、実験準備、scorecard、validation playbook、source note index を読める。
- `docs/algo/strategy_factory/` で、1戦略1枚の候補シート、reject taxonomy、backlog 台帳、gate review checklist、duplicate control、operator guide を使える。
- これはコード実行 surface ではなく、Strategy Lab / Strategy Authoring に入れる前の設計・選別・記録のための文書 surface である。

主要 docs:

- [algo/README.md](algo/README.md)
- [algo/strategy_factory/README.md](algo/strategy_factory/README.md)
- [algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md](algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md)
- [algo/RESEARCH_VALIDATION_PLAYBOOK.md](algo/RESEARCH_VALIDATION_PLAYBOOK.md)

境界:

- 外部メモや動画由来の勝率・利益主張は検証済み事実として扱わない。
- 実弾運用ではなく、研究、設計、検証のための作業資料である。

## 3-1. Strategy Input Contract / Idea Intake

できること:

- `strategy_input_contract.v1` で、戦略候補が使う入力データを source path、sha256、schema version、generated_at、available_at、revision policy、survivorship policy、execution reality 付きで記録できる。
- `strategy-input-contract-validate` で、required source missing、optional source missing、hash mismatch、boundary violation、required column missing、available_at column missing、future timestamp violation を検査し、`strategy_input_contract_validation.v1` JSON と Markdown report を出せる。
- `strategy_idea.v1` で、Strategy Authoring に進める前の戦略の種を hypothesis、baseline、invalidation、risk、required input contract、execution assumptions 付きで記録できる。
- `strategy-intake-validate` で、戦略の種を `READY_FOR_AUTHORING_DRAFT`、`NEEDS_SPEC`、`NEEDS_DATA_CHECK`、`NEEDS_RISK_SPEC`、`REJECT` に分け、`strategy_intake_decision.v1` JSON と Markdown report を出せる。
- 欠落した risk、baseline、invalidation、required input contract は validation exception だけで終わらせず、可能な範囲で `NEEDS_*` decision artifact に落とせる。

主要 command:

- `strategy-input-contract-validate`
- `strategy-intake-validate`

主要 code / schema / tests:

- `src/sis/strategy_inputs/`
- `src/sis/commands/strategy_inputs.py`
- `schemas/strategy_input_contract.v1.schema.json`
- `schemas/strategy_input_contract_validation.v1.schema.json`
- `schemas/strategy_idea.v1.schema.json`
- `schemas/strategy_intake_decision.v1.schema.json`
- `tests/strategy_inputs/`
- [strategy_inputs/README.md](strategy_inputs/README.md)

境界:

- `READY_FOR_AUTHORING_DRAFT` は Strategy Authoring draft の入口条件であり、paper observation、live trading、alpha、wallet、signing、exchange write の許可ではない。
- 入力契約は optional `validation_expectations` がある場合、CSV / JSONL / NDJSON / Parquet の required columns、timestamp upper bound、available_at column も検査できる。ただし source artifact を生成・修正しない。
- Strategy Review optional source connection は実装済みで、`strategy-review-build --input-contract --strategy-idea` が read-only source artifact と markdown summary を出せる。

## 3-2. Strategy Stage Policy / Decision

できること:

- `strategy_stage_policy.v1` で、`paper_smoke`、`normal_paper_observation`、`drift_review`、`micro_live_plan` の進行条件を strategy profile ごとに定義できる。
- `strategy-stage-policy-validate` で、required stage、fixed safety、rate range、no-live boundary を検査し、`strategy_stage_policy_validation.v1` JSON と Markdown report を出せる。
- `strategy-stage-decision` で、operator review または `strategy_paper_observation_status.v1` を読み、次 stage の計画に進める証拠があるかを `strategy_stage_decision.v1` JSON と Markdown report にできる。
- decision artifact には `policy_id`、`policy_hash`、`selected_stage`、`selected_profile`、source artifact hash、passed / failed condition、manual override reason を残せる。

主要 command:

- `strategy-stage-policy-validate`
- `strategy-stage-decision`

主要 code / schema / tests:

- `src/sis/strategy_stage/`
- `src/sis/commands/strategy_stage.py`
- `schemas/strategy_stage_policy.v1.schema.json`
- `schemas/strategy_stage_policy_validation.v1.schema.json`
- `schemas/strategy_stage_decision.v1.schema.json`
- `tests/strategy_stage/`
- [strategy_stage/README.md](strategy_stage/README.md)

境界:

- `READY_FOR_PAPER_SMOKE_PLAN` は paper smoke plan の候補であり、paper order 実行許可ではない。
- `READY_FOR_NORMAL_PAPER_OBSERVATION` は通常 paper observation の候補であり、live readiness ではない。
- `READY_FOR_DRIFT_REVIEW` は drift review を作る候補であり、micro live permission ではない。
- `READY_FOR_MICRO_LIVE_PLAN` は micro live plan の候補であり、micro live execution permission ではない。
- manual override は記録されるが、failed evidence を自動で合格にしない。

## 3-3. Strategy Paper Smoke Plan

できること:

- `strategy-paper-smoke-plan` で、`READY_FOR_PAPER_SMOKE_PLAN` の stage decision から `strategy_paper_smoke_plan.v1` JSON と Markdown report を出せる。
- `strategy_stage_policy.v1` の `paper_smoke` threshold を読み、既存 `strategy-paper-observation-cycle --smoke` の実行 preview に反映できる。
- backtest acceptance、paper candidate pack、promotion decision、operator promotion の source artifact 存在、path、hash、schema version を記録できる。
- source artifact が足りない場合も、`NEEDS_SOURCE_ARTIFACTS` として欠落を plan artifact に残せる。
- `strategy-paper-observation-cycle --smoke` は明示指定された smoke threshold を尊重できる。未指定時の既存 smoke default は 1 fill / 1 trading day のまま。

主要 command:

- `strategy-paper-smoke-plan`

主要 code / schema / tests:

- `src/sis/strategy_paper_smoke/`
- `src/sis/commands/strategy_paper_smoke.py`
- `schemas/strategy_paper_smoke_plan.v1.schema.json`
- `tests/strategy_paper_smoke/`
- [strategy_paper_smoke/README.md](strategy_paper_smoke/README.md)

境界:

- `strategy-paper-smoke-plan` は paper order を実行しない。
- `READY_TO_RUN_SMOKE_CYCLE` は paper smoke cycle の実行計画であり、normal paper observation pass、paper execution permission、live readiness ではない。
- smoke pass は normal paper observation pass として数えない。
- wallet、signing、exchange write、live order は使わない。

## 3-4. Strategy Runtime Observation Ingest

できること:

- `strategy-runtime-observation-ingest` で、`paper_observation_session_manifest.v1` と `paper_observation_ledger.jsonl` を読み、`strategy_runtime_observation_manifest.v1` JSON と Markdown summary を出せる。
- paper runtime ledger を `runtime_observation_ledger.jsonl` として正規化コピーできる。
- ledger entry、paper fills、blocked、no-fill、unique intent、unique symbol、spread、quote age、block reason を summary にできる。
- session manifest と ledger の source path / hash を残せる。
- live / wallet / signing / exchange write 系の true flag が混入した場合は `BLOCKED_BOUNDARY_VIOLATION` として扱える。

主要 command:

- `strategy-runtime-observation-ingest`

主要 code / schema / tests:

- `src/sis/strategy_runtime_observation/`
- `src/sis/commands/strategy_runtime_observation.py`
- `schemas/strategy_runtime_observation_manifest.v1.schema.json`
- `tests/strategy_runtime_observation/`
- [strategy_runtime_observation/README.md](strategy_runtime_observation/README.md)

境界:

- paper runtime artifact を読むだけで、paper order、live order、wallet、signing、exchange write は実行しない。
- `INGESTED` は paper pass、drift pass、live readiness ではない。
- Micro Live Canary 後の actual live execution observation とは混ぜない。

## 3-5. Paper vs Backtest Drift Review

できること:

- `strategy-drift-review` で、`strategy_authoring_backtest_result.v1` と `strategy_runtime_observation_manifest.v1` を読み、`paper_vs_backtest_drift_review.v1` JSON と Markdown report を出せる。
- backtest 側の `trade_count`、`total_return`、`max_drawdown`、`backtest_passed` と、paper runtime 側の fills、blocked、no-fill、spread、quote age、realized paper PnL、fee、slippage、fill price drift、order lifecycle を並べられる。
- `--max-no-fill-rate`、`--max-blocked-rate`、`--max-spread-bps`、`--max-return-drift` を review threshold として指定できる。
- `recommended_action` は `HUMAN_REVIEW_REQUIRED`、`EXTEND_OBSERVATION`、`REVISE_STRATEGY`、`REPAIR_ARTIFACTS` のいずれかになる。
- live / wallet / signing / exchange write 系の true flag が混入した場合は `BLOCKED_BOUNDARY_VIOLATION` として扱える。

主要 command:

- `strategy-drift-review`

主要 code / schema / tests:

- `src/sis/strategy_drift_review/`
- `src/sis/commands/strategy_drift_review.py`
- `schemas/paper_vs_backtest_drift_review.v1.schema.json`
- `tests/strategy_drift_review/`
- [strategy_drift_review/README.md](strategy_drift_review/README.md)

境界:

- `READY_FOR_HUMAN_DRIFT_REVIEW` は micro live plan、paper pass、live readiness ではない。
- `HUMAN_REVIEW_REQUIRED` は合格ではなく、人間が読む必要があるという意味である。
- realized paper PnL と filled notional が runtime observation にある場合だけ PnL drift を見る。ない場合は fill / block / no-fill / spread / quote age の限定 review として扱う。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-6. Strategy Learning / Revision Request / Authoring Update Handoff

できること:

- `strategy-learning-ledger-update` で、`paper_vs_backtest_drift_review.v1` から `strategy_learning_event.v1` を作り、`learning_ledger.jsonl` と `learning_summary.md` に反映できる。
- `strategy-revision-request-build` で、learning ledger から `strategy_revision_request.v1` JSON と Markdown report を作れる。
- `strategy-revision-request-review` で、revision request に対する人間判断を `strategy_revision_request_review.v1` JSON と Markdown report に記録できる。
- `strategy-authoring-update-handoff` で、承認済み revision request と現行 Strategy Authoring YAML を source hash 付きで結び、別工程の人間編集タスクを `strategy_authoring_update_handoff.v1` JSON と Markdown report にできる。
- Drift Review の `REVISE_STRATEGY`、`EXTEND_OBSERVATION`、`REPAIR_ARTIFACTS`、`HUMAN_REVIEW_REQUIRED` を、学習イベントと改訂要求に変換できる。
- learning event と revision request は `requires_human_review=true`、`auto_applied=false`、`direct_spec_edit_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false` を固定する。

主要 command:

- `strategy-learning-ledger-update`
- `strategy-revision-request-build`
- `strategy-revision-request-review`
- `strategy-authoring-update-handoff`

主要 code / schema / tests:

- `src/sis/strategy_learning/`
- `src/sis/commands/strategy_learning.py`
- `schemas/strategy_learning_event.v1.schema.json`
- `schemas/strategy_revision_request.v1.schema.json`
- `schemas/strategy_revision_request_review.v1.schema.json`
- `schemas/strategy_authoring_update_handoff.v1.schema.json`
- `tests/strategy_learning/`
- [strategy_learning/README.md](strategy_learning/README.md)

境界:

- Strategy Authoring YAML を直接編集しない。
- revision request は採用済み改訂ではなく、人間レビュー前提の要求である。
- `APPROVE_FOR_AUTHORING_UPDATE` は別工程の human authoring update の入力許可であり、YAML 自動編集ではない。
- `strategy_authoring_update_handoff.v1` は human authoring update の入力 artifact であり、採用済み改訂ではない。
- `NO_REVISION_REQUIRED` は paper pass、micro live plan、live readiness ではない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-7. Strategy Case Lite

できること:

- `strategy-case-lite-update` で、stage decision、runtime observation、drift review、learning event、revision request、authoring handoff、micro live plan、live observation、scale decision を strategy 単位の `strategy_case_lite.v1` timeline に束ねられる。
- source path、sha256、schema_version、event time、status、recommended action、failed condition 由来の blocked reason を残せる。
- `summary.latest_status`、`summary.open_actions`、`summary.blocked_reasons`、`summary.latest_source_hashes` を読める。

主要 command:

- `strategy-case-lite-update`

主要 code / schema / tests:

- `src/sis/strategy_case_lite/`
- `src/sis/commands/strategy_case_lite.py`
- `schemas/strategy_case_lite.v1.schema.json`
- `tests/strategy_case_lite/`
- [strategy_case_lite/README.md](strategy_case_lite/README.md)

境界:

- case timeline は permission artifact ではない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-8. Strategy Daily Brief

できること:

- `strategy-daily-brief` で、`data/` 配下の JSON artifact を走査し、今日見るべき項目を `strategy_daily_brief.v1` JSON と Markdown にまとめられる。
- broken artifact、pending human review、normal paper gap、drift review needed、learning request pending、boundary violation を一覧化できる。
- 各 item に category、severity、strategy_id、status、action、reason、source path、source hash、schema version を残せる。

主要 command:

- `strategy-daily-brief`

主要 code / schema / tests:

- `src/sis/strategy_daily_brief/`
- `src/sis/commands/strategy_daily_brief.py`
- `schemas/strategy_daily_brief.v1.schema.json`
- `tests/strategy_daily_brief/`
- [strategy_daily_brief/README.md](strategy_daily_brief/README.md)

境界:

- Daily Brief は read-only index であり、permission artifact ではない。
- `total_item_count=0` は paper pass、micro live readiness、live readiness ではない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-9. Strategy AI Review

できること:

- `strategy-ai-review-packet-build` で、source artifact の full payload ではなく、安全な source summary だけを `strategy_ai_review_packet.v1` にできる。
- secret / credential / account detail / wallet / exchange write 系の source が見つかった場合は `BLOCKED_SENSITIVE_SOURCE` として、AI review ready にしない。
- `strategy-ai-review-note-record` で、provider、model、prompt hash、input hash、limitations、findings、recommendation、disagreements を `strategy_ai_review_note.v1` として記録できる。
- AI note は `auto_applied=false`、`permission_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false` を固定する。

主要 command:

- `strategy-ai-review-packet-build`
- `strategy-ai-review-note-record`

主要 code / schema / tests:

- `src/sis/strategy_ai_review/`
- `src/sis/commands/strategy_ai_review.py`
- `schemas/strategy_ai_review_packet.v1.schema.json`
- `schemas/strategy_ai_review_note.v1.schema.json`
- `tests/strategy_ai_review/`
- [strategy_ai_review/README.md](strategy_ai_review/README.md)

境界:

- AI review は判断補助であり、permission engine ではない。
- 複数 AI の意見が一致しても自動採用しない。
- Strategy Authoring YAML を自動編集しない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-10. Strategy Model / Optimizer Loop

できること:

- `strategy-model-run-record` で、ML / DL / GA / optimizer の実行済み trial を `strategy_optimizer_trial_ledger.v1` と `strategy_model_run.v1` に記録できる。
- training data path / hash、label definition、split、seed、search space hash、best trial、holdout result、limitations を残せる。
- complete / failed / pruned / running trial をすべて ledger に残し、`success_only_reporting=false` を固定できる。
- model / optimizer output route は `IDEA_INTAKE_ONLY` または `REVISION_REQUEST_ONLY` に限定できる。

主要 command:

- `strategy-model-run-record`

主要 code / schema / tests:

- `src/sis/strategy_model_loop/`
- `src/sis/commands/strategy_model_loop.py`
- `schemas/strategy_model_run.v1.schema.json`
- `schemas/strategy_optimizer_trial_ledger.v1.schema.json`
- `tests/strategy_model_loop/`
- [strategy_model_loop/README.md](strategy_model_loop/README.md)

境界:

- optimizer 実行 command ではない。実行済み結果を記録する。
- Strategy Authoring YAML を直接編集しない。
- paper order、live order、wallet、signing、exchange write は実行しない。
- `optuna` 依存はこの first slice では追加していない。

## 3-11. Strategy Micro Live Plan Gate

できること:

- `strategy-micro-live-plan` で、stage decision、drift review、人間承認 artifact、risk limits、monitoring plan、kill switch procedure を読み、`strategy_micro_live_plan.v1` JSON と Markdown report を出せる。
- 既存 `configs/micro_live_policy.yaml` を渡した場合、max order notional、max daily loss、max open positions、allowed symbols が既存 `MicroLivePolicy` と矛盾しないかを plan artifact に残せる。
- `plan_status` は `READY_FOR_HUMAN_MICRO_LIVE_REVIEW`、`NEEDS_STAGE_DECISION`、`NEEDS_DRIFT_REVIEW`、`NEEDS_HUMAN_APPROVAL`、`NEEDS_RISK_LIMITS`、`BLOCKED_BOUNDARY_VIOLATION` のいずれかになる。
- source path、sha256、schema version、producer command を残せる。

主要 command:

- `strategy-micro-live-plan`

主要 code / schema / tests:

- `src/sis/strategy_micro_live_plan/`
- `src/sis/commands/strategy_micro_live_plan.py`
- `schemas/strategy_micro_live_plan.v1.schema.json`
- `tests/strategy_micro_live_plan/`
- [strategy_micro_live_plan/README.md](strategy_micro_live_plan/README.md)

境界:

- micro live execution command ではない。
- Workbench 標準 CLI として live order command を追加しない。
- `MicroLivePolicy.enabled=true` を要求しない。これは plan gate であり、実行 gate ではない。
- `READY_FOR_HUMAN_MICRO_LIVE_REVIEW` は live execution permission ではない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-12. Strategy Live Observation

できること:

- `strategy-live-observation-ingest` で、既存 micro live canary audit bundle と任意の report / micro live plan を read-only で読み、`strategy_live_observation_manifest.v1` JSON と Markdown report を出せる。
- canary status、blocked reasons、symbol、side、notional、leverage、schedule cancel、order submit、order status、cancel、close、fill / reject / cancel / close submitted の観測を summary にできる。
- account snapshot の有無、equity、available cash を残せる。account address は manifest に引き継がない。
- `LIVE_OBSERVATION_INGESTED`、`BLOCKED_CANARY`、`BLOCKED_BOUNDARY_VIOLATION` を区別できる。

主要 command:

- `strategy-live-observation-ingest`

主要 code / schema / tests:

- `src/sis/strategy_live_observation/`
- `src/sis/commands/strategy_live_observation.py`
- `schemas/strategy_live_observation_manifest.v1.schema.json`
- `tests/strategy_live_observation/`
- [strategy_live_observation/README.md](strategy_live_observation/README.md)

境界:

- live execution を実行しない。
- paper runtime observation と混ぜない。
- scale-up permission ではない。
- production live readiness ではない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-13. Strategy Scale Decision

できること:

- `strategy-scale-decision` で、`strategy_live_observation_manifest.v1` と任意の `strategy_micro_live_plan.v1` を読み、`strategy_scale_decision.v1` JSON と Markdown report を出せる。
- live observation が ingested か、blocked reason、actual fill、cancel / close safety、rejection、max loss breach を policy に照らして判定できる。
- `READY_FOR_HUMAN_SCALE_REVIEW`、`NEEDS_LIVE_OBSERVATION`、`NEEDS_REPAIR`、`REVISE_OR_RETIRE`、`BLOCKED_BOUNDARY_VIOLATION` を区別できる。

主要 command:

- `strategy-scale-decision`

主要 code / schema / tests:

- `src/sis/strategy_scale_decision/`
- `src/sis/commands/strategy_scale_decision.py`
- `schemas/strategy_scale_decision.v1.schema.json`
- `tests/strategy_scale_decision/`
- [strategy_scale_decision/README.md](strategy_scale_decision/README.md)

境界:

- scale-up execution permission ではない。
- `PREPARE_NEXT_SCALE_PLAN` は次の計画 artifact を作る候補であり、live order permission ではない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 3-14. Strategy Workbench Viewer

できること:

- `strategy-workbench-viewer-build` で、既存の JSON / Markdown / text artifact を読み、static HTML viewer と `strategy_workbench_viewer.v1` manifest を出せる。
- source artifact の path、sha256、schema_version、status、boundary violation を一覧化できる。
- `--artifact` を複数指定するか、`--data-dir` 配下を scan できる。

主要 command:

- `strategy-workbench-viewer-build`

主要 code / schema / tests:

- `src/sis/strategy_workbench_viewer/`
- `src/sis/commands/strategy_workbench_viewer.py`
- `schemas/strategy_workbench_viewer.v1.schema.json`
- `tests/strategy_workbench_viewer/`
- [strategy_workbench_viewer/README.md](strategy_workbench_viewer/README.md)

境界:

- static viewer であり、artifact の正本ではない。
- artifact を編集しない。
- paper order、live order、wallet、signing、exchange write は実行しない。
- Svelte UI / API server / hidden mutable state ではない。

## 3-15. Strategy Next Scale Plan

できること:

- `strategy-next-scale-plan` で、`strategy_scale_decision.v1` と任意の `strategy_micro_live_plan.v1` を読み、`strategy_next_scale_plan.v1` JSON と Markdown report を出せる。
- 次の order notional、position notional、daily loss、total loss、open positions、allowed symbols、session window、monitoring、schedule cancel、kill switch を artifact に残せる。
- 前回 micro live plan の risk limit に対して `max_scale_multiplier` を超えた拡大を `NEEDS_RISK_REPAIR` として止められる。

主要 command:

- `strategy-next-scale-plan`

主要 code / schema / tests:

- `src/sis/strategy_next_scale_plan/`
- `src/sis/commands/strategy_next_scale_plan.py`
- `schemas/strategy_next_scale_plan.v1.schema.json`
- `tests/strategy_next_scale_plan/`
- [strategy_next_scale_plan/README.md](strategy_next_scale_plan/README.md)

境界:

- next-scale execution permission ではない。
- `READY_FOR_HUMAN_NEXT_SCALE_REVIEW` は人間レビュー候補であり、live order permission ではない。
- paper order、live order、wallet、signing、exchange write は実行しない。

## 4. Strategy Authoring YAML

できること:

- `strategy_authoring_spec.v1` YAML を初期化、検証、説明、実行できる。
- rule-based long / short / hold / close / reduce / add / rebalance signal を作れる。
- derived features を多数作れる。例: true range, ATR, Bollinger bands, Donchian channels, Keltner channels, Ichimoku cloud, MACD line, stochastic K/D, ADX, OBV, volume z-score, calendar features, rolling correlation / beta / spread z-score / tracking error / information ratio, flow / carry / liquidity / options-vol, on-chain / sentiment / event / fundamental / factor-ranking, execution-constraint, data-quality / ensemble / capacity, lag, return / log-return, rolling return / sum / volatility / percentile-rank / skew / kurtosis, annualized volatility, realized variance, downside volatility, Sharpe / Sortino-like ratios, Kelly fraction, historical VaR, expected shortfall, cumulative return, slope, mean-reversion score, EMA, RSI, rolling min / max。
- column-to-column condition、cross / trend / consecutive condition、exclusion-none condition、regime membership filter、regime-specific override を扱える。
- paper-only dynamic multi-leg、leg exit、order override、execution override、group metadata、group aggregate metrics、pair-trade signal を扱える。
- paper-only linear model score と `strategy-author-train-model` adapter を使える。
- group-wise cross-sectional top-bottom / fraction-tail rotation、minimum candidates、score thresholds を扱える。
- opposite-signal exit、explicit close-signal exit、reduce-signal partial exit、add-signal scale-in、rebalance-signal exposure resize、rebalance band skip を扱える。
- bracket-OCO、partial-profit break-even lifecycle、trailing stop、minimum / maximum holding period、exit priority を扱える。
- order-style entry、time-in-force、post-only、reduce-only、execution-profile preset を扱える。
- slippage with row cost、partial-fill with row fill、min-fill gate、spread gate、depth-based fill、latency gate、queue-position gate を扱える。
- short-borrow availability / cost gate、tax drag、turnover / capacity / crowding fee gate を扱える。
- grouped / group-net / row-level / global net portfolio exposure limits、portfolio turnover budget、risk throttle profiles、volatility targeting、target-weight、inverse-vol、dollar-neutral、beta-neutral、group-neutral allocation を扱える。
- multi-timeframe confirmation、temporal cadence、event-window calendar filters、parameter sweep、era metrics、executed signal summary、strategy scorecard を出せる。
- `strategy_authoring_bundle.v1` で複数 strategy spec の paper portfolio 比較ができる。

主要 command:

- `strategy-author-init`
- `strategy-author-validate`
- `strategy-author-explain`
- `strategy-author-run`
- `strategy-author-bundle-run`
- `strategy-author-train-model`

主な schema:

- `strategy_authoring_spec.v1.schema.json`
- `strategy_authoring_bundle.v1.schema.json`
- `strategy_authoring_backtest_result.v1.schema.json`
- `strategy_authoring_bundle_result.v1.schema.json`

境界:

- `strategy-author-run --through backtest` は research / paper-only backtest であり、live order ではない。
- `rules.sizing.notional_usd` は signal の想定 notional であり、backtest initial capital とは混ぜない。

## 5. Backtest

できること:

- Strategy Authoring の native backtest を実行できる。
- `strategy-backtest-suite` で複数 spec / 複数 case / walk-forward / purged walk-forward / bootstrap を比較できる。
- `strategy-backtest-pack` で backtest artifact chain を一括生成できる。
- `strategy-backtest-pack-validate` で path / hash / method / paper-only boundary / framework policy を検査できる。
- `strategy-backtest-artifact-summary` で主要 artifact field を JSON stdout にまとめられる。
- `strategy-backtest-html-report` で既存 artifact から損益グラフ、benchmark 比較、期間指定 trade table、stress summary、rolling / regime / comparison diagnostics、結果ラベル付きの単一 HTML / JS report を作れる。
- `strategy-backtest-html-report` は `data/research/backtest_html_report/strategy_backtest_html_report.json` に manifest、`data/reports/strategy_backtest_html_report.html` にブラウザで開ける report を出す。どちらも generated artifact であり、必要なら再生成する。
- HTML report manifest は source artifact path / hash、`result_label`、`min_trade_count_for_candidate`、`paper_observation_candidate_is_permission=false`、`paper_only=true`、`permits_live_order=false`、`wallet_used=false`、`exchange_write_used=false` を持つ。
- HTML report の結果ラベルは `paper_observation_candidate` でも paper / live 実行許可ではない。既定では `--min-trade-count-for-candidate 30` 未満の trade count は `insufficient_evidence` / `検証不足` として扱う。
- `strategy-review-build` で既存 backtest artifact chain から人間レビュー用 `review.md` と機械検証用 `review_manifest.json` を作れる。
- `strategy-backtest-compare` で native result、suite、adapter spike、external result、portfolio comparison、metric extension、report extension、stress、regime split、rolling stability、benchmark relative、completion artifact を比較 artifact に正規化できる。
- `strategy-backtest-data-availability` で local source hash、row count、timestamp range、gap / duplicate、future candidate を記録できる。
- `strategy-backtest-baseline-compare` で cash / no-trade と return-series control を比較できる。
- `strategy-backtest-no-lookahead-diff` で future mutation replay と coverage / false-negative risk を記録できる。
- `strategy-backtest-execution-sim` で paper-only order intents / fill events を作れる。
- `strategy-backtest-assumption-ledger` と `strategy-backtest-trial-ledger` で仮定と試行履歴を残せる。
- `strategy-backtest-framework-run` で optional extra の `vectorbt`, `bt`, `empyrical_reloaded`, `quantstats` runner / extension を明示 framework list から実行できる。
- `build-backtest` で legacy bridge 系の backtest decision summary / decision log を作れる。
- stress、regime split、rolling stability、benchmark relative を出せる。
- `strategy-review-record` で `review.md` / `review_manifest.json` を読んだ人間判断を `operator_review.yaml` として保存し、`--validate-existing` で path と hash を再照合できる。

optional OSS:

- `vectorbt==1.0.0`: signal runner / external check
- `bt==1.2.0`: portfolio allocation / rebalance comparison
- `empyrical-reloaded==0.5.12`: metrics normalization
- `quantstats==0.0.81`: report / tear sheet

reference-only / 採用前 contract:

- `strategy-backtest-microstructure-readiness`: HftBacktest などの L2/L3/tick/latency/queue input readiness
- `strategy-backtest-qstrader-contract`: qstrader local input contract
- `strategy-backtest-portfolio-validation-contract`: skfolio / Riskfolio-Lib portfolio validation contract
- `strategy-backtest-pybroker-contract`: PyBroker local DataFrame input contract
- `strategy-backtest-constraint-breaker-decision`: 制約破壊の scorecard decision

標準 engine:

- `strategy_authoring_native`

境界:

- optional OSS は標準 engine を置き換えない。
- `framework_run` は pack に入るが、pack completion の必須条件ではない。
- pack validation `PASS` は alpha / paper pass / live readiness ではない。
- strategy review output は human-review artifact であり、pack validation `PASS` を収益性、paper 移行可否、live 実行可否の証明にしない。
- operator strategy review output は non-permission artifact であり、`PAPER_OBSERVATION_CANDIDATE` は validation candidate だけを意味する。`live_allowed=false` と `paper_execution_allowed=false` は固定である。
- HftBacktest / qstrader / PyBroker / skfolio / Riskfolio-Lib は dependency 追加前 contract まで。engine 実行ではない。
- `build-backtest` は Trade[XYZ] pure backtest v0.1 や Strategy Authoring native backtest の入口ではなく、既存 bridge 系 command として読む。

詳細:

- [backtest/README.md](backtest/README.md)
- [backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md)
- [backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md](backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md)
- [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md)
- [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md)

## 6. Strategy Lifecycle / Paper Observation

できること:

- `strategy-backtest-acceptance` で backtest acceptance decision を作れる。
- `strategy-paper-observation-cycle` で paper observation cycle artifact を作れる。
- `strategy-lifecycle-review` で backtest acceptance、paper observation、phase gate summary を統合して lifecycle decision を出せる。
- `strategy-paper-observation-status` で既存 paper observation review / session manifest / lifecycle review を読み、normal threshold と smoke threshold を分けた status artifact を作れる。
- decision は `REJECT_OR_REVISE`, `CONTINUE_RESEARCH`, `BACKTEST_ACCEPTED`, `CONTINUE_PAPER_OBSERVATION`, `CONTINUE_EXECUTION_READINESS`, `ELIGIBLE_FOR_LIVE_CANARY_PLAN`, `BLOCKED_BOUNDARY_VIOLATION` などを扱える。

主な schema:

- `strategy_backtest_acceptance_decision.v1.schema.json`
- `paper_observation_session_manifest.v1.schema.json`
- `strategy_lifecycle_review.v1.schema.json`
- `strategy_paper_observation_status.v1.schema.json`

主要 docs:

- [strategy_lifecycle/README.md](strategy_lifecycle/README.md)
- [strategy_lifecycle/TARGET_OPERATING_MODEL.md](strategy_lifecycle/TARGET_OPERATING_MODEL.md)
- [strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md](strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md)
- [strategy_lifecycle/LIVE_CANARY_PLAN_GATE.md](strategy_lifecycle/LIVE_CANARY_PLAN_GATE.md)

境界:

- lifecycle review は live order を許可しない。
- paper observation status は paper intent 生成、paper order 実行、ledger 再集計をしない。
- smoke pass は normal paper observation pass ではない。
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` は live order 実行許可ではなく、別計画を書いてよい候補という意味。
- `strategy-lifecycle-review` は `lifecycle-report` とは別物。前者は strategy promotion control plane、後者は operations / recovery report である。

## 7. NDX / Research DAG Gates

できること:

- `research-dag-validate` と `research-dag-export` で core DAG YAML、variable inventory、counter DAG、data source registry を検証・export できる。
- Layer 2.2 DAG foundation を local-only で validate / export できる。
- Layer 2.2 manual review pack を作り、手動 review JSON を import し、exit gate を判定できる。
- Layer 2.3 source resolve / feature panel / open-gap residual / diagnostics を fixture-first で作れる。
- Layer 2.4 residual validation gate を実行できる。
- Layer 2.5 research-only Strategy Lab export を作れる。
- Layer 2.6 paper-observation gate で research export hash / signal hash / local quote evidence を検査できる。
- Layer 2.7 operator promotion で valid approval evidence がある場合だけ paper observation に進める。
- Layer 2.8 paper observation review で fills、観測日数、block rate、連続 block、artifact completeness、boundary violation を見られる。

主要 command:

- `research-layer22-validate`
- `research-layer22-export`
- `research-layer22-review-pack`
- `research-layer22-review-import`
- `research-layer22-exit-gate`
- `research-ndx-source-resolve`
- `research-ndx-feature-panel`
- `research-ndx-residual`
- `research-ndx-diagnostics`
- `research-ndx-residual-validate`
- `research-ndx-strategy-lab-export`
- `research-ndx-paper-observation-gate`
- `research-ndx-operator-promotion`
- `research-ndx-paper-observation-review`

境界:

- `research-dag-*` は generic core DAG artifact の検証・export surface。NDX Layer 2.2 command 群とは分けて読む。
- Layer 2.2 は manual review plumbing。feature panel、residual、backtest、paper/live order には直接接続しない。
- Layer 2.4 approval は Layer 2.5 research-only export bridge の許可であり、alpha / backtest / paper / live readiness ではない。
- Layer 2.5 export は research-only。valid Layer 2.6 / 2.7 evidence がない限り paper path では fail closed する。

## 8. Trade[XYZ] Data / Venue Surface

できること:

- Trade[XYZ] probe を実行できる。
- Trade[XYZ] quotes を収集し、summary / report を書ける。
- `collect-trade-xyz-data-cycle` で registry refresh、quote collection、normalization、coverage / readiness / bundle 更新をまとめて実行できる。
- WebSocket capture、WS quality、REST parity を作れる。
- quotes を normalize できる。
- quote coverage を build できる。
- reference data、real market reference、signal candles、account fee を収集できる。
- historical L2 archive、historical asset contexts archive、bulk archive preflight / execute / normalize を扱える。
- `normalize-trade-xyz-historical-archive-quotes` で単体の historical L2 / asset context archive から raw quote rows を作り、必要なら normalized quotes を再構築できる。
- funding history を収集し、funding events を history から build できる。
- Trade[XYZ] data readiness を build できる。
- Trade[XYZ] collection status と data bundle を作れる。
- Trade[XYZ] pure backtest v0.1 を Python API から実行できる。

主要 command:

- `probe trade-xyz`
- `collect-trade-xyz-quotes`
- `collect-trade-xyz-ws`
- `build-trade-xyz-ws-quality`
- `build-trade-xyz-rest-parity`
- `normalize-quotes`
- `normalize-trade-xyz-ws-quotes`
- `build-trade-xyz-quote-coverage`
- `build-trade-xyz-reference-data`
- `collect-trade-xyz-real-market-reference`
- `collect-trade-xyz-signal-candles`
- `collect-trade-xyz-account-fee`
- `collect-trade-xyz-historical-l2-archive`
- `collect-trade-xyz-historical-asset-ctxs-archive`
- `plan-trade-xyz-historical-archive-bulk`
- `check-trade-xyz-historical-archive-preflight`
- `execute-trade-xyz-historical-archive-bulk`
- `normalize-trade-xyz-historical-archive-bulk`
- `build-trade-xyz-session-state`
- `collect-trade-xyz-funding-history`
- `build-trade-xyz-funding-events-from-history`
- `build-trade-xyz-data-readiness`
- `trade-xyz-collection-status`
- `build-trade-xyz-data-bundle`

境界:

- Trade[XYZ] は実装済み venue surface だが、現在の開発主軸は backtest-first / venue-neutral。
- Trade[XYZ] pure backtest v0.1 は public CLI ではなく Python API surface。
- 実 live order integration は opt-in safety surface 止まりで、標準 operator CLI には micro-live 実行 command を出していない。

## 9. Real Market / Tracking / Alpaca

できること:

- cost matrix、research data ingest、event calendar、feature panel、signals を build できる。
- Alpaca smoke を実行できる。
- real market data layer と provider quality gate を扱える。
- real market vs venue tracking、lead/lag、source confidence、venue quality を扱える。

主要 command:

- `build-cost-matrix`
- `ingest-research-data`
- `build-event-calendar`
- `build-feature-panel`
- `build-signals`
- `alpaca-smoke`

境界:

- Alpaca credentials がない場合は unavailable / failed として扱う。
- fresh live `status=pass` は市場時間中の fresh bar 取得で再確認が必要。
- read-only provider connectivity は live trading readiness ではない。

## 10. Execution / Paper / Read-Only Operations

できること:

- `bot-preview` で read-only HOLD preview artifact を作れる。
- execution snapshot、venue comparison、venue diagnostics、read-only surfaces を作れる。
- Trade[XYZ] read-only execution state collector contract を使える。public user address と明示 opt-in がある場合だけ `/info` 由来の account state / open orders / fills を読み、通常実行では external API、wallet、signing、exchange write を使わず未設定理由を出す。
- order status、estimate order、balance status、fill status、cancel、close、reconcile などの execution utility command がある。
- `bitget-demo-smoke` で local/mock-first Bitget demo smoke を実行できる。
- `paper-step`, `paper-from-intents`, `paper-report`, `paper-operations-cycle` で paper operation artifact を扱える。
- daemon manifest / dry-run / run、state export / restore、monitoring status、kill switch、schedule run、notification outbox を扱える。
- `check-timeframe`, `market-session`, `next-live-window` で timeframe policy と market session / next recommended window を確認できる。

主要 command:

- `bot-preview`
- `execution-snapshot`
- `execution-venue-comparison`
- `execution-venue-diagnostics`
- `execution-read-only-surfaces`
- `order-status`
- `estimate-order`
- `balance-status`
- `bitget-demo-smoke`
- `fill-status`
- `cancel-order`
- `close-position`
- `reconcile-positions`
- `healthcheck`
- `daemon-manifest`
- `daemon-dry-run`
- `daemon-run`
- `export-state`
- `restore-state`
- `monitoring-status`
- `kill-switch`
- `schedule-run`
- `render-alert`
- `notification-outbox`
- `paper-step`
- `paper-from-intents`
- `paper-report`
- `paper-operations-cycle`
- `check-timeframe`
- `market-session`
- `next-live-window`

境界:

- `bot-preview` は read-only HOLD preview。wallet、signing、exchange write は使わない。
- `bitget-demo-smoke` の `status=configured` は local env が揃った意味だけ。network / account / order submit / fill sync 成功ではない。
- Trade[XYZ] read-only execution state collector は public user address と `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1` がない限り external API を呼ばない。未設定時の current reason は `trade_xyz_execution_state_user_address_missing`。
- execution utility command が存在しても、production live trading ready ではない。

## 11. Operations / Audit / Remediation

できること:

- operations dashboard、timeline、bundle、audit pack を作れる。
- audit timeline、dashboard、bundle、bundle history を作れる。
- paper cycle history、execution gap history、execution state comparison history、execution snapshot drift history、execution drift overview を作れる。
- readiness snapshot、current state index を作れる。
- remediation planner、execution plan、session、checkpoint、evidence ingest、scoreboard、evaluator、evidence、command results を作れる。
- weekly review、lifecycle report、comparison report、ops review を作れる。
- phase gate review を実行できる。
- artifact strict validation、quote diagnostics、halt policy、go/no-go、evidence card を扱える。

主要 command:

- `lifecycle-report`
- `comparison-report`
- `ops-review`
- `operations-dashboard`
- `paper-operations-runbook`
- `paper-cycle-history`
- `execution-gap-history`
- `execution-state-comparison-history`
- `execution-snapshot-drift-history`
- `execution-drift-overview`
- `phase-gate-review`
- `operations-bundle`
- `operations-timeline`
- `operations-audit-pack`
- `audit-timeline`
- `audit-dashboard`
- `audit-bundle`
- `audit-bundle-history`
- `current-state-index`
- `readiness-snapshot`
- `remediation-planner`
- `remediation-execution-plan`
- `remediation-session`
- `remediation-session-checkpoint`
- `remediation-evidence-ingest`
- `remediation-scoreboard`
- `remediation-evaluator`
- `remediation-evidence`
- `remediation-command-results`
- `weekly-review`
- `refresh-operations-artifacts`
- `check-halt-policy`
- `check-go-no-go`
- `build-evidence-card`
- `implementation-status`
- `validate-artifacts`
- `diagnose-quotes`

境界:

- `phase-gate-review` は read-only / paper gate の判断正本。production live trading ready の証明ではない。
- operations artifacts は runtime state なので再生成が必要になる。

## 12. Venue Policy / Suitability

できること:

- `VenueId` は現行で `trade_xyz` と `bitget_demo` を許可する。
- venue suitability catalog には `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp` がある。
- venue capability contract では `bitget_futures` と `hyperliquid_perp` を known future venues として持つが、schema / paper / network / live は disabled。
- `bitget_demo` は execution-venue schema では許可されるが、Strategy Lab `evaluation_plan.mls.v1` の target venue としてはまだ disabled。
- `venue-read-only-probe` で 4 venue の capability boundary を fixture-first local artifact として出せる。external API、credentials、wallet、signing、exchange write、live order、network attempt は使わない。

境界:

- `bitget_futures` と `hyperliquid_perp` は current `VenueId` ではない。
- NDX/QQQ は research / backtest record として保持できるが、valid paper-observation evidence がない限り paper candidate / paper intent path で fail closed する。
- `venue-read-only-probe` は network readiness、credential readiness、paper permission、live permission ではない。

## 13. Schemas / Artifact Contracts

できること:

- Strategy Lab、Strategy Authoring、Backtest、NDX gates、Trade[XYZ] data readiness、paper lifecycle などの JSON Schema を tracked file として持つ。
- artifact path / source hash / no-live boundary / decision / report hash を多くの artifact に残せる。
- `jsonschema` と Pydantic validation により、CLI output を schema-valid に保てる。

主な schema families:

- Strategy Lab / lifecycle: `strategy_experiment_spec.v1`, `strategy_signal.v1`, `strategy_signal_manifest.v1`, `evaluation_plan.mls.v1`, `trial_record.v1`, `trade_candidate.v1`, `paper_candidate_pack.v1`, `promotion_decision.v1`, `paper_intent_preview.v1`, `strategy_lifecycle_review.v1`, `paper_observation_session_manifest.v1`, `strategy_paper_observation_status.v1`
- Strategy Review: `strategy_review_manifest.v1`, `operator_strategy_review.v1`
- Strategy Inputs: `strategy_input_contract.v1`, `strategy_input_contract_validation.v1`, `strategy_idea.v1`, `strategy_intake_decision.v1`
- Strategy Stage: `strategy_stage_policy.v1`, `strategy_stage_policy_validation.v1`, `strategy_stage_decision.v1`
- Strategy Paper Smoke: `strategy_paper_smoke_plan.v1`
- Strategy Runtime Observation: `strategy_runtime_observation_manifest.v1`
- Strategy Drift Review: `paper_vs_backtest_drift_review.v1`
- Strategy Learning: `strategy_learning_event.v1`, `strategy_revision_request.v1`, `strategy_revision_request_review.v1`, `strategy_authoring_update_handoff.v1`
- Strategy Micro Live Plan: `strategy_micro_live_plan.v1`
- Strategy Live Observation: `strategy_live_observation_manifest.v1`
- Strategy Scale Decision: `strategy_scale_decision.v1`
- Strategy Next Scale Plan: `strategy_next_scale_plan.v1`
- Strategy Workbench Viewer: `strategy_workbench_viewer.v1`
- Strategy Authoring / Backtest: `strategy_authoring_*`, `strategy_backtest_*`, `strategy_backtest_html_report.v1`, `backtest_data_availability_ledger.v1`
- NDX / research gates: `ndx_*`, `layer_2_2_*`, `core_dag.v1`, `counter_dag.v1`, `llm_dag_review.v1`
- Research protocol: `research_seed_registry.v1`, `research_scope.v1`, `research_variable_inventory.v1`, `research_temporal_availability.v1`, `research_causal_roles.v1`, `research_mechanism_parts.v1`
- Market / venue / quote artifacts: `quote_log_v1`, `quote_log_v2`, `quote_log_v2.trade_xyz.strict`, `trade_xyz_*`, `instrument_registry*`, `cost_snapshot`, `fee_snapshot`, `funding_event`, `funding_history_event`, `session_calendar_snapshot`, `session_state_observation`
- Venue capability: `venue_read_only_probe_summary.v1`
- Snapshot / operations guard: `data_snapshot_manifest.v1`, `feature_snapshot_manifest.v1`, `go_no_go_report`

境界:

- tracked JSON Schema は薄い guard と interoperability 用。詳細 validation は `src/sis/` の Pydantic model / builder が正本。

## 14. Tests / Quality Gates

できること:

- `tests/backtest` で backtest surfaces を検査できる。
- `tests/strategy_authoring` で authoring / backtest CLI bundle / module boundaries / HTML report manifest and UI labels を検査できる。
- `tests/research` で NDX / lifecycle / research gates を検査できる。
- `tests/paper` で paper surfaces を検査できる。
- `tests/test_cli_help_contract.py`, `tests/test_cli_smoke.py`, `tests/test_docs_current_truth.py` で CLI help / smoke / docs current-truth の drift を検査できる。
- repo 全体は `./scripts/check` でまとめて検証できる。

主要 test dirs:

- `tests/backtest`
- `tests/strategy_authoring`
- `tests/research`
- `tests/paper`
- `tests/fixtures`
- `tests/support`

## Public CLI Command Catalog

Public CLI command list は [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) に分離済みです。新しい command を追加した時は次を実行して、catalog と Typer registration の差分を確認します。

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
```

この文書は capability overview と境界説明に寄せ、command 名の網羅表は CLI catalog 側で管理します。

## 2026-06-18 差分追記: 2026-06-16版から何が変わったか

この節は、2026-06-16 に作成したこの capability document と、2026-06-18_06:54 JST 時点の repo を比較した具体差分である。

確認した正本:

- `uv run sis --help`
- `uv run python scripts/check_cli_catalog.py`
- `schemas/*.json`
- `src/sis/commands/`
- `src/sis/backtest/html_report.py`
- `tests/`
- `docs/AI_AGENT_STRATEGY_BACKTEST_GUIDE.md`
- `docs/STRATEGY_AND_BACKTEST_USER_GUIDE.md`
- この文書自身と current docs

### 1. Public CLI surface は増え、catalog は機械照合に分離された

2026-06-16 版では public command catalog をこの文書内に持っていた。現在は command list を [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) に分離し、`scripts/check_cli_catalog.py` で Typer registration と照合する方式になった。

現在の確認方法:

```bash
uv run python scripts/check_cli_catalog.py
```

増えた主要 command:

- `strategy-review-build`
- `strategy-review-record`
- `strategy-paper-observation-append`
- `strategy-paper-observation-status`
- `venue-read-only-probe`

意味:

- 「command 名一覧を手で保守する文書」から、「CLI registration と照合できる catalog」に変わった。
- command 数の固定値は current truth ではなくなり、`uv run sis --help` と `scripts/check_cli_catalog.py` の再実行が確認手順になった。

### 2. Backtest の後段に Strategy Review が増えた

2026-06-16 版では、backtest pack / comparison / validation までは扱っていたが、人間が読む review packet と operator review record はまだ中心機能として分離されていなかった。

現在できること:

- `strategy-review-build` で既存 backtest artifact chain から `review.md` と `review_manifest.json` を作れる。
- `review_manifest.json` は入力 artifact の path / hash / producer / source safety を保持する。
- `strategy-review-record` で、人間が review packet を読んだ判断を `operator_review.yaml` として保存できる。
- `strategy-review-record --validate-existing` で、保存済み operator review が同じ `review.md` / `review_manifest.json` を見ていたかを path / hash で再照合できる。

追加された schema family:

- `strategy_review_manifest.v1`
- `operator_strategy_review.v1`

境界:

- Strategy Review は paper / live 許可ではない。
- `PAPER_OBSERVATION_CANDIDATE` は validation candidate であり、paper execution permission ではない。
- `live_allowed=false` と `paper_execution_allowed=false` を維持する。

関連 docs:

- [strategy_review/README.md](strategy_review/README.md)
- [strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md](strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md)
- [strategy_review/DOGFOOD_REVIEW_2026-06-16.md](strategy_review/DOGFOOD_REVIEW_2026-06-16.md)

### 2-1. Backtest 結果を人間と AI が読みやすくする入口が増えた

2026-06-16 版では、backtest 結果は JSON artifact、pack validation、comparison、review packet を読む前提が強かった。現在は、AI / Codex 向けの操作契約、人間向けの説明ガイド、依存追加なしの HTML report が追加されている。

現在できること:

- [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md) で、AI が戦略作成、編集、backtest、失敗分岐、結果解釈、live 禁止境界を同じ手順で扱える。
- [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) で、人間が「何を作ったか」「何を直せるか」「backtest 結果をどう読むか」を専門用語少なめに確認できる。
- `strategy-backtest-html-report` で、既存 artifact から `strategy_backtest_html_report.v1` manifest と単一 HTML / JS report を作れる。
- HTML report では、累積損益、benchmark 比較、期間で絞れる trade table、stress summary、rolling / regime / comparison diagnostics、結果ラベルを見られる。
- report manifest は HTML の根拠として、source artifact path / hash、summary、visual data、gate statuses、result label、no-live boundary を持つ。

主要 artifact:

- `data/research/backtest_html_report/strategy_backtest_html_report.json`
- `data/reports/strategy_backtest_html_report.html`

主要 code / schema / test:

- `src/sis/backtest/html_report.py`
- `schemas/strategy_backtest_html_report.v1.schema.json`
- `tests/strategy_authoring/test_backtest_html_report.py`

境界:

- `strategy-backtest-html-report` は既存 artifact を読むだけで、backtest を再実行しない。
- HTML report は dependency 追加なしの repo 標準ビューアであり、optional `quantstats` report artifact を作る `strategy-backtest-report-extension` とは別 surface である。
- `paper_observation_candidate` label は paper / live 実行許可ではない。manifest では `paper_observation_candidate_is_permission=false`、`paper_only=true`、`permits_live_order=false`、`live_conversion_allowed=false`、`wallet_used=false`、`exchange_write_used=false` を固定する。
- 既定では `--min-trade-count-for-candidate 30` 未満の trade count は `insufficient_evidence` / `検証不足` として表示される。

実務上の違い:

- JSON を直接読まなくても、損益曲線、取引一覧、benchmark、stress、結果ラベルをブラウザで確認できる。
- AI は artifact の path、hash、失敗時の分岐、禁止境界を同じ guide から参照できる。
- 人間は「利益が出たか」だけでなく、「検証不足か」「次に何を確認すべきか」を report と guide で読める。

### 3. Paper observation は「作る」だけでなく「追記する」「状態を読む」能力が増えた

2026-06-16 版では、`strategy-paper-observation-cycle` で paper observation cycle artifact を作れることが中心だった。

現在できること:

- `strategy-paper-observation-append` で既存 paper observation session manifest を読み、manifest hash を確認した上で同じ session ledger に観察行を追記できる。
- `strategy-paper-observation-status` で既存 paper observation review / session manifest / lifecycle review を読み、normal observation と smoke observation を分けた status artifact を作れる。
- `data/research/strategy_lifecycle/paper_observation_status.json` に `observation_state`, `next_action`, `normal_session_count`, `smoke_session_count`, `latest_normal_requirement_gaps`, `normal_thresholds_met`, `smoke_pass_counts_as_normal_pass`, `live_conversion_allowed`, `permits_live_order`, `wallet_used`, `signing_used`, `exchange_write_used` などを出せる。

追加された schema:

- `strategy_paper_observation_status.v1`

実務上の違い:

- 同じ日の artifact 再生成を「新しい観察」と誤読しにくくなった。
- smoke pass と normal paper observation pass を分けて読めるようになった。
- 既存 session artifact がある場合、`strategy-paper-observation-cycle` は同じ session id の使い回しを避け、追記は専用 command に分離された。

境界:

- paper observation status は paper intent 生成、paper order 実行、ledger 再集計をしない。
- `needs_more_normal_paper_observation` は live へ進む意味ではない。
- `trading_days` は同一日の fill 増加では代替できない。

### 4. Venue capability は fixture-first の read-only probe として独立した

2026-06-16 版では、venue policy は `VenueId` / suitability catalog / capability contract の説明が中心だった。

現在できること:

- `venue-read-only-probe` で `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp` の capability boundary を local artifact として出せる。
- `venue_read_only_probe_summary.v1` schema で probe summary を検査できる。
- probe result は fixture-first で、external API、credentials、network attempt、wallet、signing、exchange write、live order を使わない。

実務上の違い:

- future venue を「実装済み live venue」と誤読せず、schema / paper / network / live disabled の境界を artifact として確認できる。
- Bitget / Hyperliquid は known future venues のままだが、current `VenueId` ではなく、Strategy Lab の正式 target venue でもないという説明が強くなった。

### 5. Trade[XYZ] は read-only execution state collector contract が増えた

2026-06-16 版では、Trade[XYZ] data / quote / readiness / pure backtest の説明が中心だった。

現在できること:

- Trade[XYZ] の read-only execution state collector contract を持つ。
- public user address と `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1` がある場合だけ、`/info` 由来の account state / open orders / fills を読む設計になった。
- 未設定時は external API を呼ばず、`trade_xyz_execution_state_user_address_missing` のような reason を出す。
- `execution-snapshot`, `execution-read-only-surfaces`, `execution-drift-overview`, `phase-gate-review` が concrete reason / next action を伝播する。

実務上の違い:

- 「execution drift がある」だけでなく、「何が未設定で、次に何を設定すべきか」を artifact で追いやすくなった。
- ただし wallet secrets、signing、live order、exchange write credentials は引き続き使わない。

### 6. Strategy Lab / Research Data / Operations 系 CLI の help が IO と境界を明示するようになった

2026-06-16 版では、できることの一覧はあったが、個々の CLI が「何を読むか」「何を書くか」「何をしないか」の help 契約は薄かった。

現在強化された例:

- `build-paper-intent-preview`: paper-only intent preview の入力と live conversion 禁止を明示。
- `promotion-decision`: promotion decision artifact の入力と decision の意味を明示。
- `build-paper-candidate-pack`: candidate pack の入力、selected candidate、paper-only 境界を明示。
- `evaluate-strategy-lab`: Strategy Lab signal 評価の入力と output を明示。
- `strategy-experiment-run`: experiment spec から paper-only signal artifact を作る境界を明示。
- `build-signals`, `build-feature-panel`, `check-research-quality`, `build-cost-matrix`, `alpaca-smoke`: local / read-only / generated artifact の IO を明示。
- `diagnose-quotes`: local quote rows を診断し operator report を書くことを明示。
- `validate-artifacts`: local `data/` と `schemas/` を読み、`checked_files` / `issues` を出し、`--strict` で Trade[XYZ] artifact chain を要求し、issue 時に exit 2 になることを明示。
- `check-go-no-go`: local Go/No-Go evidence summary の入力、出力、no external API / no paper order / no live permission 境界を明示。

実務上の違い:

- operator が command help だけを見ても、local artifact command と external/API/order command を混同しにくくなった。
- CLI smoke tests が help text の重要表現を守るようになった。

### 7. Docs は「巨大な current state」から「入口 + domain docs + archive」へ再編された

2026-06-16 版では、この文書自体に public command catalog や幅広い capability detail を多く抱えていた。

現在の分割:

- [CURRENT_STATE.md](CURRENT_STATE.md): short current-state index。
- [CODE_STATUS.md](CODE_STATUS.md): thin code-status index。
- [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md): 実装済み surface の一覧。
- [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md): 次に見るべき方向と external-input restart checklist。
- [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md): 非専門向けの plain Japanese capability guide。
- [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md): public CLI command catalog。
- [runbooks/README.md](runbooks/README.md): domain runbook index。
- [strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md](strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md): Strategy Lab capability detail。

実務上の違い:

- current docs から古い fixed runtime snapshot / fixed pass count / dated artifact hash を減らし、必要なときは runtime command を再実行する方針になった。
- 実装済み plan や古い audit は `docs/archive/` と `plan/archive/` に移り、current proof と historical context を分けた。
- HTML current docs には同名 Markdown source を求める checker が追加された。

### 8. Current-docs checker と full gate が強化された

2026-06-16 版では `scripts/check_current_docs.py` が metadata / links / EOF / legacy root reference を見るのが中心だった。

現在の checker / gate:

- `scripts/check_current_docs.py` は current docs の semantic drift、HTML source 対応、plan routing も検査する。
- `scripts/check_cli_catalog.py` が public CLI catalog と Typer registration を照合する。
- `./scripts/check` は CLI catalog check も含む。
- full gate の現行構成は `./scripts/check` を再実行して確認する。handoff は最後に実行した結果の記録であり、current proof の代わりにはしない。

実務上の違い:

- command を追加して docs catalog を忘れる drift を検出できる。
- current docs に古い runtime snapshot を残す drift を検出しやすくなった。
- ただし `data/` は git-ignored runtime state なので、artifact 値は都度再生成または再確認が必要である。

### 9. CI / runtime 運用まわりは Node24 対応と external-input checklist が増えた

2026-06-16 版には、CI action runtime と external input restart checklist の説明は薄かった。

現在の変化:

- GitHub Actions は Node24 runtime 対応 action に更新された。
- `docs/NEXT_DIRECTION_CURRENT.md` に external input restart checklist が追加され、Trade[XYZ] public user address、Bitget demo env、normal paper observation の再開条件を current docs から辿れる。
- README、CURRENT_STATE、CODE_STATUS、OPERATIONS_RUNBOOK、Strategy Lifecycle docs が external-input checklist へルーティングする。

実務上の違い:

- external input が必要な作業と、local-only で続けてよい作業を分けやすくなった。
- read-only / paper observation の再開手順を live permission と混同しにくくなった。

### 10. 変わっていない重要境界

機能は増えたが、次は変わっていない。

- production live trading ready ではない。
- wallet secrets、signing、exchange write は使わない。
- `READ_ONLY_GO` は live readiness ではない。
- backtest pass、pack validation pass、strategy review、operator review、paper observation status は、単独では alpha / paper execution permission / live permission を証明しない。
- Bitget futures / Hyperliquid perp は known future venues だが、current `VenueId` ではなく、Strategy Lab の正式 target venue でもない。
- `PaperIntentPreview` は paper-only artifact であり、live order へ変換しない。

## できないこと / 未証明

この repo は現時点で次を証明または実行しない。

- production live trading ready
- wallet secrets / signing / exchange write
- public operator CLI からの Trade[XYZ] micro-live 実行
- Bitget production futures / Hyperliquid perp の正式 Strategy Lab venue
- Bitget credentialed read-only network smoke の完了証明
- Bitget demo order lifecycle の完了証明
- Alpaca fresh live `status=pass` の常時保証
- backtest 結果だけによる alpha / paper pass / live readiness
- HftBacktest / qstrader / PyBroker / skfolio / Riskfolio-Lib の dependency 採用または engine 実行
- market replay からの market impact proof
- NDX Layer 2.4 approval からの paper / live readiness 直接主張
- `PaperIntentPreview` の live order 変換
- `bitget_demo` を production Bitget futures として扱うこと

## まず読む順番

1. [CURRENT_STATE.md](CURRENT_STATE.md)
2. [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md)
3. [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md)
4. [CODE_STATUS.md](CODE_STATUS.md)
5. [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
6. [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
7. [algo/README.md](algo/README.md)
8. [strategy_research_lab/README.md](strategy_research_lab/README.md)
9. [strategy_research_lab/08_CURRENT_CAPABILITIES.md](strategy_research_lab/08_CURRENT_CAPABILITIES.md)
10. [strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md](strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md)
11. [backtest/README.md](backtest/README.md)
12. [backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md)
13. [strategy_review/README.md](strategy_review/README.md)
14. [strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md](strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md)
15. [strategy_lifecycle/README.md](strategy_lifecycle/README.md)
16. [research/ndx/README.md](research/ndx/README.md)
17. [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md)
18. [ARCHITECTURE_AND_PHASES.md](ARCHITECTURE_AND_PHASES.md)
19. [MIGRATION_HISTORY.md](MIGRATION_HISTORY.md)
20. [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md)
