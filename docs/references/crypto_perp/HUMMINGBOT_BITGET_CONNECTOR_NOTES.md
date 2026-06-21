<!--
作成日: 2026-06-21_15:07 JST
更新日: 2026-06-21_15:07 JST
-->

# Hummingbot Bitget Connector Notes

Hummingbot is a comparison source, not an implementation source of truth.

Checked source:

- Hummingbot Bitget connector page: https://hummingbot.org/exchanges/bitget/
- Hummingbot release note mentioning the Bitget connector: https://github.com/hummingbot/hummingbot/releases
- Official Bitget contract API docs entrypoint: https://www.bitget.com/api-doc/contract/intro

Current notes:

- Hummingbot documents both spot `bitget` and perpetual `bitget_perpetual` connectors.
- The Hummingbot Bitget page lists WebSocket connection type for the perpetual connector and supports limit / market orders.
- The page lists one-way and hedge position modes for the perpetual connector.
- Use Hummingbot to compare endpoint coverage, reconnect assumptions, order state names, and connector drift.
- Keep official Bitget API docs as the authoritative reference for endpoint semantics, request signing, rate limits, and order lifecycle.

Do not copy connector code into `src/sis`.

Questions for later tasks:

- Does Hummingbot preserve enough raw book sequence/checksum information to detect fillability gaps?
- Do connector state transitions match the M09/M10 query-before-resubmit and reduce-only close requirements?
- Are Hummingbot Bitget docs using current Bitget contract endpoints, or a stale endpoint generation?
