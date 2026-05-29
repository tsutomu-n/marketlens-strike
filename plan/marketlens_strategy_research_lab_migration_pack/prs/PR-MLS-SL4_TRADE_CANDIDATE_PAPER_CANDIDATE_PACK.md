# PR-MLS-SL4 TradeCandidate + PaperCandidatePack

## Goal

strategy signalからpaper候補束を作る。これは注文ではない。

## Files To Add

```text
src/sis/research/strategy_lab/candidates.py
src/sis/research/strategy_lab/paper_candidate_pack.py
```

## Required Behavior

```text
- candidate / blocked / no_signal / hold を全部保存
- selected_candidate_ids と rejected_candidate_ids を保存
- rank_score / percentile_rank / tail_bucketを持つ
- claim flagsは全てfalse
```

## Artifacts

```text
data/research/paper_candidate_pack.json
data/reports/paper_candidate_pack.md
```

## Tests

```text
- blocked candidates remain in artifact
- selected/rejected ids are consistent
- live_order_submitted=false
- wallet_used=false
- exchange_write_used=false
- paper_ready_claimed=false by default
```

## Done

```text
uv run sis build-paper-candidate-pack --trial-ledger data/research/trial_ledger.jsonl
```
