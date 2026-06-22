<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# OSS / Research / Competition Adoption Notes

## 1. 採用原則

OSSはMarketLens Strikeの中核を置換しない。

採用基準:

```text
仮説を市場で棄却・前進するまでの時間を短くするか
MarketLens固有バグを発見できるか
実装/運用コストより検証価値が大きいか
```

## 2. OSS decision matrix

| OSS | 判断 | 使い方 | 中核へ入れない理由 |
|---|---|---|---|
| Hypothesis | 今すぐdev採用 | property/state-machine test | runtime不要 |
| Tardis Python/sample | fixture採用 | native tick/book golden data | data vendor依存を正本にしない |
| pybotters `<2.0` | 別workspace spike | Bitget WS/reconnect/DataStore比較 | v2予定、raw-first維持 |
| Freqtrade | 外部sidecar | lookahead/recursive/differential | GPLv3、大依存、同じdataなら独立真実ではない |
| Hummingbot | 読む/比較 | Bitget connector、state/rate-limit | framework統合不要 |
| hftbacktest | 条件付き後段 | latency/queue/replay差分 | HFT/MM化しない、データ前提が重い |
| VectorBT | 既存optional | event outcome matrix高速化 | 高速探索はoverfitも高速化 |
| River | deferred | progressive validation/drift | event数不足時は不要 |
| NautilusTrader | architecture reference | clock/event bus/cache/replay | 移行コストがMVPを遅らせる |
| cryptofeed | deferred | multi-venue WS参考 | 今はBitget単独、責務重複 |
| CCXT | optional differential | symbol/metadata照合 | native semanticを正本にする |
| OpenBB | 不採用 | 将来multi-asset調査のみ | 初期Perp truth cycleに重い |

## 3. OSS別の具体的学習項目

### Hypothesis

導入:

```toml
[dependency-groups]
dev = [
  "hypothesis>=6",
]
```

適用:

- Decimal rounding。
- event dedupe。
- time cutoff。
- order state machine。
- fee/funding二重計上。
- cash ledger invariant。

License: MPL-2.0。通常のdependency利用。ソースコピー不要。

### Tardis

使うもの:

- Bitget Futuresのraw exchange-native messages。
- trades、incremental book、derivative tickerサンプル。
- local timestampとexchange timestamp。

使わないもの:

- sample dayの成績をalpha証拠にすること。
- BTC sampleを低流動性銘柄代表とすること。

Fixture provenanceに必須:

```text
source URL
downloaded_at
source license/terms note
sha256
exchange
symbol
date
data type
```

### pybotters

比較対象:

```text
native websockets backend
vs
pybotters WebSocket/DataStore backend
```

採用条件:

- raw message lossなし。
- gap/checksumを隠さない。
- 24h soakで欠損悪化なし。
- コード量と復旧ロジックを明確に削減。

License: MIT。v2全面改修予定のため`<2.0`。

### Freqtrade

別Docker/processで使う。

借りる:

- lookahead-analysisの考え方。
- recursive-analysisの考え方。
- pairlist age/spread/volume/delist filter設計。
- dry-runとreal modeの明示分離。

禁止:

- GPLコードをMarketLens packageへコピー。
- Freqtrade結果を独立市場データの証拠と呼ぶ。
- Freqtradeのpairlistをpoint-in-time universe保証と誤解。

### Hummingbot

読むファイルの種類:

- Bitget perpetual constants。
- REST/WS endpoint mapping。
- order state mapping。
- ping/reconnect。
- funding/mark/index integration。
- order create/cancel/query handling。

注意:

- 公式Bitget v3 docsを正本にする。
- Hummingbot connectorがv2 endpointを使う場合はstaleness候補。
- connectorのnormalizationでseq/checksumが落ちる可能性を確認。

License: Apache-2.0。コードを借りる場合もnoticeを守るが、基本は設計参考。

### hftbacktest

導入条件:

- actual fillと簡易BBO replayの差が説明不能。
- limit queueが利益本体。
- L2/L3 historyが確保済み。

使う:

- latency model。
- queue/fill model。
- historical live-period reproduction。

使わない:

- HFT/MM戦略への転換。

License: MIT。

### VectorBT

用途:

- event x horizon x direction matrix。
- threshold近傍感度。
- random baseline。

全variantをTrial Ledgerへ残す。winnerだけ保存しない。

### River

採用条件:

- 数百件のprospective matured events。
- batch baselineを上回る理由がある。

用途:

- predict-one -> outcome -> learn-one。
- drift detection。
- progressive validation。

## 4. 研究から借りるもの

### Crypto momentum / factors

Liu & Tsyvinski、Liu/Tsyvinski/Wuの研究はcryptoでmomentum、attention、market/size/momentum factorを検討する根拠になる。

反映:

- reversalだけでなくcontinuationを必ず比較。
- market、size/liquidity、momentumをcontrol/contextにする。
- 研究結果を15分Perpのalpha証明としない。

### Pump-and-dump research

借りる:

- event時刻。
- 価格速度。
- volume/trade activity。
- online coordinationを別カテゴリとする考え方。

借りない:

- pumpを検出すれば安全にshortできるという結論。
- 既知pump groupの事後ラベルを実運用へ直接移植。

### Order flow imbalance

借りる:

- volumeよりBBO/OFI/depthをentry状態診断へ使う。
- impactがdepthに依存する考え方。

借りない:

- OFI単独の万能alpha化。

### Venue fragmentation

借りる:

- source venueを必須保存。
- Bitget固有moveとmarket-wide moveを分離。

借りない:

- 単純なvenue価格差を裁定可能利益と呼ぶこと。

### Wash trading / OI reliability

反映:

- reported turnoverはactivity triggerに限定。
- OI raw/unit/sourceを保存。
- volume/OI単独で方向を決めない。

### Perpetual futures pricing / liquidation

反映:

- mark、index、funding interval、contract typeを保存。
- normal distributionだけでruin/liquidationをsimulationしない。
- actual event path bootstrapを優先。

### Backtest overfitting / Deflated Sharpe

反映:

- detector/universe/fee/horizonの変更は全てtrial。
- all variants保存。
- sample不足時はPBO/DSRを`not_estimable`。
- holdoutを何度も見ない。

## 5. Competitionから借りるprotocol

対象:

- G-Research Crypto Forecasting。
- Optiver Realized Volatility Prediction。
- Optiver Trading at the Close。
- Jane Street Real-Time Market Data Forecasting。

これらのモデルをコピーしない。借りるのは実験運用である。

```text
discovery window = public leaderboard
frozen future window = private leaderboard
config hash = submission
one version / one future window
online inference = available data only
baseline = reversal / continuation / abstain
```

Competitionの危険な移植:

- clean dataset前提。
- fixed metricへの過適合。
- transaction cost無視。
- leaderboard反復。
- model ensembleの複雑化。

MarketLensのscoreは予測相関ではなくactual cashとfillabilityを主にする。

## 6. Research tasks

M11までに、次のsmall experimentsを行う。

```text
R01 reversal vs continuation by horizon
R02 market-adjusted vs raw event
R03 turnover trigger vs trade-count/OFI confirmation
R04 funding/OI inclusion ablation
R05 listing-age bands
R06 Bitget-only vs reference-confirmed（reference導入後）
R07 human veto save/missed winner
R08 actual vs simulated fill bias
R09 5/10/25 USD capacity
R10 operator time cost
```

各experimentは1枚のdecision recordを作り、結果が悪ければ機能追加せず棄却する。
