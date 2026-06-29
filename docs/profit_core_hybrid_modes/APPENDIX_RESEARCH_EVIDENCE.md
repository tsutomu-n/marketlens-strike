<!--
作成日: 2026-06-29_22:07 JST
更新日: 2026-06-29_22:07 JST
-->

# Appendix: Research And Evidence

## 結論

大量候補生成は必要。ただし、研究知見は一貫して「best backtest を信じるな」「探索回数と選択手続きを保存せよ」「OOS を見て直したら OOS ではない」と警告している。

現 repo の設計はこの方向に寄っている。足りないのは、candidate generation と multiplicity accounting と kill gate を一体化した developer-facing contract。

## Repo-local evidence

| evidence | 読み方 |
|---|---|
| [../strategy_idea_candidates/README.md](../strategy_idea_candidates/README.md) | candidate set、search ledger、selection-adjusted metrics、C9 v0 bridge はある。ただし alpha evaluator、実測 Perp cost evaluator、paper/live permission は未実装 |
| [../IMPLEMENTED_SURFACES.md](../IMPLEMENTED_SURFACES.md) | Crypto Perp profit-readiness、risk-taker review、tiny-live shadow、actual cash report gate の実装済み境界 |
| [../crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](../crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md) | `actual_cash_result_usd`、`cash_metric_basis`、`NO_TRADE`、`pbo_status=NOT_ESTIMABLE`、`tiny_live_shadow` の語彙 |
| [../EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md](../EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md) | Discovery / Validation / Execution Evidence Core の docs-only scope-control |
| [../PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md](../PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md) | Profit Core の actual cash / NO_TRADE / LLM / Add-on 境界 |

## Research evidence

| source | 実務上の意味 |
|---|---|
| Bailey, Borwein, López de Prado, Zhu, "The Probability of Backtest Overfitting" ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)) | ordinary holdout だけでは不安定。PBO は fold-by-candidate outcome matrix が無いと使えない。入力が無ければ `NOT_ESTIMABLE` が正しい |
| Bailey and López de Prado, "The Deflated Sharpe Ratio" ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)) | 大量探索、非正規 return、selection bias で Sharpe は水増しされる。DSR 入力が無い raw Sharpe は proof ではない |
| Hansen, "A Test for Superior Predictive Ability" ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569)) | White Reality Check 系の data snooping 問題を扱う。低品質な比較候補に引きずられない工夫が必要 |
| Harvey, Liu, Zhu, "... and the Cross-Section of Expected Returns" ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314)) | factor zoo では通常の有意性基準は甘い。多数探索後の winner は高いハードルが必要 |
| McLean and Pontiff, "Does Academic Research Destroy Stock Return Predictability?" ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623)) | 既知 factor や論文由来 candidate も decay する。文献をそのまま venue-specific edge と読まない |
| Benjamini and Hochberg FDR | throughput control に向くが、強相関 candidate では単独合格条件にしない。effective trial count と family cluster を併記する |

## External venue / platform docs

これらは制約情報であり、実行許可ではない。実行前には必ず最新の official docs、terms、jurisdiction、credentials、risk limit を再確認する。

| source | current implication |
|---|---|
| Bitget Demo Trading REST API ([official](https://www.bitget.com/api-doc/common/demotrading/restapi)) | Demo API Key と `paptrading: 1` header がある。virtual funds でも credential / terms / jurisdiction 境界は残る |
| Hyperliquid API docs ([official](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api)) | mainnet / testnet URL が分かれる。exchange endpoint は署名・取引系なので default docs path では扱わない |
| GRVT API docs ([official](https://api-docs.grvt.io/)) | API key、wallet login、session cookie、account id など認証境界がある。初期 default にはしない |
| Numerai docs ([official](https://docs.numer.ai/)) | validation diagnostics を過信せず live / out-of-sample で見る姿勢は、sealed holdout と validation peek count の必要性を補強する |

## 調査から修正した判断

- `event_count >= 100` は default 一律にしない。common signal、event-driven、rare dislocation で分ける。
- `PBO < 0.20` は PBO 入力が揃ってから使う。初期は `NOT_ESTIMABLE` を gate result にする。
- BH/FDR は raw p-value がある時だけ使う。相関 candidate には family cluster / effective trial count を添える。
- Virtual Execution Gate は必要だが、最初から external venue を厚くしない。
- LLM negative-veto は有用だが、machine-checkable な欠落以外を hard blocker にしない。
