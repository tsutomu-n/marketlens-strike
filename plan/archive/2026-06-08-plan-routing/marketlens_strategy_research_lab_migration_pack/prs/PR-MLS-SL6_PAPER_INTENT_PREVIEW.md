# PR-MLS-SL6 PaperIntentPreview

## Goal

PaperCandidatePackからpaper専用の仮注文意図previewを作る。live注文ではない。

## Files To Add

```text
src/sis/research/strategy_lab/paper_intent_preview.py
```

## Required Fields

```text
valid_until
source_quote_ts
source_tracking_ts
source_feature_ts
source_phase_gate_run_id
requires_revalidation=true
paper_only=true
live_conversion_allowed=false
live_order_submitted=false
wallet_used=false
exchange_write_used=false
```

## Artifacts

```text
data/bot/paper_intent_preview.json
data/reports/paper_intent_preview.md
```

## Tests

```text
- missing PromotionDecision blocks
- expired valid_until blocks paper execution later
- live_conversion_allowed cannot be true
- OrderIntent name is not used
```

## Done

```text
uv run sis build-paper-intent-preview --source-pack data/research/paper_candidate_pack.json --promotion-decision data/research/promotion_decision.json
```
