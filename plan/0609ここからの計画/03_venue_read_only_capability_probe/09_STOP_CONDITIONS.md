<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Stop Conditions

Stop and ask before proceeding if any implementation requires:

- external network calls
- Bitget or Hyperliquid credentials
- new credential names
- account, balance, position, fill, or order reads from real venues
- signing real requests
- wallet access
- order submit, cancel, amend, or close
- `VenueId` widening
- Strategy Lab schema widening
- `evaluation_plan.mls.v1` target widening
- paper execution enablement for `bitget_futures` or `hyperliquid_perp`
- live execution enablement
- dependency additions
- edits to `pyproject.toml` or `uv.lock`

Also stop if:

- existing NDX/QQQ paper-path blocking tests fail
- future venue rows are easier to interpret as ready than blocked
- CLI names or report labels imply exchange connectivity
- generated artifacts include secret-like env values
- implementation would make `bitget_demo` and production Bitget share one
  venue id
- implementation would make Trade[XYZ] and direct Hyperliquid share one venue id

