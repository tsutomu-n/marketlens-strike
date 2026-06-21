<!--
作成日: 2026-06-21_15:07 JST
更新日: 2026-06-21_15:07 JST
-->

# Freqtrade External Validation Sidecar

Freqtrade is GPLv3. Keep it as a separate sidecar process and do not import or copy Freqtrade source into MarketLens core.

Use this sidecar only for advisory validation:

- lookahead-style differential checks
- recursive indicator stability checks
- pairlist age / spread / volume / delist filter comparison
- dry-run versus real-mode boundary review

Do not treat Freqtrade output as independent market data truth when it consumes MarketLens-exported data.

## Manual Run Boundary

The compose file is not used by normal CI.

```bash
cd tools/external_validation/freqtrade
docker compose run --rm freqtrade --help
```

The default compose service has `network_mode: "none"` and read-only access to repo `data/`. Add any network or credential path only in a separate manual validation branch.
