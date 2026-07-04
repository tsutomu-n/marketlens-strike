<!--
作成日: 2026-07-03_10:10 JST
更新日: 2026-07-03_10:10 JST
-->

# Current Repo Facts

## 結論

現repoは、PR #17 の大設計を全部実装する前に、既存pipelineの reality check を作れる状態にある。候補生成、search ledger、Bitget public source refresh、C9 v0 authoring bridge、risk-taker review、actual-cash rows/gate はそれぞれ存在する。ただし、これらを横断して「候補がどこで詰まるか」を1枚で読む artifact はまだ無い。

## PR #17 の位置づけ

PR #17 は docs-only の設計バックログです。Smart Edge Candidate Factory、Multiplicity / Search Accounting、Candidate-to-Backtest Bridge、Backtest Kill Gate、Virtual Execution Gate、Risk-Taker Review、LLM Adversarial Evidence Review、Actual Cash Report Gate の大きな方向を定義している。

ただし、PR #17 は schema、CLI、runtime behavior を実装していない。したがって、PR #17をそのまま上から実装するのではなく、既存pipelineの詰まりを先に測る。

## 実装済みで再利用するもの

### Candidate generation

既存CLI:

```text
strategy-idea-candidates-build
strategy-idea-candidates-ai-packet-build
strategy-idea-candidates-ai-import
strategy-idea-candidates-bitget-source-refresh
strategy-idea-candidates-authoring-bridge
```

主な出力:

```text
strategy_idea_candidate_set.json
search_ledger.jsonl
selection_metrics.json
perp_cost_estimates.json
split_materialization.json
strategy_idea_candidate_export_manifest.json
strategy_idea_candidate_review_packet.json
authoring_preflight.json
```

重要な事実:

- `crypto-perp-risk-taker` profile がある。
- Perp family は複数存在する。
- search ledger は全candidate rowを保存する。
- sealed test non-use が保存される。
- selection-adjusted metrics は入力不足なら `NOT_ESTIMABLE`。
- generated candidate は `UNVERIFIED_CANDIDATE` であり、paper/live permissionではない。

### Bitget public source refresh

既存CLI:

```text
strategy-idea-candidates-bitget-source-refresh
```

役割:

- Bitget public RESTを明示opt-in時だけ読む。
- prep-watchdeck compatible source rootを作る。
- `data/scanner.duckdb`、`data/candles_5m/date=*/candles.parquet`、`var/snapshots/latest.json` を作る。
- credentialsやexchange writeは使わない。

known gap:

- orderbook depthはfetchしない。
- public source refreshはactual cash evidenceではない。

### C9 v0 authoring bridge

既存CLI:

```text
strategy-idea-candidates-authoring-bridge
```

役割:

- shortlisted candidateの一部を candidate-scoped Strategy Authoring spec / suite / bundle / backtest packへ流す。
- prep-watchdeck compatible source rootを読む。
- 変換不能候補は blocker artifact を出す。

既知制約:

```text
SUPPORTED_FAMILIES =
  perp_momentum_continuation
  perp_funding_rate_carry_filter
```

既知blocker:

```text
BLOCKED_UNSUPPORTED_FAMILY_MAPPING
BLOCKED_MISSING_SOURCE_COLUMNS
BLOCKED_NO_SYMBOL_DATA
BLOCKED_UNSUPPORTED_PRODUCT_TYPE
BLOCKED_UNSUPPORTED_SIDE_BIAS
BLOCKED_BACKTEST_PACK
```

重要な誤読リスク:

- `BRIDGED` は technical bridge status。
- `BRIDGED` は economic pass ではない。
- `actual_cash_result_available=false`。
- bridge cost matrixは estimate only。
- generated backtest specは `min_trade_count: 0`、`pass_thresholds: {}` を持つ可能性がある。

### Crypto Perp profit-readiness

既存CLI:

```text
crypto-perp-profit-readiness-inventory
crypto-perp-profit-readiness-plan
crypto-perp-profit-readiness-run-local
crypto-perp-source-availability
crypto-perp-replay-slice
crypto-perp-feature-pack
crypto-perp-edge-score
crypto-perp-tournament-rows-v2
crypto-perp-bias-guard
crypto-perp-risk-taker-review
crypto-perp-cash-ledger
crypto-perp-actual-cash-rows-build
crypto-perp-actual-cash-report-gate
crypto-perp-tournament-gate
crypto-perp-truth-cycle-status
```

重要な事実:

- inventoryは real event / matured outcome が無い場合止める。
- source availabilityは actual cash sourceが無い場合 `can_compute_actual_cash=false` を出す。
- actual cash rowsは cash ledger + explicit assignment からだけ作る。
- preview / estimate / virtual / dogfood は actual cash rowsにしない。
- risk-taker reviewは human-risk-review artifactであり、live permissionではない。

### Tiny-live / virtual周辺

既存状態:

- tiny-live measurementは mock / explicit approval boundary。
- tiny-live shadowは non-order preflight artifact。
- Bitget demo smokeは local/mock-first。
- Bitget demo order lifecycleは未証明。
- Hyperliquid / GRVTは current default path では未対応。

## 現在の最大不確実性

1. 実データでcandidateを作った時、C9 bridgeで何件止まるか。
2. `BRIDGED` になった候補がどの程度 technical-only に留まるか。
3. candidate id / source refs / hash lineage が risk review や actual cash gate まで残るか。
4. actual cash rowsに到達するために何が不足しているか。
5. virtual execution以前に、source / bridge / rows不足で止まるのではないか。

## この sprint が調べること

この sprint は次を調べる。

```text
candidate_count_total
candidate_count_shortlisted
candidate_count_rejected
trial_count_total
bridge_bridged_count
bridge_blocked_count
blocked_reason_counts
blocked_by_family
blocked_by_side_bias
risk_review_status_counts
actual_cash_available_count
candidate_id_lineage_status
fields_missing_for_actual_cash_result_usd
next_single_blocker_to_fix
```

## この sprint が調べないこと

- 新しい市場構造priorの妥当性。
- GA/ML候補生成。
- PBO/DSR/Reality Checkの完全実装。
- demo/testnet PnL。
- production live readiness。

## 判断

現repoは、候補をさらに賢く作る前に、既存候補がどこで詰まるかを測るべき段階です。

したがって、次のPRは Smart Prior Generator ではなく `profit_core_reality_check` です。
