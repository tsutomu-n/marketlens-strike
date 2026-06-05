<!--
作成日: 2026-06-05_22:12 JST
更新日: 2026-06-05_22:48 JST
-->

# Backtest-First Venue-Neutral Pivot Plan 2026-06-05

この文書は、`Trade[XYZ]` を当面の注文口にしない前提で、最短でバックテストに取り組み、後続で Bitget などの CEX demo trading を paper / demo execution 検証に使える状態へ進めるための実行計画である。

## 結論

決定:

```text
当面の主目的:
  可能な限り早く、戦略をバックテストで評価できる開発ループを作る。

当面の非目的:
  Trade[XYZ] を注文口として完成させること。

将来候補:
  Trade[XYZ] は将来の注文口候補として残す。
  Bitget などの CEX demo は paper / demo execution の検証先として検討する。
```

主経路を次に切り替える。

```text
旧主経路:
  Trade[XYZ] real-data readiness
  -> 30日 quote coverage
  -> Trade[XYZ] pure backtest / paper / micro live

新主経路:
  Backtest-first
  -> existing Strategy Authoring baseline inventory
  -> first reproducible backtest run
  -> venue-neutral signal / candidate / paper intent contract
  -> optional CEX demo adapter, mock-first
  -> paper/demo order lifecycle verification
```

2026-06-05_22:48 JST の追加レビューで、実装順を次に修正する。

```text
M0:
  Trade[XYZ] collector を主経路から外す。

M1:
  既存 Strategy Authoring example の入力データを棚卸しし、最短 backtest を1本通す。
  ここが「バックテストに取り組める」の最初の完了点。

M2:
  trade_xyz 固定の schema / model / compiler cast を、最小 enum へ広げる。

M3:
  bitget_demo は fixture / mock / paper-only でまず通す。

M4:
  Bitget API は classic demo v2 か UTA v3 かを公式 docs で選定してから adapter 化する。

M5:
  demo write API は最後。credential と明示許可がない限り実行しない。
```

## 現在の確認済み事実

確認時刻:

```text
2026-06-05_22:48 JST
```

コードと docs から確認した事実:

```text
Trade[XYZ] pure backtest:
  実装済み。
  ただし public CLI は未公開。
  入口は Python API の sis.backtest.engine.runner.run_backtest().

Strategy Authoring fixed-horizon backtest:
  public CLI あり。
  uv run sis strategy-author-run --spec <path> --through backtest
  ただし example spec の validate は現時点で data/research/feature_panel.parquet 不在により失敗する。

TradeCandidate:
  src/sis/research/strategy_lab/candidates.py で execution_venue が Literal["trade_xyz"]。

PaperIntentPreview:
  src/sis/research/strategy_lab/paper_intent_preview.py で execution_venue が Literal["trade_xyz"]。

StrategyExperimentSpec / StrategySignalRecord:
  src/sis/research/strategy_lab/specs.py で SymbolBinding と StrategySignalRecord が trade_xyz 固定。
  同じ specs.py の PROXY_REQUIREMENTS は XYZ100->QQQ, SP500->SPY を強制している。
  この制約は Trade[XYZ] proxy symbol 向けであり、bitget_demo の crypto symbol にそのまま適用してはいけない。

strategy_signal schema:
  schemas/strategy_signal.v1.schema.json で execution_venue が const trade_xyz。

trade_candidate / paper_intent_preview schema:
  schemas/trade_candidate.v1.schema.json と schemas/paper_intent_preview.v1.schema.json は execution_venue を required にしている。
  ただし schema 上の enum / const は未定義。
  現状は Pydantic model だけが trade_xyz に制限しており、schema/model parity が崩れている。

paper preview compiler:
  src/sis/research/strategy_lab/authoring/compiler/paper_preview.py に Literal["trade_xyz"] cast が残っている。

ExecutionAdapter:
  src/sis/execution/base.py に汎用 Protocol がある。

Trade[XYZ] collector:
  2026-06-05_22:12 JST 時点でまだ until-ready / data-cycle が稼働中。
```

Bitget 公式 docs から確認した事実:

```text
確認時刻:
  2026-06-05_22:48 JST

Bitget demo trading:
  Demo API Key が必要。
  REST demo trading では request header に paptrading: 1 を付ける。
  Classic WebSocket demo trading は demo 用 public/private endpoint を使う。
  docs には KYC が必要と記載されている。

Bitget UTA:
  v3 API / UTA docs は 2026年5月にも変更が入っている。
  adapter 実装前に classic demo v2 と UTA v3 のどちらを最初の対象にするか決める必要がある。
```

参照:

- <https://www.bitget.com/api-doc/classic/demotrading/restapi>
- <https://www.bitget.com/api-doc/classic/demotrading/websocket>
- <https://www.bitget.com/api-doc/uta/changelog>

## 目的

この pivot の目的:

```text
1. Trade[XYZ] の30日 quote coverage 完了を待たずに、バックテスト開発へ入る。
2. 戦略評価、候補生成、paper intent を取引所固有の注文口から分離する。
3. Bitget demo などの CEX demo を、戦略評価後の execution lifecycle 検証に使えるようにする。
4. read-only / paper / demo / live の境界を崩さない。
5. Trade[XYZ] を将来候補として残しつつ、今の開発速度を Trade[XYZ] readiness に縛らない。
```

## 制約

絶対に守る制約:

```text
live order:
  まだ production live order は扱わない。

wallet / signing:
  repo内で wallet / signing / secret を扱わない。

exchange write:
  Bitget demo を含め、明示タスクとcredential準備なしに外部 write API を叩かない。

backtest:
  backtest 結果を live ready と読まない。

paper intent:
  PaperIntentPreview は paper/demo intent であり、OrderIntent や live order ではない。

Trade[XYZ]:
  当面の注文口ではない。
  ただし既存コードは壊さない。

データ:
  取引所固有データを strategy evaluation の必須前提にしない。
  timestamp / price / fee / fill source の出所を artifact に残す。
```

外部前提:

```text
Bitget demo:
  Demo API Key、secret、passphrase、必要なら KYC が必要。
  credential は .env / local secret に置き、git に入れない。

Trade[XYZ] archive:
  AWS credential がないため archive backfill は blocked。
  新主経路では当面 blocker にしない。
```

## 方針

### 1. Trade[XYZ] collector は主経路から外す

現在動いている collector は、Trade[XYZ] の 30日 quote coverage を作るためのもの。新方針では主目的ではない。

推奨:

```text
今すぐ停止する。
```

理由:

```text
1. 新主経路に直接必要ない。
2. status / handoff / operator attention を消費する。
3. 収集が続くほど、Trade[XYZ] readiness が主目的であるように見える。
4. 将来再開は可能。
```

代替:

```text
現在の 24h cycle だけ自然終了まで放置し、その後 until-ready を再起動しない。
```

この代替は低リスクだが、開発の焦点がぶれるため推奨しない。

### 2. まず既存の Strategy Authoring backtest を主入口にする

最短で使える public CLI はこれ。

```bash
uv run sis strategy-author-run --spec <spec.yaml> --through backtest
```

これは Trade[XYZ] pure backtest とは別 surface だが、最短で戦略評価ループを回すにはこちらが実務的である。

ただし、2026-06-05_22:48 JST 時点では example spec の validation が `data/research/feature_panel.parquet` 不在で失敗する。したがって最初の実装タスクは Bitget 接続ではなく、既存 backtest 入力の棚卸しと、欠けている最小 fixture / 既存生成手順の確定である。

Trade[XYZ] pure backtest は、後で engine 汎用化または public CLI 化を検討する。

### 3. venue-neutral 化は最小範囲から行う

最初から多取引所抽象化を大きく作らない。

最小変更:

```text
trade_xyz 固定の Literal / schema const を、当面必要な enum に広げる。

初期 enum:
  trade_xyz
  bitget_demo

ただし:
  bitget_demo は demo execution 用の名前。
  production bitget live とは分ける。
```

### 4. Bitget は backtest の前提ではなく demo execution adapter として扱う

Bitget demo は、次の検証に使う。

```text
OrderIntent / PaperIntentPreview 相当
-> demo order estimate / submit
-> order status
-> fill sync
-> position sync
-> cancel / close
```

最初の目的は収益性検証ではない。注文 lifecycle と状態同期の検証である。

Bitget adapter 実装前に、次を必ず決める。

```text
first lane:
  classic demo v2
  UTA v3 demo
  spot
  USDT futures

決め方:
  1. ユーザーが実際に作れる Demo API Key / account type を確認する。
  2. 実装直前に公式 docs を再確認する。
  3. endpoint / path / permission / rate limit / request header を lane ごとに1枚の docs に残す。
  4. その後に mock-first adapter を実装する。
```

## データ方針

backtest-first で使うデータの優先順位:

```text
1. 既存 local artifact:
   data/research/feature_panel.parquet
   data/normalized/quotes.parquet
   data/research/venue_cost_matrix.csv

2. 既存 generator / ingestion command:
   repo内の既存 CLI / scripts で再生成できるなら、それを使う。

3. deterministic fixture:
   既存 generator が重い、または外部 credential が必要なら、最小 fixture を tests / docs example 用に作る。

4. external exchange API:
   Bitget や Trade[XYZ] の外部 API から新規取得するのは最後。
```

現時点の確認:

```text
存在する:
  data/normalized/quotes.parquet
  docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml

見つかっていない:
  data/research/feature_panel.parquet
  data/research/venue_cost_matrix.csv

実行結果:
  uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
  -> feature_panel_path not found: data/research/feature_panel.parquet
```

## 対象ファイル

### docs / handoff

```text
docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md
docs/backtest/README.md
docs/OPERATIONS_RUNBOOK.md
.ai_memory/HANDOFF.md
```

### strategy / schema

```text
src/sis/research/strategy_lab/specs.py
src/sis/research/strategy_lab/candidates.py
src/sis/research/strategy_lab/paper_intent_preview.py
src/sis/research/strategy_lab/signal_registry.py
src/sis/research/strategy_lab/evaluation_plan.py
src/sis/research/strategy_lab/authoring/contracts/spec.py
src/sis/research/strategy_lab/authoring/io.py
src/sis/research/strategy_lab/authoring/compiler/paper_preview.py
src/sis/venues/ids.py
schemas/strategy_signal.v1.schema.json
schemas/trade_candidate.v1.schema.json
schemas/paper_intent_preview.v1.schema.json
schemas/evaluation_plan.mls.v1.schema.json
```

### paper / execution

```text
src/sis/paper/broker.py
src/sis/paper/runner.py
src/sis/execution/base.py
src/sis/execution/trade_xyz_adapter.py
src/sis/execution/bitget_demo_adapter.py
configs/fee_model.trade_xyz.yaml
configs/fee_model.bitget_demo.yaml
```

`src/sis/execution/bitget_demo_adapter.py` と `configs/fee_model.bitget_demo.yaml` は新規候補。Bitget credential がない段階では、まず mock / dry-run / parser contract だけを実装する。

### tests

```text
tests/strategy_authoring/
tests/backtest/
tests/test_trade_xyz_live_order_policy.py
tests/test_trade_xyz_adapter_safety.py
tests/test_micro_live_canary.py
tests/test_bitget_demo_adapter.py
tests/test_paper_from_intents_venue_neutral.py
```

新規 test file は必要になった時点で追加する。

## Task Chain

### T0: Trade[XYZ] collector を主経路から外す

goal:

```text
現在動いている Trade[XYZ] until-ready / data-cycle を停止または自然終了待ちに切り替え、今後自動再起動しない状態にする。
```

target_files:

```text
.ai_memory/HANDOFF.md
docs/OPERATIONS_RUNBOOK.md
data/ops/trade_xyz_until_ready_supervisor_state.json
logs/trade_xyz_data_cycle/
```

out_of_scope:

```text
Trade[XYZ] データ削除
Trade[XYZ] 実装削除
Trade[XYZ] readiness 修正
```

acceptance:

```text
1. Trade[XYZ] collector / until-ready process が重複していない。
2. 停止する場合は supervisor / cycle / child process が消えている。
3. lock が absent または stale でない。
4. handoff に「Trade[XYZ] は当面主経路ではない」と記録されている。
5. 今後の next action が backtest-first に変わっている。
```

verification:

```bash
pgrep -af '[c]ollect_trade_xyz_data_until_ready|[c]ollect_trade_xyz_data_cycle|[c]ollect-trade-xyz-data-cycle|[c]ollect-trade-xyz-quotes' || true
test ! -e .tmp/trade_xyz_data_until_ready.lock && echo supervisor_lock=absent || true
test ! -e .tmp/trade_xyz_data_cycle.lock && echo cycle_lock=absent || true
uv run python scripts/check_current_docs.py
```

destructive_level:

```text
medium
```

notes:

```text
実行中process停止を含むため medium。
データ削除はしない。
停止前に必ず process / lock / log を再読込する。
SIGKILL は使わず、まず supervisor と cycle process に SIGTERM を送る。
lock は process が消え、log で停止状態を確認してから扱う。
stale lock を削除する場合も、対応 PID が存在しないことを確認してから行う。
```

### T1a: Backtest baseline の入力棚卸しと最初の validate を通す

goal:

```text
Bitget / Trade[XYZ] 追加収集に進む前に、既存 Strategy Authoring example を使って backtest 入力の欠けを確定し、最小の再現入力を用意する。
```

target_files:

```text
docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md
docs/backtest/README.md
docs/OPERATIONS_RUNBOOK.md
docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
data/research/feature_panel.parquet
data/research/venue_cost_matrix.csv
data/normalized/quotes.parquet
tests/strategy_authoring/
```

out_of_scope:

```text
Bitget API 接続
Trade[XYZ] 追加収集
Strategy Authoring の設計変更
production live order
```

implementation notes:

```text
最初に確認するもの:
  1. example spec が参照する feature_panel_path / quote_data_path / cost_model_path。
  2. それらを生成する既存 CLI / scripts の有無。
  3. 既存 generator がない、または外部 credential を要求する場合の deterministic fixture 方針。

2026-06-05_22:48 JST の確認:
  quote_data_path は存在する。
  feature_panel_path は存在しない。
  cost_model_path は存在しない。
  strategy-author-validate は feature_panel_path not found で exit 2。
```

acceptance:

```text
1. `uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml` が通る。
2. 入力 artifact の出所が docs に明記される。
3. fixture を作る場合は deterministic で、外部 API / credential に依存しない。
4. backtest を通すためだけに Bitget API や Trade[XYZ] collector を使わない。
```

verification:

```bash
find data/research data/normalized docs/strategy_research_lab/examples -maxdepth 2 -type f \( -name 'feature_panel.parquet' -o -name 'quotes.parquet' -o -name 'venue_cost_matrix.csv' -o -name '*authoring_spec*.yaml' \) -print | sort
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run pytest -q tests/strategy_authoring/test_contracts_validation.py
uv run python scripts/check_current_docs.py
```

destructive_level:

```text
low
```

### T1: Backtest-first の最短実行経路を固定する

goal:

```text
Trade[XYZ] readiness を待たず、既存 public CLI で Strategy Authoring backtest を1回通す再現手順と artifact を固定する。
```

target_files:

```text
docs/backtest/README.md
docs/OPERATIONS_RUNBOOK.md
docs/strategy_research_lab/examples/
data/research/strategy_signals.parquet
data/research/strategy_signals.jsonl
data/research/strategy_signal_manifest.json
data/reports/strategy_backtest_report.md
data/research/strategy_backtest_metrics.json
data/research/strategy_authoring_run.json
```

out_of_scope:

```text
Bitget API 接続
Trade[XYZ] pure backtest public CLI 化
production live order
```

acceptance:

```text
1. `uv run sis strategy-author-run --spec <spec> --through backtest` の実行例が明記されている。
2. 出力 artifact が明記されている。
3. 失敗時に見る validation error / missing input が明記されている。
4. backtest は paper-only で live ready ではないと明記されている。
5. `data/research/strategy_authoring_run.json` の `through` が `backtest` である。
6. `data/research/strategy_backtest_metrics.json` と `data/reports/strategy_backtest_report.md` が生成される。
```

verification:

```bash
uv run sis strategy-author-validate --spec <spec.yaml>
uv run sis strategy-author-run --spec <spec.yaml> --through backtest
uv run pytest -q tests/strategy_authoring
```

destructive_level:

```text
low
```

### T2: venue id を最小限に共通化する

goal:

```text
StrategySignalRecord / TradeCandidate / PaperIntentPreview で execution_venue を trade_xyz 固定から、当面必要な venue enum へ広げる。
```

target_files:

```text
src/sis/research/strategy_lab/specs.py
src/sis/research/strategy_lab/candidates.py
src/sis/research/strategy_lab/paper_intent_preview.py
src/sis/research/strategy_lab/evaluation_plan.py
src/sis/research/strategy_lab/authoring/contracts/spec.py
src/sis/research/strategy_lab/authoring/io.py
src/sis/research/strategy_lab/authoring/compiler/paper_preview.py
src/sis/venues/ids.py
schemas/strategy_signal.v1.schema.json
schemas/trade_candidate.v1.schema.json
schemas/paper_intent_preview.v1.schema.json
tests/strategy_authoring/
```

out_of_scope:

```text
全取引所プラグイン機構
動的 venue registry
live Bitget adapter
```

implementation notes:

```text
候補:
  src/sis/venues/ids.py を新設し、VenueId = Literal["trade_xyz", "bitget_demo"] を定義する。

ただし:
  過度な抽象化を避ける。
  既存 tests の trade_xyz 期待は残す。
  bitget_demo は demo execution 用で、本番 bitget live と混同しない。

必ず修正対象に含めるもの:
  src/sis/research/strategy_lab/specs.py の SymbolBinding / StrategySignalRecord。
  src/sis/research/strategy_lab/candidates.py の TradeCandidate。
  src/sis/research/strategy_lab/paper_intent_preview.py の PaperIntentPreview。
  src/sis/research/strategy_lab/authoring/compiler/paper_preview.py の Literal["trade_xyz"] cast。
  src/sis/research/strategy_lab/evaluation_plan.py の target_venue。
  schemas/strategy_signal.v1.schema.json の execution_venue const。
  schemas/trade_candidate.v1.schema.json / schemas/paper_intent_preview.v1.schema.json の execution_venue schema。

PROXY_REQUIREMENTS:
  XYZ100->QQQ, SP500->SPY は Trade[XYZ] proxy symbol だけに適用する。
  bitget_demo の BTCUSDT などには適用しない。
  ただし proxy validation を削除して既存 Trade[XYZ] guard を弱めない。

schema/model parity:
  Pydantic model と JSON Schema で許可 venue を揃える。
  片方だけ bitget_demo を許す状態を残さない。
```

acceptance:

```text
1. 既存 trade_xyz spec / signal / candidate / paper intent は壊れない。
2. bitget_demo の最小 fixture が validation を通る。
3. schema と Pydantic model の許容 venue が一致する。
4. PaperIntentPreview の安全フラグは維持される。
5. Trade[XYZ] proxy symbol validation は trade_xyz では維持され、bitget_demo では誤適用されない。
6. `paper_preview.py` に trade_xyz 固定 cast が残っていない。
```

verification:

```bash
uv run pytest -q tests/strategy_authoring
uv run pytest -q tests/test_artifact_validation.py
uv run python scripts/check_current_docs.py
```

destructive_level:

```text
low
```

### T3: PaperIntentPreview / paper runner を venue-neutral にする

goal:

```text
PaperIntentPreview を trade_xyz 以外の venue でも paper-only に処理できるようにする。
```

target_files:

```text
src/sis/paper/runner.py
src/sis/paper/broker.py
src/sis/research/strategy_lab/authoring/compiler/paper_preview.py
configs/fee_model.trade_xyz.yaml
configs/fee_model.bitget_demo.yaml
tests/test_paper_from_intents_venue_neutral.py
```

out_of_scope:

```text
Bitget demo order submit
real account balance sync
production live fills
```

implementation notes:

```text
現状:
  paper runner は normalized/quotes.parquet から latest quote を取り、intent.execution_venue / symbol で lookup する。
  fee model は configs/fee_model.trade_xyz.yaml に固定。

変更:
  fee model lookup を venue 別にする。
  venue が bitget_demo の場合も paper-only fill / block ができるようにする。
  quote schema は最低限 venue, canonical_symbol, ts_client, bid/ask/mid/mark, market_status, is_tradable を使う。
  paper-from-intents は intent.execution_venue と intent.execution_symbol / canonical_symbol に合う quote が必要。
  bitget_demo の最初の検証では alias 解決を増やさず、fixture quote 側に bitget_demo の venue と symbol を持たせる。
  alias / symbol mapping は必要になった時に別タスクで追加する。
```

acceptance:

```text
1. trade_xyz paper-from-intents の既存挙動が維持される。
2. bitget_demo intent + fixture quote で paper order / fill / observation ledger が生成される。
3. live_order_submitted=false, wallet_used=false, exchange_write_used=false が維持される。
4. quote missing 時は LATEST_QUOTE_MISSING で block される。
5. quote alias の暗黙フォールバックで別 venue の価格を拾わない。
```

verification:

```bash
uv run pytest -q tests/test_paper_from_intents_venue_neutral.py
uv run sis paper-from-intents --intents-path <fixture-or-generated-intents>
uv run pytest -q tests/strategy_authoring
```

destructive_level:

```text
low
```

### T4a: Bitget API lane を実装前に決める

goal:

```text
Bitget adapter 実装前に、最初に接続する API lane を1つだけ選び、公式 docs から endpoint / auth / permission / rate limit / account type を固定する。
```

target_files:

```text
docs/OPERATIONS_RUNBOOK.md
docs/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md
configs/env.example
.env.example
```

out_of_scope:

```text
adapter 実装
credential 作成
外部 API 実行
demo order submit
```

implementation notes:

```text
選択肢:
  classic demo v2 spot
  classic demo v2 futures
  UTA v3 spot
  UTA v3 USDT futures

2026-06-05_22:48 JST の公式 docs 確認:
  classic demo REST は Demo API Key と paptrading: 1 header が必要。
  classic demo WebSocket は wss://wspap.bitget.com/v2/ws/public と wss://wspap.bitget.com/v2/ws/private。
  UTA v3 は 2026年5月にも changelog 更新があり、classic demo v2 と混ぜて設計しない。

決定時に残す情報:
  lane name
  product type
  REST base/path
  WebSocket endpoint
  required headers
  credential names
  read-only endpoint
  write endpoint
  rate limit
  docs URL
  docs checked timestamp
```

acceptance:

```text
1. first lane が1つだけ選ばれている。
2. docs checked timestamp と公式 docs URL が残っている。
3. adapter 実装で使う endpoint / header / permission が lane ごとに分かる。
4. classic v2 と UTA v3 の endpoint / permission が混ざっていない。
```

verification:

```bash
uv run python scripts/check_current_docs.py
```

destructive_level:

```text
low
```

### T4: Bitget demo adapter の read-only / mock-first contract を作る

goal:

```text
Bitget demo API を本接続する前に、adapter interface、署名境界、request construction、response parsing、safety flags をテストで固定する。
```

target_files:

```text
src/sis/execution/base.py
src/sis/execution/bitget_demo_adapter.py
tests/test_bitget_demo_adapter.py
configs/env.example
.env.example
docs/OPERATIONS_RUNBOOK.md
```

out_of_scope:

```text
本番 Bitget live trading
real money
credential を repo に保存すること
網羅的な Bitget API SDK 実装
```

implementation notes:

```text
前提:
  T4a で選んだ API lane だけを対象にする。
  endpoint / header / path は T4a の docs checked timestamp に紐づける。
  実装中に公式 docs が変わっていた場合は、adapter ではなく T4a の docs を先に更新する。

classic demo v2 を選んだ場合の確認済み前提:
  Demo API Key を使う。
  REST request header に paptrading: 1 を付ける。
  WebSocket public は wss://wspap.bitget.com/v2/ws/public。
  WebSocket private は wss://wspap.bitget.com/v2/ws/private。

最初の adapter:
  read_balance
  estimate_order
  read_order_status
  read_fills
  cancel_order
  healthcheck

submit order:
  最初は mock / dry-run / explicit --execute なしで禁止。
```

acceptance:

```text
1. Credential 未設定時は明示的に unavailable / blocked で止まる。
2. request construction に paptrading: 1 が入る。
3. secret は log / artifact に出ない。
4. demo と live の adapter_name / venue id が混ざらない。
5. mock response で status / fills / cancel の parser test が通る。
```

verification:

```bash
uv run pytest -q tests/test_bitget_demo_adapter.py
uv run ruff check src/sis/execution/bitget_demo_adapter.py tests/test_bitget_demo_adapter.py
uv run ruff format --check src/sis/execution/bitget_demo_adapter.py tests/test_bitget_demo_adapter.py
```

destructive_level:

```text
low
```

### T5: Bitget demo の最小 smoke を opt-in で追加する

goal:

```text
ユーザーが Demo API Key を用意した後だけ、Bitget demo の read-only smoke を実行できるようにする。
```

target_files:

```text
src/sis/commands/
src/sis/execution/bitget_demo_adapter.py
configs/env.example
docs/OPERATIONS_RUNBOOK.md
tests/test_cli_smoke.py
```

out_of_scope:

```text
自動 live/demo order submit
credential 自動生成
KYC 代行
```

acceptance:

```text
1. `uv run sis bitget-demo-smoke --help` が出る。
2. credential 未設定なら exit 2 で明示理由を出す。
3. read-only endpoint の healthcheck / account read だけを行う。
4. order submit は別 flag なしでは実行できない。
```

verification:

```bash
uv run sis bitget-demo-smoke --help
uv run pytest -q tests/test_cli_smoke.py tests/test_bitget_demo_adapter.py
```

destructive_level:

```text
medium
```

notes:

```text
外部 API 接続を含むため medium。
write API はこの task では使わない。
```

### T6: demo order lifecycle を paper と分離して検証する

goal:

```text
backtest / paper で選ばれた intent を、Bitget demo の注文 lifecycle 検証へ進める。ただし production live order とは分ける。
```

target_files:

```text
src/sis/execution/bitget_demo_adapter.py
src/sis/commands/
data/ops/
data/reports/
tests/test_bitget_demo_adapter.py
```

out_of_scope:

```text
自動売買 daemon
real money
live Bitget adapter
複数取引所 best execution
```

acceptance:

```text
1. demo order submit は explicit flag と credential がないと実行できない。
2. submit / status / fill / cancel / close の artifact が残る。
3. paper/backtest の artifact と demo execution artifact が混ざらない。
4. demo execution 成功を live_ready と読まない。
```

verification:

```bash
uv run pytest -q tests/test_bitget_demo_adapter.py
uv run sis execution-snapshot
uv run sis phase-gate-review
```

destructive_level:

```text
high
```

notes:

```text
demo でも外部 write API を使うため high。
ユーザー承認と Demo API Key が必須。
```

## 実装順序

推奨順:

```text
1. T0: Trade[XYZ] collector を停止または自然終了待ちに切り替える。
2. T1: Strategy Authoring backtest の最短実行を固定する。
3. T2: execution_venue の最小 enum 化。
4. T3: paper intent / paper runner の venue-neutral 化。
5. T4: Bitget demo adapter を mock-first で作る。
6. T5: Bitget demo read-only smoke を opt-in 追加する。
7. T6: demo order lifecycle を explicit opt-in で検証する。
```

やってはいけない順:

```text
1. Bitget demo order submit を先に作る。
2. backtest なしで demo trade 成功を進捗扱いする。
3. trade_xyz 固定を場当たり的に string 置換する。
4. paper intent を OrderIntent や live order と同一視する。
5. Trade[XYZ] collector を回し続けながら主目的を backtest-first と書く。
```

## テスト方針

最小テスト:

```bash
uv run pytest -q tests/strategy_authoring
uv run pytest -q tests/backtest
uv run pytest -q tests/test_artifact_validation.py
uv run python scripts/check_current_docs.py
```

変更が paper / execution に入った場合:

```bash
uv run pytest -q tests/test_trade_xyz_live_order_policy.py tests/test_trade_xyz_adapter_safety.py tests/test_micro_live_canary.py
uv run pytest -q tests/test_bitget_demo_adapter.py
uv run pytest -q tests/test_paper_from_intents_venue_neutral.py
```

全体確認:

```bash
./scripts/check
```

外部 API を含む検証:

```text
デフォルトでは実行しない。
ユーザーが Bitget Demo API Key を用意し、明示的に許可した時だけ実行する。
```

## 完了条件

この pivot 計画全体の完了条件:

```text
1. Trade[XYZ] を当面の注文口にしない方針が handoff / docs に残っている。
2. Trade[XYZ] collector が主経路から外れている。
3. `strategy-author-run --through backtest` が最短 backtest 入口として使える。
4. execution_venue が trade_xyz 固定から最小 venue enum へ広がっている。
5. trade_xyz 既存挙動が壊れていない。
6. bitget_demo の paper/demo intent fixture が validation を通る。
7. Bitget demo adapter は credential 未設定で fail-closed する。
8. demo order lifecycle は explicit opt-in なしに外部 write しない。
9. backtest / paper / demo / live の境界が artifact と docs で分かる。
10. `backtest_data_ready` や `live_ready` を未検証のまま true 扱いしない。
```

## 未決事項

実装前に決める必要があるもの:

```text
1. Trade[XYZ] collector を今すぐ止めるか、現在の 24h cycle だけ自然終了まで待つか。
   推奨: 今すぐ止める。

2. 最初の backtest 対象 strategy spec をどれにするか。
   推奨: 既存 template / example を使い、まず1本だけ通す。

3. Bitget demo の対象 product を spot demo にするか futures demo にするか。
   推奨: 最初は order lifecycle が単純な product を選ぶ。詳細は Demo API Key 作成後に公式 docs と account type で確認する。
```

## 現実的な Better 案

最短で目的に近づくための Better 案:

```text
1. Trade[XYZ] collector を止める。
2. その日のうちに Strategy Authoring backtest を1本通す。
3. venue-neutral 化は schema / model / tests の最小範囲にする。
4. Bitget demo は mock-first にして、credential 前でも開発できるようにする。
5. 実 API smoke は read-only から始める。
6. demo order submit は最後に explicit opt-in で追加する。
```

採用しない案:

```text
1. Trade[XYZ] 30日 coverage 完了まで待つ。
2. Bitget demo order submit から始める。
3. 全取引所対応の巨大 plugin system を先に作る。
4. 既存 Trade[XYZ] pure backtest をいきなり汎用化して CLI 公開する。
```

理由:

```text
どれも、現在の目的である「できるだけ早く backtest に入る」から外れる。
```

## 次の一手

実行するなら次は T0。

推奨 command は、実行直前に process / lock を再確認してから決める。

事前確認:

```bash
pgrep -af '[c]ollect_trade_xyz_data_until_ready|[c]ollect_trade_xyz_data_cycle|[c]ollect-trade-xyz-data-cycle|[c]ollect-trade-xyz-quotes' || true
cat .tmp/trade_xyz_data_until_ready.lock/pid 2>/dev/null || true
cat .tmp/trade_xyz_data_cycle.lock/pid 2>/dev/null || true
```

停止後確認:

```bash
pgrep -af '[c]ollect_trade_xyz_data_until_ready|[c]ollect_trade_xyz_data_cycle|[c]ollect-trade-xyz-data-cycle|[c]ollect-trade-xyz-quotes' || true
test ! -e .tmp/trade_xyz_data_until_ready.lock && echo supervisor_lock=absent || true
test ! -e .tmp/trade_xyz_data_cycle.lock && echo cycle_lock=absent || true
```

停止が完了したら、T1 に進む。
