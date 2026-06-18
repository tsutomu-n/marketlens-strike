<!--
作成日: 2026-06-19_00:26 JST
更新日: 2026-06-19_02:36 JST
-->

# Strategy Operations Workbench Completion Plan

## 結論

今の `Target Strategy Operations Workbench` の方向性は正しい。2026-06-19_02:22 JST 時点では、本計画の対象である artifact / review / gate / observation contract の first slice は T12b まで実装済みである。

ただし、これは production live trading system の完成ではない。次の境界は意図的に対象外として残す。

- T10 `Micro Live Plan Gate` は既存 `src/sis/execution/live_order_policy.py` の `MicroLivePolicy` を読むが、micro live execution command ではない。
- T11 `Micro Live Canary Observation Contract` は既存 `micro_live_canary` audit bundle を read-only で読むが、micro live を実行しない。
- T12 `Static Workbench Viewer` は Python CLI の static HTML viewer であり、Svelte UI / API server ではない。
- T12b `Next Scale Plan` は次の拡大計画 artifact であり、next-scale execution permission ではない。
- OSS 追加は許容するが、`optuna` / `pandera` / `mlflow` は現時点では実装完了の blocker ではない。入れるなら採用条件とテスト範囲を分ける。

したがって最終判断は次。

```text
現在の完成形定義: 採用してよい
現在の実装済み first slices: T12b まで土台として有効
現在の計画粒度: コーダーが対象ファイル、テスト方針、完了条件を追える粒度
本計画の完了範囲: Strategy Operations Workbench の artifact / review / gate / observation contract
本計画の非完了範囲: production live trading system、standard public live execution CLI、wallet / signing / exchange write readiness
```

## 2026-06-19_02:36 JST 再監査結論

「この計画で、計画した達成目標をすべて完了できるか」への答えは、条件付きで yes である。

yes と言える範囲:

- artifact / review / gate / observation contract を CLI、schema、tests、current docs で閉じる。
- 個人トレーダーが、backtest、paper、drift、learning、micro live plan、scale plan を同じ evidence chain 上で読む。
- stage 条件を固定値ではなく policy artifact として変えられる。
- AI / ML / GA / optimizer output を直接採用せず、review note または ledger として残す。
- micro live 以降を execution permission ではなく、plan / observation / scale review artifact として扱う。

no と言うべき範囲:

- 100点の実運用システム全体、つまり broker 接続、credential 管理、wallet / signing、venue-general live execution、kill switch 実動作監視、Svelte UI、実際の scale-up execution までは完了しない。
- 戦略が利益を出すこと、alpha があること、paper と live の約定品質が一致することは証明しない。
- Runtime Observation や Learning Event を Strategy Input Contract へ自動で再投入する完全な closed loop は、この計画では first slice に留まる。

したがって、この計画の達成目標を次のように固定する。

```text
達成目標:
  Human-in-the-loop Strategy Operations Workbench の first operational slice を完成させる。

完成の意味:
  個人トレーダーが、入力、仮説、backtest、paper smoke、normal paper、drift、learning、
  micro live plan、live observation、scale decision、next scale plan を
  local artifact と CLI で追跡し、人間判断で次へ進められる状態。

完成ではないもの:
  自動売買本体、production live readiness、実損失を伴う実行、Svelte UI、
  broker / exchange write adapter、wallet / signing、利益保証。
```

この境界であれば、現 T0〜T12b は達成目標に対して十分である。境界を「実際に live へ発注し、継続監視し、拡大実行するところまで」と定義するなら、この計画だけでは不足であり、別計画が必要である。

## 目的

個人システムトレーダーが、思いつき、単発 backtest、AI の説得力ある文章、都合のよい paper 結果だけで戦略を進めないようにする。

同時に、慎重すぎて永遠に進めない状態にもさせない。

完成時にできることは次。

```text
Input Contract
  -> Idea Intake
  -> Strategy Authoring / Backtest
  -> Review
  -> Stage Decision
  -> Paper Smoke
  -> Runtime Observation
  -> Normal Paper
  -> Drift Review
  -> Learning / Revision Request
  -> Human Authoring Update Handoff
  -> 再 backtest / 再 review
  -> 条件を満たす場合だけ Micro Live Plan
  -> Micro Live Canary Observation Contract
  -> Scale Decision
  -> Next Scale Plan
  -> Static Workbench Viewer
```

この repo は live bot を自動生成しない。最後まで、artifact、CLI、schema、test、human decision を正本にする。

この計画が完了しても、標準 operator CLI で live order を出せる状態にはしない。既存の `Trade[XYZ]` micro live safety code は historical / explicitly scoped surface として存在するが、Workbench 標準 route ではまず plan artifact と observation artifact に接続する。

## 追加調査からの修正点

確認した外部実務上の要点:

- QuantConnect docs は、backtest の fills は historical data 上の simulation であり、live fill は brokerage 側が決める、と明記している。つまり backtest fill と live fill を同じものとして扱えない。
  - https://www.quantconnect.com/docs/v1/algorithm-reference/trading-and-orders
- QuantConnect の paper trading は live trading node 上で paper brokerage を選んで動かす導線で、paper は実時間運用の一段階であって backtest の延長ではない。
  - https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/getting-started
- Quantpedia は paper trading を real-time data feed と simulated fills の組み合わせとして説明し、backtest overfit を疑うためにも使うとしている。
  - https://quantpedia.com/how-to-paper-trade-quantpedia-backtests/
- Investopedia は automated trading の実務リスクとして、mechanical failures、monitoring、over-optimization、小さい trade size で始めることを挙げている。
  - https://www.investopedia.com/articles/trading/11/automated-trading-systems.asp
- NIST AI RMF は、AI を使う場合に ongoing monitoring、roles / responsibilities、人間と AI の oversight、feedback incorporation を要求する方向を示す。個人運用では軽量化してよいが、AI output の自動採用は避ける。
  - https://www.nist.gov/itl/ai-risk-management-framework
  - https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf

これを反映した修正:

- Backtest は「paper smoke へ進める価値があるか」を見る一次証拠であり、採用証明ではない。
- Paper smoke は「配線と現実時刻の挙動確認」であり、normal paper pass ではない。
- Normal paper は real-time / simulated fills の差を観測する段階で、PnL だけでなく no-fill、blocked、spread、latency、operator burden を見る。
- Micro live は execution 実装より先に plan artifact、loss cap、position cap、kill switch、monitoring schedule を作る。
- AI / ML / GA は candidate / critique / optimizer であり、permission engine ではない。

追加調査で確認した OSS の位置づけ:

- Optuna は hyperparameter optimization framework で、動的 search space や pruning に向く。ただし、この repo では `strategy_optimizer_trial_ledger.v1` が先にあり、Optuna は trial runner を実装する段階で optional extra として検討する。
  - https://optuna.readthedocs.io/
- Pandera は dataframe-like objects の runtime validation に向く。ただし、現時点の input contract は `polars` と local checks で first slice を満たしているため、複数データセットに同じ column / dtype contract を再利用する段階で検討する。
  - https://pandera.readthedocs.io/
- MLflow Tracking は parameter、code version、metrics、artifacts の記録と UI に向く。ただし solo repo では operational weight が増えるため、local JSON artifact で追えない量の model run が出てから採用する。
  - https://mlflow.org/docs/latest/ml/tracking/

## 固定制約

全 slice で固定する制約:

- live order を出さない。
- wallet、signing、exchange write を使わない。
- paper execution も暗黙実行しない。実行系 command は人間が別途明示する。
- `data/` の runtime artifact を current truth として docs に固定しない。
- source path、sha256、schema_version、producer command を残す。
- `auto_applied=false` を基本にする。
- Strategy Authoring YAML は自動編集しない。編集入力 artifact までを作る。
- stage advance は candidate と permission を分ける。
- user override は reviewer、reason、policy hash を残す。
- Trade[XYZ] は explicitly scoped の read-only / historical surface とし、Workbench の標準 route にしない。
- 既存 `src/sis/execution/` の micro live code を参照してよいが、Workbench の T10/T11 では public live execution CLI を追加しない。
- `MicroLivePolicy.enabled=true`、credential、wallet、signing、exchange write、adapter write action は、本計画の通常テストでは要求しない。

## OSS / 依存関係方針

現時点で新規依存を急いで増やさない。

理由:

- 既に `pydantic`、`jsonschema`、`pyyaml`、`polars`、`duckdb`、`exchange-calendars` があり、artifact contract、schema validation、column scan、timestamp check、local analytical query は足りる。
- optional backtest extras として `vectorbt`、`bt`、`empyrical-reloaded`、`quantstats` が設計済みで、backtest 側の拡張余地はある。
- 先に不足しているのは OSS ではなく、artifact contract の接続である。

追加してよい候補:

| 候補 | 入れる条件 | 使い道 | 今すぐ入れない理由 |
|---|---|---|---|
| `optuna` | `strategy-model-run-record` の ledger が実運用され、runner 実装が必要になった後 | parameter search と trial pruning | 今は trial ledger 記録だけで足りる。採用時は optional extra と runner test を別 slice にする |
| `pandera` | 複数 input contract で同じ dataframe schema を再利用し、dtype / range / nullable を宣言管理する必要が出た後 | column-level validation | `polars` + local checks で first slice は足りる |
| `great-expectations` | non-developer 向け data quality report が必要になった後 | data quality suite | 個人 repo には重く、運用負荷が先に増える |
| `scikit-learn` | model-run record / baseline model が必要になった後 | lightweight ML baseline | 現時点では AI / ML より artifact flow が先 |
| `mlflow` | local JSON ledger では追えない数の model run、artifact、metric、model version が出た後 | model registry / experiment tracking | solo use には過剰になりやすい。採用時は local tracking URI と artifact path を固定する |

## 完了ロードマップ

### T0. Plan / Docs Alignment

目的:

- 完成形、未実装、次の実装順を docs で混同しない。

対象ファイル:

- `docs/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md`
- `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `plan/README.md`
- `scripts/check_current_docs.py`

テスト方針:

```bash
uv run python scripts/check_current_docs.py
```

完了条件:

- current docs から本計画へ辿れる。
- “実装済み” と “これから実装する” が分かれている。
- stale な `drift review 未実装` のような矛盾表現が残らない。

### T1. Authoring Update Handoff

実装状態: 実装済み。

目的:

- `APPROVE_FOR_AUTHORING_UPDATE` 済みの `strategy_revision_request_review.v1` を、Strategy Authoring YAML の人間編集入力にする。
- YAML 自動編集はしない。

対象ファイル:

- `src/sis/strategy_learning/models.py`
- `src/sis/strategy_learning/service.py`
- `src/sis/strategy_learning/rendering.py`
- `src/sis/commands/strategy_learning.py`
- `schemas/strategy_authoring_update_handoff.v1.schema.json`
- `tests/strategy_learning/test_strategy_learning.py`
- `tests/strategy_learning/test_strategy_learning_cli.py`
- `docs/strategy_learning/README.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`

CLI:

```bash
uv run sis strategy-authoring-update-handoff \
  --revision-request data/strategy_learning/<strategy-id>/revision_requests/<id>.json \
  --revision-review data/strategy_learning/<strategy-id>/revision_requests/<id>_review.json \
  --authoring-spec configs/strategies/<strategy-id>.yaml \
  --out data/strategy_learning/<strategy-id>/authoring_update_handoffs
```

完了条件:

- `strategy_authoring_update_handoff.v1` JSON と Markdown が出る。
- source request、source review、authoring spec の path / sha256 / schema version を残す。
- review decision が `APPROVE_FOR_AUTHORING_UPDATE` でない場合は `NEEDS_REVISION_REVIEW_APPROVAL`。
- `auto_applied=false`、`direct_spec_edit_allowed=false`、`paper_execution_allowed=false`、`live_allowed=false`。
- authoring YAML を一切書き換えない。

テスト方針:

```bash
uv run pytest tests/strategy_learning -q
uv run sis strategy-authoring-update-handoff --help
uv run python scripts/check_current_docs.py
```

### T2. Input Contract Column / Availability Validation

実装状態: 実装済み。

目的:

- path / hash だけでなく、実ファイルの column、timestamp、available_at、timezone、missingness を検査する。

対象ファイル:

- `src/sis/strategy_inputs/models.py`
- `src/sis/strategy_inputs/validation.py`
- `src/sis/commands/strategy_inputs.py`
- `schemas/strategy_input_contract.v1.schema.json`
- `schemas/strategy_input_contract_validation.v1.schema.json`
- `tests/strategy_inputs/`
- `docs/strategy_inputs/README.md`

完了条件:

- CSV / JSONL / Parquet のうち repo 既存 reader で扱える形式を最小対応する。
- required feature column がない場合は `MISSING_REQUIRED_COLUMN`。
- max source timestamp が decision timestamp を超える場合は `FUTURE_DATA_VIOLATION`。
- `available_at_required=true` で available_at 情報がない場合は fail。
- schema 変更は後方互換を保つ。破壊的 schema change が必要なら v2 にする。

テスト方針:

```bash
uv run pytest tests/strategy_inputs -q
uv run sis strategy-input-contract-validate --help
```

### T3. Normal Paper Observation Evidence Contract

実装状態: 実装済み。

目的:

- smoke と normal paper を artifact 上で分ける。
- normal paper が十分かどうかを固定値で docs に書かず、artifact が判断できるようにする。

対象ファイル:

- `src/sis/research/strategy_lifecycle/paper_observation_cycle.py`
- `src/sis/commands/research.py`
- `src/sis/strategy_stage/`
- `schemas/strategy_stage_policy.v1.schema.json`
- `schemas/strategy_stage_decision.v1.schema.json`
- `tests/strategy_stage/`
- `docs/strategy_stage/README.md`

完了条件:

- paper smoke result と normal paper status を別 input として stage decision が読める。
- normal requirement gaps は `paper_evidence_summary.normal_fills` と `paper_evidence_summary.normal_trading_days` として fills と trading_days を artifact に残す。
- smoke pass が normal pass にならないテストを追加する。

テスト方針:

```bash
uv run pytest tests/strategy_stage tests/strategy_paper_smoke -q
```

### T4. Runtime Observation PnL / Cost Enrichment

実装状態: 実装済み。

目的:

- Drift Review が PnL drift と cost drift を見られるように、runtime observation に realized paper PnL、fee estimate、slippage estimate、order lifecycle を足す。

対象ファイル:

- `src/sis/strategy_runtime_observation/models.py`
- `src/sis/strategy_runtime_observation/service.py`
- `src/sis/strategy_runtime_observation/rendering.py`
- `src/sis/commands/strategy_runtime_observation.py`
- `schemas/strategy_runtime_observation_manifest.v1.schema.json`
- `tests/strategy_runtime_observation/`
- `docs/strategy_runtime_observation/README.md`

完了条件:

- PnL がない artifact では `pnl_available=false` と理由を出す。
- PnL がある artifact では realized PnL、fee、slippage、fill price drift を summary に出す。
- missing PnL を pass と扱わない。
- order lifecycle は `order_lifecycle_counts` として summary に残す。

テスト方針:

```bash
uv run pytest tests/strategy_runtime_observation -q
```

### T5. Drift Review v2

実装状態: 実装済み。

目的:

- no-fill / blocked / spread だけでなく、realized paper PnL、cost、drawdown、order lifecycle drift を判断材料にする。

対象ファイル:

- `src/sis/strategy_drift_review/models.py`
- `src/sis/strategy_drift_review/service.py`
- `src/sis/strategy_drift_review/rendering.py`
- `src/sis/commands/strategy_drift_review.py`
- `schemas/paper_vs_backtest_drift_review.v1.schema.json`
- `tests/strategy_drift_review/`
- `docs/strategy_drift_review/README.md`

完了条件:

- `NEEDS_MORE_RUNTIME_DATA` と `REVISE_STRATEGY` と `EXTEND_OBSERVATION` の分岐が PnL / cost ありでもテストされる。
- PnL がない場合は no-fill / blocked / spread だけの限定 review と明記する。
- `READY_FOR_HUMAN_DRIFT_REVIEW` を micro live permission としない。
- `--max-return-drift` 指定時は runtime return と backtest total return の差を condition / recommended action に反映する。

テスト方針:

```bash
uv run pytest tests/strategy_drift_review -q
```

### T6. Strategy Case Lite

実装状態: 実装済み。

目的:

- 同じ strategy の input、idea、reviews、stage decisions、paper observations、drift reviews、learning events、revision requests を束ねる。

対象ファイル:

- `src/sis/strategy_case_lite/`
- `src/sis/commands/strategy_case_lite.py`
- `src/sis/cli.py`
- `schemas/strategy_case_lite.v1.schema.json`
- `tests/strategy_case_lite/`
- `docs/strategy_case_lite/README.md`
- `scripts/check_current_docs.py`

CLI:

```bash
uv run sis strategy-case-lite-update \
  --strategy-id <strategy-id> \
  --stage-decision data/strategy_stage_decisions/<id>.json \
  --out data/strategy_cases
```

完了条件:

- case timeline が JSON と Markdown で読める。
- latest status、open actions、blocked reasons、latest source hashes を持つ。
- permission artifact ではないと明記する。

テスト方針:

```bash
uv run pytest tests/strategy_case_lite -q
uv run sis strategy-case-lite-update --help
```

### T7. Strategy Daily Brief

実装状態: 実装済み。

目的:

- 個人トレーダーが毎日 artifact を探し回らず、今日見るものを 1 枚で判断できるようにする。

対象ファイル:

- `src/sis/strategy_daily_brief/`
- `src/sis/commands/strategy_daily_brief.py`
- `src/sis/cli.py`
- `schemas/strategy_daily_brief.v1.schema.json`
- `tests/strategy_daily_brief/`
- `docs/strategy_daily_brief/README.md`
- `scripts/check_current_docs.py`

CLI:

```bash
uv run sis strategy-daily-brief \
  --data-dir data \
  --out data/reports/strategy_daily_brief
```

完了条件:

- broken artifact、pending human reviews、normal paper gaps、drift review needed、learning request pending、boundary violation を一覧にする。
- `Daily Brief` は permission artifact ではない。
- 生成物に source paths と generated_at を残す。

テスト方針:

```bash
uv run pytest tests/strategy_daily_brief -q
uv run sis strategy-daily-brief --help
```

### T8. AI Review Packet / AI Review Note

実装状態: 実装済み。

目的:

- LLM に渡してよい情報だけを packet 化し、AI の回答を review note として取り込む。

対象ファイル:

- `src/sis/strategy_ai_review/`
- `src/sis/commands/strategy_ai_review.py`
- `src/sis/cli.py`
- `schemas/strategy_ai_review_packet.v1.schema.json`
- `schemas/strategy_ai_review_note.v1.schema.json`
- `tests/strategy_ai_review/`
- `docs/strategy_ai_review/README.md`

完了条件:

- packet は secrets、credentials、wallet、account detail、exchange write path を含まない。
- note は provider、model、prompt hash、input hash、limitations、findings、recommendation を持つ。
- AI note は `auto_applied=false`、`permission_allowed=false`。
- 複数 AI の比較は disagreement を残し、合議による自動採用をしない。

テスト方針:

```bash
uv run pytest tests/strategy_ai_review -q
uv run sis strategy-ai-review-packet-build --help
```

### T9. Model / Optimizer Trial Ledger

実装状態: 実装済み。

目的:

- ML / DL / GA / optimizer を使う場合に、成功 trial だけが残る過剰最適化を防ぐ。

対象ファイル:

- `src/sis/strategy_model_loop/`
- `src/sis/commands/strategy_model_loop.py`
- `src/sis/cli.py`
- `schemas/strategy_model_run.v1.schema.json`
- `schemas/strategy_optimizer_trial_ledger.v1.schema.json`
- `tests/strategy_model_loop/`
- `docs/strategy_model_loop/README.md`

完了条件:

- training data hash、label definition、split、seed、search space、all trials、best trial、holdout result、limitations を残す。
- model / optimizer output は Idea Intake または Revision Request へ戻すだけ。
- Strategy Authoring YAML を直接書かない。
- `optuna` 採用はこの slice の後半で判断し、最初は generic ledger で実装する。

テスト方針:

```bash
uv run pytest tests/strategy_model_loop -q
```

### T10. Micro Live Plan Gate

実装状態: 実装済み。

目的:

- micro live execution ではなく、実損失限定の計画 artifact を作る。
- 既存の `MicroLivePolicy` / `evaluate_micro_live_gates` と矛盾しない形で、Workbench 側の stage / drift / risk evidence を接続する。

対象ファイル:

- `src/sis/strategy_micro_live_plan/`
- `src/sis/commands/strategy_micro_live_plan.py`
- `src/sis/cli.py`
- `src/sis/execution/live_order_policy.py`
- `schemas/strategy_micro_live_plan.v1.schema.json`
- `tests/strategy_micro_live_plan/`
- `tests/test_trade_xyz_live_order_policy.py`
- `docs/strategy_micro_live_plan/README.md`

完了条件:

- required inputs: approved drift review、stage decision、risk limits、monitoring schedule、kill switch procedure。
- stage decision は `READY_FOR_MICRO_LIVE_PLAN` でなければ `NEEDS_STAGE_DECISION`。
- drift review は `READY_FOR_HUMAN_DRIFT_REVIEW` かつ人間レビュー済み approval artifact を持たなければ `NEEDS_DRIFT_REVIEW` または `NEEDS_HUMAN_APPROVAL`。
- max order notional、max position notional、max daily loss、max total loss、max open positions、allowed symbols、session window を必須にする。
- risk limits は既存 `MicroLivePolicy` の `max_notional_usd`、`max_daily_loss_usd`、`max_open_positions`、`allowed_symbols` と照合できるようにする。
- `kill_switch_clear=false`、`schedule_cancel` 手順なし、monitoring owner / cadence なしの場合は ready にしない。
- `plan_status=READY_FOR_HUMAN_MICRO_LIVE_REVIEW` は live execution permission ではない。
- wallet / signing / exchange write は false のまま。
- Workbench 標準 CLI として micro live execution command を追加しない。

テスト方針:

```bash
uv run pytest tests/strategy_micro_live_plan -q
uv run pytest tests/test_trade_xyz_live_order_policy.py -q
uv run sis strategy-micro-live-plan --help
```

### T11. Micro Live Canary Observation Contract

実装状態: 実装済み。

目的:

- micro live を実行する前ではなく、実行後の最小実弾観測を取り込む artifact contract を定義する。
- 既存 `src/sis/execution/micro_live_canary.py` の report / audit bundle を、Workbench 側の read-only observation として読めるようにする。

対象ファイル:

- `src/sis/strategy_live_observation/`
- `src/sis/commands/strategy_live_observation.py`
- `src/sis/cli.py`
- `src/sis/execution/micro_live_canary.py`
- `schemas/strategy_live_observation_manifest.v1.schema.json`
- `tests/strategy_live_observation/`
- `tests/test_micro_live_canary.py`
- `docs/strategy_live_observation/README.md`

完了条件:

- live execution を実行しない。
- 既存の外部実行結果 artifact、または既存 micro live canary audit bundle を read-only で読むだけ。
- actual fill、fee、latency、rejection、position reconciliation、max loss breach を記録する。
- source report / audit bundle の path、sha256、schema-like version または producer command を残す。
- `strategy_live_observation_manifest.v1` は `strategy_runtime_observation_manifest.v1` と別 schema にする。
- paper runtime observation と混ぜない。
- `LIVE_OBSERVATION_INGESTED` は scale-up permission、normal live readiness、production readiness ではない。

テスト方針:

```bash
uv run pytest tests/strategy_live_observation -q
uv run pytest tests/test_micro_live_canary.py -q
```

### T12. Static Workbench Viewer

目的:

- artifact を読む static HTML viewer を作る。正本にはしない。

実装判断:

- repo には `package.json` はあるが、現時点では UI app / SvelteKit app がない。
- 本計画では Svelte UI ではなく、既存 Python CLI に合わせた static HTML viewer を実装する。
- SvelteKit app を作る場合は別 plan で routing、state、起動方法、E2E を決める。

実装状態: 実装済み。

対象ファイル:

- `src/sis/strategy_workbench_viewer/`
- `src/sis/commands/strategy_workbench_viewer.py`
- `src/sis/cli.py`
- `schemas/strategy_workbench_viewer.v1.schema.json`
- `tests/strategy_workbench_viewer/`
- `docs/strategy_workbench_viewer/README.md`

完了条件:

- JSON / Markdown / text artifact を明示指定または `data/` scan で読める。
- review.md、manifest JSON、stage decision、drift review、learning ledger、case lite、daily brief、micro live plan、live observation、scale decision を viewer の材料にできる。
- source path、sha256、schema_version、status、boundary violation を manifest に残す。
- UI は paper / live permission を直接発行しない。
- hidden mutable state を持たない。
- HTML 表示時に artifact 由来文字列を escape する。

テスト方針:

```bash
uv run pytest tests/strategy_workbench_viewer -q
uv run sis strategy-workbench-viewer-build --help
```

既存 JS app がないため、Svelte UI は deferred として current docs に理由を残す。

### T12a. Scale Decision Contract

実装状態: 実装済み。

目的:

- live observation 後に、次の scale plan を準備する候補か、hold / revise / repair かを artifact として残す。
- scale-up execution permission とは分ける。

対象ファイル:

- `src/sis/strategy_scale_decision/`
- `src/sis/commands/strategy_scale_decision.py`
- `src/sis/cli.py`
- `schemas/strategy_scale_decision.v1.schema.json`
- `tests/strategy_scale_decision/`
- `docs/strategy_scale_decision/README.md`

完了条件:

- `strategy_live_observation_manifest.v1` を required input とする。
- actual fill、cancel / close safety、rejection、max loss breach、blocked canary を policy で判定できる。
- `READY_FOR_HUMAN_SCALE_REVIEW` は scale-up execution permission ではない。
- `PREPARE_NEXT_SCALE_PLAN` は次の計画 artifact の候補であり、live order permission ではない。
- wallet / signing / exchange write は false のまま。

テスト方針:

```bash
uv run pytest tests/strategy_scale_decision -q
uv run sis strategy-scale-decision --help
```

### T12b. Next Scale Plan Contract

実装状態: 実装済み。

目的:

- scale decision 後に、次の拡大計画を人間レビューへ出せるかを artifact として残す。
- next-scale execution permission とは分ける。

対象ファイル:

- `src/sis/strategy_next_scale_plan/`
- `src/sis/commands/strategy_next_scale_plan.py`
- `src/sis/cli.py`
- `schemas/strategy_next_scale_plan.v1.schema.json`
- `tests/strategy_next_scale_plan/`
- `docs/strategy_next_scale_plan/README.md`

完了条件:

- `strategy_scale_decision.v1` を required input とする。
- 任意の `strategy_micro_live_plan.v1` を読み、前回 risk limit からの倍率上限を検査できる。
- order notional、position notional、daily loss、total loss、open positions、allowed symbols、session window、monitoring、schedule cancel、kill switch を必須にする。
- `READY_FOR_HUMAN_NEXT_SCALE_REVIEW` は next-scale execution permission ではない。
- `next_scale_execution_allowed=false`、`live_allowed=false`、wallet / signing / exchange write false を固定する。

テスト方針:

```bash
uv run pytest tests/strategy_next_scale_plan -q
uv run sis strategy-next-scale-plan --help
```

### T13. Optional OSS Adoption Slices

目的:

- OSS を入れる場合に、依存追加が目的化しないようにする。

対象ファイル:

- `pyproject.toml`
- `uv.lock`
- `src/sis/strategy_model_loop/`
- `src/sis/strategy_inputs/`
- `docs/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md`
- 対応する `tests/`

採用条件:

- `optuna`: trial runner を実装し、`strategy_optimizer_trial_ledger.v1` に all trials、pruned trials、failed trials、seed、sampler、pruner、search space hash を保存できる場合だけ採用する。
- `pandera`: input contract validation が複数 dataframe format / schema で重複し、dtype / range / nullable / uniqueness を宣言的に共有する必要が出た場合だけ採用する。
- `mlflow`: local JSON artifact だけでは model run の比較、artifact、metric、model version を追えなくなった場合だけ採用する。

完了条件:

- 新規依存は optional extra か明示的な main dependency として理由を docs に残す。
- lockfile を更新する。
- 依存がない環境で既存 CLI が壊れない。
- OSS を使わない fallback または明示的 skip message を持つ。

テスト方針:

```bash
uv sync --dev --locked
uv run pytest tests/<affected-slice> -q
./scripts/check
```

## 実装順

実装順は固定する。

```text
T0 docs alignment
T1 authoring update handoff
T2 input contract column / availability validation
T3 normal paper evidence contract
T4 runtime observation PnL / cost enrichment
T5 drift review v2
T6 strategy case lite
T7 daily brief
T8 AI review packet
T9 model / optimizer trial ledger
T10 micro live plan gate
T11 live observation contract
T12 static workbench viewer
T12a scale decision contract
T12b next scale plan contract
T13 optional OSS adoption, only when a concrete runner or validation reuse need appears
```

T8 / T9 は T1〜T7 の土台ができた後に実装する。現時点では T12 static workbench viewer、T12a scale decision contract、T12b next scale plan contract まで実装済みである。AI、ML、UI は入力と観測の土台が弱いと、判断支援ではなく誤判断を増幅する。

## 全体テスト方針

各 slice の最小テスト:

```bash
uv run pytest tests/<slice> -q
uv run sis <new-command> --help
uv run python scripts/check_current_docs.py
```

主要 milestone ごとの full check:

```bash
./scripts/check
```

Schema を追加した場合:

- JSON Schema が parse できる。
- Pydantic model の dump が schema validation に通る。
- boundary flag が true の fixture は blocked になる。
- missing source artifact の fixture は success ではなく needs / blocked status になる。

CLI を追加した場合:

- `uv run sis --help` に command が出る。
- `--help` が落ちない。
- output path、replace behavior、missing input error をテストする。

Docs を追加した場合:

- Tokyo timestamp header を付ける。
- `scripts/check_current_docs.py` の対象に入れるか、意図的に archive 扱いにする。
- current docs から辿れる導線を作る。

## 全体完了条件

この計画の完了条件:

- T1〜T11 が実装され、`./scripts/check` が通る。
- T12 static viewer が実装され、Svelte UI は明示的に別計画扱いになっている。
- T12b next scale plan が実装され、next-scale execution permission と分離されている。
- T13 は、必要が出た OSS だけを採用し、不要なら deferred として残す。
- Daily Brief が、少なくとも input / review / stage / smoke / runtime / drift / learning / authoring handoff / case / AI review / model loop / micro live plan gap の未処理状態を読める。
- Micro Live Plan Gate は既存 `MicroLivePolicy` と矛盾しない plan artifact として存在する。
- Live Observation Contract は既存 micro live canary report / audit bundle を read-only で取り込める。
- docs に “paper pass = live ready” と読める表現が残らない。
- `uv run sis --help`、schemas、tests、current docs が矛盾しない。

この計画で完了扱いにしないもの:

- production live trading system。
- standard public live execution CLI。
- credential、wallet、signing、exchange write の readiness。
- venue-general live execution adapter。
- 実損失を伴う micro live の実行そのもの。
- Svelte UI app。

## 抜け・漏れ・誤謬リスク

この計画でも残るリスク:

- 実 market data provider の品質は、local artifact だけでは保証できない。
- paper fills は simulated なので、live fills と一致しない。
- Micro live は計画 artifact までで、execution system の安全性は別問題。
- 既存 micro live safety code は `Trade[XYZ]` 寄りであり、Workbench 標準 route に接続するには T10/T11 の adapter boundary が必要。
- AI / ML / GA は証拠を増やす一方、overfitting と narrative bias も増やす。
- 個人運用では Daily Brief が読まれなければ artifact があっても意味がない。
- config を緩める override が増えると、stage gate が形式化する。
- Viewer UI を後回しにすると、artifact は揃っても日次運用の摩擦は残る。
- realized PnL が broker / paper engine 由来の場合、その計算定義の差を別途管理する必要がある。

対策:

- T1〜T12 と scale decision / next scale plan contract 実装済みの前提で、Svelte UI は別 plan に切る。
- T8 以降の AI / ML / OSS / UI 系は `auto_applied=false` と source hash を徹底する。
- Micro live は execution ではなく plan gate と observation contract までに分ける。
- Daily Brief で override、boundary violation、missing data、stale artifact を上位表示する。
