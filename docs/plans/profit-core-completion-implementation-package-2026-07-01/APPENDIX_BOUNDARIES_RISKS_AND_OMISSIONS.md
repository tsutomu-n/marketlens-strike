<!--
作成日: 2026-07-01_21:05 JST
更新日: 2026-07-01_21:05 JST
-->

# Appendix: Boundaries, Risks, And Omissions

## Must Not Break

- Do not mix `actual_cash` with virtual, proxy, estimate, paper, demo, or testnet evidence.
- Keep `NO_TRADE` as first-class outcome.
- Do not treat `BRIDGED_TECHNICAL_ONLY` as alpha proof, profit proof, paper permission, or live readiness.
- Do not treat `AVAILABLE` as performance pass.
- Do not treat `NOT_ESTIMABLE` as implementation failure when required inputs are missing.
- Do not mix `risk_taker_sprint` output into mainline performance.
- Do not reuse the same sealed holdout after threshold/family policy changes.
- Do not let LLM approve, rewrite strategy, decide PnL, decide actual_cash, override gates, or grant paper/live/tiny-live permission.
- Do not read external venue docs, demo docs, or testnet docs as legal/account clearance.
- Do not run wallet, signing, exchange write, live order, or tiny-live measurement without a separate explicit approval scope.

## Stop Conditions

Stop and record `docs/action-required.md` if any of these becomes necessary:

- Credential use or credential mutation.
- Public network write or exchange write.
- Live order or tiny-live execution.
- Legal, jurisdiction, tax, or account-condition approval.
- Dependency addition or replacement that changes locked runtime behavior.
- DB/schema migration outside additive local JSON artifacts.
- Need to choose a venue-specific real API behavior without current official docs verification.
- User-specific risk budget, account balance, API key permission, IP restriction, or withdrawal setting.

## Omission Pass

Potential omissions and fixes:

- Omission: assuming CP1-CP3 contracts imply pipeline connection.
  - Fix: P1-P3 explicitly attach protocol, multiplicity, bridge status, and backtest kill gate.
- Omission: treating C9 `BRIDGED` as proof.
  - Fix: split to `BRIDGED_TECHNICAL_ONLY` and blocker vocabulary.
- Omission: treating multiplicity account as correction.
  - Fix: require search ledger consistency and `NOT_ESTIMABLE` states where inputs are absent.
- Omission: letting virtual execution become profit evidence.
  - Fix: `cash_metric_basis=virtual_exchange`, `actual_cash=false`, PnL not authoritative.
- Omission: allowing LLM review to approve.
  - Fix: constrained adversarial finding vocabulary only.
- Omission: moving sprint winners to cash path.
  - Fix: P8 promotion debt requires re-registration under `verification_throughput`.
- Omission: readiness packet being read as permission.
  - Fix: P9 is human approval input only.
- Omission: P10 external adapter freezing stale venue docs.
  - Fix: current official docs verification is part of checkpoint acceptance.
- Omission: P11 accepting unrelated actual-cash rows.
  - Fix: enforce candidate id, event id, order id, venue, action, ledger, fee/funding, and row hash consistency.
- Omission: P12 promoting on small lucky sample.
  - Fix: require event count, diversity, concentration, loss, burden, reconciliation, and edge over `NO_TRADE`.
- Omission: P13 optimizing on only good news.
  - Fix: block success-only feedback and require new accounting ids.

## Better Revisions Included

- Start with local/mock virtual gate before external venue adapter.
- Put machine-readable evidence packet before LLM adversarial review.
- Treat `risk_taker_sprint` as isolated attack mode before enabling broader generators.
- Make actual-cash measurement explicit artifact recording, not automatic execution.
- Keep external venue details out of static plan docs except as current-verification requirements.
- Define final goal as false-positive-resistant profit evidence pipeline, not guaranteed profit.
- Make P13 a proposal artifact, not an optimizer that mutates protocol thresholds.

## Plan Review Findings

Finding 1: The original long-horizon doc contains stale "現在地" language.

Resolution:

- This package states current code truth separately and directs coders to verify source files, tests, schemas, and CLI help.

Finding 2: P11/P12 can be misread as permission to execute actual cash.

Resolution:

- P11 is record-only. P12 is report-only. Execution remains out of scope.

Finding 3: P13 original wording says failures are reflected in next protocol.

Resolution:

- This plan uses review-ready calibration artifact. Creating the next protocol is a separate future cycle.

Finding 4: P3 has no public CLI.

Resolution:

- The task chain does not invent a CLI requirement. Completion is schema/model/test and bridge integration.

Finding 5: External venue current docs are temporally unstable.

Resolution:

- P10 requires current official docs verification immediately before real adapter implementation.

## Residual Risks

- The repo can produce evidence artifacts, but market profit still depends on future market data and actual fills.
- `NOT_ESTIMABLE` can be a correct stop result and still become a practical bottleneck.
- P13 calibration can propose safer next thresholds, but it cannot prove the next protocol is profitable.
- Any future actual-cash execution requires user/account-specific approval that cannot be encoded in this static plan.
