# 08. Ostium Probe Spec

## 目的

Ostiumで対象3商品の実装上の未確定項目を潰す。

## 対象

```txt
US500/SPX相当
NDX/Nasdaq相当
XAU/Gold相当
```

## 未確定項目

```txt
- 現行symbol名
- latest price取得可否
- trading hours取得可否
- bid/ask取得可否
- opening fee
- rolling / rollover fee
- OI cap
- dynamic spread対象有無
- liquidation reference price
- market close中のclose可否
```

## 使用OSS/SDK

- `ostium-python-sdk`
- `httpx`
- `pydantic`

## 最初に作るprobe

```bash
uv run sis probe ostium
```

## 出力

```txt
data/registry/ostium_instrument_registry.json
data/raw/quotes/ostium/YYYY-MM-DD.jsonl
```

## Probe項目

### 1. Feed一覧

SDKまたはRESTでfeed一覧を取得し、候補symbolを探す。

候補キーワード:

```txt
SPX
US500
S&P
NDX
NASDAQ
NAS100
XAU
GOLD
```

### 2. Latest price

対象symbolでlatest priceを取得できるか確認。

### 3. Trading hours

RWA asset schedule / trading hoursを取得。

### 4. Fees / caps

以下を取得。

```txt
opening_fee
rolling_fee
rollover_fee
OI cap
max leverage
```

### 5. Price reference

以下が取れるか確認。

```txt
bid
ask
mid
oracle price
price-after-impact
oracle timestamp
```

## 判定

GO:

```txt
- symbol確定
- latest price取得可能
- trading hours取得可能
- 少なくともexecution priceを構成可能
```

CONDITIONAL:

```txt
- symbol/priceは取れるがfee/liquidation referenceが未確定
```

NO-GO:

```txt
- 対象symbolが見つからない
- price取得不能
- session/market statusが不明すぎる
```
