<!--
作成日: 2026-07-14_22:08 JST
更新日: 2026-07-14_22:08 JST
-->

# D01 推奨解決案 R01: Campaign成功、Vault、Impact会計

記録日時: 07月14日(火)_午後10時08分28秒.

## 0. この文書の位置づけ

この文書は、[D01: 小資本・正の歪度・Campaign運用](./HYPOTHESIS_SEARCH_ENGINE_DIRECTION_01_CONVEX_CAMPAIGN_2026-07-14.md)で未決となった`D01-U001`、`D01-U002`、`D01-U003`と、残るdata、venue、parameter、方向性統合、文書保存のリスクに対する推奨回答を記録する。

- recommendation id: `D01-R01`
- status: `RECOMMENDATION_RECORDED / PENDING_USER_ADOPTION`
- implementation status: `NOT_IMPLEMENTED`
- master-plan integration: `NOT_STARTED`
- CP0: `NOT_STARTED`
- branch: 未作成
- code/schema/config/dependency/data/CLI変更: なし

この文書に記載した推奨は、自動的な採用決定ではない。ユーザーが採用を明示した後、D01本体のdecision ledgerを`DECISION_REQUIRED`から`POLICY_ADOPTED`へ変更する。採用前に実装者が推奨案を確定仕様として使ってはならない。

## 1. 結論

推奨する3つの中核決定は次である。

1. **D01-U001**: Ratchet回収額を含むGeneration全体の確定wealthが目標倍率へ到達した時点をCampaign成功とする。
2. **D01-U002**: Profit VaultとPrincipal Recovery Vaultは自動Rebaseの原資へ戻さない。
3. **D01-U003**: 生活Impactは、市場riskから保護された純利益由来の確定資金で判定する。

これにより、次が同時に成立する。

- 「10倍」がRatchet有無で10倍と10.5倍へ揺れない。
- 一度保護した資金を不調期へ自動再投入しない。
- 初期元本回収、内部transfer、含み益を生活Impact利益へ水増ししない。
- Strategy edgeとcapital wrapperを同じ単位で比較できる。
- Campaign Simulatorの資金保存fixtureを一意に作れる。

## 2. D01-U001 推奨: Generation全体の確定wealthで成功判定

### 2.1 推奨式

```text
campaign_progress_wealth
= machine_settled_balance
  + cumulative_generation_ratchet_withdrawals
```

```text
campaign_success
<=> campaign_progress_wealth
    >= generation_initial_balance * campaign_target_multiple
```

ここで扱うのは、当該Generationに帰属する確定済み資金だけである。open positionのunrealized PnL、別GenerationのVault、別機体の利益、Reload Poolは加算しない。

### 2.2 500 USD、10倍Campaignの例

```text
generation_initial_balance B       =   500 USD
campaign_target_multiple K         =    10
campaign_target_total_wealth K*B   = 5,000 USD
```

4倍到達時に初期元本の50%をRatchet回収する。

```text
Ratchet判定前の機体残高           2,000 USD
Ratchet回収額                        250 USD
Ratchet後の機体残高                1,750 USD
Generation累積Ratchet回収額          250 USD
```

Campaign成功時に必要な機体残高は次になる。

```text
required_machine_balance
= campaign_target_total_wealth
  - cumulative_generation_ratchet_withdrawals
= 5,000 - 250
= 4,750 USD
```

したがって、成功時の総額は厳密に5,000 USDである。

```text
機体確定残高                       4,750 USD
Ratchet回収済み                      250 USD
---------------------------------------------
Campaign総確定wealth               5,000 USD
```

### 2.3 成功後の資金route

次Generationの種銭を500 USDとする場合:

```text
機体から次Generationへ残す            500 USD
機体からScale Reserveへ移す          4,250 USD
Ratchetで既に保護済み                  250 USD
---------------------------------------------
開始元本を除くCampaign純増            4,500 USD
                                     = +9 R_campaign
```

これにより、当初の理想化した`死亡 -1 R_campaign / 成功 +9 R_campaign`と整合する。ただし、この二択式はfee、funding、時間、途中trade、Reload、相関を無視するため、実市場の必要成功率には使わない。

### 2.4 推奨する名称

`success_multiple`や`machine_balance_cap_multiple`だけでは意味が曖昧になる。次へ分ける。

```yaml
campaign_target:
  basis: total_settled_generation_wealth
  multiple: 10
  includes_generation_ratchet_withdrawals: true
  includes_unrealized_pnl: false

machine_account:
  settled_balance_hard_cap: optional
```

Campaign目標と機体口座hard capは別である。hard capは異常overshoot、venue limit、operator mistakeを防ぐ上限であり、成功倍率の定義ではない。

### 2.5 この案を推奨する理由

- Ratchetあり・なしを同じ成功倍率で比較できる。
- 資産帯別の10倍、6倍、3倍、2倍を同じ式で扱える。
- Ratchet追加によって期待payoffが暗黙に変わらない。
- 以前の5,000 USDから9,500 USDへ増える例と整合する。
- `R_campaign`、Break-even sanity fixture、cash ledgerが単純になる。
- 人間の説明、schema、Simulatorが同じ成功条件を使える。

### 2.6 棄却する代替案

機体自身の残高が5,000 USDへ到達するまで走らせ、Ratchet 250 USDを別に保持する案は、総Campaign wealthを5,250 USD、純増を+9.5Rにする。このpayoffを意図的に狙う別policyとして試すことは可能だが、名前を`10x`にしてはならない。

```yaml
alternative_policy:
  id: MACHINE_BALANCE_10X_PLUS_RATCHET
  total_wealth_multiple: 10.5
  status: NOT_DEFAULT
```

## 3. D01-U002 推奨: Vaultを自動Rebaseへ戻さない

### 3.1 Vaultの非交渉条件

一度Vaultへ移した資金は、通常のRatchet、Reload、Rebase、target chasingから隔離する。

```yaml
vault:
  automatic_redeployment_allowed: false
  counts_toward_wealth_milestone: true
  counts_toward_rebase_eligible_equity: false
  counts_as_reload_pool: false
  can_become_trading_collateral: false
```

Vaultから再投入したい場合は、自動処理ではなく、新しい投資判断として扱う。

```text
VAULT_REDEPLOYMENT_PROPOSED
-> human review
-> amount and purpose freeze
-> new Capital Epoch
-> external contribution相当で記録
```

### 3.2 Wealth MilestoneとCapital Rebaseを分ける

総資産が1.6倍になった事実と、再投入可能額が1.6倍になった事実は同じではない。

#### Wealth Milestone

```text
confirmed_system_wealth
= machine balances
  + reload pool
  + scale reserve
  + principal recovery vault
  + protected profit vault
  - settled liabilities
```

これは成長の報告、生活Impact、資金保存監査に使う。

#### Capital Rebase Eligibility

```text
rebase_eligible_equity
= machine balances
  + reload pool
  + scale reserve
  - reserved maximum loss
  - settled liabilities
```

Vaultと完了済み外部withdrawalは除外する。

### 3.3 Rebaseの推奨処理

```text
1. 全position close
2. fee/funding/liability確定
3. 24時間minimum threshold確認
4. rebase_eligible_equityを計算
5. 増加利益の50%をnew operating capへ追加
6. 残り50%をProtected Profit Vaultへ移す
7. new Generationだけnew policyを適用
```

Rebase後の運用額を作るだけのeligible equityがなければ、Rebaseを延期する。Vaultから不足分を補わない。

### 3.4 8,000 USD例

旧運用上限5,000 USD、eligible equity 8,000 USD、増加利益3,000 USDなら:

```text
new operating cap increase     1,500 USD
Protected Profit Vault         1,500 USD
new operating cap total        6,500 USD
```

一方、system wealthが8,000 USDでも、その中に既存Vault 2,000 USDが含まれ、eligible equityが6,000 USDしかない場合:

```text
system wealth milestone        PASS
capital rebase 1.6x            NOT READY
```

この分離により、保護資金を使ってRebase条件を見せかけ上満たすことを防ぐ。

### 3.5 物理的隔離

台帳だけVaultにしても、cross marginやauto-marginがその残高をcollateralへ使えるなら保護されていない。

初期研究contractの推奨は次である。

```yaml
margin_assumption:
  mode: isolated
  auto_margin_replenishment: false
  cross_collateral: false
  vault_as_collateral: false
```

これはvenue採用決定ではない。実際のvenue、account mode、API、規約が確定した時点で公式仕様を再検証する。

## 4. D01-U003 推奨: 保護済み純利益で生活Impactを判定

### 4.1 Primary metric

生活Impactは、市場riskから外れ、利用可能になった純利益で測る。

```text
impact_profit
= completed_external_profit_withdrawals
  + protected_profit_vault_balance
```

次を含めない。

- 初期元本または追加元本。
- Principal Recovery Vault。
- active machine balance。
- Reload Pool。
- Scale Reserve。
- unrealized PnL。
- internal transfer。
- 未確定fee/funding。
- 外部から追加した資金。

### 4.2 Vaultを二種類へ分ける

```text
Principal Recovery Vault
  初期元本の回収
  Impact profitへ数えない

Protected Profit Vault
  実現利益の保護分
  Impact profitへ数える
```

4倍到達時に回収する初期元本50%はPrincipal Recovery Vaultへ入れる。

```text
500 USD machine
-> 4x到達
-> 250 USDをPrincipal Recovery Vault
```

Rebase時に増加利益の50%を隔離する場合はProtected Profit Vaultへ入れる。

```text
増加利益 3,000 USD
-> 1,500 USDをnew operating capital
-> 1,500 USDをProtected Profit Vault
```

### 4.3 年間Impact目標

5,000 USD基準では次を固定する。

```text
anchor capital                 5,000 USD
monthly impact reference         800 USD
annual impact target           9,600 USD
annual impact ratio                 1.92
evaluation horizon                365 days
```

Primary estimand候補:

```text
P(
  protected net profit >= 9,600 USD
  within 365 days
)
```

Co-primary downside:

```text
P(
  Reload停止またはCapital Epoch停止が
  Impact到達より先に起きる
)
```

両方を報告し、Impact到達率が高いだけでは採用しない。

### 4.4 365日run中に目標を動かさない

Rebaseしても、開始済み365日runの9,600 USD目標は変更しない。

```yaml
impact_evaluation:
  target_locked_at_run_start: true
  horizon_days: 365
  anchor_operating_capital_usd: 5000
  target_protected_net_profit_usd: 9600
```

資金が増えたたびに目標を増やすと、成功条件が逃げ続ける。損失時に目標を下げると、失敗を成功へ変えられる。`gamma=0.5`は次のCapital Epochまたは次の365日契約のreporting targetへ適用する。

### 4.5 Profit認識の上限

Vaultへtransferしただけで、system全体の累積net profitを超えるImpact profitを認識してはならない。

```text
recognized_impact_profit
<= cumulative_system_net_profit
   - previously_recognized_impact_profit
```

外部追加資金、内部transfer、元本回収でImpactを作れないよう、各Vault creditに`economic_source`を持たせる。

## 5. Data不足への推奨回答

現行30 Event、5 Episodeでは次をBLOCKする。

```text
ML_DISCOVERY_READY = BLOCKED
TAIL_PROBABILITY_ESTIMABLE = false
CAMPAIGN_RUIN_ESTIMABLE = false
REAL_MARKET_ROBUSTNESS = NOT_ESTIMABLE
```

固定の最低Episode数を根拠なく置かない。CP0/CP6で次から必要数を逆算する。

- tail base rate。
- false survivor loss。
- false kill loss。
- minimum power。
- symbol/era/regime dependency。
- horizon overlap。
- Campaign ruin upper bound。
- fee/funding/execution scenario数。

データ不足はGate緩和で解決せず、`DEFER_DATA`へ分離する。DEFERには必要data、最大追加費用、次の反証実験、expiryを必須にする。

## 6. Venue・Marginへの推奨回答

初期の保守的simulation baselineは次とする。

```yaml
venue_baseline:
  product: crypto_perpetual_futures
  margin_mode: isolated
  auto_margin_replenishment: false
  cross_collateral: false
  profit_vault_as_collateral: false
  liquidation_as_stop_loss: false
  zero_cut_assumption: false
```

CP0/CP7でvenueごとに次を公式仕様からfreezeする。

- mark/index/lastとliquidation trigger。
- maintenance marginとrisk tier。
- isolated/cross/portfolio margin。
- insurance fundとADL。
- negative balance関連条件。
- stop triggerとfillの関係。
- minimum order、tick、quantity step。
- fee、funding、slippage。
- outage、delisting、contract変更。

一つのvenueの仕様を全Crypto Perpetual Futuresへ一般化しない。

## 7. 数値parameterへの推奨回答

### 7.1 Risk fraction

1%をreference baselineとし、全Gridを比較する。

```yaml
machine_risk:
  reference_baseline: 0.010
  comparison_grid: [0.005, 0.010, 0.015, 0.020, 0.030]
  stress_only: [0.050]
```

1%は最適値ではない。比較中心であり、全trialをledgerへ残す。

### 7.2 Ratchet

```yaml
ratchet:
  withdrawal_ratio_of_initial_balance: 0.5
  trigger_once_per_generation: true
  destination: principal_recovery_vault
  trigger_policy:
    target_10x: 4.0
    target_6x: 3.0
    target_3x: 2.0
    target_2x: 1.5
```

### 7.3 Rebase

```yaml
rebase:
  trigger_multiple: 1.6
  confirmation_hours: 24
  requires_all_positions_closed: true
  eligible_profit_redeployment_ratio: 0.5
  protected_profit_vault_ratio: 0.5
  existing_vault_redeployment: false
  applies_to_new_generations_only: true
```

### 7.4 Downscale

20%をreference baselineとし、15%、20%、25%を比較する。

```yaml
downscale:
  reference_drawdown: 0.20
  comparison_grid: [0.15, 0.20, 0.25]
```

これらはproduction値ではなく、事前固定したsimulation candidateである。

## 8. 今後の方向性統合への推奨

D02以降はD01へ直接混ぜず、独立文書として保存する。最終統合時に少なくとも次を比較する。

- 365日Impact到達率への限界増分。
- Impact到達前ruin率。
- false survivor、false kill。
- 必要dataとlicense。
- build、compute、artifact、operator費用。
- time-to-first-useful-rejection。
- 既存Kill chainとの適合。
- D01との相乗、重複、排他条件。

D01が先に書かれたという理由だけでD02以降より優先しない。ただし、ユーザー指定の「現行の一般的利益探索よりD01を重くする」は維持する。

## 9. 文書保存への推奨

U001〜U003の採否をD01へ反映した後、4件の既存plan文書と本recommendation文書だけを対象に、docs-onlyのlocal checkpoint commitを作ることを推奨する。

含めないもの:

- user-owned `AGENTS.md`差分。
- user-owned `.gitignore`差分。
- `.ai-work/`。
- runtime data。
- Python、schema、config、dependency。

branchはまだ不要で、pushもしない。

## 10. 推奨統合設定

```yaml
recommendation:
  id: D01-R01
  status: PENDING_USER_ADOPTION

campaign_target:
  basis: total_settled_generation_wealth
  formula: machine_balance + cumulative_generation_ratchet_withdrawals
  includes_unrealized_pnl: false

ratchet:
  trigger_once_per_generation: true
  withdrawal_ratio_of_initial_balance: 0.5
  destination: principal_recovery_vault

vault:
  principal_recovery_counts_as_impact_profit: false
  protected_profit_counts_as_impact_profit: true
  automatic_redeployment_allowed: false
  counts_toward_wealth_milestone: true
  counts_toward_rebase_eligible_equity: false
  can_become_trading_collateral: false

impact_evaluation:
  basis: protected_realized_net_profit
  includes:
    - protected_profit_vault
    - completed_external_profit_withdrawals
  excludes:
    - principal_recovery_vault
    - machine_working_balance
    - reload_pool
    - scale_reserve
    - unrealized_pnl
    - external_contributions
  horizon_days: 365
  anchor_operating_capital_usd: 5000
  target_protected_net_profit_usd: 9600
  target_locked_at_run_start: true

machine_risk:
  reference_baseline: 0.010
  comparison_grid: [0.005, 0.010, 0.015, 0.020, 0.030]
  stress_only: [0.050]

rebase:
  trigger_multiple: 1.6
  confirmation_hours: 24
  requires_all_positions_closed: true
  eligible_profit_redeployment_ratio: 0.5
  protected_profit_vault_ratio: 0.5
  existing_vault_redeployment: false
  applies_to_new_generations_only: true

downscale:
  reference_drawdown: 0.20
  comparison_grid: [0.15, 0.20, 0.25]
```

## 11. 採用時のD01更新内容

ユーザーがこの推奨を採用した場合だけ、D01本体を次のように更新する。

1. `D01-U001/U002/U003`を`POLICY_ADOPTED`へ変更する。
2. 10倍/10.5倍を「未決矛盾」から「棄却した代替案」へ移す。
3. Campaign成功式をtotal settled generation wealthへ統一する。
4. VaultをPrincipal RecoveryとProtected Profitへ分ける。
5. Rebase eligible equityから全Vaultを除外する。
6. Primary estimandをprotected realized net profitへ固定する。
7. 365日run開始時にImpact targetをfreezeする。
8. Test fixtureの期待値を+9R campaignへ戻す。
9. handoffと`.ai-work`の未決事項を解消済みへ更新する。

## 12. 残る未決事項

この推奨を採用しても、次は未決のまま残る。

- 資産帯別machine数とReload単位。
- minimum executable balance。
- max margin、notional、leverage、concurrent positions。
- Risk Cluster距離とQuarantine解除。
- maximum Campaign duration/trade count。
- Scale ReserveからReload Poolへ移せる条件。
- venue、jurisdiction、account/margin mode。
- 必要data source、期間、episode数、費用。
- Campaign Simulator Artifact Schema。
- 税、実際の生活出金、external cash-flowの扱い。
- D02以降との優先順位。

これらを合理的推測で埋めず、data、費用、実装範囲に応じてCP0または後続方向性統合で決める。

## 13. 非主張

この推奨は次を意味しない。

- 月16%または年9,600 USDを達成できる。
- 10倍Campaignに正の期待値がある。
- Crypto Perpetual Futuresが他市場より有利である。
- isolated marginやzero-cutが損失上限を保証する。
- XGBoost、LightGBM、Campaign Simulatorが実装済みである。
- Paper/live/cashの使用を許可する。

## 14. 次の判断

次に必要なのは、ユーザーによる次の一括判断である。

```text
D01-R01を採用する
または
修正点を指定する
```

採用が明示されるまでは、D01-U001/U002/U003を未決として維持し、master plan、SP_STATE、schema、codeへ固定しない。
