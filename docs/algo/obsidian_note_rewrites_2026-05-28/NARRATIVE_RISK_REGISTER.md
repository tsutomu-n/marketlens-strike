# Narrative Risk Register

| Risk Tag | 典型的な物語 | 修正後の扱い |
|---|---|---|
| `MARKETING_NARRATIVE` | 自動化すれば受動収入になる | 収益導線と取引優位性を分離し、戦略候補から外す |
| `PREDICTION_OVERCLAIM` | MLやAIで未来価格を高精度に予測できる | 予測ではなく条件付きフィルタ、確率、誤差管理に落とす |
| `BACKTEST_OVERFIT` | バックテストで良ければ使える | 時系列分割、手数料、スリッページ、複数市場で反証する |
| `EXECUTION_GAP` | シグナルがあれば約定できる | 板、遅延、手数料、約定失敗、流動性を別部品として扱う |
| `SECURITY_SECRET` | bot設定を埋めれば動く | 秘密鍵、APIキー、wallet、RPCは運用リスクとして隔離する |
| `MEV_LATENCY_ARMS_RACE` | Jito/Warp/低遅延で勝てる | レイテンシー競争、MEV、チップ、逆選択を前提にする |
| `DATA_VENDOR_DEPENDENCE` | オンチェーン/ニュース/APIを足せば精度が上がる | データ遅延、改訂、欠損、料金、利用規約を検証対象にする |
| `REGULATORY_COMPLIANCE` | 自動売買やニュース生成は技術問題だけ | 取引所規約、広告、紹介、著作権、金融規制を確認対象にする |
| `OPERATIONAL_COMPLEXITY` | 多機能化すれば堅牢になる | 小さい部品に分割し、止める条件を先に決める |
| `DANGEROUS_AUTOMATION` | botが自律的に機会を拾う | paper observation、資金上限、kill switchなしでは進めない |

## 高リスクノート

- `1107_自動化された暗号通貨ニュースで稼ぐ方法.md`: `MARKETING_NARRATIVE`, `REGULATORY_COMPLIANCE`
- `1129-Solanaトレーディングボット.md`: `DANGEROUS_AUTOMATION`, `SECURITY_SECRET`, `MEV_LATENCY_ARMS_RACE`
- `1202-JitoとSolana.md`: `MEV_LATENCY_ARMS_RACE`, `EXECUTION_GAP`, `SECURITY_SECRET`
- `0714-トレード戦略-Order-Book.md`: `EXECUTION_GAP`, `PREDICTION_OVERCLAIM`
- `0714-Adaptive-Alpha-Trendトレードプログラム.md`: `PREDICTION_OVERCLAIM`, `BACKTEST_OVERFIT`, `OPERATIONAL_COMPLEXITY`
- `0902-Genetic Alogo for Trading.md`: `BACKTEST_OVERFIT`, `PREDICTION_OVERCLAIM`
- `0725-時系列-予測モデル.md`: `PREDICTION_OVERCLAIM`, `DATA_VENDOR_DEPENDENCE`

