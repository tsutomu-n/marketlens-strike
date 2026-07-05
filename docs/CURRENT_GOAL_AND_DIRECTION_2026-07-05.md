<!--
作成日: 2026-07-05_11:55 JST
更新日: 2026-07-05_11:55 JST
-->

# Current Goal And Direction 2026-07-05

## 結論

ここから目指すのは、backtest-first / venue-neutral のまま、Crypto Perp と Strategy Idea Candidate の evidence quality を上げることです。

短期の中心は次の5つです。

1. C9 bridge を、候補別の source / blocker / backtest pack validation が追える形で再実行する。
2. Bitget public source refresh と ticker-aware source availability を、local file source として明確に扱う。
3. `crypto-perp-backtest-candidate-pack` を actual cash なしの短期終着点として使う。
4. candidate / event / source ごとに欠損、timestamp、費用、`NO_TRADE` 比較を残し、evidence quality を上げる。
5. Strategy Review / Workbench / NDX gates は判断材料として使い、profit proof や live readiness と混同しない。

これは profit proof、actual cash readiness、tiny-live readiness、live readiness、wallet readiness、signing readiness、exchange-write readiness ではありません。

## 正本

実装の正本は docs ではありません。判断時は次を先に確認します。

- `src/`
- `tests/`
- `schemas/`
- `configs/`
- `scripts/`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `.python-version`
- `uv.lock`
- CLI help: `uv run sis --help`

現在の読み入口は [CURRENT_DOCS_INDEX_2026-07-05.md](CURRENT_DOCS_INDEX_2026-07-05.md) です。

## Current Objective

### 1. Strategy Idea Candidate / C9 Bridge

C9 bridge は、shortlist 済みの strategy idea candidate を candidate-scoped Strategy Authoring spec / suite / bundle / standard backtest pack へ接続する fail-closed 経路です。

現行の実務目標は、全候補を成功扱いにすることではありません。候補ごとに次を残すことです。

- candidate id
- candidate family
- input source path / hash
- export manifest / search ledger hash
- generated authoring / backtest artifacts
- bridge status
- blocker reason
- known gaps

`BRIDGED` は artifact 接続と validation が通ったという意味です。alpha proof、profit proof、paper permission、live permission ではありません。

C9 v0 は対応 family と source mapping に限る経路です。変換不能な candidate は `BLOCKED_*` として止めます。

### 2. Bitget Public Source / Ticker-Aware Source Availability

Bitget public source refresh は public market data を local source root に保存するための入口です。public network を使う時は明示 opt-in が必要です。

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis strategy-idea-candidates-bitget-source-refresh \
  --symbol BTCUSDT \
  --product-type USDT-FUTURES \
  --granularity 5m \
  --limit 200 \
  --out data/strategy_idea_candidates/btc-perp/bitget_public_source
```

ticker-aware source availability は、候補や event が使える source を event / ticker 単位で読むための local-file-only 補助です。欠損 source は 0 埋めせず、欠損として残します。

```bash
uv run sis crypto-perp-source-availability --help
```

この source availability は actual cash source 作成、credentialed read、exchange write、live order を行いません。

### 3. Crypto Perp Backtest Candidate Pack

actual cash なしの Crypto Perp 短期終着点は [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) です。

```bash
uv run sis crypto-perp-backtest-candidate-pack
```

この command は local artifact から timestamp-safe simulation evidence pack を作り、候補を次の4択に分類します。

- `BACKTEST_REJECT`
- `BACKTEST_REVISE`
- `BACKTEST_COLLECT_MORE_DATA`
- `BACKTEST_CANDIDATE_HOLD`

`BACKTEST_PROMOTE_TO_LIVE` はありません。`BACKTEST_CANDIDATE_HOLD` でも、actual cash readiness、tiny-live readiness、paper permission、live readiness は出ません。

### 4. Evidence Quality

次に強くするのは、勝ち筋の物語ではなく evidence quality です。

採用前に見るもの:

- source row count
- source timestamp range
- `available_at` / information cutoff
- missing source
- fee / funding / slippage / operator time
- `REVERSAL_SHORT` / `CONTINUATION_LONG` / `NO_TRADE` の同一 event set 比較
- sample insufficiency
- largest loss / profit concentration
- backtest overfitting risk

`NO_TRADE` は正式 action です。`NO_TRADE` が leader の時に trade action へ手動で差し替えません。

### 5. Strategy Ops / Paper Observation / NDX

Strategy Review、Workbench Viewer、Strategy Case Index、NDX local research gates は、既存 artifact を読むための判断材料です。

これらが作る `READY_FOR_HUMAN_REVIEW`、`PASS`、`READ_ONLY_GO`、`APPROVE_*` は、paper execution、live trading、wallet、signing、exchange write の許可ではありません。

normal paper observation には新しい trading day を含む evidence が必要です。同日 rerun や fill 水増しは normal threshold の代替になりません。

## Stop Conditions

次の場合は進めず、artifact に blocker / known gap として残します。

- candidate family が C9 v0 mapping 対象外。
- source root が無い、読めない、required columns を満たさない。
- ticker / timeframe / horizon に対する quote history が足りない。
- source timestamp が signal cutoff 後にしか存在しない。
- fee / funding / slippage / operator time 後に `NO_TRADE` を上回らない。
- sample size が少なく PBO / rolling stability が評価不能。
- actual cash rows を要求しているのに cash ledger または live measurement artifact が無い。
- credentialed read、paper order、tiny live、live order、wallet、signing、exchange write が必要になる。

## Commands To Inspect

```bash
uv run sis strategy-idea-candidates-bitget-source-refresh --help
uv run sis strategy-idea-candidates-authoring-bridge --help
uv run sis crypto-perp-source-availability --help
uv run sis crypto-perp-backtest-candidate-pack --help
uv run sis strategy-review-build --help
uv run sis strategy-workbench-viewer-build --help
uv run sis research-layer22-validate --help
```

## Not Goals

- profit proof
- actual cash readiness
- tiny-live execution
- live readiness
- account readiness
- wallet readiness
- signing readiness
- exchange-write readiness
- automatic trading daemon
- broad venue enablement
- schema widening without a separate implementation plan
- runtime artifact valueを tracked docs の固定正本にすること

## Verification

固定の pass count はこの文書に置きません。作業時点で次を再実行します。

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
uv run sis --help
./scripts/check
```
