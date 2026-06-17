<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# Stop conditions

Stop implementation and return to planning if any of these are encountered:

- The implementation needs live order submission.
- The implementation needs wallet, signing, account write, or exchange write credentials.
- The implementation needs a public live or micro-live Strategy Lab CLI.
- The implementation needs a new production venue id or schema enum widening.
- The implementation needs external API access in tests or default local commands.
- The implementation needs to set `paper_ready_claimed=true`, `tiny_live_ready_claimed=true`, or `live_ready_claimed=true`.
- The implementation needs to set `live_conversion_allowed=true`.
- The implementation needs to set `wallet_used=true` or `exchange_write_used=true`.
- NDX/QQQ paper candidate or paper intent can pass without matching Layer 2.6 and Layer 2.7 artifacts.
- Raw JSON `PaperIntentPreview` can bypass the evidence-aware validation.
- Paper observation can pass without local quote evidence and paper broker revalidation.
- Fixture-only evidence is described as alpha proof, robust backtest proof, or live readiness.
- Paper-observation gate thresholds become discretionary and undocumented.
- The plan requires a new dependency or lockfile churn.
