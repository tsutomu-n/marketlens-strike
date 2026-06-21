<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# Operations / Tiny Live Measurement Runbook

## 1. 毎日のpublic運用

```bash
uv run sis crypto-perp-refresh   --config configs/crypto_perp/bitget_personal_edge_lab.yaml   --through events

uv run sis crypto-perp-watchdeck   --config configs/crypto_perp/bitget_personal_edge_lab.yaml   --top 20
```

確認:

- universe diff。
- provider degraded。
- event数。
- data gaps。
- capture queue。
- operatorが読む上位event。

## 2. Human decision

Event発生後、outcomeを見る前に記録。

```bash
uv run sis crypto-perp-review   --event data/crypto_perp/events/<event-id>/event.json   --action REVERSAL_SHORT   --size-cap-usd 25   --reason catalyst_not_checked   --reviewer operator
```

`catalyst_not_checked`がある場合、actionableではなくshadow扱いにする。

## 3. Outcome settlement

```bash
uv run sis crypto-perp-settle   --event-id <event-id>   --through outcome
```

未成熟horizonはpending。後で再実行。

## 4. Credential setup checklist

Gitに保存しない。

```text
API key id
created_at
read permission
trade permission（M09だけ）
withdrawal disabled confirmed
IP allowlist confirmed
passphrase stored in local secret store
rotation date
revocation procedure tested
```

環境変数名:

```text
BITGET_API_KEY
BITGET_API_SECRET
BITGET_API_PASSPHRASE
```

## 5. Credentialed read-only probe

```bash
SIS_ALLOW_CREDENTIALED_READ=1 uv run sis crypto-perp-account-probe   --config configs/crypto_perp/bitget_personal_edge_lab.yaml
```

確認:

```text
account equity
available balance
position mode
margin mode
current positions
open orders
fee rate
```

既存position/orderがあればtiny live measurementをblock。

## 6. Tiny live前提

次をすべて満たす。

```text
別明示承認あり
lifetime experiment budget決定
measurement notional 5〜25 USD
isolated margin
leverage明示
max open positions 1
no existing position
no existing open order
withdrawal disabled API key
IP restriction
manual kill switch available
order preview PASS
```

## 7. Preview

```bash
uv run sis crypto-perp-order-preview   --event-id <event-id>   --side short   --notional-usd 5   --margin-mode isolated   --leverage 1
```

Operator確認:

```text
symbol
side
position side
qty
notional
reference price
min order
price/qty step
margin
fee
clientOid
expires_at
```

## 8. Arm and submit

実行例。実装後のhelpを正本とする。

```bash
SIS_ENABLE_TINY_LIVE_MEASUREMENT=1 uv run sis crypto-perp-live-measure   --preview data/crypto_perp/previews/<preview-id>.json   --confirm-live   --confirmation-phrase 'I ACCEPT THIS 5 USD LIVE MEASUREMENT'
```

規則:

- 1回だけ。
- automatic strategy daemonなし。
- create timeoutで再送しない。
- same clientOidをquery。
- fill確認後、予定holdingまたは即時calibration close。

## 9. Close

```bash
SIS_ENABLE_TINY_LIVE_MEASUREMENT=1 uv run sis crypto-perp-live-close   --measurement-id <measurement-id>   --reduce-only   --confirm-live
```

flatになるまでorder/fill/positionをreconcile。

## 10. Failure handling

### Order create timeout

```text
UNKNOWN_AFTER_TIMEOUT
-> query by clientOid
-> found: reconcile
-> not found after bounded checks: human review
-> blind resend禁止
```

### Partial fill

```text
record filled qty
cancel remainder
close filled qty reduceOnly
reconcile flat
```

### Close failure

```text
BLOCKED_RECONCILIATION
new entry permanently blocked
local high-priority alert
manual Bitget UI確認
```

### WS down

REST order queryとposition queryを正本にしてclose/reconcile。WSだけでposition stateを確定しない。

### Wrong account/mode

submit前block。自動でaccount modeを変更しない。

## 11. Cash ledger

Live measurement後:

```bash
uv run sis crypto-perp-cash-ledger-refresh
```

確認:

```text
deposits
withdrawals
realized PnL
fees
funding
current liquidatable equity
net cash
```

## 12. Capital policy

Example:

```text
capital ceiling: 3000 USD
first experiment budget: 300 USD
measurement notional: 5 -> 10 -> 25 USD
no automatic top-up
profit scale only after realized evidence
```

全損許容は、experiment budget内のmarket lossだけ。

## 13. Stop conditions

即停止:

- duplicate order。
- wrong side/symbol/qty。
- clientOid query不一致。
- position reconciliation不能。
- cross margin。
- API key leak疑い。
- fee/contract multiplier不明。
- provider schema drift。
- cash ledger不一致。

Strategy停止候補:

- actual cost後にshort/long両方負。
- 25 USDでもunfillable頻発。
- 最大損失1件が複数winnerを消す。
- operator timeが利益を超える。
- maker前提でしか利益がない。

## 14. Weekly review

```text
events detected
human decisions
matured outcomes
actual measurements
fill/rejection/latency
cash result
data gap
operator time
largest win/loss
replay bias
next experiment
```
