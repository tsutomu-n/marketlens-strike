<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# Source Index

確認日: 2026-06-20 JST

## MarketLens Strike

- Repository: https://github.com/tsutomu-n/marketlens-strike
- `AGENTS.md`
- `docs/CURRENT_STATE.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md`
- `docs/strategy_inputs/README.md`
- `docs/strategy_research_lab/README.md`
- `docs/strategy_research_lab/13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md`
- `src/sis/cli.py`
- `src/sis/settings.py`
- `src/sis/storage/jsonl_store.py`
- `src/sis/ops/alerts.py`
- `src/sis/venues/capabilities.py`
- `src/sis/venues/suitability.py`
- `src/sis/execution/live_order_policy.py`
- `pyproject.toml`

## Bitget official

- Instruments: https://www.bitget.com/api-doc/uta/public/Instruments
- Tickers: https://www.bitget.com/api-doc/uta/public/Tickers
- Candles: https://www.bitget.com/api-doc/uta/public/Get-Candle-Data
- Open interest: https://www.bitget.com/api-doc/uta/public/Get-Open-Interest
- Funding history: https://www.bitget.com/api-doc/uta/public/Get-History-Funding-Rate
- Place order: https://www.bitget.com/api-doc/uta/trade/Place-Order
- Account assets: https://www.bitget.com/api-doc/uta/account/Get-Account
- Public trade WS: https://www.bitget.com/api-doc/contract/websocket/public/New-Trades-Channel
- Depth WS: https://www.bitget.com/api-doc/contract/websocket/public/Order-Book-Channel
- WebSocket limits: https://www.bitget.com/api-doc/common/websocket-intro

## OSS

- Hypothesis: https://github.com/HypothesisWorks/hypothesis
- pybotters: https://github.com/pybotters/pybotters
- Freqtrade: https://github.com/freqtrade/freqtrade
- Hummingbot: https://github.com/hummingbot/hummingbot
- hftbacktest: https://github.com/nkaz001/hftbacktest
- Tardis Python: https://github.com/tardis-dev/tardis-python
- VectorBT: https://github.com/polakowo/vectorbt
- River: https://github.com/online-ml/river
- NautilusTrader: https://github.com/nautechsystems/nautilus_trader

## Research

- Risks and Returns of Cryptocurrency: https://www.nber.org/papers/w24877
- Common Risk Factors in Cryptocurrency: https://www.nber.org/papers/w25882
- Trading and Arbitrage in Cryptocurrency Markets: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3171204
- Crypto Wash Trading: https://arxiv.org/abs/2108.10984
- Perpetual Futures Pricing: https://arxiv.org/abs/2310.11771
- Crypto derivatives liquidation/leverage: https://arxiv.org/abs/2102.04591
- Open interest reliability: https://arxiv.org/abs/2310.14973
- Intraday crypto periodicity: https://arxiv.org/abs/2306.17095
- Order Flow Imbalance: https://arxiv.org/abs/1011.6402
- Probability of Backtest Overfitting: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Pump-and-dump detection: https://arxiv.org/abs/1811.10109
- Real-time pump detection: https://arxiv.org/abs/2005.06610

## Competitions

- G-Research Crypto Forecasting: https://www.kaggle.com/competitions/g-research-crypto-forecasting
- Optiver Realized Volatility Prediction: https://www.kaggle.com/competitions/optiver-realized-volatility-prediction
- Optiver Trading at the Close: https://www.kaggle.com/competitions/optiver-trading-at-the-close
- Jane Street Real-Time Market Data Forecasting: https://www.kaggle.com/competitions/jane-street-real-time-market-data-forecasting

## Source interpretation boundary

- 公式docsはAPI contractの第一候補だが、runtime probeとの差をartifactへ保存する。
- OSS connectorは実装参考であり、取引所仕様の正本ではない。
- 論文は観測変数・反証方法の参考であり、Bitget 15m strategyの収益証明ではない。
- Competitionはprotocolの参考であり、clean dataset上のwinner modelを本番へ移植しない。
