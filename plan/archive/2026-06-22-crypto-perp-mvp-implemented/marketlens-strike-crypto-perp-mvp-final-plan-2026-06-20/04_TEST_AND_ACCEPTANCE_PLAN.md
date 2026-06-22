<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# Test and Acceptance Plan

## 1. 原則

- 通常CIは外部networkなし。
- live testは通常CIに入れない。
- fixture、property、state machine、golden hand calculationを優先。
- 成功pathよりfailure/restart/retryを多くテストする。
- `PASS`はalphaやlive permissionを意味しない。

## 2. 通常コマンド

```bash
uv sync --dev --locked
uv run python -V
uv run pytest tests/crypto_perp -q
uv run pytest tests/strategy_inputs -q
uv run pytest tests/strategy_authoring -q
uv run pytest tests/strategy_workbench_viewer -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

## 3. Model / schema tests

全artifactで検査:

- valid Pydantic dumpがtracked JSON Schemaを通る。
- extra fieldを拒否。
- naive datetimeを拒否。
- bad hash、absolute path、secret pathを拒否。
- boundary permission trueを通常artifactで拒否。
- enum driftを検出。
- Decimal serialization roundtrip。

## 4. REST tests

`pytest-httpx`を使用。

Cases:

```text
200 valid
200 empty data
200 wrong shape
200 malformed numeric string
400 parameter error
401/403 unexpected auth requirement
429 then success
429 exhaustion
500 then success
500 exhaustion
timeout
transport error
malformed JSON
response code != HTTP status
clock skew
pagination overlap
pagination gap
pagination repeated cursor
```

Invariant:

- malformed/wrong shapeをsilent emptyへ変換しない。
- order create以外はbounded retry可。
- order createはsame clientOid query-first。

## 5. Universe tests

```text
new symbol
removed symbol
online -> limit_open
online -> restrictedAPI
fee change
price multiplier change
quantity multiplier change
min order change
funding interval change
launch/off time change
identical snapshot -> empty diff
partial provider response -> degraded, not mass removal
```

最後のcaseが重要。API partial responseを全銘柄delistと誤認しない。

## 6. Candle quality tests

```text
ascending/descending input
page overlap
missing interval
duplicate key
non-final current bar
latest bar revision
zero-volume valid bar
invalid OHLC
negative volume
mark/index/market source separation
timezone alignment
```

Gapは補間しない。zero-volume barとmissing barを分ける。

## 7. Event tests

- thresholdちょうど。
- 74h window 296 bars。
- recent/previous non-overlap。
- insufficient warm-up。
- BTC/ETH missing。
- broad market pump。
- near miss 80〜100%。
- dedupe bucket。
- max alerts/hour。
- future mutation differential。
- same event dataからdeterministic ID。

## 8. WebSocket / book tests

```text
subscribe ack
error frame
ping/pong
snapshot
incremental update
books1 repeated snapshot
duplicate trade id
duplicate book seq
out-of-order seq
gap
checksum pass
checksum fail
reconnect
resubscribe
SIGTERM graceful close
truncated gzip recovery
```

Property:

- bids descending、asks ascending。
- best bid < best ask。
- size=0 updateはlevel削除。
- checksum invalid後のbookはfillabilityに使わない。

## 9. Prospective decision tests

- decision source hash一致。
- decision_atがoutcome evidenceより前。
- replacement lineage。
- overwrite拒否。
- system/human decision分離。
- future outcome fieldsをdecisionへ混入させない。
- long/short/no-trade全enum。

## 10. Outcome tests

- horizon maturity。
- 1m high/low順序。
- 15mだけでstop/take両方hit -> ambiguous。
- MFE/MAE long/short符号。
- no-trade benchmark。
- market-adjusted return。
- missing event data -> INCONCLUSIVE。

## 11. Order preview property tests

Hypothesisで生成:

```text
price > 0
qty > 0
priceMultiplier
quantityMultiplier
minOrderAmount
minOrderQty
maxMarketOrderQty
side
leverage
```

Properties:

- normalized qtyがstepの整数倍。
- limit priceがtickの整数倍。
- normalized notionalがrequested capを超えない。
- minimum未満はblocked。
- wrong side/position mode組合せを拒否。
- clientOidは1〜32文字・許可文字のみ。

## 12. Order state machine

Hypothesis RuleBasedStateMachineを使用。

States:

```text
CREATED
SUBMITTED
UNKNOWN_AFTER_TIMEOUT
ACKNOWLEDGED
PARTIALLY_FILLED
FILLED
CANCEL_PENDING
CANCELED
REJECTED
CLOSE_PENDING
FLAT
BLOCKED_RECONCILIATION
```

Properties:

- final stateから再submitしない。
- filled qty <= requested qty。
- timeout後はquery-before-resubmit。
- close qty <= open position qty。
- reduceOnly closeが新規positionを作らない。
- reconciliation failure後は次entry禁止。

## 13. Cash ledger tests

Golden equation:

```text
net_cash
= withdrawals - deposits
+ liquidatable_equity
- external infra costs not already reflected
```

Trading fee/fundingがaccount equityへ既に反映されている場合、二重控除しない。ledgerはcash-flow viewとattribution viewを分ける。

Cases:

- multiple experiments/pods。
- ruined pod retained。
- deposit/withdrawal reversal。
- duplicate external reference。
- fee/funding attribution。
- current equity missing。

## 14. Replay/calibration tests

- long asks entry / bids exit。
- short bids entry / asks exit。
- partial depth。
- insufficient depth -> UNFILLABLE。
- no extrapolation。
- fee fallback reason code。
- multiple funding events。
- actual vs simulated bias。
- 5/10/25/50/100/250 USD grid。
- 5/15/30/60 sec latency。

## 15. External validation tests

### Tardis

- raw sample provenance/hash。
- parser golden output。
- reconstructed best bid/ask。
- depth VWAP hand calculation。

### pybotters spike

24h比較:

```text
messages_received
raw_messages_persisted
reconnect_count
gap_count
checksum_count
CPU/memory
implementation LOC
```

### Freqtrade sidecar

- lookahead differential。
- recursive startup candle differential。
- same event timestamps comparison。
- output is advisory only。

## 16. Network smoke

### Public

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-probe --network ...
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-refresh --through events ...
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-record --duration-minutes 10 ...
```

### Credentialed read-only

```bash
SIS_ALLOW_CREDENTIALED_READ=1 uv run sis crypto-perp-account-probe ...
```

Secretsはstdout/log/artifactに出ないことを確認。

## 17. Tiny live manual acceptance

前提checklistを満たした場合のみ。

1. 5 USD preview。
2. operatorがexact symbol/side/notional/clientOidを確認。
3. one-shot submit。
4. order/fill/position query。
5. reduceOnly close。
6. flat confirmation。
7. fee/PnL/latency artifact。
8. cash ledger append。

失敗時は次注文をblock。

## 18. Acceptance matrix

| ID | Requirement |
|---|---|
| A01 | network opt-in無しで外部接続しない |
| A02 | secretをartifact/logへ出さない |
| A03 | valid configがPydantic/Schema双方を通る |
| A04 | invalid boundary/naive datetime/unknown fieldを拒否 |
| A05 | Bitget v3 instruments/tickers/candles/OI/fundingをfixture normalize |
| A06 | docs/runtime limit差をprobe artifactへ保存 |
| A07 | partial universe responseをmass delistと誤認しない |
| A08 | add/remove/status/fee/precision/funding interval差分を検出 |
| A09 | non-final/revised/gap/duplicate candleを正しく扱う |
| A10 | event featureはfuture mutationに不変 |
| A11 | eventに売買方向を固定しない |
| A12 | near missを保存 |
| A13 | candidate-only recorderがraw-first |
| A14 | WS reconnect/gap/checksum/resyncをテスト |
| A15 | decisionはoutcome前にimmutable保存 |
| A16 | long/short/no-tradeを同じcontractで扱う |
| A17 | ambiguous OHLC順序をoptimistic解決しない |
| A18 | Hypothesis property testsを導入 |
| A19 | Tardis golden fixtureを導入 |
| A20 | pybotters採用はspike結果で決定 |
| A21 | Freqtradeは別process、GPLコードをcoreへコピーしない |
| A22 | credentialed read-onlyとwriteを別flag/commandにする |
| A23 | order previewがprecision/minimum/modeを検査 |
| A24 | clientOid idempotencyを保証 |
| A25 | tiny live notional上限25 USD |
| A26 | isolated margin・max open position 1 |
| A27 | create timeout時にquery-before-resubmit |
| A28 | closeはreduceOnly、flat reconciliation必須 |
| A29 | actual cash ledgerに全deposit/podを含める |
| A30 | replayはdirection-neutralでdepth外挿しない |
| A31 | actual vs simulated biasを報告 |
| A32 | reversal/continuation/no-tradeを同じevent setで比較 |
| A33 | insufficient dataをINCONCLUSIVEとする |
| A34 | existing Trade[XYZ]/NDX/Strategy Lab regression PASS |
| A35 | CLI catalog/current docs/full `scripts/check` PASS |

## 19. Completion evidence

各task出力:

```text
implementation manifest
focused pytest output
full gate output
CLI help snapshot
schema validation result
network smoke artifact（該当時のみ）
soak report（M05/M07）
manual live evidence（M09、承認時のみ）
```
