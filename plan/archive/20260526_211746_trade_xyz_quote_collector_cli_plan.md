# Trade[XYZ] Quote Collector CLI Consumed Plan

Timestamp: 2026-05-26 21:17:46 JST  
Updated: 2026-05-27 JST

> Current status: historical consumed plan plus status note. PR12 read-only smoke and Trade[XYZ] phase gate cutover are complete. Check `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, and `uv run sis collect-trade-xyz-quotes --help` before using this as an implementation source.

## 結論

`trade_xyz` quote collector の public CLI 化と、PR12 read-only smoke までの phase gate 接続は完了済み。

現行 command:

```bash
uv run sis collect-trade-xyz-quotes --write-summary --write-report
```

この文書は current implementation plan ではなく、PR9a-PR12 で消化された historical plan として読む。

## 現行 status

Implemented:

- `uv run sis collect-trade-xyz-quotes` が public CLI として使える。
- `--registry-path` で registry JSON を指定できる。
- `--normalize/--no-normalize` で normalize 実行を切り替えられる。
- `--symbols`, `--max-symbols`, `--duration-minutes`, `--interval-seconds`, `--replace`, `--dry-run`, `--write-summary`, `--write-report`, `--output-dir` が使える。
- `--write-summary` は `data/ops/trade_xyz_quote_collection_summary.json`、`--write-report` は `data/reports/trade_xyz_quote_collection_report.md` を出す。
- default では raw quote JSONL 収集後に `data/normalized/quotes.parquet` と `data/normalized/sis.duckdb` を更新する。
- `probe trade-xyz` が生成する `data/registry/trade_xyz_instrument_registry.json` を標準入力 artifact とする。
- `log-quotes --venue gtrade` は current public CLI surface ではない。
- `phase-gate-review` は Trade[XYZ] artifacts を使って `READ_ONLY_GO` を出せる。

Current command flow:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes
```

Raw only:

```bash
uv run sis collect-trade-xyz-quotes --no-normalize
```

## 実装済み surface

CLI:

- `src/sis/commands/quotes.py`
- command: `collect-trade-xyz-quotes`
- options:
  - `--registry-path`
  - `--normalize/--no-normalize`
  - `--symbols`
  - `--max-symbols`
  - `--duration-minutes`
  - `--interval-seconds`
  - `--replace/--append`
  - `--dry-run`
  - `--write-summary`
  - `--write-report`
  - `--output-dir`

Registry helper:

- `src/sis/venues/trade_xyz/registry.py`
- `load_trade_xyz_registry(path)`

Tests:

- `tests/test_cli_smoke.py`
- help 表示
- happy path
- `--no-normalize`
- registry missing
- no active instruments

Docs already updated:

- `README.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/CURRENT_STATE.md`

## 入出力 contract

Input:

- default registry: `data/registry/trade_xyz_instrument_registry.json`
- shape: `InstrumentSpec[]`
- active `trade_xyz` instruments only

Raw output:

- `data/raw/quotes/trade_xyz/<YYYY-MM-DD>.jsonl`

Normalized output:

- `data/normalized/quotes.parquet`
- `data/normalized/sis.duckdb`

Stdout:

- `quote_count=<n>`
- `raw_quotes_path=<path>`
- normalize 実行時:
  - `normalized_quotes_path=<path>`
  - `duckdb_path=<path>`
- summary/report 実行時:
  - `summary_path=<path>`
  - `report_path=<path>`
- `recommended_read_order_*`

## PR12 result

2026-05-27 の latest artifact:

- `data/ops/trade_xyz_quote_collection_summary.json`: 310 rows, 3673.995702 observed seconds
- `data/ops/pr12_fresh_read_only_smoke_summary.json`: `final_decision=READ_ONLY_GO`
- `data/reports/pr12_fresh_read_only_smoke_report.md`
- `data/ops/phase_gate_review_summary.json`: `phase_gate_decision=READ_ONLY_GO`, `next_actions=[]`

## 現在の残課題

`collect-trade-xyz-quotes` と Trade[XYZ] read-only phase gate は実装済みだが、Bot 化前にはまだ不足がある。

現状では live order はまだ出さない。残る主題は、paper / preview / no-trade reason を正式な bot artifact として切り出す作業である。

既知の不足:

- tracking report を Bot 判断へ接続する decision artifact
- `bot_decision.json` / orders preview の生成
- live order はまだ出さない

## 次に作るべきもの

次候補:

```text
Trade[XYZ] bot decision preview
```

目的:

- Trade[XYZ] + real market + tracking の品質を Bot 前段の Go/No-Go artifact に落とす。
- 実発注はしない。まず paper / preview / no-trade reason を生成する。

## Bot 前段 artifact

新規 artifact 候補:

- `data/ops/trade_xyz_data_quality.json`
- `data/reports/trade_xyz_data_quality.md`
- `data/ops/trade_xyz_readiness.json`
- `data/reports/trade_xyz_readiness.md`
- `data/bot/bot_decision.json`
- `data/reports/bot_orders_preview.md`

`bot_decision.json` の最低限の内容:

```text
symbol
side
decision: trade | no_trade
confidence
source_confidence
venue_quality_score
spread_bps
depth_10bps_usd
quote_age_ms
market_session_status
block_reasons
max_notional_usd
required_gates
```

## Gate inputs

Trade[XYZ] quote quality:

- quote row count
- quote age / freshness
- tradable rate
- spread p50 / p90
- depth 10bps / 25bps
- block reason rate
- `BLOCK_API_ERROR` rate
- missing bid / ask rate

Real market quality:

- provider availability
- source confidence
- stale/delayed data status
- market session status
- event blackout status

Tracking quality:

- real market vs venue price difference
- lead/lag confidence
- tracking status per symbol
- source confidence threshold

Paper readiness:

- fee model available
- paper fills use Trade[XYZ] quote and tracking quality
- no-trade reason is explicit

## Acceptance

Done when:

- `uv run sis collect-trade-xyz-quotes` remains public and tested.
- A single command can refresh Trade[XYZ] quote, real market, tracking, readiness artifacts without live order.
- `phase-gate-review` or a Trade[XYZ]-specific readiness command no longer requires legacy `gtrade` / `ostium` artifacts for the Trade[XYZ] Bot path.
- `bot_decision.json` can express both `trade` and `no_trade` decisions.
- no-trade reasons are explicit and test-covered.
- `./scripts/check` passes.

## Non-goals

- live order execution
- wallet / signing / secret handling
- production daemon deployment
- replacing paper execution with real execution
- removing historical legacy evidence docs

## Verification

Current CLI verification:

```bash
uv run sis collect-trade-xyz-quotes --help
uv run sis validate-artifacts --help
uv run pytest tests/test_cli_smoke.py -q
./scripts/check
```

PR12 verification included:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --symbols SP500,XYZ100,NVDA,AAPL,MSFT --duration-minutes 60 --interval-seconds 60 --normalize --replace --write-summary --write-report
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis paper-operations-cycle
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

## Docs status

The active docs have been updated to treat `collect-trade-xyz-quotes` as implemented:

- `docs/DOCUMENT_AUDIT_2026-05-27.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/CODE_STATUS.md`

Do not update historical generated artifacts in `docs/archive/` or `docs/live_evidence_reports/`.

---

## New Task: Bot Preview v1後の次作業計画

作成日時: 2026-05-27 20:47 JST

### 結論

ここからは、`bot-preview v1` を土台にして、次を順番に進める。

1. `bot-preview v1` を現在の安全な正本として固定する。
2. 注文候補を出す前に、候補生成ルールを別タスクで定義する。
3. 候補生成は paper 接続までに限定し、live order には進まない。
4. manual micro live は最後の別ゲートとして扱う。

### 現在地

実装済み:

- `uv run sis bot-preview`
- `data/bot/bot_decision.json`
- `data/reports/bot_orders_preview.md`
- v1 は常に `decision=HOLD`
- `READ_ONLY_GO` でも `BOT_ORDER_LOGIC_NOT_IMPLEMENTED` を理由に注文候補を出さない
- wallet / signing / exchange write は未使用
- `./scripts/check` は `280 passed`

### Task 1: Bot Preview v1を運用正本にする

目的:

- Bot前の確認入口を `phase-gate-review` + `bot-preview` に固定する。
- `check-go-no-go` / `build-evidence-card` は補助reportとして扱い続ける。

作業:

- README / runbook / current state docs の導線を確認する。
- `uv run sis bot-preview --fail-on-not-ready` をmerge前確認に含めるか判断する。
- `bot_decision.json` の v1 schema をdocsに短く固定する。

Done:

- `bot-preview` の出力場所、HOLD固定、no wallet/no signing/no exchange write がdocsから一目で分かる。
- artifact不足時の exit code 2 がテスト済み。

### Task 2: Order Candidate Preview v2を設計する

目的:

- `bot-preview` が注文候補を出す前に、判断ルールを固定する。
- v2でも live order は出さない。

未決事項:

- symbol選定ルール
- BUY / SELL / HOLD の判定条件
- limit price の算出方法
- quantity / notional の算出方法
- max risk / stop条件
- no-trade reason の優先順位
- candidateをpaperへ渡すJSON schema

推奨方針:

- 既定は v1 と同じ `HOLD`。
- 注文候補は `--include-order-candidates` 指定時だけ出す。
- 出力先は `data/bot/order_candidates.json` と `data/reports/bot_orders_preview.md`。
- wallet / signing / exchange write は引き続き禁止。

Done:

- 注文候補schemaが決まっている。
- no-trade reasonが候補生成より優先される。
- candidate生成はpaper専用で、live executionへ接続しない。

### Task 3: Paper接続を定義する

目的:

- Bot preview候補を、本物のお金を使わないpaper flowで検証できるようにする。

作業:

- `bot_decision.json` / `order_candidates.json` をpaper入力に変換する境界を決める。
- paper result と bot decision の比較reportを定義する。
- `data/reports/bot_paper_comparison.md` のような出力を検討する。

Done:

- Bot判断とpaper結果が同じrunで追跡できる。
- paperで失敗した理由がBot側のreasonと比較できる。
- live orderに進まず検証できる。

### Task 4: Manual Micro Live前ゲートを別タスク化する

目的:

- micro live safety codeが存在することと、実運用できることを混同しない。

前提:

- public CLI化はまだしない。
- dedicated API wallet、資金、権限、scheduleCancel preflight が必要。
- max notional は安全上限内に固定する。

必要な定義:

- operator confirm flag
- dedicated API wallet requirement
- scheduleCancel preflight
- max_notional_usd
- failure stop condition
- audit artifact
- local-only manual runbook

Done:

- manual micro live を実行してよい条件と、止める条件が明文化されている。
- 標準CIや通常PR verificationには live canary を含めない。

### Stop Conditions

次の状態では先へ進まない。

- `phase-gate-review` が `READ_ONLY_GO` でない。
- `bot-preview` が artifact不足を出している。
- no-trade reason が曖昧。
- 注文候補の数量・価格・リスク上限が未定義。
- wallet / signing / exchange write に触れそうな変更が混ざる。

### 次に着手する最小単位

次の1PRはこれだけにする。

```text
Bot Preview v2 design doc:
- order candidate schema
- HOLD / BUY / SELL rules
- no-trade reason priority
- paper handoff boundary
- explicit non-goals: live order, wallet, signing, exchange write
```

---

## 指示待ちタスク台帳: Bot Preview v1以降

作成日時: 2026-05-27 20:52 JST

この台帳は、ユーザーから明示指示があるまで実装しない。番号単位で依頼できるように、内容と要素を細分化する。

### A. Bot Preview v1 固定化

A1. v1 schemaの明文化

- 対象: `data/bot/bot_decision.json`
- 要素: `schema_version`, `generated_at`, `venue`, `decision`, `reason_codes`, `read_only_artifacts`, `symbols_checked`, `next_actions`
- 成果物: docs上の短いschema説明
- 実装有無: docsのみ

A2. v1 reportの明文化

- 対象: `data/reports/bot_orders_preview.md`
- 要素: HOLD判定、理由、phase gate状態、artifact参照、注文候補なし、no wallet/no signing/no exchange write
- 成果物: docs上のreport説明
- 実装有無: docsのみ

A3. merge前確認コマンドの追加判断

- 候補: `uv run sis bot-preview --fail-on-not-ready`
- 要素: 標準checkに入れるか、手動確認に留めるか
- 判断基準: `data/` artifact依存があるためCI標準には入れにくい
- 実装有無: 方針決定後にscripts/docs更新

A4. v1の完了条件固定

- 要素: HOLD固定、artifact不足時exit 2、wallet不使用、exchange write不使用
- 成果物: acceptance section
- 実装有無: docs/test確認のみ

### B. Order Candidate Preview v2 設計

B1. candidate schema定義

- 対象候補: `data/bot/order_candidates.json`
- 必須要素: `schema_version`, `generated_at`, `venue`, `source_decision_path`, `candidates`, `blocked_reasons`
- candidate要素: `symbol`, `side`, `order_type`, `limit_price`, `quantity`, `notional_usd`, `reason`, `risk_notes`
- 実装有無: まずdocs/schema案のみ

B2. BUY / SELL / HOLD 判定ルール定義

- 要素: どの入力でBUY/SELLを許可するか
- 入力候補: phase gate, quote summary, tracking quality, source confidence, venue quality, paper state
- 未決事項: 戦略シグナルを使うか、まず全HOLDに近い安全ルールにするか
- 実装有無: docsのみ

B3. no-trade reason優先順位

- 例: `PHASE_GATE_NOT_READY` > `QUOTE_STALE` > `LOW_LIQUIDITY` > `LOW_SOURCE_CONFIDENCE` > `ORDER_LOGIC_DISABLED`
- 要素: 複数理由がある時に何を一番上に出すか
- 成果物: reason priority table
- 実装有無: docsのみ

B4. limit price算出ルール

- 候補: best bid/ask基準、mid基準、conservative offset基準
- 必須要素: 価格が欠けた場合は候補を作らない
- 成果物: price rule spec
- 実装有無: docsのみ

B5. quantity / notional算出ルール

- 候補: 固定notional、policy上限割合、symbol別上限
- 必須要素: max_notional_usd, max_leverage, min_size, rounding
- 成果物: sizing rule spec
- 実装有無: docsのみ

B6. `--include-order-candidates` CLI仕様

- 対象: `uv run sis bot-preview --include-order-candidates`
- 既定: 指定なしではv1同様HOLDのみ
- 指定時: candidate schemaに従ってpreviewだけ出す
- 禁止: live order, wallet, signing, exchange write
- 実装有無: docs後に実装可

B7. v2 acceptance定義

- 条件: artifacts不足時は候補ゼロ、reason明示、paper専用、testsあり
- 成果物: acceptance checklist
- 実装有無: docsのみ

### C. Paper接続設計

C1. bot candidateからpaper inputへの変換境界

- 入力: `data/bot/order_candidates.json`
- 出力候補: paper order planまたは既存paper runner入力
- 要素: symbol, side, quantity, price, reason, source artifact
- 実装有無: docsのみ

C2. paper実行との接続方式

- 候補1: 既存 `paper-operations-cycle` にcandidate読込を追加
- 候補2: 新CLI `paper-from-bot-preview` を追加
- 候補3: まずreportだけで実行接続しない
- 推奨: 候補2。既存paper flowを壊しにくい
- 実装有無: 方針決定後

C3. bot vs paper比較report

- 出力候補: `data/reports/bot_paper_comparison.md`
- 要素: candidate, paper fill/block, PnL, block reason, mismatch reason
- 実装有無: docs後に実装可

C4. paper接続の停止条件

- candidateなし
- price/quantity欠損
- phase gate not ready
- source confidence不足
- venue quality不足
- 実装有無: docs/test対象

C5. paper接続acceptance

- candidateあり/なし両方をtest
- live orderに接続していないことをtest
- generated reportにreasonが出ることをtest
- 実装有無: tests込みで実装可

### D. Manual Micro Live前ゲート設計

D1. manual canary前提条件

- dedicated API wallet
- small balance only
- max_notional_usd上限
- scheduleCancel preflight
- kill switch clear
- explicit confirm flag
- local only
- 実装有無: docsのみ

D2. public CLI化しない境界

- 標準CLIには出さない
- 通常CIには入れない
- manual opt-inだけにする
- 実装有無: docsのみ

D3. manual runbook項目

- preflight
- command
- expected artifacts
- abort conditions
- recovery steps
- post-run audit
- 実装有無: docsのみ

D4. failure stop condition

- scheduleCancel失敗
- orderStatus確認不能
- cancelByCloid失敗
- reduce-only close失敗
- unexpected fill
- API wallet残高/権限異常
- 実装有無: docs/test対象

D5. micro live acceptance

- mock/fake exchange testsのみ標準verificationに含める
- real live canaryはmanual local only
- max_notional_usd <= 50 を維持
- 実装有無: docs後に必要なら実装

### E. Documentation / Handoff整理

E1. current docs同期

- 対象: README, CURRENT_STATE, CODE_STATUS, OPERATIONS_RUNBOOK
- 要素: v1実装済み、v2未実装、paper接続未実装、micro live未公開
- 実装有無: docsのみ

E2. beginner HTML同期

- 対象: `docs/trade_xyz_bot_beginner_guide.html`
- 要素: HOLD preview済み、注文候補は未実装、paper接続は次段階
- 実装有無: docsのみ

E3. plan分割

- 対象: `plan/`
- 候補: `bot_preview_v2_design_plan.md`, `bot_paper_connection_plan.md`, `manual_micro_live_gate_plan.md`
- 実装有無: docsのみ

E4. historical docs非対象確認

- 対象外: `docs/archive/`, `docs/live_evidence_reports/`
- 実装有無: 触らない

### F. 検証カテゴリ

F1. unit tests

- bot preview schema
- reason priority
- candidate generation rules
- paper conversion

F2. CLI smoke

- `uv run sis bot-preview --help`
- `uv run sis bot-preview`
- `uv run sis bot-preview --fail-on-not-ready`
- 将来: `uv run sis bot-preview --include-order-candidates`

F3. integration tests

- ready artifacts + HOLD
- missing artifacts + exit 2
- candidate generated but paper-only
- paper comparison report generated

F4. full gate

- `./scripts/check`
- test count docs update if count changes

### G. 実装禁止境界

G1. live order禁止

- exchange write APIを呼ばない
- order submitしない

G2. wallet / signing禁止

- secretを読まない
- private keyを扱わない

G3. micro live public CLI禁止

- manual canary設計前に公開しない

G4. candidate自動有効化禁止

- v2でも既定はHOLD
- `--include-order-candidates` のような明示オプションなしに候補を出さない

### 推奨される次の指示単位

実装前に、次のどれか1つだけを指定する。

```text
A1だけ: v1 schema docsを固定する
B1だけ: order candidate schemaを設計する
B2だけ: BUY/SELL/HOLDルールを設計する
B3だけ: no-trade reason優先順位を設計する
C2だけ: paper接続方式を決める
D3だけ: manual micro live runbook項目を作る
E3だけ: planファイルを分割する
```
