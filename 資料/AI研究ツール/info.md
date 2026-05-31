結論：**再開して、Trade[XYZ]専用 Pure Backtest Engine v0.1 の最初のパッチを作りました。**
実装範囲は、Repo資料の方針どおり **既存 `build-backtest` / `bridge.py` を壊さず、CLI公開もせず、tests中心で `accounting / no-lookahead / cost / fill` を先に固定するスライス**です。

## 成果物

* [適用用パッチ](sandbox:/mnt/data/trade_xyz_backtest_engine_v0_1_apply.patch)
* [パッチ＋overlay ZIP](sandbox:/mnt/data/trade_xyz_backtest_engine_v0_1_resume_delivery.zip)

## 今回実装した範囲

追加したモジュール：

```txt
src/sis/backtest/engine/__init__.py
src/sis/backtest/engine/order.py
src/sis/backtest/engine/fill.py
src/sis/backtest/engine/portfolio.py
src/sis/backtest/engine/runner.py

src/sis/backtest/trade_xyz/__init__.py
src/sis/backtest/trade_xyz/schema.py
src/sis/backtest/trade_xyz/cost_model.py
```

追加したテスト：

```txt
tests/backtest/test_trade_xyz_schema.py
tests/backtest/test_trade_xyz_cost_model.py
tests/backtest/test_fill_model.py
tests/backtest/test_portfolio_accounting.py
tests/backtest/test_no_lookahead.py
```

## 実装方針

今回のパッチは、Trade[XYZ]専用の純粋バックテスト基盤の最初のsliceです。既存の `src/sis/backtest/bridge.py` はStrategy Lab / paper-only compatibility surfaceとして温存し、新 engine は wallet / signing / exchange write を持たない別contractとして開始する方針に合わせています。

MVPは、資料で決めていた `SP500 long-only / single-symbol / market-like fill / deterministic fixture first / nullable funding / fee_model.trade_xyz.yaml経由 / CLI未公開` の範囲に閉じています。

## 実装した主要セマンティクス

* signal timestamp は **bar close decision** として扱う
* fill は必ず `row.ts > signal.ts` の次のexecutable rowで行う
* 同じrowのfuture情報でfillしない
* long entryのfill価格優先順：

  * `exec_buy_price`
  * `best_ask`
  * `ask_price`
  * `mid_price + half spread`
* long exitのfill価格優先順：

  * `exec_sell_price`
  * `best_bid`
  * `bid_price`
  * `mid_price - half spread`
* `fill_price_source` を必ず記録
* `is_tradable=false` は新規entry不可
* `block_reasons` 非空は新規entry不可
* row resolved feeを優先
* feeがrowで解決できない場合は `configs/fee_model.trade_xyz.yaml` をfallbackに使う
* `fee_mode=unknown` かつfee未解決ならentry不可
* `funding_rate=None` は許容し、MVPでは funding impact = 0
* non-null fundingは **fixtureで明示されたdirect period rate** としてのみ扱い、年率化・時間按分はしない

このあたりは、資料上のstop conditionである「fee unknownでentryできてしまう」「funding単位を推測する」「same-row future informationでfillする」を潰すための実装です。

## 検証結果

sandbox内で、アップロードされたRepo ZIPにパッチを当てて検証しました。

実行したコマンド：

```bash
git apply --check /mnt/data/trade_xyz_backtest_engine_v0_1_apply.patch
git apply /mnt/data/trade_xyz_backtest_engine_v0_1_apply.patch

uv run ruff check src/sis/backtest/engine src/sis/backtest/trade_xyz tests/backtest
uv run pytest -q tests/backtest tests/test_backtest_fixed_horizon.py tests/test_backtest_bridge.py
uv run pyrefly check src/sis/backtest/engine src/sis/backtest/trade_xyz
```

結果：

```txt
git apply --check: passed
ruff: All checks passed
pytest selected: 27 passed
pyrefly: 0 errors
```

フルテスト全体は今回の完了条件にしていません。対象sliceは、既存bridge互換テストと新規backtest testsに限定して検証しました。

## 適用手順

```bash
cd /home/tn/projects/marketlens-strike
git checkout feature/backtest-engine-roadmap

git apply /path/to/trade_xyz_backtest_engine_v0_1_apply.patch

uv run ruff check src/sis/backtest/engine src/sis/backtest/trade_xyz tests/backtest
uv run pytest -q tests/backtest tests/test_backtest_fixed_horizon.py tests/test_backtest_bridge.py
uv run pyrefly check src/sis/backtest/engine src/sis/backtest/trade_xyz
```

## まだ入れていないもの

以下は意図的に入れていません。

```txt
public CLI
live order
wallet
signing
exchange write
nonce
cloid lifecycle
cancel / modify
orderUpdates / userFills ingestion
kill switch
MT5
IC Markets
CFD
short
multi-symbol
limit / stop
partial fill
L2 replay
sweep-depth
artifact writer
```

資料上でも、MVP backtestにはlive execution系を入れず、CLI公開はcontracts安定後に回す設計になっています。

## 次に作るべきslice

次は **PR-6: Metrics and report artifacts** が妥当です。

追加対象：

```txt
src/sis/backtest/engine/metrics.py
src/sis/backtest/engine/artifacts.py
tests/backtest/test_backtest_artifacts.py
```

出力候補：

```txt
backtest_run.json
orders.parquet
fills.parquet
equity_curve.parquet
metrics.json
candidate_result.json
data_manifest.json
config_hash.txt
backtest_report.md
```

このsliceで、`no_live_order=true`、`wallet_used=false`、`exchange_write_used=false` をartifact metadataとして固定するのが次の実務的な一手です。出力artifact contractは資料側でもMVP必須項目として整理されています。

14:01:12.(05/31)
