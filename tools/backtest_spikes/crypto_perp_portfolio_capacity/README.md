<!--
作成日: 2026-07-16_23:46 JST
更新日: 2026-07-16_23:57 JST
-->

# Crypto Perp Portfolio Capacity Discovery Spike

現行Backtest Candidate Packを変更せず、共有資本、同時position、同一symbol上限、
同時timestamp policyをDecimal参照実装で再生するPR-BT0専用の検証コード。

## 境界

- `src/`、`schemas/`、Candidate Pack、既存VectorBT adapterは変更しない。
- BAR proxyをactual cash、実約定、利益証明として扱わない。
- VectorBTは参照実装が受理したscheduleのgross PnLとfixed trading costだけを検算する。
- このSpikeの判定だけではPR-BT1以降へ進まない。

## Focused tests

```bash
UV_CACHE_DIR=/tmp/marketlens-uv-cache \
uv run --extra vectorbt pytest \
  tools/backtest_spikes/crypto_perp_portfolio_capacity/tests -q
```

## Runtime inventory

```bash
uv run python \
  -m tools.backtest_spikes.crypto_perp_portfolio_capacity.inspect_runtime \
  --candidate-pack-dir /home/tn/projects/marketlens-strike/data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest \
  --out data/research/crypto_perp_portfolio_capacity/discovery
```

## 64-case matrix

```bash
UV_CACHE_DIR=/tmp/marketlens-uv-cache \
uv run --extra vectorbt python \
  -m tools.backtest_spikes.crypto_perp_portfolio_capacity.run_matrix \
  --candidate-pack-dir /home/tn/projects/marketlens-strike/data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest \
  --initial-cash-usd 3000 \
  --out data/research/crypto_perp_portfolio_capacity/matrix
```
