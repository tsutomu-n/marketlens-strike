# Signal To Trade Candidate Spec

この文書は、戦略 signal を売買候補へ変換する時の実務仕様です。

## 用語境界

| Term | Meaning | Not this |
|---|---|---|
| `StrategySignalRecord` | 戦略 generator が作った方向・強度・理由つき signal | order, position, execution instruction |
| `TrialRecord` | 評価結果と次 stage 選択の記録 | best trial だけの要約 |
| `TradeCandidate` | paper candidate pack に渡す売買候補 | paper order, live order |
| `PaperIntentPreview` | paper runner へ渡す仮注文意図 | live order, wallet action |

## Signal row の最低条件

Strategy Lab signal は少なくとも次を持つ必要があります。

- identity: `signal_id`, `strategy_id`, `strategy_family`, `strategy_version`
- time: `generated_at`, `ts_signal`, `timeframe`
- symbol binding: `execution_venue`, `execution_symbol`, `real_market_symbol`
- direction: `side`
- strength: `raw_score`, `rank_score`, `percentile_rank`, `tail_bucket`
- confidence: `confidence`, `source_confidence`, `venue_quality_score`
- lineage: `feature_snapshot_ref`, `quote_ref`, `tracking_ref`
- explanation: `reason_codes`, `block_reasons`

## Candidate 化の考え方

Candidate 化では、signal の「売買方向らしさ」をそのまま order にしません。次の問いに答えます。

1. signal は実市場データと execution venue の対応が明確か。
2. source confidence は低すぎないか。
3. venue quality は paper で観測するに足るか。
4. rank / percentile / tail bucket は同時期の他候補と比較して十分か。
5. 同じ strategy family の既存候補と重複していないか。
6. cost stress / slippage stress 後でも観測価値があるか。
7. block reason を記録した上で止めるべきではないか。

## Mapping example

Strategy signal:

```text
strategy_id=equity_index_momentum_v0
execution_symbol=XYZ100
real_market_symbol=QQQ
side=long
rank_score=0.90
tail_bucket=top
confidence=0.80
reason_codes=["close_above_sma20", "vix_not_spiking"]
```

Candidate:

```text
candidate_id=candidate-trial-{run_id}-{signal_id}
strategy_id=equity_index_momentum_v0
trial_id=trial-{run_id}
execution_symbol=XYZ100
real_market_symbol=QQQ
side=long
status=candidate
rank_score=0.90
tail_bucket=top
confidence=0.80
entry_reason_codes=["trial_selected"]
block_reasons=[]
live_order_submitted=false
```

この候補はまだ order ではありません。quantity、wallet、signing、exchange write は出てきません。

現行 CLI では、default evaluation は最新 `ts_signal` の 1 件だけを `TrialRecord.metrics.selected_signal_ids` に記録します。`evaluate-strategy-lab --candidate-limit 0` を使うと threshold 通過 signal を複数 selected signal として記録でき、`build-paper-candidate-pack` はその `selected_signal_ids` から候補を作ります。過去の全 signal row を無条件に order 候補へ展開するわけではありません。

## Blocked candidate

Candidate pack 内に blocked candidate を残すことは有用です。

例:

```text
status=blocked
side=none
block_reasons=["no_signals", "LOW_SOURCE_CONFIDENCE", "DUPLICATE_SIGNAL_FAMILY"]
```

blocked を残す理由:

- 似た仮説を何度も量産しない。
- 採用されなかった理由を taxonomy 化できる。
- gate が厳しすぎたのか、signal が弱かったのかを後で分解できる。

現行 code には `PaperCandidatePack.blocked_candidate_ids` はありません。blocked は `TradeCandidate.status`, candidate-level `block_reasons`, pack-level `block_reasons` で表します。

## Good candidate の条件

最低条件:

- `execution_symbol` と `real_market_symbol` が明確に分離されている。
- `signal_id` または `trial_id` から由来を追える。`signal_id` は artifact 内で重複していない。
- `confidence` が 0.0 から 1.0 の範囲。
- `rank_score` / `percentile_rank` がある場合 0.0 から 1.0 の範囲。
- `entry_reason_codes` が空ではない、または selection policy で説明できる。
- `block_reasons` がある場合、停止理由として十分に具体的。
- `live_order_submitted=false`。

悪い candidate:

- `side=long` だが根拠が `reason_codes=[]`。
- `execution_symbol=XYZ100` なのに `real_market_symbol=XYZ100` として QQQ proxy を失っている。
- `confidence=1.0` を検証なしに固定している。
- `status=candidate` なのに source / venue quality が不明。
- `paper_ready_claimed=true` のような claim を含む。

## Signal strength と order size を混ぜない

`raw_score`, `rank_score`, `percentile_rank`, `confidence` は候補の優先度を表す情報です。これらをそのまま quantity や notional に変換しないでください。

order size を扱う場合は、少なくとも以下が別途必要です。

- capital allocation rule
- max notional
- per-symbol exposure cap
- volatility scaling
- liquidity / spread cap
- stale quote handling
- position state
- risk halt policy

現行 Strategy Lab docs では、size 決定は paper preview の補助情報に留めます。live order sizing ではありません。

## Review questions

Candidate を残す前に確認すること:

- この候補はどの `strategy_id` / `strategy_version` 由来か。
- 同じ `strategy_family` の候補と何が違うか。
- `execution_symbol` と `real_market_symbol` は正しいか。
- `rank_score` は同じ universe 内の相対評価か。
- `source_confidence` と `venue_quality_score` は取得済みか。
- reject するならどの taxonomy code を残すか。
- paper に進めるなら、どの `PromotionDecision` が必要か。
