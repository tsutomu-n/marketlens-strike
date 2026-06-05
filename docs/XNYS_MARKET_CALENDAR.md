<!--
作成日: 2026-05-26_08:55 JST
更新日: 2026-06-05_08:11 JST
-->

# XNYS Market Calendar

この文書は、`real_market` と `tracking` で使う米国 regular session 判定の前提を短くまとめる。

## Current Use

- `SPY` と `QQQ` は real-market 側の正データ symbol
- `Trade[XYZ]` 側ではそれぞれ `SP500` と `XYZ100` に対応づける
- micro live と tracking の session gate は、underlying の regular session を前提にする

## Why It Matters

- `underlying_session_regular=false` の時は tracking が fail-closed になり得る
- micro live gate は regular session 外を block する
- paper / live quality gate は afterhours や premarket を許容しない前提で組まれている

## Practical Interpretation

- `SP500` の underlying truth は `SPY`
- `XYZ100` の underlying truth は `QQQ`
- equities は各 `real_market_symbol` を使う

## Related Config

- `configs/instrument_registry.seed.json`
- `configs/halt_policy.yaml`
- `configs/real_market_provider_policy.yaml`
