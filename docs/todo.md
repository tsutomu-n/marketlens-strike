結論：**計画を修正します。前回案のままだと一部不足があります。最大の抜けは、gTrade側が `/trading-variables` だけでは「quote window」として不十分な点です。**

`/trading-variables` はspread・fee・OI・市場状態の取得には有効ですが、gTrade公式のv4 pricingでは `m` = mark price、`i` = index price、`t` = timestamp が分離されています。markは実行・TP/SL・PnL、indexは清算に使うため、Go/No-Goのquote evidenceには **v4 pricing websocket / chart snapshot系の価格取得** が必要です。([docs.gains.trade][1])

現状の `src/sis/venues/gtrade/quotes.py` は sidecar payload から `spread_bps`、`oracle_ts_ms`、`market_status`、`is_tradable` は作っていますが、`mark_price` / `index_price` は埋めていません。
したがって、ここからの最短タスクは **gTrade pricing window collector を追加すること**です。

以下はそのまま `docs/NEXT_TASK_PLAN.md` に貼れる粒度です。

---

# MarketLens Strike Next Task Plan

## 0. 目的

```txt
目的:
  Ostium / gTrade を使って、QQQ / SPY / XAU の4h〜3dスイング研究が成立するか判定する。

非目的:
  - 売買Bot化
  - 1m/5m短期スキャルピング
  - 高レバ実弾
  - 新venue追加
  - 個別株対応

現在の状態:
  - 実装は operational
  - Go/No-Go は CONDITIONAL_GO_NEEDS_LIVE_WINDOW
  - 残blockerは stale_rate と tradable_rate
```

Acceptance Audit上も、現在の判定は `CONDITIONAL_GO_NEEDS_LIVE_WINDOW` で、残blockerは `stale_rate` と `tradable_rate` です。 

---

# 1. 修正した全体方針

## 変更前

```txt
gTrade:
  /trading-variables を取得
  sidecar JSONLをPythonでquote log化
  stale/tradable/costを判定
```

## 変更後

```txt
gTrade:
  /trading-variables = pair, spread, fee, OI, market status
  v4 pricing websocket = mark price, index price, timestamp
  両方をmergeして quote_log_v1 を作る

Ostium:
  Builder API /v1/prices = bid/ask/mid/market status
  SDK sidecar = pair metadata, fee, OI, rollover
```

## 理由

gTrade公式は、v4 pricing APIでmark/indexを分離し、markは実行・TP/SL・PnL、indexは清算専用と説明しています。v4 websocketのmessage formatも `m`, `i`, `t` として示されています。([docs.gains.trade][1])
一方で `/trading-variables` は、取引管理に必要な主要データを取得するendpointであり、SDKの正規化にも使いますが、rate limitがあり、必要以上にfetchしないことが推奨されています。([docs.gains.trade][2])

---

# 2. 優先順位つきタスク

## Task 0: 現状baseline再確認

### 目的

開発開始前に、現在の正常状態を固定する。

### 使うもの

```txt
uv
bun
ruff
pytest
既存Acceptance Audit
```

### 作業

```bash
uv run pytest
uv run ruff check .

cd sidecars/gtrade
bun run typecheck
bun test

cd ../ostium
bun run typecheck
bun test
```

### Done

```txt
- pytestが通る
- ruffが通る
- gTrade sidecar typecheck/testが通る
- Ostium sidecar typecheck/testが通る
```

Acceptance Auditでは、これらは既に通過済みとして記録されています。

---

## Task 1: Justfile追加

### 目的

長いコマンド列を固定し、個人開発時の手打ちミスをなくす。

### 使うもの

```txt
OSS:
  casey/just
```

`just` はコマンドランナーとして使えます。([GitHub][3])

### 追加ファイル

```txt
Justfile
```

### 内容

```makefile
set shell := ["bash", "-cu"]

check:
    uv run ruff check .
    uv run pytest
    cd sidecars/gtrade && bun run typecheck && bun test
    cd sidecars/ostium && bun run typecheck && bun test

probe-gtrade-vars:
    cd sidecars/gtrade && bun run probe

probe-ostium:
    cd sidecars/ostium && bun run probe:pairs
    uv run sis probe ostium --read-only-live

refresh-gtrade-once:
    cd sidecars/gtrade && bun run probe
    uv run sis log-quotes --venue gtrade --replace
    uv run sis normalize-quotes
    uv run sis build-cost-matrix
    uv run sis build-backtest
    uv run sis check-go-no-go
    uv run sis build-evidence-card

status:
    uv run sis implementation-status
    uv run sis check-go-no-go
```

### 受け入れ条件

```bash
just check
just probe-gtrade-vars
just probe-ostium
just refresh-gtrade-once
just status
```

---

## Task 2: GitHub Actions CI追加

### 目的

個人開発でも、push時に破壊的変更を検出する。

### 使うもの

```txt
actions/checkout
astral-sh/setup-uv
oven-sh/setup-bun
```

`astral-sh/setup-uv` はGitHub ActionsでuvをセットアップするためのActionです。([GitHub][4])
`oven-sh/setup-bun` はGitHub ActionsでBunをセットアップするためのActionです。([GitHub][5])

### 追加ファイル

```txt
.github/workflows/ci.yml
```

### 内容

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run pytest

  sidecars:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2

      - name: gTrade sidecar
        run: |
          cd sidecars/gtrade
          bun install
          bun run typecheck
          bun test

      - name: Ostium sidecar
        run: |
          cd sidecars/ostium
          bun install
          bun run typecheck
          bun test
```

### Done

```txt
- GitHub Actionsがpush時に動く
- Python test/lintが通る
- gTrade sidecar test/typecheckが通る
- Ostium sidecar test/typecheckが通る
```

---

## Task 3: gTrade v4 pricing collector追加

### 目的

gTradeの `mark_price` / `index_price` / `timestamp` を取得する。

これは最重要タスクです。
現在のquote conversionは `mark_price` / `index_price` を埋めていません。

### 使うもの

```txt
TypeScript
Bun
@gainsnetwork/sdk
WebSocket
gTrade v4 pricing endpoint
```

gTrade公式ドキュメントでは、v4 pricing websocketは `wss://backend-pricing.eu.gains.trade/v4` と示され、messageに `m`、`i`、`t` が含まれます。([docs.gains.trade][1])

### 追加ファイル

```txt
sidecars/gtrade/src/pricing_ws.ts
sidecars/gtrade/src/pricing_collector.ts
sidecars/gtrade/src/pricing_parser.ts
sidecars/gtrade/src/pricing_collector.test.ts
```

### 出力先

```txt
data/raw/sidecar/gtrade-pricing/YYYY-MM-DD.jsonl
```

### JSONL例

```json
{
  "ts_client": "2026-05-22T22:45:00.000Z",
  "venue": "gtrade",
  "source": "gtrade_pricing_v4",
  "network": "arbitrum",
  "prices": [
    {
      "canonical_symbol": "SPY",
      "venue_symbol": "SPY/USD",
      "pair_index": 86,
      "mark_price": 512.34,
      "index_price": 512.34
    },
    {
      "canonical_symbol": "QQQ",
      "venue_symbol": "QQQ/USD",
      "pair_index": 87,
      "mark_price": 443.21,
      "index_price": 443.21
    },
    {
      "canonical_symbol": "XAU",
      "venue_symbol": "XAU/USD",
      "pair_index": 90,
      "mark_price": 2365.12,
      "index_price": 2365.12
    }
  ],
  "oracle_ts_ms": 1779457500000,
  "raw_payload_sha256": "..."
}
```

### 実装要点

```txt
1. WebSocketへ接続
2. 受信payloadの m / i / t をparse
3. pairIndex 86 / 87 / 90 だけ抽出
4. mark/indexをcanonical_symbolへmap
5. JSONLへappend
6. reconnect処理を入れる
7. 最低限、duration/intervalまたはmax-messagesで終了可能にする
```

### CLI案

```bash
cd sidecars/gtrade
bun run pricing:collect -- --duration-minutes 60
```

### package.json追加

```json
{
  "scripts": {
    "pricing:collect": "tsx src/pricing_collector.ts",
    "pricing:test": "bun test src/pricing_collector.test.ts"
  }
}
```

### Done

```txt
- SPY/QQQ/XAUのmark/indexがJSONLに保存される
- v4 timestampがoracle_ts_msとして保存される
- marketが閉じていても、取得可能なら保存する
- reconnect時にプロセスが落ちない
- test fixtureでm/i/tのparseが検証される
```

---

## Task 4: gTrade window collector追加

### 目的

`quote window` を実際に作る。
現状の refresh command は1回probeに近く、window evidenceとして弱いです。Acceptance Auditのrefresh commandも、単発の `bun run gtrade:probe` から始まっています。

### 使うもの

```txt
gTrade trading-variables sidecar
gTrade pricing collector
Bun
```

### 追加ファイル

```txt
sidecars/gtrade/src/collect_window.ts
```

### CLI案

```bash
cd sidecars/gtrade
bun run collect:window -- --duration-minutes 120 --metadata-interval-seconds 60
```

### 処理内容

```txt
1. pricing websocketを常時購読
2. /trading-variables を60秒ごとに取得
3. pricing payload と trading variables snapshot をそれぞれJSONL保存
4. duration経過で終了
```

### 出力

```txt
data/raw/sidecar/gtrade-pricing/YYYY-MM-DD.jsonl
data/raw/sidecar/gtrade/YYYY-MM-DD.jsonl
```

### Done

```txt
- 60分以上のwindowを保存できる
- pricing rowsが複数行になる
- trading-variables rowsが複数行になる
- 取得中断時にも既存行は残る
```

---

## Task 5: Python側でpricing sidecarをQuoteLogへ統合

### 目的

`mark_price` / `index_price` を `QuoteLog` へ入れる。

### 変更ファイル

```txt
src/sis/venues/gtrade/quotes.py
src/sis/cli.py
tests/test_gtrade_pricing_ingestion.py
```

### 現状

`convert_sidecar_to_quote_logs()` は、`spread_bps`、`oracle_ts_ms`、`market_status`、`is_tradable` を作りますが、`mark_price` / `index_price` を設定していません。

### 追加仕様

```bash
uv run sis log-quotes --venue gtrade --replace
```

実行時に、以下の2つをmergeする。

```txt
data/raw/sidecar/gtrade/YYYY-MM-DD.jsonl
data/raw/sidecar/gtrade-pricing/YYYY-MM-DD.jsonl
```

### merge rule

```txt
key:
  pair_index
  nearest pricing oracle_ts_ms
  nearest metadata ts_client

許容差:
  pricingとmetadataの差 <= 60秒
```

### QuoteLogへ入れる値

```txt
mark_price
index_price
exec_buy_price = mark_price
exec_sell_price = mark_price
oracle_ts_ms = pricing t
spread_bps = tradingVariables spreadP
market_status = tradingVariables isIndicesOpen / isCommoditiesOpen
is_tradable = market_status == OPEN
```

### Done

```txt
- data/raw/quotes/gtrade/YYYY-MM-DD.jsonl にmark/indexが入る
- normalize後のquotes.parquetにmark/indexが入る
- build-backtestでstale_rejectedが不自然に増えない
```

---

## Task 6: market-session / next-live-window CLI追加

### 目的

開場まで待つ時間と、取得すべきwindowを機械的に表示する。

### 使うもの

```txt
exchange_calendars
zoneinfo
```

`exchange_calendars` は取引所カレンダーライブラリです。([GitHub][6])

### 注意点

```txt
QQQ/SPY:
  XNYS calendarを使う

XAU:
  XNYSではない
  gTrade commodity session configを手書きする
```

ここは重要です。
XAUをXNYSで判定するのは誤りです。

### 追加ファイル

```txt
src/sis/market_calendar.py
tests/test_market_calendar.py
```

### CLI

```bash
uv run sis market-session --venue gtrade --symbol QQQ
uv run sis next-live-window --venue gtrade --symbol QQQ
uv run sis next-live-window --venue gtrade --symbol XAU
```

### 出力例

```txt
symbol=QQQ
venue=gtrade
calendar=XNYS
now_jst=2026-05-22T21:10:00+09:00
market_status=PRE_OPEN
next_open_jst=2026-05-22T22:30:00+09:00
next_close_jst=2026-05-23T05:00:00+09:00
recommended_start_jst=2026-05-22T22:45:00+09:00
recommended_end_jst=2026-05-23T04:30:00+09:00
```

### ルール

```txt
QQQ/SPY:
  open後15分は避ける
  close前30分は避ける

XAU:
  daily break前10分は避ける
  daily break後10分は避ける
  weekend closeを避ける
```

### Done

```txt
- QQQ/SPYはXNYSで次windowを出す
- XAUはcommodity configで次windowを出す
- JSTで表示される
- DSTに対応する
```

---

## Task 7: stale/tradable診断CLI追加

### 目的

Go/No-Goで落ちたときに、原因を即座に切り分ける。

### 追加ファイル

```txt
src/sis/reports/quote_diagnostics.py
tests/test_quote_diagnostics.py
```

### CLI

```bash
uv run sis diagnose-quotes
uv run sis diagnose-quotes --venue gtrade --symbol QQQ
```

### 出力例

```txt
venue=gtrade symbol=QQQ
rows=120
market_open_rows=110
tradable_rate=0.9167
stale_rate=0.0083
missing_mark_price=0
missing_index_price=0
spread_p90_bps=1.4
oracle_age_p50_ms=850
oracle_age_p90_ms=1800
decision=PASS
```

### 診断項目

```txt
rows
tradable_rate
stale_rate
missing_mark_price_rate
missing_index_price_rate
missing_spread_rate
oracle_age_p50_ms
oracle_age_p90_ms
spread_p50_bps
spread_p90_bps
```

### Done

```txt
- Go/No-Goが落ちた理由を個別に表示できる
- stale原因が「古いtimestamp」か「missing timestamp」か分かる
- tradable原因が「閉場」か「market_status unknown」か分かる
```

---

## Task 8: HTTP mock / fixture test追加

### 目的

外部APIに依存せず、parserとnormalizerをテストする。

### 使うもの

```txt
pytest-httpx
vcrpy
```

`pytest-httpx` はHTTPX requestに対してfixtureでmock responseを返せるライブラリです。([GitHub][7])

### 追加依存

```bash
uv add --dev pytest-httpx vcrpy
```

### 追加ファイル

```txt
tests/fixtures/gtrade_pricing_v4.sample.json
tests/fixtures/gtrade_trading_variables.sample.json
tests/fixtures/ostium_prices.sample.json

tests/test_gtrade_pricing_parser.py
tests/test_gtrade_sidecar_contract.py
tests/test_ostium_probe_http.py
```

### Done

```txt
- gTrade v4 m/i/t fixtureからmark/indexを抽出できる
- gTrade tradingVariables fixtureからspread/market_statusを抽出できる
- Ostium /v1/prices fixtureからbid/ask/mid/spreadを抽出できる
- CI上で外部APIなしに通る
```

---

## Task 9: Artifact validation CLI追加

### 目的

生成物のschema不整合を検出する。

### 使うもの

```txt
jsonschema
既存schemas/*.schema.json
```

### 追加ファイル

```txt
src/sis/validation/artifacts.py
tests/test_artifact_validation.py
```

### CLI

```bash
uv run sis validate-artifacts
uv run sis validate-artifacts --strict
```

### 検証対象

```txt
data/registry/gtrade_instrument_registry.json
data/registry/ostium_instrument_registry.json
data/raw/quotes/gtrade/*.jsonl
data/raw/quotes/ostium/*.jsonl
data/research/backtest_metrics.json
data/evidence/evidence_card_*.json
```

### Done

```txt
- 正常artifactはPASS
- schema違反はexit code 2
- CIに組み込める
```

---

## Task 10: backtest bridgeのcost_matrix連携強化

### 目的

backtestが `venue_cost_matrix.csv` を使うようにする。

### 現状リスク

現状のbacktest bridgeは、gTradeなら固定10bps + quote spread、Ostiumならspread中心です。これはMVPとしてはよいですが、holding costやrolloverを十分反映していません。

### 変更ファイル

```txt
src/sis/backtest/costs.py
src/sis/backtest/bridge.py
tests/test_backtest_cost_matrix.py
```

### 実装

```python
def load_cost_profiles(path: Path) -> dict[tuple[str, str], CostProfile]:
    ...

def round_trip_cost_bps(
    *,
    venue: str,
    symbol: str,
    holding_horizon: str,
    quote_spread_bps: float | None,
    cost_profiles: dict[tuple[str, str], CostProfile],
) -> float:
    ...
```

### 優先順位

```txt
spread:
  1. quote row live spread_bps
  2. cost_matrix spread_p90_bps
  3. cost_matrix spread_p50_bps
  4. fallback 0

holding:
  4h -> holding_cost_4h_bps
  1d -> holding_cost_24h_bps
  3d -> holding_cost_72h_bps
```

### Done

```txt
- build-backtestがvenue_cost_matrix.csvを参照する
- cost sourceがreportに出る
- cost_matrixが存在しない場合でもfallbackで動く
```

---

## Task 11: live evidence runbook作成

### 目的

市場開場後に、誰が見ても同じ手順でquote windowを取得できるようにする。

### 追加ファイル

```txt
docs/LIVE_EVIDENCE_RUNBOOK.md
scripts/refresh_live_evidence.sh
scripts/refresh_live_evidence.ps1
```

### Runbook構成

```md
# Live Evidence Runbook

## 目的
gTrade tradable session中にquote windowを取得し、stale_rate/tradable_rate blockerを解消する。

## 実行前確認
- just check
- sis next-live-window --venue gtrade --symbol QQQ
- CI passing

## 実行
just collect-gtrade-window
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis diagnose-quotes
uv run sis check-go-no-go
uv run sis build-evidence-card

## 判定
GO / CONDITIONAL_GO / NO_GO の条件を書く
```

### Done

```txt
- 開場後に迷わず実行できる
- 生成物が明記されている
- blocker別の対応が明記されている
```

---

# 3. 実行順

## 開場前にやる

```txt
1. Task 1: Justfile
2. Task 2: CI
3. Task 3: gTrade v4 pricing collector
4. Task 4: gTrade window collector
5. Task 5: pricing sidecar -> QuoteLog統合
6. Task 6: market-session / next-live-window CLI
7. Task 7: diagnose-quotes CLI
8. Task 8: HTTP mock tests
9. Task 9: artifact validation
10. Task 10: backtest cost integration
11. Task 11: runbook
```

## 開場後にやる

```txt
1. sis next-live-window --venue gtrade --symbol QQQ
2. gTrade window collectorを推奨windowで実行
3. log-quotes
4. normalize
5. build-cost-matrix
6. diagnose-quotes
7. build-backtest
8. check-go-no-go
9. build-evidence-card
```

---

# 4. 修正したGo/No-Go条件

## GO

```txt
- gTrade pricing v4でSPY/QQQ/XAUのmark/indexが取れる
- /trading-variablesでspread/fee/market_statusが取れる
- QuoteLogにmark_price/index_price/spread_bps/oracle_ts_ms/is_tradableが入る
- stale_rate <= threshold
- tradable_rate >= threshold
- 4h/1d/3d backtestがcost_matrix反映後も成立
- 短期スキャルピングなしで成立
```

## CONDITIONAL_GO

```txt
- 実装は通る
- 価格も取れる
- ただしlive window不足、または市場時間外取得でtradable_rate未達
```

## NO_GO

```txt
- mark/indexが取れない
- pricing websocketが安定しない
- market_statusが不明のまま
- stale_rateが改善しない
- tradable_rateが開場中でも改善しない
- 4h〜3dでcost控除後の期待値が残らない
```

---

# 5. 抜け・漏れ・誤謬リスクの修正

## 修正1: `/trading-variables` だけではquoteとして不十分

`/trading-variables` は必要ですが、mark/index価格のためにgTrade v4 pricingを追加します。公式docsもmark/index分離を説明しています。([docs.gains.trade][1])

## 修正2: 単発probeではquote windowではない

Acceptance Auditのrefresh commandは単発probe起点です。
今後は `collect-window` で連続サンプリングします。

## 修正3: QQQ/SPYとXAUの市場時間を同じ扱いにしない

QQQ/SPYはXNYSでよいですが、XAUはcommodity session configを使います。
`exchange_calendars` は株式市場カレンダー判定に使い、XAUには手書きsession configを用意します。

## 修正4: stale_rateの原因を分解する

単にstaleとだけ出すのではなく、以下を分けます。

```txt
- oracle_ts_ms missing
- oracle_ts_ms old
- pricing timestamp old
- sidecar timestamp old
- market_status unknown
```

## 修正5: backtest bridgeはまだ戦略検証ではない

現状のbacktest bridgeはpipeline smoke testに近いです。
signal CSVを入れるまでは「優位性あり」とは判断しません。

---

# 6. 使うもの一覧

| 目的              | 使うもの                                       | 理由                          |
| --------------- | ------------------------------------------ | --------------------------- |
| タスク実行           | `just`                                     | 個人開発の長いコマンドを固定              |
| CI              | `astral-sh/setup-uv`                       | uv前提のPython検証               |
| CI              | `oven-sh/setup-bun`                        | Bun sidecar検証               |
| gTrade価格        | v4 pricing websocket                       | mark/index/timestamp取得      |
| gTrade metadata | `/trading-variables` + `@gainsnetwork/sdk` | spread/fee/OI/market status |
| 市場時間            | `exchange_calendars`                       | QQQ/SPYのXNYS判定              |
| HTTP mock       | `pytest-httpx`                             | Ostium httpx probeのテスト      |
| API録画           | `vcrpy`                                    | payload回帰テスト                |
| schema検証        | `jsonschema`                               | artifact validation         |
| 保存/分析           | Polars / DuckDB / Parquet                  | 既存方針継続                      |

---

# 7. コーダーへの最初の指示

```md
# 最初に実装する順番

1. Justfileを追加する
2. GitHub Actions CIを追加する
3. gTrade v4 pricing collectorを追加する
4. gTrade collect-windowを追加する
5. Python側でpricing JSONLとtrading-variables JSONLをmergeしてQuoteLog化する
6. market-session / next-live-window CLIを追加する
7. diagnose-quotes CLIを追加する
8. HTTP mock testsを追加する
9. artifact validation CLIを追加する
10. backtest bridgeにvenue_cost_matrix.csvを反映する
11. LIVE_EVIDENCE_RUNBOOK.mdを作る

最重要Done:
- SPY/QQQ/XAUのmark_price/index_priceがquotes.parquetに入る
- tradable session中に60分以上のwindowを収集できる
- diagnose-quotesでstale_rate/tradable_rateを表示できる
- check-go-no-goがCONDITIONAL_GO_NEEDS_LIVE_WINDOWから次の判断へ進む
```

---

# 8. 最終判断

**前回計画は70〜80点でした。今回の修正版は、gTrade v4 pricingと連続window収集を追加したので、目的に対してかなり近くなっています。**

次にやるべき最重要タスクはこれです。

```txt
1. gTrade v4 pricing collector
2. gTrade collect-window
3. pricing + tradingVariables merge
4. market-session CLI
5. diagnose-quotes
```

これを入れれば、開場後に `tradable_rate` と `stale_rate` を実測で潰せます。

[1]: https://docs.gains.trade/developer/integrators/guides/mark-%2B-index-introduction "Mark + Index Introduction | Gains Network"
[2]: https://docs.gains.trade/developer/integrators/backend "Backend | Gains Network"
[3]: https://github.com/casey/just "GitHub - casey/just:  Just a command runner · GitHub"
[4]: https://github.com/astral-sh/setup-uv "GitHub - astral-sh/setup-uv: Set up your GitHub Actions workflow with a specific version of https://docs.astral.sh/uv/ · GitHub"
[5]: https://github.com/oven-sh/setup-bun "GitHub - oven-sh/setup-bun: Set up your GitHub Actions workflow with a specific version of Bun · GitHub"
[6]: https://github.com/gerrymanoim/exchange_calendars "GitHub - gerrymanoim/exchange_calendars: Calendars for various securities exchanges. · GitHub"
[7]: https://github.com/Colin-b/pytest_httpx "GitHub - Colin-b/pytest_httpx: pytest fixture to mock HTTPX · GitHub"
