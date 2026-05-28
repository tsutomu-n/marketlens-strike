# Parts Extraction Matrix

| 部品 | 使うノート | 採用前の反証 |
|---|---|---|
| Universe Selector | Solana bot, Solana examples, multi-asset allocation | 取引対象を増やすほど結果が悪化しないか |
| Data Collector | cryptofetch, PyBotters, Polars, on-chain strategy | 欠損、遅延、改訂、API制限で壊れないか |
| Feature Factory | AlphaTrend, LightGBM, time series, order book | 特徴量追加がリークや過学習ではないか |
| Regime Detector | Trend Bot, regime switching, maturity exit | レンジ、急変、低流動性で誤作動しないか |
| Signal Generator | Trend strategies, order book, ML modules | 単純ベースラインを上回るか |
| Participation Filter | order book, Jito, token safety | 約定可能性、スリッページ、MEVで消えないか |
| Position Sizer | Trend Bot, RGCE, portfolio optimization | VaR/ESがテールリスクを過小評価しないか |
| Exit Module | maturity exit, Trend Bot, VectorBT | 利確/損切りが期待値を削らないか |
| Risk Guard | RGCE, SDH, backtest docs | kill switch、資金上限、異常検知が先にあるか |
| Execution Adapter | PyBotters, Jito, Solana bot | 秘密情報、API仕様、約定失敗を扱えるか |
| Evaluation Harness | VectorBT, Backtest Trade, backtest note | ウォークフォワード、コスト、複数期間で通るか |
| Monitoring Layer | SDH, RGCE, news automation | 異常時に止まるか、通知が有効か |
| Security Guard | Solana bot, Jito, cryptofetch, PyBotters | 秘密鍵/APIキーをdocsやログに出さないか |
| Research Assistant | automated news, GA, time series | 出力を売買判断ではなく仮説生成に限定できるか |

