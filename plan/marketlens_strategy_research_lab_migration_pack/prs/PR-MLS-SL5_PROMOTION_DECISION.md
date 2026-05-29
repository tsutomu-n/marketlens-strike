# PR-MLS-SL5 PromotionDecision

## Goal

paperへ昇格するには人間の判断artifactを要求する。

## Files To Add

```text
src/sis/research/strategy_lab/promotion_decision.py
src/sis/commands/strategy_lab.py
```

## Rules

```text
- phase-gate-review is not paper approval
- bot-preview is not paper approval
- PromotionDecision required before PaperIntentPreview
- live_ready_claimed remains false
```

## Artifacts

```text
data/research/promotion_decision.json
data/reports/promotion_decision.md
```

## Tests

```text
- promote requires required_evidence present
- reject/hold can be created with reasons
- missing PromotionDecision blocks PaperIntentPreview
- live_ready_claimed true fails
```

## Done

```text
uv run sis promotion-decision --source-pack data/research/paper_candidate_pack.json --decision hold
```
