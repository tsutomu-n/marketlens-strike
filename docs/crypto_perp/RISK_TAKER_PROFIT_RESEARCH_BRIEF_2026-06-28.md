<!--
作成日: 2026-06-28_17:18 JST
更新日: 2026-06-28_17:21 JST
-->

# Risk-Taker Profit Research Brief

確認日時: 2026-06-28_17:18 JST

## 結論

個人トレーダー向けの risk-taker mode は、損失上限を緩めて大きく張る mode ではありません。実務的には、`NO_TRADE` を正式な比較対象にしたうえで、手数料、funding、slippage、operator time、清算距離、地域制約を差し引いても残る候補だけに検証資源を寄せる mode です。

次に作るべき資料・artifact は、候補数を増やすものではなく、候補ごとに「攻めてよいか / 研究だけに戻すか / 捨てるか」を判定する `risk-taker review artifact` です。

## 確認範囲

- repo current docs:
  - `docs/REALISTIC_ROADMAP_CURRENT_2026-06-28.md`
  - `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md`
  - `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md`
- repo CLI:
  - `uv run sis strategy-idea-candidates-build --help`
  - `uv run sis crypto-perp-tournament-rows-v2 --help`
  - `uv run sis crypto-perp-tournament-gate --help`
- 外部一次情報:
  - Bitget Terms of Use
  - Bitget futures fee / order cost docs
  - Bitget API request interaction docs
  - Bitget liquidation guide
- 研究:
  - Kelly / risk-constrained Kelly
  - individual trader performance
  - cryptocurrency momentum / reversal
  - momentum crash / volatility management
  - perpetual futures / funding mechanism
  - bitcoin futures liquidation / leverage

## 現在の repo で使える足場

`strategy-idea-candidates-build` には `crypto-perp-risk-taker` profile があり、現在の help 上は default profile です。candidate cap は 250、shortlist は 10 です。

`crypto-perp-tournament-rows-v2` は `--fee-rate`、`--funding-rate`、`--slippage-bps`、`--operator-time-minutes`、`--operator-hourly-cost-usd` を受け取れます。これは actual cash ではありませんが、before-cost proxy より実務判断に近い cost-adjusted estimate です。

`crypto-perp-tournament-gate` は default で `--max-largest-loss-usd 25`、`--max-profit-concentration 0.60`、`--max-operator-time-minutes 120` を持っています。ここに `NO_TRADE` leader を許容するかどうかの明示 option もあります。

したがって、現時点での利益追求は次の順序が現実的です。

1. 候補を作る。
2. 同じ event set で `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を比較する。
3. fee / funding / slippage / operator time を入れた後でも `NO_TRADE` を上回るかを見る。
4. largest loss、profit concentration、operator time で落とす。
5. actual cash ledger が無い段階では、size-up や live permission へ進めない。

## 外部情報からの制約

### Venue / jurisdiction

Bitget Terms of Use は 2026-06-16 更新版で、eligibility と restricted person の条件を示しています。Terms では prohibited / restricted / illegal jurisdiction からの access を認めず、restricted person には prohibited countries に居住、設立、または operations がある者を含めています。本文中では United States 関連の prohibited 判定にも触れています。

実務上の扱い:

- `operator_jurisdiction_status` が `allowed` と確認できない限り、credentialed read、API key、exchange write、tiny live、live order に進めない。
- operator が United States またはその他 prohibited location に該当する可能性があるなら、Bitget は public data research / local simulation source に留める。
- compliant venue が別に必要なら、venue abstraction と fee / funding / instrument mapping を先に作る。

### Cost

Bitget の futures order cost docs は、USDT-M perpetual futures の例として maker 0.02%、taker 0.06% を示し、funding fee は `position value × funding rate` として説明しています。funding は通常 8 時間ごとですが、銘柄や条件により変わり得ます。

実務上の扱い:

- `fee_funding_slippage_breakeven_bps` を候補ごとに出す。
- taker 前提の entry / exit は round trip で見て、薄い edge を即座に殺す。
- funding carry を passive income と読まない。funding は spot との乖離を抑える mechanism であり、transaction cost、spread reversal、forced exit、funding interval timing に食われる。

### API / operational limits

Bitget API docs は、request が多すぎる場合 429 を返すこと、public market information interface の unified rate limit が最大 20 requests/sec であること、private endpoint は API key / signature 側の制限に従うことを示しています。

実務上の扱い:

- public data research と private signed endpoint を分ける。
- API rate limit は source freshness と execution feasibility の一部として扱う。
- risk-taker roadmap だけでは credentialed read / exchange write を許可しない。

### Liquidation / leverage

Bitget の liquidation guide は、overleveraging、stop-loss 不在、含み益に乗せた追加 position が liquidation cause になり得ると説明しています。さらに、funding fee、transaction cost、low liquidity、risk management system により、表示上の estimated liquidation price より早く liquidation risk が高まる可能性にも触れています。

実務上の扱い:

- position size は available margin から決めない。先に `max_loss_usd`、`stop_distance_bps`、`liquidation_buffer_bps` を決める。
- `liquidation_buffer_bps` と `stop_distance_bps` が近い candidate は落とす。
- funding fee erosion、flash crash、chain liquidation を tail scenario として review artifact に残す。

## 研究から使える知見

### 1. Kelly は上限であり、実務 size ではない

Kelly は長期成長率最大化の理論ですが、sample error、regime shift、fat tail、執行費用が大きい個人トレードでは、そのまま position size に使うと過大になります。

Busseti / Ryu / Boyd の risk-constrained Kelly は、drawdown probability constraint を入れて成長率と drawdown risk を trade off します。実装上は `kelly_fraction_raw` ではなく、`kelly_fraction_capped`、`estimation_error_haircut`、`drawdown_probability_limit`、`risk_unit_usd` を artifact に残すべきです。

### 2. 個人の active trading は平均的には不利

Barber / Odean は、高回転の個人投資家ほど市場に劣後しやすいことを示しています。Barber / Lee / Liu / Odean の Taiwan data でも、個人投資家の trading は大きな損失を生み、特に aggressive orders が損失要因とされています。

実務上は「自分だけは勝てる」という前提を置かず、`dollars_per_hour`、`actual_cash_edge_over_no_trade_usd`、`largest_loss_usd` を残して、費用後に本当に残っているかを見る必要があります。

### 3. Crypto momentum / reversal は試す価値があるが、信じる対象ではない

Liu / Tsyvinski / Wu は crypto の market、size、momentum factor を示しています。Wen / Bouri / Xu / Zhao は intraday momentum と reversal の evidence を示し、large intraday jumps、FOMC announcement、liquidity、COVID-19 などで pattern が変わることも示しています。

つまり、`perp_momentum_continuation`、`perp_reversal_after_liquidation_move`、`perp_basis_mark_index_spread`、`perp_volatility_breakout_compression` は検証対象として妥当です。ただし、論文上の factor は Bitget USDT-M perpetual の現在の executable edge ではありません。

### 4. Momentum は crash する

Barroso / Santa-Clara は momentum の crash risk と volatility management の重要性を示しています。risk-taker candidate は、profit だけでなく `volatility_state`、`panic_state`、`recent_jump_state`、`single_symbol_concentration`、`market_rebound_risk` を出す必要があります。

実務上は、high volatility、post-crash rebound、funding crowding、spread widening のときに size を維持しない設計にします。

### 5. Perpetual futures は funding があるから収束する、ではない

He / Manela / Ross / von Wachter は、perpetual futures が満期を持たず、fixed-maturity futures のように spot へ必ず収束するわけではないこと、funding が futures / spot gap を抑える mechanism であることを示しています。

実務上は、funding carry を単独の勝ち筋にしません。holding time、funding interval、entry / exit spread、forced exit、liquidity、fee tier を同時に見る必要があります。

### 6. Liquidation は通常分布で見積もらない

Cheng / Deng / Wang / Yu は、bitcoin perpetual futures の liquidation / leverage / margin を扱い、return の normality assumption が optimal margin を大きく過小評価し得ることを示しています。risk-taker mode では、平均損益よりも tail、forced liquidation、margin buffer を先に見る必要があります。

実務上は、`max_loss_usd`、`largest_loss_usd`、`max_adverse_excursion_R`、`liquidation_buffer_bps`、`margin_mode`、`isolated_margin_required` を candidate artifact に入れます。これが無い candidate は、利益が出ていても size-up しません。

## Risk-Taker Review Artifact に入れるべき項目

| Field | 用途 | Stop / Kill 条件 |
| --- | --- | --- |
| `operator_jurisdiction_status` | operator が venue を使えるか | `prohibited` / `unknown` は live / credential / tiny-live 禁止 |
| `venue_terms_checked_at` | 規約確認時刻 | 古い、または Terms 更新後は再確認 |
| `source_freshness_status` | market / funding / spread source の鮮度 | stale / missing は `INCONCLUSIVE_DATA` |
| `after_cost_edge_over_no_trade` | 費用後に `NO_TRADE` を上回るか | 0 以下は kill |
| `fee_funding_slippage_breakeven_bps` | 何 bps 動けば費用を超えるか | expected move より大きければ kill |
| `expected_R_after_stress_cost` | stress cost 後の期待 R | 0 以下は shortlist しない |
| `actual_cash_edge_over_no_trade_usd` | 実損益 basis の差分 | proxy / estimate で代用禁止 |
| `risk_unit_usd` | 1R の損失額 | daily / weekly loss budget 超過なら kill |
| `largest_loss_usd` | 一撃死リスク | gate threshold 超過なら kill |
| `max_adverse_excursion_R` | entry 後の逆行耐性 | stop / liquidation buffer を食うなら kill |
| `liquidation_buffer_bps` | 清算までの距離 | stop が清算に近すぎるなら kill |
| `capital_tied_up_minutes` | 資金拘束 | edge に対して長すぎるなら kill |
| `dollars_per_hour` | operator 時間あたり期待値 | 手動監視に見合わなければ kill |
| `volatility_state` | crash / rebound / noise 状態 | high volatility では size down / no trade |
| `panic_state` | liquidation cascade / event shock | panic 中は no trade または reduced risk |
| `profit_concentration` | 少数 event 依存 | gate threshold 超過なら kill |

## 実装前の判断表

| 判断 | 進む | 止める |
| --- | --- | --- |
| Venue | operator jurisdiction が allowed、Terms 確認済み | prohibited / unknown / Terms stale |
| Source | rows、timestamp、available-at、funding、spread が揃う | source missing / stale / 0-fill が必要 |
| Cost | fee / funding / slippage / operator time 後に positive | before-cost だけ positive |
| NO_TRADE 比較 | actual cash または conservative estimate で上回る | `NO_TRADE` が leader |
| Tail | largest loss、MAE、liquidation buffer が許容範囲 | 一撃で週次 loss budget を壊す |
| Skill evidence | 複数 event で再現 | 1 winner、single split、過剰な後知恵 |
| Time | `dollars_per_hour` が手動監視に見合う | 監視負荷が profit を食う |

## Practical Selection Rule

1. `operator_jurisdiction_status` が `allowed` でない venue は実行候補にしない。
2. source が薄い candidate は攻めない。missing source は 0 埋めせず `INCONCLUSIVE_DATA` として止める。
3. cost / stress cost 後に `NO_TRADE` を上回らない candidate は落とす。
4. `expected_R_after_stress_cost` が positive でも、`largest_loss_usd`、`max_adverse_excursion_R`、`liquidation_buffer_bps`、`operator_time_minutes` が悪ければ落とす。
5. event 数が少ない段階では Kelly を使わず、fixed loss budget にする。
6. actual cash ledger が無い段階では size-up しない。
7. high volatility、panic、funding crowding、spread widening では entry を止めるか size を落とす。

## Better Implementation Target

次の改善は `crypto-perp-risk-taker` の候補 family を増やすことではなく、candidate / event / action ごとに以下を出す review artifact を作ることです。

- `operator_jurisdiction_status`
- `venue_terms_checked_at`
- `source_freshness_status`
- `after_cost_edge_over_no_trade`
- `fee_funding_slippage_breakeven_bps`
- `expected_R_after_stress_cost`
- `actual_cash_edge_over_no_trade_usd`
- `risk_unit_usd`
- `largest_loss_usd`
- `max_adverse_excursion_R`
- `liquidation_buffer_bps`
- `capital_tied_up_minutes`
- `dollars_per_hour`
- `volatility_state`
- `panic_state`
- `profit_concentration`
- `kill_reason`

artifact の読み方は単純にします。

- `EXECUTION_CANDIDATE`: jurisdiction、source、cost、tail、time がすべて通る。
- `RESEARCH_ONLY`: source または legal / venue certainty が足りず、実行には進めない。
- `KILL`: `NO_TRADE`、cost、tail、operator time、profit concentration のどれかで失格。
- `INCONCLUSIVE_DATA`: source 欠損で判断不能。勝ち扱いにしない。

## 参考資料

- Bitget, [Terms of Use](https://www.bitget.com/support/articles/360014944032-terms-of-use)
- Bitget, [How to Calculate Order Costs in Bitget Futures?](https://www.bitget.com/support/articles/12560603828198)
- Bitget, [Request Interaction](https://www.bitget.com/api-doc/common/signature-samaple/interaction)
- Bitget, [How to Avoid Liquidation in Futures Trading?](https://www.bitget.com/support/articles/12560603808523)
- Kelly, [A New Interpretation of Information Rate](https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf)
- Busseti, Ryu, Boyd, [Risk-Constrained Kelly Gambling](https://arxiv.org/abs/1603.06183)
- Barber, Odean, [Trading Is Hazardous to Your Wealth](https://ideas.repec.org/a/bla/jfinan/v55y2000i2p773-806.html)
- Barber, Lee, Liu, Odean, [Just How Much Do Individual Investors Lose by Trading?](https://academic.oup.com/rfs/article-abstract/22/2/609/1595677)
- Liu, Tsyvinski, Wu, [Common Risk Factors in Cryptocurrency](https://ideas.repec.org/a/bla/jfinan/v77y2022i2p1133-1177.html)
- Wen, Bouri, Xu, Zhao, [Intraday return predictability in the cryptocurrency markets](https://ideas.repec.org/a/eee/ecofin/v62y2022ics1062940822000833.html)
- Barroso, Santa-Clara, [Momentum Has Its Moments](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2041429)
- He, Manela, Ross, von Wachter, [Fundamentals of Perpetual Futures](https://arxiv.org/abs/2212.06888)
- Cheng, Deng, Wang, Yu, [Liquidation, Leverage and Optimal Margin in Bitcoin Futures Markets](https://arxiv.org/abs/2102.04591)

## 抜け・漏れ・誤謬リスク

- Bitget Terms、fee、API limit は current 情報であり、実装直前に再確認が必要です。
- この資料は法務、税務、投資助言ではありません。特に United States 関連の eligibility は、Terms と実際の居住地・法人関係・使用サービス範囲で変わり得ます。
- Bitget 以外の compliant venue は未評価です。operator が Bitget を使えない場合は、venue 切替と instrument / fee / funding / API mapping が別 task になります。
- 研究論文は market-level / historical sample の evidence であり、この repo の strategy が今後儲かる証明ではありません。
- `crypto-perp-tournament-rows-v2` は estimate であり actual cash ではありません。actual cash ledger または live measurement artifact が無い限り、size-up の根拠にしません。
- API availability、symbol availability、fee tier、funding interval、liquidity、delisting は変わり得ます。source freshness を artifact に入れない判断は危険です。
