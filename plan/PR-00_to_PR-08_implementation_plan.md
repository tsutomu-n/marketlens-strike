# PR-00 to PR-08 implementation plan

Status: historical. 現行コードでは PR-00〜PR-08 の code/test surface は完了済みであり、この文書は migration contract と実装順序の記録として読む。current status は `docs/CURRENT_STATE.md` と `docs/CODE_STATUS.md` を正とする。

## 結論

このmigrationのゴールは、現行の gTrade / Ostium / QQQ-SPY-XAU 評価基盤を、Trade[XYZ] / Hyperliquid HIP-3 を主venueにした米国株・ETF・株価指数perp向けの read-only collection、real-market tracking、venue-gated paper execution、micro live canary へ段階移行することです。

PR-00〜PR-08は順番固定です。PR-00〜PR-02を飛ばしてTrade[XYZ]実装へ入らないでください。

## Global Done

PR-08完了時点で、次を満たす。

- Python 3.13でCIとlocal checkが通る。
- gTrade / Ostiumはactive pathから外れている。
- Trade[XYZ] universeとHIP-3 asset mappingを保存できる。
- Trade[XYZ] read-only quoteをJSONL/Parquet/DuckDBへ保存できる。
- real market側の15分足featuresを作れる。
- real market price と Trade[XYZ] mark/oracle/mid のtracking reportを作れる。
- venue quality gate付きpaper executionができる。
- micro live canaryで `scheduleCancel -> tiny limit -> cancelByCloid -> reduce-only close` の安全確認ができる。

## Global Stop Conditions

次の場合は実装を止めて、ログ・原因・未解決点を記録する。

- API / schema / auth / env / CI / deploy / DB / 外部副作用の解釈がPR specと衝突する。
- 秘密鍵、API secret、seed phrase、wallet秘密鍵が必要になった。
- PR-08より前にlive write pathが必要になった。
- `scheduleCancel` なしでlive発注する設計になりそうな場合。
- manual signingを導入しないと進められない場合。
- 対象外銘柄をactive registryへ戻す必要が出た場合。

## Common Verification

PR-00ではlocked syncを使う。PR-01以降も、PR-00後のrepoでは原則 `uv sync --dev --locked` を使う。

```bash
uv sync --dev --locked
uv run python -V
uv run ruff check .
uv run pyrefly check
uv run pytest -q
./scripts/check
```

PR-08のlive系テストは標準PR検証に含めない。mock adapter / fake exchange / dry-run policy tests only を標準検証とし、live canaryはmanual preflight後のlocal opt-in専用にする。

Manual live canary only:

```bash
SIS_ENABLE_LIVE_TESTS=1 uv run pytest tests/test_micro_live_canary.py -q
```

## PR-00: Python 3.13 migration

Goal:

- active runtime、CI、lockfile、setup docsをPython 3.13前提へ揃える。

Primary files:

```text
pyproject.toml
.python-version
uv.lock
.github/workflows/ci.yml
scripts/check
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/OPERATIONS_RUNBOOK.md
```

Acceptance:

- `.python-version` is `3.13`
- `pyproject.toml` requires `>=3.13,<3.14`
- Ruff target is `py313`
- pyrefly version is `3.13`
- `uv.lock` is regenerated for Python 3.13
- `scripts/check` logs `uv run python -V`
- `./scripts/check` passes

Detailed plan:

- `plan/PR-00_python_313_migration_plan.md`
- `plan/PR-00_TASK_CHAIN.yaml`

## PR-01: Legacy venue archive

Goal:

- gTrade / Ostiumをactive pathから外し、migration中の参照資料としてarchiveする。

Primary files and moves:

```text
sidecars/gtrade/                    -> archive/legacy_sidecars/gtrade/
sidecars/ostium/                    -> archive/legacy_sidecars/ostium/
src/sis/venues/gtrade/              -> src/sis/venues/archive/gtrade/
src/sis/venues/ostium/              -> src/sis/venues/archive/ostium/
src/sis/execution/gtrade_adapter.py -> src/sis/execution/archive/gtrade_adapter.py
src/sis/execution/ostium_adapter.py -> src/sis/execution/archive/ostium_adapter.py
package.json
pyproject.toml
uv.lock
scripts/check
src/sis/venues/__init__.py
src/sis/execution/__init__.py
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
```

Acceptance:

- active workspace/scriptsから `sidecars/gtrade` と `sidecars/ostium` が消えている。
- active importsから `sis.venues.gtrade` と `sis.venues.ostium` が消えている。
- `ostium-python-sdk` はactive import除去後に削除する。
- `uv.lock` は `ostium-python-sdk` 削除に合わせて更新する。
- `scripts/check` からgTrade / Ostium sidecar checkを外す。
- `./scripts/check` がarchive済みsidecarを参照しない。
- `package.json` にactive `gtrade` / `ostium` scriptが残らない。
- `bun install --frozen-lockfile` が不要なら `scripts/check` からも外す。
- archived files are present and discoverable.
- replacement `tests/test_legacy_archive.py` がactive archive境界を検証する。

PR-01 Bun policy:

```text
package.json から active gtrade/ostium workspace と scripts を外す。
scripts/check から Bun sidecar checks を外す。
bun install --frozen-lockfile が不要になるなら scripts/check からも外す。
Bun lockfile が存在し、package workspace変更で更新が必要な場合のみ lockfile を更新対象に含める。
Trade[XYZ] testはPR-03以降で追加する。
```

Additional verification:

```bash
uv lock --python /usr/bin/python3.13
uv sync --dev --locked
```

No-Go:

- active configに `gtrade` / `ostium` が残る。
- PR-01でTrade[XYZ]実装を始める。

## PR-02: Schema generalization

Goal:

- 旧venue固定schemaを、Trade[XYZ] / Lighter / BitMEX-readonly と equity / ETF / index / basket_index / crypto_beta_equity に対応するv2 schemaへ切り替える。

Primary files:

```text
src/sis/models.py
schemas/instrument_registry.schema.json
schemas/quote_log_v1.schema.json
schemas/quote_log_v2.schema.json
configs/instrument_registry.seed.json
configs/halt_policy.yaml
configs/fee_model.trade_xyz.yaml
configs/real_market_provider_policy.yaml
configs/micro_live_policy.yaml
tests/test_models_schema.py
tests/test_normalize.py
tests/test_halt_policy.py
```

Acceptance:

- `Venue.TRADE_XYZ`, `Venue.LIGHTER`, `Venue.BITMEX_READONLY`, `Venue.LEGACY_GTRADE`, `Venue.LEGACY_OSTIUM` がmodel/schemaに反映される。
- `AssetClass.EQUITY`, `ETF`, `INDEX`, `BASKET_INDEX`, `CRYPTO_BETA_EQUITY`, `UNKNOWN` が反映される。
- `schemas/instrument_registry.schema.json` がTrade[XYZ] seedをacceptする。
- `schemas/quote_log_v2.schema.json` がHIP-3 quote fieldsをacceptする。
- active `configs/instrument_registry.seed.json` に `gtrade`, `ostium`, `XAU` が残らない。

No-Go:

- `commodity` や `XAU` がactive registryに残る。

## PR-03: Trade[XYZ] HIP-3 universe mapping

Goal:

- Trade[XYZ]の対象銘柄をinstrument registryへ取り込み、HIP-3の `dex`, `coin`, `asset_id` mappingを保存する。

Primary files:

```text
src/sis/venues/trade_xyz/__init__.py
src/sis/venues/trade_xyz/client.py
src/sis/venues/trade_xyz/models.py
src/sis/venues/trade_xyz/registry.py
src/sis/venues/trade_xyz/report.py
tests/test_trade_xyz_registry.py
tests/fixtures/trade_xyz_all_mids.sample.json
tests/fixtures/trade_xyz_meta.sample.json
```

Acceptance:

- `data/registry/trade_xyz_instrument_registry.json` が生成できる。
- every active symbol has `venue=trade_xyz`, `dex=xyz`, `coin=xyz:<symbol>`.
- asset id is resolved by `100000 + perp_dex_index * 10000 + index_in_meta` when fields are known.
- unresolved asset mapping is `api_orderable=false`.
- active registry excludes `MSTR`, `COIN`, `CRCL`, `XAU`, `WTI`, `JPY`, `BTC`.
- `data/reports/trade_xyz_universe_report.md` が生成できる。

No-Go:

- `dex` / `coin` / `asset_id` 不明のままorderable扱いにする。

## PR-04: Trade[XYZ] read-only collector

Goal:

- Trade[XYZ] market dataをread-onlyで取得し、既存のraw/normalized storageへ接続する。

Primary files:

```text
src/sis/venues/trade_xyz/collector.py
src/sis/venues/trade_xyz/normalizer.py
src/sis/venues/trade_xyz/quality.py
src/sis/storage/normalize.py
tests/test_trade_xyz_collector.py
tests/test_trade_xyz_normalizer.py
tests/fixtures/trade_xyz_l2_book.sample.json
```

Acceptance:

- fixture dataからv2 quote JSONLを書ける。
- `best_bid`, `best_ask`, `mid_price`, `spread_bps`, `depth_10bps_usd`, `depth_25bps_usd` を計算できる。
- missing book side は `is_tradable=false` になり、raw payloadは保存される。
- `QuoteLog.raw_payload_sha256` is stable for identical payloads.
- `normalize_quotes()` がParquetとDuckDBへ接続できる。

No-Go:

- raw payload hashなし。
- reconnect/gap記録なし。
- live order/write method追加。

## PR-05: Real market data layer

Goal:

- Trade[XYZ]上の出来高を正にせず、米国株/ETF/指数のreal market dataから15分足featuresを作る。

Primary files:

```text
src/sis/real_market/__init__.py
src/sis/real_market/models.py
src/sis/real_market/symbols.py
src/sis/real_market/calendar.py
src/sis/real_market/quality.py
src/sis/real_market/feature_builder.py
src/sis/real_market/providers/__init__.py
src/sis/real_market/providers/alpaca.py
src/sis/real_market/providers/yfinance_provider.py
src/sis/real_market/providers/stooq_provider.py
src/sis/real_market/providers/sec_edgar.py
src/sis/real_market/providers/fred_provider.py
tests/test_real_market_models.py
tests/test_real_market_quality.py
tests/test_real_market_features.py
```

Acceptance:

- `RealMarketBar` and `RealMarketFeature` models exist.
- 15m return, realized volatility, volume z-score, session/event flags can be built.
- source confidence is computed from price, volume, freshness, session, secondary-source agreement.
- `source_confidence < 0.70` blocks live or paper entry.
- `data/reports/free_real_market_data_quality_report.md` が生成できる。

No-Go:

- yfinance単独をlive正データ扱いにする。

## PR-06: Real market vs Trade[XYZ] tracking

Goal:

- real marketを正、Trade[XYZ]を執行窓口として扱えるか判定するtracking layerを作る。

Primary files:

```text
src/sis/tracking/__init__.py
src/sis/tracking/models.py
src/sis/tracking/real_vs_venue.py
src/sis/tracking/lead_lag.py
src/sis/tracking/reports.py
tests/test_tracking_models.py
tests/test_real_vs_venue_tracking.py
tests/test_lead_lag.py
```

Acceptance:

- `mark_real_diff_bps` and `oracle_real_diff_bps` are computed.
- underlying regular session以外ではinitial implementationで `trade_allowed=false`。
- venue quality score is computed from spread/depth/mark diff/source confidence.
- `data/reports/real_market_to_trade_xyz_tracking_report.md` が生成できる。
- report includes per-symbol decisions and block rates.

No-Go:

- 原市場closed中に `trade_allowed=true`。

## PR-07: Paper execution + venue quality gates

Goal:

- Trade[XYZ] v2 quoteとtracking recordを使い、venue quality gate付きpaper executionへ移行する。

Primary files:

```text
src/sis/paper/broker.py
src/sis/paper/runner.py
src/sis/core/execution_plan.py
src/sis/risk/halt_policy.py
src/sis/reports/paper_cycle_history.py
src/sis/reports/operations_dashboard.py
tests/test_paper_trading.py
tests/test_paper_runner.py
tests/test_halt_policy.py
```

Acceptance:

- fill price priority uses best bid/ask first.
- paper fill rejects when tracking, venue quality, source confidence, market status, tradable state, spread/depth/funding gates fail.
- `fee_model.trade_xyz.yaml` is used for fee/cost model.
- paper reports include `source_confidence`, `venue_quality_score`, `block_reasons`, `fee_mode`, `estimated_round_trip_cost_bps`, `fill_price_source`.

No-Go:

- best bid/askなしでmarket fill扱い。

## PR-08: Trade[XYZ] micro live safety adapter

Goal:

- Trade[XYZ]で安全確認用micro live canaryを実行できる最小surfaceを追加する。

Primary files:

```text
src/sis/execution/trade_xyz_adapter.py
src/sis/execution/live_order_policy.py
src/sis/execution/micro_live_canary.py
tests/test_trade_xyz_live_order_policy.py
tests/test_trade_xyz_adapter_safety.py
tests/test_micro_live_canary.py
```

Required live sequence:

```text
load micro_live_policy.yaml
assert enabled=true passed explicitly by CLI flag
assert kill_switch_clear
assert daily_loss_remaining
assert active real market regular session
assert tracking gate pass
read account state using master/subaccount address
scheduleCancel deadline now+300s
place tiny post-only or passive limit order with cloid
query orderStatus by cloid
cancelByCloid if still open
if filled, close via reduceOnly limit
write micro_live_safety_report.md and audit bundle
```

Acceptance:

- policy blocks disabled micro live, missing scheduleCancel, market order, notional above limit.
- canary calls scheduleCancel before order.
- canary cancels by cloid when open.
- filled position close uses reduce-only.
- `data/reports/micro_live_safety_report.md` includes policy/account/action refs.
- standard PR verification uses mock adapter / fake exchange / dry-run policy tests only.

Hard No-Go:

- market order.
- notional > 50 USD.
- leverage > 2.
- opening trade while underlying session not regular.
- opening trade during earnings/macro blackout.
- live order when source_confidence < 0.70.
- live order when venue_quality_score < 0.70.
- live order without scheduleCancel success.

## PR-08 manual preflight

Before any opt-in micro live canary:

```text
PR-00〜PR-07 merged and green
data/reports/real_market_to_trade_xyz_tracking_report.md exists
target symbol is SP500/XYZ100 or explicitly approved NVDA/AAPL/MSFT
source_confidence >= 0.70
venue_quality_score >= 0.70
underlying session is regular
no earnings/macro blackout
kill switch clear
daily loss remaining >= max_notional risk
max_notional_usd <= 50
max_leverage <= 2
scheduleCancel preflight passed
API wallet is fresh and dedicated
account query uses master/subaccount address, not API wallet address
canary command includes explicit confirm flag
```

Manual live canary:

```text
opt-in only
local only
explicit confirm flag required
scheduleCancel preflight required
API wallet dedicated
max_notional_usd <= 50
```

Manual command after preflight only:

```bash
SIS_ENABLE_LIVE_TESTS=1 uv run pytest tests/test_micro_live_canary.py -q
```

## Cross-PR Dependency Order

```text
PR-00 unlocks Python 3.13 CI and reproducible locked sync.
PR-01 removes old active venue paths so new schema does not preserve legacy active assumptions.
PR-02 creates v2 model/schema/config contract used by every later PR.
PR-03 creates registry and mapping needed by collector.
PR-04 creates Trade[XYZ] quote data used by tracking and paper.
PR-05 creates real market features used by tracking.
PR-06 combines PR-04 and PR-05 into trade_allowed and quality decisions.
PR-07 uses PR-06 decisions for paper execution.
PR-08 uses PR-06/PR-07 gates for opt-in micro live safety canary.
```

## What Not To Commit

- secrets
- `.env`
- private keys
- seed phrase
- wallet secrets
- generated data under `data/` unless a specific tracked report is explicitly intended
- rewritten historical evidence under `docs/live_evidence_reports/`
