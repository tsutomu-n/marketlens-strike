<!--
作成日: 2026-06-21_15:07 JST
更新日: 2026-06-21_15:07 JST
-->

# pybotters Bitget Spike

This is a separate workspace for comparing MarketLens native Bitget public WebSocket capture with `pybotters<2.0`.

Do not import this workspace from `src/sis`. Do not copy pybotters internals into MarketLens core.

## Purpose

- Compare raw message loss, reconnect behavior, DataStore behavior, and book gap visibility.
- Produce a 10 minute network smoke report and a 24 hour soak report before any adoption decision.
- Keep MarketLens recorder raw-first even if pybotters becomes useful as an alternate backend.

## Manual Setup

```bash
cd tools/oss_spikes/pybotters_bitget
uv sync
```

Network smoke is manual only. It is not part of normal CI.

Required output before adoption:

- start/end time
- Bitget public channels and symbols
- native backend raw message count
- pybotters raw message count
- reconnect count
- visible gap/checksum failures
- dropped/hidden message evidence
- operator conclusion: adopt / reject / extend soak

Adoption condition:

- no raw message loss regression
- no hidden gap/checksum failure
- 24 hour soak does not worsen missing data
- code and recovery logic are materially simpler than the native backend
