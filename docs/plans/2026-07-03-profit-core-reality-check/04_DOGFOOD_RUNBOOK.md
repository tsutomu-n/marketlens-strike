<!--
作成日: 2026-07-03_10:10 JST
更新日: 2026-07-03_18:11 JST
-->

# Dogfood Runbook

## 結論

最初のdogfoodは利益検証ではない。BTCUSDT / ETHUSDT の小さなrunで、既存pipelineがどこで止まるかを確認する。

## 前提

- network accessは明示opt-in時だけ。
- credentialsは使わない。
- exchange writeは使わない。
- runtime outputは `data/` 配下に置く。
- tracked docsには固定結果やpass countを書かない。

## 対象

```text
symbols: BTCUSDT, ETHUSDT
timeframe: 5m
product_type: USDT-FUTURES
candidate_cap: 250
shortlist_count: 25
```

最初からSOL、DOGE、meme銘柄、複数venueには広げない。

## Step 0: Working tree確認

```bash
git status --short
uv run python -V
uv run sis --help
```

未commit変更がある場合は、dogfood結果と混ぜない。

## Step 1: Public source refresh

明示opt-inでBitget public source rootを作る。

```bash
uv run sis strategy-idea-candidates-bitget-source-refresh \
  --symbol BTCUSDT \
  --symbol ETHUSDT \
  --product-type USDT-FUTURES \
  --granularity 5m \
  --limit 500 \
  --network \
  --out data/profit_core_reality_check/source_refresh/btc_eth_5m
```

確認:

```text
network_attempted=true
credentials_used=false
exchange_write_used=false
live_order_submitted=false
status=pass
source_root=...
known_gap_count=...
```

失敗時:

```text
public_network_opt_in_required -> --network または SIS_ALLOW_PUBLIC_NETWORK=1 を確認
contracts=0 -> symbol/product type確認
tickers_snapshot=0 -> public source不備
candles_5m=0 -> history candles不備
```

## Step 2: Input contract / validationを用意

既存のinput contract作成手順がある場合はそれを使う。無い場合、dogfood用に source root から最小source file / hash を作る。重要なのは、source path、sha256、available_at、max_observed_timestamp が validation artifactに残ることです。

このrunbookでは具体的な生成CLIを増やさない。既存 `strategy-input-contract-validate` を使う。

```bash
uv run sis strategy-input-contract-validate \
  --contract data/profit_core_reality_check/inputs/btc_eth_5m/strategy_input_contract.json \
  --out data/profit_core_reality_check/inputs/btc_eth_5m
```

確認:

```text
validation_status=PASS
source hash present
available_at present
max_observed_timestamp present
```

失敗時は候補生成へ進まない。

## Step 3: Candidate generation

```bash
uv run sis strategy-idea-candidates-build \
  --contract data/profit_core_reality_check/inputs/btc_eth_5m/strategy_input_contract.json \
  --validation data/profit_core_reality_check/inputs/btc_eth_5m/strategy_input_contract_validation.json \
  --profile crypto-perp-risk-taker \
  --candidate-cap 250 \
  --shortlist-count 25 \
  --out data/profit_core_reality_check/candidates/btc_eth_5m
```

確認するartifact:

```text
strategy_idea_candidate_set.json
search_ledger.jsonl
selection_metrics.json
perp_cost_estimates.json
split_materialization.json
review/strategy_idea_candidate_review_packet.json
authoring_preflight.json
exported_strategy_ideas/strategy_idea_candidate_export_manifest.json
```

確認する数字:

```text
candidate_count_total
candidate_count_shortlisted
candidate_count_rejected
trial_count_total
cap_rejection_count
duplicate_rejection_count
selection_adjusted_metrics_status_counts
```

ここでcandidateが少なくても失敗ではない。search ledgerが無い、selected-only、sealed test used なら失敗。

## Step 4: C9 bridge

```bash
uv run sis strategy-idea-candidates-authoring-bridge \
  --candidate-set data/profit_core_reality_check/candidates/btc_eth_5m/strategy_idea_candidate_set.json \
  --export-manifest data/profit_core_reality_check/candidates/btc_eth_5m/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json \
  --ledger data/profit_core_reality_check/candidates/btc_eth_5m/search_ledger.jsonl \
  --prep-watchdeck-root data/profit_core_reality_check/source_refresh/btc_eth_5m/source_root \
  --out data/profit_core_reality_check/authoring_bridge/btc_eth_5m
```

確認するartifact:

```text
strategy_idea_candidate_authoring_bridge_manifest.json
<candidate_id>/bridge_blocker.json
<candidate_id>/strategy_authoring_spec.yaml
<candidate_id>/backtest_pack/strategy_backtest_pack_validation.json
```

確認する数字:

```text
bridged_count
blocked_count
status_counts
blocked_by_family
blocked_by_side_bias
```

重要:

```text
BRIDGED は technical bridge only。
BRIDGED を economic pass と読まない。
```

## Step 5: Optional profit-readiness / risk artifacts

既存Crypto Perp event / outcome / rows-v2 / source availability / bias guardがある場合だけ読む。無い場合は missing として reality check に残す。

Inventory:

```bash
uv run sis crypto-perp-profit-readiness-inventory \
  --data-dir data/crypto_perp \
  --out data/profit_core_reality_check/profit_readiness_inventory/latest
```

Risk reviewは必要入力が揃う場合だけ実行する。

```bash
uv run sis crypto-perp-risk-taker-review \
  --rows-v2 <crypto_perp_tournament_rows.v2.json> \
  --source-availability <source_availability.json> \
  --bias-guard <bias_guard.json> \
  --operator-jurisdiction-status unknown \
  --source-freshness-status unknown \
  --out data/profit_core_reality_check/risk_review/latest
```

`unknown` は便利な合格ではない。現実に未確認なら unknown として止める。

## Step 6: Reality check summary

実装後の予定CLI:

```bash
uv run sis profit-core-reality-check \
  --candidate-set data/profit_core_reality_check/candidates/btc_eth_5m/strategy_idea_candidate_set.json \
  --search-ledger data/profit_core_reality_check/candidates/btc_eth_5m/search_ledger.jsonl \
  --export-manifest data/profit_core_reality_check/candidates/btc_eth_5m/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json \
  --authoring-bridge data/profit_core_reality_check/authoring_bridge/btc_eth_5m/strategy_idea_candidate_authoring_bridge_manifest.json \
  --profit-readiness-inventory data/profit_core_reality_check/profit_readiness_inventory/latest/profit_readiness_inventory.json \
  --out data/profit_core_reality_check/summary/btc_eth_5m
```

任意artifactは存在する場合だけ渡す。

`candidate-set`、`search-ledger`、`export-manifest`、`authoring-bridge` は同じdogfood runから渡す。別runの export manifest を混ぜると、正しく `SHORTLISTED_IDS_MISSING_FROM_EXPORT_MANIFEST` や `EXPORTED_IDS_MISSING_FROM_BRIDGE` で止まる。その場合はprofit blockerではなくlineage入力ミスとして扱う。

出力:

```text
profit_core_reality_check.json
profit_core_reality_check.md
```

## Step 7: Read and decide

見る順番:

1. `next_single_blocker_to_fix`
2. `bridge_status_counts`
3. `blocked_by_family`
4. `blocked_by_side_bias`
5. `lineage_status`
6. `actual_cash_available_count`
7. `known_gaps`

このrunの目的は、次に直す1箇所を決めることです。

## Expected first outcomes

多くの場合、次のどれかになる。

```text
UNSUPPORTED_FAMILY_DOMINATES
UNSUPPORTED_SIDE_BIAS_DOMINATES
BRIDGED_TECHNICAL_ONLY
BLOCKED_MISSING_EVENT_OR_OUTCOME
ACTUAL_CASH_SOURCE_MISSING
```

これで正常です。profit proofが出ないことを失敗扱いしない。

## Stop rules

次の場合は即停止する。

- search ledger が無い。
- selected-only outputになっている。
- sealed test used for selection が true。
- bridge manifest が無いのにbridge結果を推測している。
- BRIDGEDをeconomic passとして扱っている。
- actual cash rowsが無いのにactual cashありとしている。
- optional artifact欠損を勝手に生成している。

## Record keeping

tracked docsにruntime数値を固定しない。dogfood結果を残すなら、次のようにする。

```text
docs/reports/ または docs/archive/ に snapshot として明示する
実行日時、commit SHA、input path、known gaps を記録する
pass countをcurrent truthとして書かない
```

## 完了条件

このrunbookの完了条件:

1. BTCUSDT / ETHUSDT のcandidate runができる。
2. C9 bridge manifestまたは明確なbridge blockerが出る。
3. reality check summaryが出る。
4. `next_single_blocker_to_fix` が1つに決まる。
5. その blocker を直す次PR候補が選べる。
