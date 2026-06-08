<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# B_TEST_FIXTURE_PLAN

## Existing fixtures expected

```text
tests/fixtures/research_layer_2_2/reviews/valid_approve.json
tests/fixtures/research_layer_2_2/reviews/valid_warn_requires_resolution.json
tests/fixtures/research_layer_2_2/reviews/invalid_pack_hash_mismatch.json
tests/fixtures/research_layer_2_2/reviews/invalid_unknown_evidence_ref.json
tests/fixtures/research_layer_2_2/reviews/blocker_temporal_leakage.json
tests/fixtures/research_layer_2_2/reviews/reject_seed.json
```

## Add or synthesize in tests

```text
high_without_human_decision.json
high_with_unresolved_human_decision.json
high_with_resolved_human_decision.json
reject_seed_with_confirming_resolution.json
approve_regression_second_review_true.json
```

## Fixture design notes

```text
- Use pack_hash placeholder replacement as existing tests do.
- Keep evidence_refs inside generated evidence_catalog.
- Do not add new schema fields unless necessary.
- Prefer constructing dict payloads in test helpers if fixture count becomes excessive.
```
