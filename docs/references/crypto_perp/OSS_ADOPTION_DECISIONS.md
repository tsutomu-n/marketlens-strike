<!--
作成日: 2026-06-21_15:07 JST
更新日: 2026-06-21_15:07 JST
-->

# Crypto Perp OSS Adoption Decisions

## Decision Matrix

| Tool | Decision | Use | Core boundary |
|---|---|---|---|
| Hypothesis | adopted as dev dependency | property tests and later state-machine tests | no runtime dependency |
| Tardis downloadable CSV | fixture / parser reference | parser, L2 book, VWAP golden tests | vendor data is not the source of alpha truth |
| pybotters `<2.0` | separate workspace spike | Bitget public WS reconnect/DataStore comparison | no core import before 24h soak evidence |
| Freqtrade | external sidecar only | lookahead/recursive/differential checks | GPLv3 code is not copied or imported |
| Hummingbot | read and compare | Bitget connector endpoint/state/rate-limit notes | official Bitget docs remain authoritative |
| hftbacktest | deferred | only if queue/latency explains actual fill gaps | not needed for MVP-B |
| River | deferred | progressive validation after enough matured events | not useful before event count exists |
| NautilusTrader | deferred/reference only | architecture comparison | migration cost is too high for this MVP |

## Source Pointers Checked

- Tardis Bitget Futures downloadable samples: https://docs.tardis.dev/historical-data-details/bitget-futures
- Tardis CSV data types and L2 reconstruction notes: https://docs.tardis.dev/downloadable-csv-files/data-types
- Tardis datasets API: https://docs.tardis.dev/downloadable-csv-files/api
- pybotters Bitget DataStore docs: https://pybotters.readthedocs.io/ja/stable/generated/pybotters.BitgetDataStore.html
- Freqtrade license: https://github.com/freqtrade/freqtrade/blob/develop/LICENSE
- Hummingbot Bitget connector page: https://hummingbot.org/exchanges/bitget/

## Non-Negotiable Boundary

Validation tools can shorten bug discovery time. They do not replace prospective decisions, raw snapshots, MarketLens schemas, or actual cash accounting.
