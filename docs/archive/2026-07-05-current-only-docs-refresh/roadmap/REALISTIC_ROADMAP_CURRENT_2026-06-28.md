<!--
作成日: 2026-06-28_14:56 JST
更新日: 2026-06-28_17:10 JST
-->

# Realistic Roadmap Current

## 結論

次にやるべきことは、追加機能を増やすことではなく、C9 bridge（shortlist 済みの戦略アイデア候補を、この repo の Strategy Authoring spec / backtest pack まで候補別に接続する変換経路）修正後に実データで再実行し、evidence quality（候補判断に使う証拠の実データ性、欠損の明示、actual cash との距離の明確さ）を上げることです。

backtest、Strategy Review、Workbench は判断材料です。profit proof、paper execution permission、live readiness、wallet readiness、signing readiness、exchange write readiness ではありません。

この文書は standalone roadmap です。既存入口 docs からリンクしません。品質確認だけは `scripts/check_current_docs.py` の対象に入れます。

## 正本

この roadmap は次を正本として読みます。

- [CURRENT_STATE.md](CURRENT_STATE.md)
- [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
- [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
- [strategy_idea_candidates/README.md](strategy_idea_candidates/README.md)
- [strategy_idea_candidates/GOAL_AND_GLOSSARY.md](strategy_idea_candidates/GOAL_AND_GLOSSARY.md)
- [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)
- [crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md)
- `uv run sis --help`

実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、lockfile、CI、CLI help です。`data/` は runtime / generated state であり、fresh checkout では再生成対象です。

`./.ai_memory/HANDOFF.md` は restart artifact です。現 checkout では stale の可能性があるため、この roadmap の正本にしません。

固定 pass count、固定 current-doc count、古い artifact snapshot はこの文書に置きません。必要な時にコマンドを再実行します。

## Lane 1: Strategy Idea / C9 Bridge

最短の次実務は、C9 bridge（shortlist 済み候補を Strategy Authoring と標準 backtest pack に候補別 artifact として渡す変換経路）の実データ再実行です。

1. `strategy-idea-candidates-bitget-source-refresh` で C9 bridge 互換 source root（bridge が読める形式に整えた Bitget public market data の local directory）を作る。
2. `strategy-idea-candidates-authoring-bridge` を相対 `--out` で再実行する。
3. bridge manifest（候補ごとに入力、出力、生成 artifact、停止理由をつなぐ一覧）の `BRIDGED`（候補別 spec / suite / bundle / backtest pack validation まで通った状態）と `BLOCKED_*`（変換不能、source 不足、validation 失敗などで止めた状態）を候補単位で整理する。
4. `BRIDGED` 候補だけを Strategy Review / Workbench（人間レビューや静的 HTML 表示で候補の証拠を読むための surface）に流す。
5. `BLOCKED_*` 候補は手動で成功扱いにしない。

C9 v0（C9 bridge の最初の限定版。全候補ではなく、対応 family だけを安全に変換し、変換不能なら blocker として止める実装）の対応 family は `perp_momentum_continuation` と `perp_funding_rate_carry_filter` だけです。その他の Perp family（この repo の候補 generator が使う戦略テンプレート分類）は v0 対応外として止めます。

`venue_cost_matrix.csv` は `ESTIMATE_ONLY` です。実測 slippage、実 fill、actual cash、live measurement の証拠として読んではいけません。

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis strategy-idea-candidates-bitget-source-refresh \
  --symbol BTCUSDT \
  --product-type USDT-FUTURES \
  --granularity 5m \
  --limit 200 \
  --out data/strategy_idea_candidates/btc-perp/bitget_public_source

uv run sis strategy-idea-candidates-authoring-bridge \
  --candidate-set data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json \
  --export-manifest data/strategy_idea_candidates/btc-perp/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json \
  --ledger data/strategy_idea_candidates/btc-perp/search_ledger.jsonl \
  --prep-watchdeck-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --out data/strategy_idea_candidates/btc-perp/authoring_bridge
```

public network は明示承認と opt-in がある時だけ使います。承認がない場合は local source root の存在確認、bridge help、fixture / existing artifact の検査までに止めます。

## Lane 2: Crypto Perp Profit Evidence

利益判断の次段は、同じ event set で `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を比較することです。

`NO_TRADE` は失敗ではありません。正式 action として比較し、`NO_TRADE` が leader の時は無理に trade action を採用しません。

`crypto-perp-tournament-rows-preview` は before-cost proxy です。actual cash report の入力ではありません。

`crypto-perp-tournament-rows-v2` は cost-adjusted estimate / stress estimate です。fee、funding、slippage、operator time の見積を含められますが、実現損益ではありません。

actual cash report に進むには、cash ledger または live measurement artifact が必要です。欠損 source は 0 埋めせず、`INCONCLUSIVE_DATA` を正式な停止結果として残します。

```bash
uv run sis crypto-perp-source-availability --help
uv run sis crypto-perp-replay-slice --help
uv run sis crypto-perp-feature-pack --help
uv run sis crypto-perp-edge-score --help
uv run sis crypto-perp-tournament-rows-v2 --help
uv run sis crypto-perp-bias-guard --help
uv run sis crypto-perp-tournament-report --help
uv run sis crypto-perp-tournament-gate --help
```

actual cash path へ進める時だけ、cash ledger 系 surface を使います。

```bash
uv run sis crypto-perp-cash-ledger --help
uv run sis crypto-perp-actual-cash-rows-build --help
uv run sis crypto-perp-actual-cash-report-gate --help
```

## Lane 3: Strategy Ops / Paper Observation

Strategy Review の `READY_FOR_HUMAN_REVIEW` は、人間レビューの準備完了です。paper 実行許可ではありません。

normal paper observation には、新しい trading day を含む evidence が必要です。同日 artifact の再実行だけでは normal observation の日数は増えません。

smoke pass と normal threshold は分けて読みます。smoke は導通確認であり、normal paper observation pass ではありません。

Drift Review、Learning、Revision Request は authoring 改善の材料です。Strategy Authoring YAML を自動編集する許可ではありません。

```bash
uv run sis strategy-review-build --help
uv run sis strategy-review-record --help
uv run sis strategy-paper-observation-status --help
uv run sis strategy-drift-review --help
uv run sis strategy-learning-ledger-update --help
uv run sis strategy-revision-request-build --help
uv run sis strategy-revision-request-review --help
```

## Lane 4: NDX / Venue-Neutral Research

backtest-first / venue-neutral を維持します。

NDX Layer gates は local research / paper-observation gate です。alpha、wallet、exchange write、live readiness を証明しません。

Trade[XYZ] は実装済み read-only venue context ですが、default product axis に戻しません。Trade[XYZ] 前提の collector、readiness claim、order path work は、ユーザーが明示的に Trade[XYZ] scope を指定した時だけ扱います。

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import \
  --pack data/research/ndx/review/llm_review_input.json \
  --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate \
  --root configs/research_layer_2_2/ndx \
  --pack data/research/ndx/review/llm_review_input.json \
  --review data/research/ndx/review/normalized_review.json \
  --out data/research/ndx/review
```

## Lane 5: Human Approval / Tiny Live

`crypto-perp-tiny-live-shadow` と tiny-live review packet は、実発注なしの readiness artifact です。

tiny live measurement は、次が揃うまで roadmap の実行対象にしません。

- 別の明示承認
- isolated margin
- withdrawal disabled API key
- IP restriction
- max notional 25 USD
- flat reconciliation

production live trading、wallet、signing、exchange write、自動売買は通常の次手に入れません。

```bash
uv run sis crypto-perp-tiny-live-shadow --help
uv run sis crypto-perp-tiny-live-review-packet --help
uv run sis crypto-perp-tiny-live-shadow-readiness --help
```

## Research Notes For Implementation

実装前の外部研究は、候補を増やすためではなく、候補を止める条件を強くするために使います。ここに挙げる知見は profit proof ではありません。

Backtest overfitting / data snooping:

- Candidate generation は複数仮説検定として扱う。`candidate_count_total`、`trial_count`、`parameter_grid_hash`、`selection_policy`、`rejection_reason` を保存しない候補評価は採用判断に使わない。
- PBO / CSCV、Deflated Sharpe Ratio、White Reality Check、Hansen SPA は、良い backtest を証明する道具ではなく、探索後に見つかった winner が偶然であるリスクを読むための guard として扱う。
- raw Sharpe、raw p-value、single split の勝ち、best candidate だけの report は evidence quality が低い。必要入力が足りない場合は `NOT_ESTIMABLE` または `INCONCLUSIVE_DATA` として止める。

Multiple testing / factor zoo:

- family と parameter grid を増やすほど、通常の有意性基準は甘くなる。新しい factor / signal は通常の t-stat や p-value だけで十分とは読まない。
- `BRIDGED` 候補でも、bridge validation は artifact 接続の成功であって alpha proof ではない。候補全量、棄却数、失敗理由、探索量を review source として残す。

Crypto perpetual futures / funding:

- funding rate は perps の価格を spot に寄せる mechanism であり、単体の安定収益源とは読まない。
- perpetual futures は満期がなく、fixed-maturity futures のような強制収束を前提にできない。`perp_funding_rate_carry_filter` は fee、funding、slippage、holding time、exit risk を同時に見る。
- funding / basis の opportunity は transaction cost、spread reversal、forced exit、venue fragmentation に弱い。estimate は actual cash と分ける。

Transaction cost / microstructure:

- `crypto-perp-tournament-rows-v2` の fee、funding、slippage、operator time は必須の conservative estimate として扱う。
- before-cost proxy を actual cash report に渡さない。cash ledger または live measurement artifact が無い限り、`actual_cash_result_usd` は証拠として使わない。
- crypto data は venue 差、volume quality、liquidity、price discovery の差が大きい。source row count、timestamp、available-at、missing source、known gaps を candidate / event 単位で残す。

Implementation consequences:

- C9 bridge 後の manifest は、candidate id、family、parameter set hash、candidate set hash、export manifest hash、ledger hash、artifact paths、bridge status、blocker reason を候補単位で持つ。
- `crypto-perp-bias-guard` は event 数、fold 数、lookahead、recursive warmup、profit concentration、largest loss を採用前の停止条件として扱う。
- `NO_TRADE` は正式 action のまま残す。`NO_TRADE` が leader の時、trade action へ手動で差し替えない。
- 研究論文や外部 article は実装判断の guardrail であり、この repo の候補が儲かる根拠ではない。

Primary references:

- Bailey, Borwein, López de Prado, Zhu, [The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)
- Bailey, López de Prado, [The Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)
- White, [A Reality Check for Data Snooping](https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf)
- Hansen, [A Test for Superior Predictive Ability](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569)
- Harvey, Liu, Zhu, [...and the Cross-Section of Expected Returns](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314)
- He, Manela, Ross, von Wachter, [Fundamentals of Perpetual Futures](https://arxiv.org/html/2212.06888v5)
- Bank for International Settlements, [Crypto carry](https://www.bis.org/publ/work1087.pdf)
- Easley, O'Hara, Yang, Zhang, [Microstructure and Market Dynamics in Crypto Markets](https://stoye.economics.cornell.edu/docs/Easley_ssrn-4814346.pdf)
- [The Two-Tiered Structure of Cryptocurrency Funding Rate Markets](https://www.mdpi.com/2227-7390/14/2/346)

## Risk-Taker Research Base For Personal Trader

個人トレーダー向けの risk-taker mode は、guard を外して大きく張ることではありません。利益追求のために、期待値が残りやすい仮説へ検証速度を寄せ、損失上限、清算距離、手数料後の残り幅、operator の実行負荷を先に固定する mode です。これは live order permission ではありません。

Reality check:

- 個人の active trading は平均的には不利です。Barber / Odean は高回転の個人投資家ほど市場に劣後しやすいことを示し、day trader 研究でも net positive abnormal return を継続できる層はごく小さい。risk-taker mode は「自分も勝てるはず」という前提ではなく、自分の skill が費用後に残っているかを検証するものです。
- したがって最初の profit target は `勝つこと` ではなく、`after-fee / after-funding / after-slippage / after-operator-time で NO_TRADE を上回る candidate が反復して残ること` に置きます。

Practical profit metrics:

- `operator_jurisdiction_status`: operator がその venue を使える地域にいるか。prohibited / unknown の場合、credentialed read、exchange write、live order、tiny-live measurement に進まない。
- `expected_R_after_stress_cost`: stress cost 後の期待 R。0 以下なら shortlist しない。
- `actual_cash_edge_over_no_trade_usd`: actual cash basis で `NO_TRADE` を上回った差分。proxy / estimate では代用しない。
- `dollars_per_hour`: expected profit / operator time。手動監視が重い候補を過大評価しない。
- `capital_tied_up_minutes`: 資金拘束時間。短期 edge でも資金拘束が長いなら個人には不利。
- `max_adverse_excursion_R`、`max_drawdown_usd`、`largest_loss_usd`: 一撃死と連敗耐性を見る。
- `fee_funding_slippage_breakeven_bps`: maker/taker fee、funding、spread、slippage を超えるために必要な最低値幅。

Sizing and bankroll:

- position size は available margin から決めない。先に `max_loss_usd`、`stop_distance_bps`、`liquidation_buffer_bps`、`max_daily_loss_usd`、`max_weekly_loss_usd` を決め、その loss budget から notional を逆算する。
- Kelly は最大成長の理論上限として読む。実務では sample error と regime shift が大きいため、actual cash sample が揃うまで full Kelly を使わない。
- Baker / McHale は parameter uncertainty があるなら Kelly bet を縮小すべきとする。Busseti / Ryu / Boyd は drawdown probability constraint を持つ risk-constrained Kelly を提示している。したがって artifact には `kelly_fraction_raw` より `kelly_fraction_capped`、`estimation_error_haircut`、`drawdown_probability_limit` を残す。
- event 数が少ない時は Kelly ではなく fixed fractional / fixed loss budget を使う。candidate 単位では `risk_unit_usd`、`expected_R`、`worst_case_R`、`payoff_skew`、`time_to_invalidate_minutes`、`max_consecutive_loss_budget`、`capital_at_risk_usd` を残す。

Signal families worth testing, not trusting:

- Crypto 研究では time-series momentum、cross-sectional momentum、size、investor attention、短期 momentum / 長め horizon reversal、intraday momentum / reversal の証拠がある。ただしこれは平均的・過去 sample の話であり、Bitget USDT-FUTURES の今の executable edge ではありません。
- `crypto-perp-risk-taker` では、`perp_momentum_continuation`、`perp_reversal_after_liquidation_move`、`perp_basis_mark_index_spread`、`perp_volatility_breakout_compression`、`perp_open_interest_liquidation_pressure` を high-upside family として優先できます。
- ただし C9 v0 bridge は現時点で `perp_momentum_continuation` と `perp_funding_rate_carry_filter` だけ対応します。未対応 family は promising でも `BRIDGED` にしない。

Momentum crash and regime handling:

- Momentum は crash するものとして扱う。Barroso / Santa-Clara と Daniel / Moskowitz は momentum crash と volatility management の重要性を示し、crypto momentum tail 研究も severe crash と single-name concentration risk を指摘している。
- risk-taker candidate は `volatility_state`、`panic_state`、`recent_jump_state`、`market_rebound_risk`、`single_symbol_concentration` を review source に出す。
- high volatility / post-crash rebound / funding crowding / spread widening の時は、entry を止めるか size を落とす。勝ち筋 narrative を優先して size を維持しない。

Perp-specific execution reality:

- Bitget Terms of Use は prohibited countries に United States を含めています。operator が米国居住、米国領内、またはその他 prohibited location に該当する場合、Bitget は public data research / local simulation の候補 source に留め、live / credential / exchange-write venue として扱わない。
- Perpetual futures は満期がなく、funding が spot との乖離を抑える mechanism です。funding carry は passive income ではなく、spread reversal、transaction cost、forced exit、funding interval timing に食われます。
- Bitget の public docs では USDT-M perpetual futures の例として maker 0.02%、taker 0.06% が示され、funding fee は position value × funding rate で計算されます。実際の rate は account level / official announcements / product conditions で変わるため、実装直前に公式値を再確認します。
- 清算は「理論上の最大損失」ではなく、手動 exit 失敗、stop 不発、gap、funding、fee、margin rule change を含む実行リスクです。Bitget docs も overleveraging と stop-loss 不在を liquidation cause として説明している。
- Bitget API は public market data と private signed endpoints の境界があり、public market information は rate limit、private endpoint は signature / API key が必要です。risk-taker roadmap だけでは credentialed read / exchange write を許可しません。

Practical selection rule:

1. operator jurisdiction / venue availability が prohibited または unknown なら、実行候補にしない。合法・規約上使える venue へ移すか、research-only に落とす。
2. source が薄い candidate は攻めない。row count、timestamp、available-at、symbol coverage、funding availability、spread / slippage source を見る。
3. stress cost 後に `NO_TRADE` を上回らない candidate は攻めない。
4. `expected_R_after_stress_cost` が positive でも、`largest_loss_usd`、`max_adverse_excursion_R`、`liquidation_buffer_bps`、`operator_time_minutes` が悪ければ落とす。
5. `dollars_per_hour` が低い候補は、勝っていても個人トレーダー向きではない。
6. actual cash sample が無い段階では、position size を大きくする理由を作らない。

Better implementation target:

- `crypto-perp-risk-taker` の次の改善は、候補生成量を増やすことより、risk-taker review artifact に `operator_jurisdiction_status`、`venue_terms_checked_at`、`after_cost_edge_over_no_trade`、`fee_funding_slippage_breakeven_bps`、`risk_unit_usd`、`expected_R_after_stress_cost`、`max_adverse_excursion_R`、`capital_tied_up_minutes`、`dollars_per_hour`、`volatility_state`、`panic_state`、`source_freshness_status` を出すことです。
- tiny-live や実発注へ進む前に、actual cash ledger で `NO_TRADE` を上回る差分が複数 event で残るかを確認します。

Risk-taker references:

- Kelly, [A New Interpretation of Information Rate](https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf)
- Busseti, Ryu, Boyd, [Risk-Constrained Kelly Gambling](https://stanford.edu/~boyd/papers/kelly.html)
- Baker, McHale, [Optimal Betting Under Parameter Uncertainty](https://ideas.repec.org/a/inm/ordeca/v10y2013i3p189-199.html)
- Barber, Odean, [Trading is Hazardous to Your Wealth](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=219228)
- Barber, Lee, Liu, Odean, [The Cross-Section of Speculator Skill](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=529063)
- Liu, Tsyvinski, [Risks and Returns of Cryptocurrency](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3226952)
- Liu, Tsyvinski, Wu, [Common Risk Factors in Cryptocurrency](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3379131)
- Dobrynskaya, [Cryptocurrency Momentum and Reversal](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3913263)
- Wen, Bouri, Xu, Zhao, [Intraday return predictability in the cryptocurrency markets](https://ideas.repec.org/a/eee/ecofin/v62y2022ics1062940822000833.html)
- Barroso, Santa-Clara, [Momentum Has Its Moments](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2041429)
- Daniel, Moskowitz, [Momentum Crashes](https://www.nber.org/papers/w20439)
- Cheng, Deng, Wang, Yu, [Liquidation, Leverage and Optimal Margin in Bitcoin Futures Markets](https://arxiv.org/abs/2102.04591)
- He, Manela, Ross, von Wachter, [Fundamentals of Perpetual Futures](https://arxiv.org/html/2212.06888v5)
- [The Two-Tiered Structure of Cryptocurrency Funding Rate Markets](https://www.mdpi.com/2227-7390/14/2/346)
- Bitget, [Terms of Use](https://www.bitget.com/support/articles/360014944032-terms-of-use)
- Bitget, [Understanding Futures Fees](https://www.bitget.com/support/articles/12560603817155)
- Bitget, [How to Avoid Liquidation in Futures Trading](https://www.bitget.com/support/articles/12560603808523)
- Bitget, [API Docs](https://bitgetlimited.github.io/apidoc/en/mix/)

## Stop Conditions

- C9 bridge（shortlist 済み候補を Strategy Authoring / backtest artifact に変換する経路）が `BLOCKED_*`（変換不能や source 不足などの明示的な停止結果）を返した候補を、手動で `BRIDGED`（候補別 backtest pack validation まで通った状態）扱いにしない。
- backtest validation `PASS` を profit proof と読まない。
- proxy / estimate rows を actual cash report に食わせない。
- source availability が不足している event を 0 埋めで進めない。
- `NO_TRADE` が leader の時に、無理に trade action を採用しない。
- event 数不足、profit concentration、largest loss、operator time が悪い場合は、追加実装より候補停止を優先する。
- explicit approval なしに public network、credentialed read、exchange write、live order、tiny-live measurement を実行しない。
- `READ_ONLY_GO`、`READY_FOR_HUMAN_REVIEW`、backtest pack validation `PASS` を、paper / live / wallet / signing / exchange-write permission と読まない。

## Verification

この文書を更新した時は、固定 count ではなく次のコマンドを再実行します。

```bash
uv run python scripts/check_current_docs.py
git diff --check
uv run sis --help
```

必要に応じて CLI 個別 help も spot check します。

```bash
uv run sis strategy-idea-candidates-authoring-bridge --help
uv run sis strategy-idea-candidates-bitget-source-refresh --help
uv run sis crypto-perp-profit-readiness-plan --help
uv run sis crypto-perp-profit-readiness-run-local --help
```
